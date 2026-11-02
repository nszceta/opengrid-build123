"""FEA of the openGrid Heavy blocking-pin Multiconnect snap (CalculiX).

Run (all cases, PETG):

    uv run --group sim examples/simulate_blocking_pin.py --case all

Pipeline: build123d shapes -> STEP -> gmsh (C3D10) -> CalculiX deck (NLGEOM static,
surface-to-surface penalty contact, ``*TIE`` thread proxy, plasticity) -> ccx ->
``.frd``/``.dat`` parsing -> matplotlib PNGs, ``summary.json``/``summary.md`` and an
``index.html`` gallery under ``output/simulation/blocking_pin/``.
See ``docs/blocking-pin-snap-simulation.md`` for the method, loads and results.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]
I64 = NDArray[np.int64]

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "output" / "simulation" / "blocking_pin"
CCX_DEFAULT = Path.home() / ".local" / "share" / "opengrid-fea" / "bin" / "ccx"

# --------------------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Material:
    name: str
    youngs: float  # MPa
    poisson: float
    yield_stress: float  # MPa
    interlayer: float  # MPa, tensile strength across layer lines
    hardening: float  # MPa, linear isotropic hardening slope vs. plastic strain

    @property
    def interlayer_strain(self) -> float:
        """Momentary strain at which sigma = interlayer strength (E-limited)."""
        return self.interlayer / self.youngs


PETG = Material("PETG", 2100.0, 0.38, 45.0, 25.0, 2100.0 / 50.0)
PLA = Material("PLA", 3500.0, 0.36, 55.0, 20.0, 3500.0 / 50.0)
# Elegoo PLA+ store spec: tensile 38 (X-Y) / 24 (Z) MPa, bending modulus 2979 (X-Y) / 2582 (Z) MPa.
# No tensile modulus is published; 2800 MPa sits between the two bending moduli.
PLA_PLUS = Material("PLA+", 2800.0, 0.36, 38.0, 24.0, 2800.0 / 50.0)
MATERIALS = {"PETG": PETG, "PLA": PLA, "PLA+": PLA_PLUS}

# --------------------------------------------------------------------------------------
# Mesh container + gmsh
# --------------------------------------------------------------------------------------

# gmsh tet10 -> CalculiX C3D10: swap the last two mid-edge nodes.
_GMSH_TO_CCX_TET10 = [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]
# CalculiX tetra face numbering (1-based corner nodes): S1 1-2-3, S2 1-4-2, S3 2-4-3, S4 3-4-1
_TET_FACES = np.array([[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]])


@dataclass
class Mesh:
    name: str
    nodes: F64  # (n, 3)
    tets: I64  # (m, 10) node indices, CalculiX order
    tris: I64  # (t, 6) boundary triangles, node indices
    tri_elem: I64 = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    tri_face: I64 = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    tri_normal: F64 = field(default_factory=lambda: np.zeros((0, 3)))
    tri_centroid: F64 = field(default_factory=lambda: np.zeros((0, 3)))
    tri_area: F64 = field(default_factory=lambda: np.zeros(0))

    @property
    def volume(self) -> float:
        return float(self.tet_volumes().sum())

    def tet_volumes(self) -> F64:
        p = self.nodes[self.tets[:, :4]]
        v = np.einsum("ij,ij->i", p[:, 1] - p[:, 0], np.cross(p[:, 2] - p[:, 0], p[:, 3] - p[:, 0])) / 6.0
        return v


def _face_keys(tri_corners: I64, nnodes: int) -> I64:
    s = np.sort(tri_corners, axis=1)
    k = np.int64(nnodes + 1)
    return (s[:, 0] * k + s[:, 1]) * k + s[:, 2]


def finalize_mesh(mesh: Mesh) -> Mesh:
    """Fix tet orientation, map boundary triangles to (element, face), compute normals."""

    nodes, tets = mesh.nodes, mesh.tets
    vol = mesh.tet_volumes()
    if np.any(vol < 0.0):
        raise ValueError(f"{mesh.name}: {int((vol < 0.0).sum())} inverted tetrahedra")
    n = len(nodes)
    tet_keys = np.concatenate([_face_keys(tets[:, f], n) for f in _TET_FACES])
    order = np.argsort(tet_keys)
    sorted_keys = tet_keys[order]
    tri_keys = _face_keys(mesh.tris[:, :3], n)
    pos = np.searchsorted(sorted_keys, tri_keys)
    if np.any(pos >= len(sorted_keys)) or np.any(sorted_keys[np.minimum(pos, len(sorted_keys) - 1)] != tri_keys):
        raise ValueError(f"{mesh.name}: boundary triangle without a matching tet face")
    flat = order[pos]
    m = len(tets)
    face = flat // m
    elem = flat % m
    mesh.tri_elem = elem.astype(np.int64)
    mesh.tri_face = (face + 1).astype(np.int64)
    p = nodes[mesh.tris[:, :3]]
    cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    area = 0.5 * np.linalg.norm(cross, axis=1)
    normal = cross / np.maximum(2.0 * area, 1e-30)[:, None]
    centroid = p.mean(axis=1)
    # Orient outward: away from the tet's fourth (opposite) vertex.
    opposite_local = np.array([3, 2, 0, 1])[face]
    opp = nodes[tets[elem, opposite_local]]
    flip = np.einsum("ij,ij->i", normal, opp - centroid) > 0.0
    normal[flip] *= -1.0
    mesh.tri_normal, mesh.tri_centroid, mesh.tri_area = normal, centroid, area
    return mesh


def mesh_step(
    shape: Any,
    name: str,
    workdir: Path,
    size_fn: Callable[[float, float, float], float],
    *,
    min_size: float,
    max_size: float,
    algorithm3d: int = 1,
) -> Mesh:
    """Mesh a build123d shape into quadratic tets (via STEP) with a position-dependent size."""

    import build123d as bd
    import gmsh

    workdir.mkdir(parents=True, exist_ok=True)
    step = workdir / f"{name}.step"
    bd.export_step(shape, str(step))
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("Mesh.MaxNumThreads1D", 1)
        gmsh.option.setNumber("Mesh.MaxNumThreads2D", 1)
        gmsh.option.setNumber("Mesh.MaxNumThreads3D", 1)
        gmsh.model.add(name)
        gmsh.model.occ.importShapes(str(step))
        gmsh.model.occ.synchronize()
        vols = gmsh.model.getEntities(3)
        if len(vols) != 1:
            raise ValueError(f"{name}: expected one volume, got {len(vols)}")
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeMin", min_size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", max_size)
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.option.setNumber("Mesh.Algorithm3D", algorithm3d)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.HighOrderOptimize", 1)
        gmsh.model.mesh.setSizeCallback(lambda _d, _t, x, y, z, _lc: size_fn(x, y, z))
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.setOrder(2)
        node_tags_raw, coords, _ = gmsh.model.mesh.getNodes()
        node_tags = np.asarray(node_tags_raw)
        _, tet_nodes = gmsh.model.mesh.getElementsByType(11)
        _, tri_nodes = gmsh.model.mesh.getElementsByType(9)
        lookup = np.full(int(node_tags.max()) + 1, -1, dtype=np.int64)
        lookup[node_tags.astype(np.int64)] = np.arange(len(node_tags))
        tets = lookup[np.asarray(tet_nodes, dtype=np.int64).reshape(-1, 10)][:, _GMSH_TO_CCX_TET10]
        tris = lookup[np.asarray(tri_nodes, dtype=np.int64).reshape(-1, 6)]
        nodes = np.asarray(coords, dtype=np.float64).reshape(-1, 3)
        used = np.unique(tets)
        remap = np.full(len(nodes), -1, dtype=np.int64)
        remap[used] = np.arange(len(used))
        mesh = Mesh(name, nodes[used], remap[tets], remap[tris])
    finally:
        gmsh.finalize()
    return finalize_mesh(mesh)


# --------------------------------------------------------------------------------------
# CalculiX deck
# --------------------------------------------------------------------------------------


@dataclass
class Body:
    name: str
    mesh: Mesh
    material: Material
    node0: int = 0  # global id of local node 0 is node0 + 1
    elem0: int = 0

    def gid(self, local: NDArray[np.int64] | int) -> Any:
        return local + self.node0 + 1

    @property
    def elset(self) -> str:
        return f"E_{self.name.upper()}"


@dataclass
class ContactPair:
    name: str
    slave: tuple[Body, NDArray[np.bool_]]  # (body, triangle mask)
    master: tuple[Body, NDArray[np.bool_]]
    friction: float = 0.3
    large_sliding: bool = False


@dataclass
class Tie:
    name: str
    slave: tuple[Body, NDArray[np.bool_]]
    master: tuple[Body, NDArray[np.bool_]]
    tolerance: float = 0.05


@dataclass
class StepSpec:
    """One *STEP. ``cload`` values are step-end magnitudes; ``boundary`` are step-end displacements."""

    load_scale: float  # step-end value of the load multiplier
    initial: float = 0.02
    minimum: float = 1e-6
    maximum: float = 0.25
    max_inc: int = 400


class Deck:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, *rows: str) -> None:
        self.lines.extend(rows)

    def ints(self, values: Sequence[int], per_line: int = 12) -> None:
        for i in range(0, len(values), per_line):
            self.lines.append(", ".join(str(v) for v in values[i : i + per_line]) + ",")

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def write_bodies(deck: Deck, bodies: Sequence[Body]) -> None:
    n0 = 0
    e0 = 0
    for b in bodies:
        b.node0, b.elem0 = n0, e0
        n0 += len(b.mesh.nodes)
        e0 += len(b.mesh.tets)
    for b in bodies:
        deck.add(f"*NODE, NSET=N_{b.name.upper()}")
        ids = b.gid(np.arange(len(b.mesh.nodes)))
        deck.lines.extend(
            f"{i}, {x:.7g}, {y:.7g}, {z:.7g}" for i, (x, y, z) in zip(ids.tolist(), b.mesh.nodes.tolist(), strict=True)
        )
    for b in bodies:
        deck.add(f"*ELEMENT, TYPE=C3D10, ELSET={b.elset}")
        eids = np.arange(len(b.mesh.tets)) + b.elem0 + 1
        gt = b.gid(b.mesh.tets)
        deck.lines.extend(f"{e}, " + ", ".join(map(str, row)) for e, row in zip(eids.tolist(), gt.tolist(), strict=True))
    seen: dict[str, Material] = {}
    for b in bodies:
        seen[b.material.name] = b.material
    for m in seen.values():
        deck.add(f"*MATERIAL, NAME={m.name}", "*ELASTIC", f"{m.youngs:g}, {m.poisson:g}", "*PLASTIC")
        deck.add(f"{m.yield_stress:g}, 0.", f"{m.yield_stress + m.hardening * 0.5:g}, 0.5")
    for b in bodies:
        deck.add(f"*SOLID SECTION, ELSET={b.elset}, MATERIAL={b.material.name}")


def surface_rows(body: Body, mask: NDArray[np.bool_]) -> list[str]:
    m = body.mesh
    e = m.tri_elem[mask] + body.elem0 + 1
    f = m.tri_face[mask]
    return [f"{a}, S{b}" for a, b in zip(e.tolist(), f.tolist(), strict=True)]


def write_springs(deck: Deck, bodies: Sequence[Body], dofs: Sequence[tuple[Body, int]], nodes: Sequence[int], k: float) -> int:
    """Weak grounded SPRING1 elements that stabilise rigid-body modes before contact closes."""

    first = sum(len(b.mesh.tets) for b in bodies) + 1
    eid = first
    for _body, dof in dofs:
        deck.add(f"*ELEMENT, TYPE=SPRING1, ELSET=E_SPR{dof}")
        for node in nodes:
            deck.add(f"{eid}, {node}")
            eid += 1
        deck.add(f"*SPRING, ELSET=E_SPR{dof}", f"{dof}", f"{k / len(nodes):.9e}")
    return eid - first


def write_surface(deck: Deck, name: str, body: Body, mask: NDArray[np.bool_]) -> None:
    deck.add(f"*SURFACE, NAME={name}")
    deck.lines.extend(surface_rows(body, mask))


def tri_node_ids(body: Body, mask: NDArray[np.bool_]) -> I64:
    return np.unique(body.mesh.tris[mask])


def write_nset(deck: Deck, name: str, body: Body, local_nodes: NDArray[np.int64]) -> None:
    deck.add(f"*NSET, NSET={name}")
    deck.ints(body.gid(np.unique(local_nodes)).tolist())


def consistent_face_loads(body: Body, mask: NDArray[np.bool_], total: Sequence[float]) -> dict[int, tuple[float, float, float]]:
    """Distribute a total force vector over triangles by area (corner 0, mid-edge 1/3 each)."""

    m = body.mesh
    area = m.tri_area[mask]
    if area.sum() <= 0.0:
        raise ValueError("empty load surface")
    w = area / area.sum()
    tris = m.tris[mask]
    out: dict[int, np.ndarray] = {}
    for tri, wi in zip(tris.tolist(), w.tolist(), strict=True):
        for node in tri[3:]:
            out.setdefault(node, np.zeros(3))
            out[node] += (wi / 3.0) * np.asarray(total, dtype=np.float64)
    return {int(k): (float(v[0]), float(v[1]), float(v[2])) for k, v in out.items()}


# --------------------------------------------------------------------------------------
# Running CalculiX and parsing results
# --------------------------------------------------------------------------------------


def ccx_path() -> Path:
    return Path(os.environ.get("CCX", str(CCX_DEFAULT))).expanduser()


@dataclass
class RunResult:
    returncode: int
    seconds: float
    converged: bool
    log_tail: str
    stopped: bool = False  # terminated by the caller once the result was decided (collapse lift reached)


def run_ccx(workdir: Path, job: str, threads: int, stop: Callable[[], bool] | None = None, poll: float = 20.0) -> RunResult:
    """Run ccx; ``stop`` is polled while it runs and terminates the job when it returns True."""

    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = str(threads)
    env["CCX_NPROC_EQUATION_SOLVER"] = str(threads)
    env["CCX_NPROC_RESULTS"] = str(threads)
    t0 = time.time()
    stopped = False
    with (workdir / f"{job}.log").open("w") as log:
        proc = subprocess.Popen([str(ccx_path()), job], cwd=workdir, env=env, stdout=log, stderr=subprocess.STDOUT)
        while True:
            try:
                proc.wait(timeout=poll)
                break
            except subprocess.TimeoutExpired:
                if stop is not None and stop():
                    stopped = True
                    proc.terminate()
                    proc.wait()
                    break
    text = (workdir / f"{job}.log").read_text(errors="replace")
    done = "Job finished" in text
    res = RunResult(proc.returncode, time.time() - t0, done and proc.returncode == 0, "\n".join(text.splitlines()[-25:]))
    res.stopped = stopped
    return res


_FRD_SETS = re.compile(r"^\s{2}100C")


@dataclass
class FrdResult:
    """Nodal fields per result set: ``fields[k][name]`` -> (node_ids, values)."""

    times: list[float] = field(default_factory=list)
    fields: list[dict[str, tuple[I64, F64]]] = field(default_factory=list)


_FLOAT = re.compile(r"[-+]?\d\.\d+E[-+]\d+")


def parse_frd(path: Path) -> FrdResult:
    """Parse the ASCII .frd nodal result blocks (fixed 12-character fields)."""

    res = FrdResult()
    if not path.exists():
        return res
    cur: dict[str, tuple[I64, F64]] | None = None
    name = ""
    ncomp = 0
    rows: list[str] = []
    in_block = False
    with path.open(errors="replace") as fh:
        for line in fh:
            if _FRD_SETS.match(line):
                cur = {}
                res.times.append(float(line[12:24]))
                res.fields.append(cur)
            elif cur is None:
                continue
            elif line.startswith(" -4"):
                name, ncomp = line.split()[1], 0
                rows, in_block = [], False
            elif line.startswith(" -5"):
                in_block = True
                if line.split()[1] != "ALL":  # the calculated |vector| component is not stored
                    ncomp += 1
            elif in_block and line.startswith(" -1"):
                rows.append(line)
            elif in_block and line.startswith(" -3"):
                if rows:
                    ids = np.array([int(r[3:13]) for r in rows], dtype=np.int64)
                    vals = np.array(_FLOAT.findall("".join(r[13:].rstrip("\n") for r in rows)), dtype=np.float64)
                    cur[name] = (ids, vals.reshape(len(rows), ncomp))
                in_block = False
                rows = []
    return res


@dataclass
class DatBlock:
    kind: str  # "disp" | "force" | "total_force" | other
    set_name: str
    time: float
    data: F64  # rows: [node, c1, c2, c3] or [fx, fy, fz]


_DAT_HEAD = re.compile(r"^\s*(?P<what>[a-z][a-z \(\),/]*?)\s+for set\s+(?P<set>\S+)\s+and time\s+(?P<t>\S+)", re.I)


def parse_dat(path: Path) -> list[DatBlock]:
    blocks: list[DatBlock] = []
    if not path.exists():
        return blocks
    cur: DatBlock | None = None
    rows: list[list[float]] = []

    def flush() -> None:
        nonlocal cur, rows
        if cur is not None and rows:
            cur.data = np.asarray(rows, dtype=np.float64)
            blocks.append(cur)
        cur, rows = None, []

    for line in path.read_text(errors="replace").splitlines():
        m = _DAT_HEAD.match(line)
        if m:
            flush()
            what = m.group("what").lower()
            kind = "disp" if "displacement" in what else "total_force" if "total force" in what else "force" if "force" in what else what
            cur = DatBlock(kind, m.group("set").upper(), float(m.group("t")), np.zeros((0, 0)))
            continue
        if cur is not None:
            parts = line.split()
            if not parts:
                continue
            try:
                rows.append([float(p) for p in parts])
            except ValueError:
                flush()
    flush()
    return blocks


def von_mises(s: F64) -> F64:
    sxx, syy, szz, sxy, syz, szx = (s[:, i] for i in range(6))
    return np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3.0 * (sxy**2 + syz**2 + szx**2)
    )


def max_principal(t: F64) -> F64:
    m = np.zeros((len(t), 3, 3))
    m[:, 0, 0], m[:, 1, 1], m[:, 2, 2] = t[:, 0], t[:, 1], t[:, 2]
    m[:, 0, 1] = m[:, 1, 0] = t[:, 3]
    m[:, 1, 2] = m[:, 2, 1] = t[:, 4]
    m[:, 0, 2] = m[:, 2, 0] = t[:, 5]
    return cast(F64, np.linalg.eigvalsh(m)[:, 2])


# --------------------------------------------------------------------------------------
# Validation cases (no board/snap geometry involved)
# --------------------------------------------------------------------------------------


@dataclass
class ValidationResult:
    name: str
    passed: bool
    metrics: dict[str, float]
    detail: str


def _boundary_mask_by_plane(mesh: Mesh, axis: int, value: float, tol: float = 1e-6) -> NDArray[np.bool_]:
    return cast(NDArray[np.bool_], np.all(np.abs(mesh.nodes[mesh.tris[:, :3]][:, :, axis] - value) < tol, axis=1))


def _base_deck(job: str) -> Deck:
    d = Deck()
    d.add(f"** {job}", "*HEADING", job)
    return d


def validate_cantilever(workdir: Path, threads: int, h: float = 0.4) -> ValidationResult:
    import build123d as bd

    length, width, thick, load = 10.0, 2.0, 0.8, 0.5
    mat = PETG
    beam = bd.Box(length, width, thick, align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER))
    mesh = mesh_step(beam, "beam", workdir, lambda *_: h, min_size=h * 0.5, max_size=h * 1.5)
    body = Body("beam", mesh, mat)
    d = _base_deck("cantilever")
    write_bodies(d, [body])
    clamp = np.unique(mesh.tris[_boundary_mask_by_plane(mesh, 0, 0.0)])
    tip_mask = _boundary_mask_by_plane(mesh, 0, length)
    write_nset(d, "NCLAMP", body, clamp)
    write_nset(d, "NTIP", body, np.unique(mesh.tris[tip_mask]))
    d.add("*BOUNDARY", "NCLAMP, 1, 3")
    d.add("*STEP", "*STATIC", "1., 1.")
    d.add("*CLOAD")
    for node, (fx, fy, fz) in consistent_face_loads(body, tip_mask, (0.0, 0.0, -load)).items():
        d.add(f"{int(body.gid(node))}, 3, {fz:.9g}")
    d.add("*NODE PRINT, NSET=NTIP", "U", "*NODE PRINT, NSET=NCLAMP, TOTALS=ONLY", "RF", "*END STEP")
    (workdir / "cantilever.inp").write_text(d.text())
    res = run_ccx(workdir, "cantilever", threads)
    blocks = parse_dat(workdir / "cantilever.dat")
    disp = next(b for b in blocks if b.kind == "disp")
    tip_uz = float(disp.data[:, 3].mean())
    rf = next((b for b in blocks if b.kind == "total_force"), None)
    rfz = float(rf.data[0][-1]) if rf is not None else math.nan
    inertia = width * thick**3 / 12.0
    eb = -load * length**3 / (3.0 * mat.youngs * inertia)
    # Timoshenko shear correction (rectangular section, kappa = 5/6) for reference.
    shear = -load * length / ((5.0 / 6.0) * width * thick * mat.youngs / (2.0 * (1.0 + mat.poisson)))
    err = abs(tip_uz - eb) / abs(eb)
    bal = abs(rfz - load) / load
    ok = res.converged and err <= 0.05 and bal <= 0.01
    return ValidationResult(
        "cantilever",
        ok,
        {
            "tip_uz_fea_mm": tip_uz,
            "tip_uz_euler_bernoulli_mm": eb,
            "tip_uz_timoshenko_mm": eb + shear,
            "error_vs_EB_pct": 100.0 * err,
            "elements": float(len(mesh.tets)),
            "elements_through_thickness": thick / h,
            "reaction_fz_N": rfz,
            "applied_N": load,
            "reaction_balance_error_pct": 100.0 * bal,
        },
        "Euler-Bernoulli tip deflection within 5 %, reaction within 1 %",
    )


def validate_contact(
    workdir: Path, threads: int, h: float = 0.8, gap: float = 0.0, spring_k: float = 0.0, initial: float = 0.1,
    kscale: float = 1.0, mu: float = 0.3, shear: float = 15.0, tag: str = "contact", lam: float = 0.002,
) -> ValidationResult:
    """Block pressed onto a block (initially touching); friction holds a sub-limit shear load (stick)."""

    import build123d as bd

    mat = PETG
    base = bd.Box(12, 12, 4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX))
    top = bd.Box(6, 6, 4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)).translate((0, 0, gap))
    mb = mesh_step(base, "cbase", workdir, lambda *_: h, min_size=h * 0.5, max_size=h * 1.5)
    mt = mesh_step(top, "ctop", workdir, lambda *_: h, min_size=h * 0.5, max_size=h * 1.5)
    b0, b1 = Body("base", mb, mat), Body("top", mt, mat)
    d = _base_deck("contact")
    write_bodies(d, [b0, b1])
    slave_mask = _boundary_mask_by_plane(mt, 2, gap)
    master_mask = _boundary_mask_by_plane(mb, 2, 0.0)
    fix_nodes = np.unique(mb.tris[_boundary_mask_by_plane(mb, 2, -4.0)])
    load_mask = _boundary_mask_by_plane(mt, 2, 4.0 + gap)
    write_surface(d, "S_TOP", b1, slave_mask)
    write_surface(d, "S_BASE", b0, master_mask)
    write_nset(d, "NFIX", b0, fix_nodes)
    write_nset(d, "NLOADED", b1, np.unique(mt.tris[load_mask]))
    kc = contact_stiffness(mat, h) * kscale
    d.add("*SURFACE INTERACTION, NAME=SI", "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR", f"{kc:g}")
    if mu > 0.0:
        d.add("*FRICTION", f"{mu:g}, {kc * lam:g}")
    d.add("*CONTACT PAIR, INTERACTION=SI, TYPE=SURFACE TO SURFACE", "S_TOP, S_BASE")
    if spring_k > 0.0:
        write_springs(d, [b0, b1], [(b1, 1), (b1, 2), (b1, 3)], b1.gid(np.unique(mt.tris[load_mask])[:1]).tolist(), spring_k)
    d.add("*BOUNDARY", "NFIX, 1, 3")
    d.add("*STEP, NLGEOM, INC=100", "*STATIC", f"{initial:g}, 1., 1e-6, 0.25")
    d.add("*CLOAD")
    for node, (fx, fy, fz) in consistent_face_loads(b1, load_mask, (shear, 0.0, -100.0)).items():
        g = int(b1.gid(node))
        d.add(f"{g}, 1, {fx:.9g}", f"{g}, 3, {fz:.9g}")
    d.add("*NODE PRINT, NSET=NFIX, TOTALS=ONLY", "RF", "*NODE PRINT, NSET=NLOADED", "U", "*END STEP")
    (workdir / f"{tag}.inp").write_text(d.text())
    res = run_ccx(workdir, tag, threads)
    blocks = parse_dat(workdir / f"{tag}.dat")
    rf = [b for b in blocks if b.kind == "total_force"]
    disp = [b for b in blocks if b.kind == "disp"]
    if not rf or not disp:
        return ValidationResult("contact", False, {}, "no output: " + res.log_tail)
    fx, fy, fz = (float(v) for v in rf[-1].data[0][-3:])
    ux, _uy, uz = (float(v) for v in disp[-1].data[:, 1:4].mean(axis=0))
    err_z = abs(fz - 100.0) / 100.0
    err_x = abs(fx + shear) / shear if shear else 0.0
    ok = res.converged and err_z <= 0.01 and err_x <= 0.01
    return ValidationResult(
        "contact",
        ok,
        {
            "reaction_fz_N": fz,
            "reaction_fx_N": fx,
            "applied_fz_N": -100.0,
            "applied_fx_N": shear,
            "balance_error_z_pct": 100.0 * err_z,
            "balance_error_x_pct": 100.0 * err_x,
            "top_block_uz_mm": uz,
            "top_block_ux_mm": ux,
            "contact_stiffness_N_per_mm3": kc,
        },
        "reaction force equals applied load within 1 % through penalty contact with friction (stick)",
    )


def validate_tie(workdir: Path, threads: int, h: float = 0.8) -> ValidationResult:
    """Coaxial plug tied into a sleeve (the thread-proxy mechanism); pull the plug out."""

    import build123d as bd

    mat = PETG
    plug = bd.Cylinder(5.0, 6.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    sleeve = bd.Cylinder(9.0, 3.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)) - bd.Cylinder(
        5.0, 3.0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    mp = mesh_step(plug, "tplug", workdir, lambda *_: h, min_size=h * 0.5, max_size=h * 1.5)
    ms = mesh_step(sleeve, "tsleeve", workdir, lambda *_: h * 1.3, min_size=h * 0.5, max_size=h * 2.0)
    bp, bs = Body("plug", mp, mat), Body("sleeve", ms, mat)
    d = _base_deck("tie")
    write_bodies(d, [bp, bs])
    cyl_p = cast(NDArray[np.bool_], np.abs(np.hypot(mp.tri_centroid[:, 0], mp.tri_centroid[:, 1]) - 5.0) < 0.05) & (mp.tri_centroid[:, 2] < 3.0)
    cyl_s = cast(NDArray[np.bool_], np.abs(np.hypot(ms.tri_centroid[:, 0], ms.tri_centroid[:, 1]) - 5.0) < 0.05)
    write_surface(d, "S_PLUG", bp, cyl_p)
    write_surface(d, "S_SLEEVE", bs, cyl_s)
    d.add("*TIE, NAME=T1, POSITION TOLERANCE=0.05", "S_SLEEVE, S_PLUG")
    fix = np.unique(ms.tris[_boundary_mask_by_plane(ms, 2, 0.0)])
    write_nset(d, "NFIX", bs, fix)
    top_mask = _boundary_mask_by_plane(mp, 2, 6.0)
    write_nset(d, "NTOP", bp, np.unique(mp.tris[top_mask]))
    d.add("*BOUNDARY", "NFIX, 1, 3")
    # Radial fixity of the free plug end keeps the problem well-posed without constraining axial slip.
    d.add("*STEP", "*STATIC", "1., 1.", "*CLOAD")
    for node, (_fx, _fy, fz) in consistent_face_loads(bp, top_mask, (0.0, 0.0, 50.0)).items():
        d.add(f"{int(bp.gid(node))}, 3, {fz:.9g}")
    d.add("*NODE PRINT, NSET=NFIX, TOTALS=ONLY", "RF", "*NODE PRINT, NSET=NTOP", "U", "*END STEP")
    (workdir / "tie.inp").write_text(d.text())
    res = run_ccx(workdir, "tie", threads)
    blocks = parse_dat(workdir / "tie.dat")
    rf = [b for b in blocks if b.kind == "total_force"]
    disp = [b for b in blocks if b.kind == "disp"]
    if not rf or not disp:
        return ValidationResult("tie", False, {}, "no output: " + res.log_tail)
    fz = float(rf[-1].data[0][-1])
    uz_top = float(disp[-1].data[:, 3].mean())
    # Hand estimate: plug elastic stretch over 6 mm under 50 N vs rigid-tie 3 mm engaged length (upper bound).
    stretch_free = 50.0 * 6.0 / (mat.youngs * math.pi * 25.0)
    err = abs(fz + 50.0) / 50.0
    ok = res.converged and err <= 0.01 and uz_top > 0.0
    return ValidationResult(
        "tie",
        ok,
        {
            "reaction_fz_N": fz,
            "applied_fz_N": 50.0,
            "balance_error_pct": 100.0 * err,
            "plug_top_uz_mm": uz_top,
            "free_plug_stretch_estimate_mm": stretch_free,
        },
        "*TIE transmits the full axial load into the fixed sleeve (reaction within 1 %)",
    )


def contact_stiffness(mat: Material, h: float) -> float:
    """Penalty slope K [N/mm^3] of the linear pressure-overclosure law: ~10x the element stiffness E/h."""

    return 10.0 * mat.youngs / h


# --------------------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------------------

BOARD_WIDTH = 3  # cells per side of the board patch
CLAMP_TOL = 0.05
SYM_TOL = 1e-6
SINGULAR_DISTANCE = 0.5  # mm (~1.25 elements in the legs); nodes closer than this to a sharp edge are excluded from "robust" peaks
SHARP_EDGE_DEG = 30.0


@dataclass(frozen=True)
class CaseSpec:
    name: str
    title: str
    kind: str  # "ins" | "service" | "overload"
    material: str = "PETG"
    shank: bool = True
    blocking_clearance: float | None = None
    snap_overrides: tuple[tuple[str, float], ...] = ()
    pull: float = 0.0  # final axial pull per snap [N] (service)
    shear: float = 0.0  # final shear (-y) per snap [N] (service)
    levels: tuple[float, ...] = ()  # overload: pull level at the end of each step [N]
    mesh_scale: float = 1.0
    friction: float = 0.3
    board_e_scale: float = 1.0  # board modulus multiplier (stiff-board evidence case only)
    radial: bool = False  # insertion fallback: snap alone, ledges displaced radially to clear the lip (no contact)
    k_scale: float = 1.0  # multiplies the penalty slope K
    stick_ratio: float = 0.002  # friction stick slope / K (a small slope converges much better in ccx)
    ins_start: float = 2.7  # insertion: initial height of the snap above the seated position [mm]

    @property
    def symmetry(self) -> str:
        return "half" if self.shear > 0.0 else "quarter"


def overload_levels() -> tuple[float, ...]:
    """Pull level [N] at the end of each overload step (50 N steps through 400 N, then coarser to 1500 N)."""

    return (50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0, 500.0, 600.0, 800.0, 1000.0, 1250.0, 1500.0)


def case_registry() -> dict[str, list[CaseSpec]]:
    """Case name (CLI) -> specs to run; ``all`` covers every PLAN case."""

    ovl = overload_levels()
    reg: dict[str, list[CaseSpec]] = {
        # Contact insertion at mesh 1.4 (mu 0.3, penalty x0.3) gives force and stroke; the strain / sigma_zz gate comes from INS-R.
        "INS": [CaseSpec("INS", "Insertion (no screw), contact, mu 0.3", "ins", shank=False, k_scale=0.3, mesh_scale=1.4)],
        "INSR": [
            CaseSpec("INS-R", "Insertion, radial-displacement bound (snap alone), mesh 1.0", "ins", shank=False, radial=True),
            CaseSpec("INS-R-fine", "Insertion, radial-displacement bound (snap alone), mesh 0.7", "ins", shank=False, radial=True, mesh_scale=0.7),
        ],
        "SVC-A": [CaseSpec("SVC-A", "Service: 100 N axial pull, mu 0.3", "service", pull=100.0)],
        "SVC-C": [CaseSpec("SVC-C", "Service: 100 N pull + 25 N shear, mu 0.3", "service", pull=100.0, shear=25.0)],
        "OVL": [CaseSpec("OVL", "Overload: pull to collapse, mu 0.3", "overload", levels=ovl)],
        "UNB": [CaseSpec("UNB", "Overload, shank removed (unblocked), mu 0.3", "overload", shank=False, levels=(5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0, 75.0, 100.0, 150.0, 200.0, 300.0))],
        "SENS": [
            CaseSpec(f"SENS-{int(round(c * 100)):03d}", f"Overload, blocking clearance {c:.2f}, mu 0.3", "overload", blocking_clearance=c, levels=ovl)
            for c in (0.10, 0.20)
        ],
        "PLA": [
            CaseSpec("PLA-INS", "Insertion, PLA, mu 0.3", "ins", material="PLA", shank=False, k_scale=0.3, mesh_scale=1.4),
            CaseSpec("PLA-SVC-A", "Service 100 N, PLA, mu 0.3", "service", material="PLA", pull=100.0),
        ],
        # Frictionless (mu 0) mesh-convergence study of the service case: 1.4 / 1.0 / 0.7.
        "MESH": [
            CaseSpec(f"SVC-A-mesh{int(round(10 * sc)):02d}", f"Service 100 N, mu 0, mesh scale {sc}", "service", pull=100.0, friction=0.0, mesh_scale=sc)
            for sc in (1.4, 1.0, 0.7)
        ],
        # Non-gated evidence cases (bounds): frictionless collapse and the SVC-C lift decomposition.
        "BOUND": [
            CaseSpec("OVL-mu0", "Overload, frictionless bound (not gated), mesh 1.4", "overload", friction=0.0, levels=ovl, mesh_scale=1.4),
            CaseSpec("SVC-C-mu0", "Service 100 N + 25 N shear, frictionless bound (not gated), mesh 1.4", "service", pull=100.0, shear=25.0, friction=0.0, mesh_scale=1.4),
            CaseSpec("SVC-C-nogap", "SVC-C with blocking_clearance 0 and seat_clearance 0 (non-printable lower bound), mesh 1.4", "service", pull=100.0, shear=25.0, mesh_scale=1.4, blocking_clearance=0.0, snap_overrides=(("seat_clearance", 0.0),)),
            CaseSpec("SVC-C-stiffboard", "SVC-C with board modulus x100 (how much lift is board bending), mesh 1.4", "service", pull=100.0, shear=25.0, mesh_scale=1.4, board_e_scale=100.0),
        ],
    }
    return reg


@dataclass
class Geometry:
    board: Any
    snap: Any
    screw: Any | None
    snap_cfg: Any
    screw_cfg: Any
    shift_z: float  # snap/screw lift relative to the seated position [mm]
    board_shift: float  # board_thickness - snap height: seated offset of the snap frame in the board frame


def _heavy_board(width: int) -> Any:
    from opengrid_build123.opengrid import BoardKind, ChamferMode, GridConfig, ScrewMounting, build_open_grid

    return build_open_grid(
        GridConfig(
            kind=BoardKind.HEAVY,
            board_width=width,
            board_height=width,
            chamfers=ChamferMode.NONE,
            connector_holes=False,
            screw_mounting=ScrewMounting.NONE,
        )
    )


def _make_snap_screw(spec: CaseSpec, shift: tuple[float, float, float]) -> tuple[Any, Any | None, Any, Any]:
    """Snap and screw in the board frame at the seated position plus ``shift`` (real builders, thread proxy)."""

    import build123d as bd
    from opengrid_build123 import opengrid as og

    snap_cfg = replace(og.BlockingPinSnapConfig(), **dict(spec.snap_overrides))
    clearance = {} if spec.blocking_clearance is None else {"blocking_clearance": spec.blocking_clearance}
    screw_cfg = replace(og.MulticonnectBlockingScrewConfig(snap=snap_cfg), **clearance)
    seat = snap_cfg.board_thickness - snap_cfg.height
    snap = og._blocking_pin_snap_shape(snap_cfg, thread_proxy=True)
    screw = None
    if spec.kind != "ins":
        screw = og._multiconnect_blocking_screw_shape(screw_cfg, thread_proxy=True)
        screw = screw.rotate(bd.Axis.X, 180.0).translate((0.0, 0.0, snap_cfg.height + screw_cfg.head.total_height))
        if not spec.shank:
            radius = og._blocking_thread_proxy_radius(snap_cfg.threads)
            span = snap_cfg.height - snap_cfg.hub_height + 0.05
            tube = bd.Cylinder(snap_cfg.snap_body.width, span, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)) - bd.Cylinder(
                radius, span, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
            )
            screw = screw - tube.translate((0.0, 0.0, snap_cfg.hub_height))
    offset = (shift[0], shift[1], shift[2] + seat)
    snap = snap.translate(offset)
    if screw is not None:
        screw = screw.translate(offset)
    return snap, screw, snap_cfg, screw_cfg


_LIFT_CACHE: dict[tuple[tuple[str, float], ...], float] = {}


def first_contact_lift(spec: CaseSpec) -> float:
    """Smallest vertical lift of the (screw-less) snap from its seated position at which it touches the board.

    The ledges sit 0.05 mm (normal) below the lip ramp when seated; the model starts with the snap lifted by
    this amount so the first contact is closed and the static problem is well posed. The free play is added
    back when the lift is reported.
    """

    key = spec.snap_overrides
    if key in _LIFT_CACHE:
        return _LIFT_CACHE[key]
    probe = replace(spec, kind="ins")
    board1 = _heavy_board(1)
    lo, hi = 0.0, 0.5

    def overlap(d: float) -> float:
        snap, _s, _c, _k = _make_snap_screw(probe, (0.0, 0.0, d))
        try:
            common = snap & board1
            return float(sum(s.volume for s in common.solids()))
        except Exception:
            return 0.0

    if overlap(hi) <= 1e-7:
        raise ValueError(f"snap does not touch the board within {hi} mm of lift")
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        if overlap(mid) > 1e-7:
            hi = mid
        else:
            lo = mid
    _LIFT_CACHE[key] = lo
    return lo


def build_geometry(spec: CaseSpec, workdir: Path) -> Geometry:
    """Real builders -> board / snap / screw in the board frame, in their initial (just-touching) position."""

    import build123d as bd

    if spec.kind == "ins":
        shift = (0.0, 0.0, 0.0 if spec.radial else spec.ins_start)
    else:
        shift = (0.0, 0.0, first_contact_lift(spec))
    snap, screw, snap_cfg, screw_cfg = _make_snap_screw(spec, shift)
    board = _heavy_board(BOARD_WIDTH)

    def cut(shape: Any) -> Any:
        xmax = 1.0e3
        if spec.symmetry == "quarter":
            box = bd.Box(xmax, xmax, xmax, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.CENTER))
        else:
            box = bd.Box(xmax, 2 * xmax, xmax, align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER))
        out = shape & box
        solids = out.solids()
        if len(solids) != 1:
            raise ValueError(f"symmetry cut produced {len(solids)} solids")
        return solids[0]

    mult = 4.0 if spec.symmetry == "quarter" else 2.0
    cut_parts: dict[str, Any] = {}
    for name, full in (("board", board), ("snap", snap), ("screw", screw)):
        if full is None:
            cut_parts[name] = None
            continue
        part = cut(full)
        rel = abs(part.volume * mult - full.volume) / full.volume
        if rel > 2e-3:
            raise ValueError(f"{name}: symmetry-cut volume mismatch {rel:.2e}; model is not symmetric")
        cut_parts[name] = part
    return Geometry(cut_parts["board"], cut_parts["snap"], cut_parts["screw"], snap_cfg, screw_cfg, shift[2], snap_cfg.board_thickness - snap_cfg.height)


# --------------------------------------------------------------------------------------
# Meshing the case geometry
# --------------------------------------------------------------------------------------


def _blend(fine: float, coarse: float, dist: float, grad: float = 0.5) -> float:
    return min(coarse, fine + grad * max(0.0, dist))


def size_functions(spec: CaseSpec, geo: Geometry) -> dict[str, tuple[Callable[[float, float, float], float], float, float]]:
    """Per-body gmsh size fields (callbacks of board-frame position) -> (fn, min, max)."""

    sc = spec.mesh_scale
    cfg = geo.snap_cfg
    ri = cfg.leg_bore_radius
    web = cfg.web_thickness
    hub = cfg.hub_height
    zoff = geo.board_shift + geo.shift_z
    half = cfg.snap_body.width / 2.0
    lip_zone_z = cfg.board_thickness - 5.6  # board z above which the lip/ramp/groove top is refined
    hypot = math.hypot

    leg_half = cfg.leg_width / 2.0 + cfg.leg_slot_width + 0.5
    lip_r = 12.5  # board lip radius (side), see PLAN board table
    corner_s = 14.23  # board corner chamfer, diagonal radius at z 12.4

    def snap_size(x: float, y: float, z: float) -> float:
        zs = z - zoff
        r = hypot(x, y)
        u = min(abs(x), abs(y))  # distance from the nearest leg axis
        far = max(0.0, u - leg_half)  # distance into a corner post
        if zs < web + 1.2 and r > ri - 0.4 and u < leg_half + 0.3:
            return 0.32 * sc  # leg roots and slot bottoms
        if r > ri - 0.45:
            top_zone = zs > cfg.height - 2.6  # pads / depth stop and ledge zone
            if u < leg_half:
                return 0.4 * sc
            return _blend(0.9 if top_zone else 1.1, 1.8, far, 0.8) * sc
        if zs < hub + 0.6 and r > cfg.sleeve_outer_radius - 0.7:
            return 0.6 * sc  # annular relief and sleeve wall
        return _blend(0.6, 1.8, (ri - 0.45) - r, 0.6) * sc

    def screw_size(x: float, y: float, z: float) -> float:
        zs = z - zoff
        r = hypot(x, y)
        if zs > cfg.height + 0.2:
            return 1.0 * sc  # head
        skin = (ri - float(geo.screw_cfg.blocking_clearance)) - r
        return _blend(0.65, 2.0, skin, 0.5) * sc

    def board_size(x: float, y: float, z: float) -> float:
        ax, ay = abs(x), abs(y)
        m, u = max(ax, ay), min(ax, ay)
        s = (ax + ay) * math.sqrt(0.5)
        dz = max(0.0, lip_zone_z - z)
        d_lip = hypot(hypot(max(0.0, lip_r - m, m - (lip_r + 1.3)), max(0.0, u - (leg_half + 0.8))), dz)
        d_cor = hypot(hypot(max(0.0, corner_s - 0.2 - s, s - (corner_s + 1.6)), max(0.0, 5.5 - u)), max(0.0, 10.5 - z))
        return min(_blend(0.5, 6.0, d_lip, 0.6), _blend(0.75, 6.0, d_cor, 0.6)) * sc

    return {
        "snap": (snap_size, 0.1 * sc, 1.6 * sc),
        "screw": (screw_size, 0.1 * sc, 2.2 * sc),
        "board": (board_size, 0.1 * sc, 6.5 * sc),
    }


def _radial(mesh: Mesh) -> tuple[F64, F64]:
    c = mesh.tri_centroid
    rc = np.hypot(c[:, 0], c[:, 1])
    rhat = np.zeros_like(c)
    rhat[:, 0] = c[:, 0] / np.maximum(rc, 1e-12)
    rhat[:, 1] = c[:, 1] / np.maximum(rc, 1e-12)
    return rc, cast(F64, np.einsum("ij,ij->i", mesh.tri_normal, rhat))


def _on_cylinder(mesh: Mesh, radius: float, tol: float = 0.02) -> NDArray[np.bool_]:
    """Triangles whose six nodes (corners and mid-edge) all lie on the cylinder r = radius about the z axis."""

    p = mesh.nodes[mesh.tris]
    return cast(NDArray[np.bool_], np.all(np.abs(np.hypot(p[:, :, 0], p[:, :, 1]) - radius) < tol, axis=1))


def _on_symmetry_plane(mesh: Mesh, symmetry: str) -> NDArray[np.bool_]:
    p = mesh.nodes[mesh.tris[:, :3]]
    on_x = np.all(np.abs(p[:, :, 0]) < SYM_TOL, axis=1)
    if symmetry == "half":
        return cast(NDArray[np.bool_], on_x)
    on_y = np.all(np.abs(p[:, :, 1]) < SYM_TOL, axis=1)
    return cast(NDArray[np.bool_], on_x | on_y)


@dataclass
class Model:
    spec: CaseSpec
    geo: Geometry
    bodies: dict[str, Body]
    zoff: float
    pairs: list[ContactPair]
    ties: list[Tie]
    masks: dict[str, NDArray[np.bool_]]  # named triangle masks (keyed "<body>:<name>")
    clamp_nodes: I64
    notes: dict[str, float] = field(default_factory=dict)


def save_mesh(mesh: Mesh, path: Path) -> None:
    np.savez_compressed(path, nodes=mesh.nodes, tets=mesh.tets, tris=mesh.tris)


def load_mesh(name: str, path: Path) -> Mesh:
    z = np.load(path)
    return finalize_mesh(Mesh(name, z["nodes"], z["tets"], z["tris"]))


def build_model(spec: CaseSpec, workdir: Path, log: Callable[[str], None], reuse_mesh: bool = False) -> Model:
    from opengrid_build123 import opengrid as og

    t0 = time.time()
    geo = build_geometry(spec, workdir)
    log(f"  geometry built ({time.time() - t0:.1f} s), lift to first contact {geo.shift_z:.4f} mm")
    sizes = size_functions(spec, geo)
    material = MATERIALS[spec.material]
    bodies: dict[str, Body] = {}
    for name in ("board", "snap", "screw"):
        shape = getattr(geo, name)
        if shape is None:
            continue
        t1 = time.time()
        fn, lo, hi = sizes[name]
        saved = workdir / "geometry" / f"{name}.mesh.npz"
        if reuse_mesh and saved.exists():
            mesh = load_mesh(name, saved)
        else:
            mesh = mesh_step(shape, name, workdir / "geometry", fn, min_size=lo, max_size=hi)
            save_mesh(mesh, saved)
        body_mat = material if (name != "board" or spec.board_e_scale == 1.0) else replace(material, name=f"{material.name}_E{spec.board_e_scale:g}", youngs=material.youngs * spec.board_e_scale)
        bodies[name] = Body(name, mesh, body_mat)
        log(f"  mesh {name}: {len(mesh.nodes)} nodes, {len(mesh.tets)} tets ({time.time() - t1:.1f} s)")
    cfg = geo.snap_cfg
    zoff = geo.board_shift + geo.shift_z
    hub, height, ri = cfg.hub_height, cfg.height, cfg.leg_bore_radius
    proxy = og._blocking_thread_proxy_radius(cfg.threads)
    masks: dict[str, NDArray[np.bool_]] = {}
    pairs: list[ContactPair] = []
    ties: list[Tie] = []
    board, snap = bodies["board"], bodies["snap"]
    bm, sm = board.mesh, snap.mesh
    sym_b = _on_symmetry_plane(bm, spec.symmetry)
    sym_s = _on_symmetry_plane(sm, spec.symmetry)
    bc = bm.tri_centroid
    cell = np.maximum(np.abs(bc[:, 0]), np.abs(bc[:, 1]))
    masks["board:lip"] = (cell <= cfg.snap_body.width / 2.0 + 1.8) & (bc[:, 2] >= cfg.board_thickness - 6.0) & (bm.tri_normal[:, 2] < 0.95) & ~sym_b
    sc_ = sm.tri_centroid
    srad, snrad = _radial(sm)
    szs = sc_[:, 2] - zoff
    masks["snap:outer"] = (szs >= height - 4.6) & (srad >= ri + 0.35) & (np.abs(sm.tri_normal[:, 2]) < 0.95) & ~sym_s
    if not spec.radial:
        pairs.append(ContactPair("LEDGE_LIP", (snap, masks["snap:outer"]), (board, masks["board:lip"]), spec.friction))
    masks["snap:bore"] = (szs >= hub - 0.05) & (srad >= 9.0) & (srad <= ri + 0.3) & (snrad < -0.3) & ~sym_s
    masks["snap:stop"] = (np.abs(szs - hub) < 0.02) & (sm.tri_normal[:, 2] > 0.9) & (srad >= proxy - 0.2) & ~sym_s
    masks["snap:thread"] = _on_cylinder(sm, proxy) & (szs <= hub + 0.03) & ~sym_s
    if "screw" in bodies:
        screw = bodies["screw"]
        cm = screw.mesh
        cc = cm.tri_centroid
        crad, _cnrad = _radial(cm)
        czs = cc[:, 2] - zoff
        sym_c = _on_symmetry_plane(cm, spec.symmetry)
        masks["screw:shank"] = (czs >= hub - 0.1) & (czs <= height + 0.05) & (crad >= 8.8) & (np.abs(cm.tri_normal[:, 2]) < 0.9) & ~sym_c
        masks["screw:stop"] = (np.abs(czs - hub) < 0.02) & (cm.tri_normal[:, 2] < -0.9) & (crad >= proxy - 0.2) & ~sym_c
        masks["screw:thread"] = _on_cylinder(cm, proxy) & (czs >= 0.15) & (czs <= hub + 0.03) & ~sym_c
        masks["screw:head"] = (
            (czs >= height + 0.45) & (czs <= height + spec_head_cone_top(geo) + 0.05) & (crad >= proxy - 0.1) & (cm.tri_normal[:, 2] < -0.5) & (crad <= geo.screw_cfg.head.large_diameter / 2.0 + 0.05)
        )
        if masks["screw:shank"].any():
            pairs.append(ContactPair("SHANK_BORE", (screw, masks["screw:shank"]), (snap, masks["snap:bore"]), spec.friction))
        if masks["screw:stop"].any():
            pairs.append(ContactPair("STOP_SLEEVE", (screw, masks["screw:stop"]), (snap, masks["snap:stop"]), spec.friction))
        ties.append(Tie("THREAD", (screw, masks["screw:thread"]), (snap, masks["snap:thread"])))
        cm_nodes = cm.nodes
        del cm_nodes
    xmax = float(bm.nodes[:, 0].max())
    ymax = float(np.abs(bm.nodes[:, 1]).max())
    nb = bm.nodes
    clamp = (nb[:, 0] >= xmax - CLAMP_TOL) | (np.abs(nb[:, 1]) >= ymax - CLAMP_TOL)
    return Model(spec, geo, bodies, zoff, pairs, ties, masks, np.nonzero(clamp)[0].astype(np.int64))


def spec_head_cone_top(geo: Geometry) -> float:
    h = geo.screw_cfg.head
    return h.top_height + h.middle_height


# --------------------------------------------------------------------------------------
# Deck assembly for a case
# --------------------------------------------------------------------------------------

INS_STEPS = 20  # insertion frames
INS_RADIAL_STEPS = 4
SERVICE_STEPS = 4  # service load frames
SPRING_K = 2.0  # N/mm, grounded stabiliser springs at one head node (< 2 % of the service load at 0.1 mm)
SAMPLE_NODES = 24


def _sample(ids: NDArray[np.int64], n: int) -> NDArray[np.int64]:
    ids = np.unique(ids)
    if len(ids) <= n:
        return ids
    return ids[np.linspace(0, len(ids) - 1, n).astype(np.int64)]


@dataclass
class DeckInfo:
    amplitude: list[tuple[float, float]]  # total time -> load [N] (pull) or stroke fraction
    nsets: dict[str, tuple[str, NDArray[np.int64]]]  # nset name -> (body, local node ids)
    nsteps: int
    quarter_factor: float
    spring_node: int | None = None


def write_case(model: Model, workdir: Path, threads: int) -> tuple[Path, DeckInfo]:
    spec, geo = model.spec, model.geo
    cfg = geo.snap_cfg
    mat = MATERIALS[spec.material]
    d = Deck()
    d.add(f"** blocking-pin snap FEA: {spec.name} ({spec.title}); material {spec.material}")
    d.add("*HEADING", f"{spec.name} {spec.material}")
    bodies = [model.bodies[k] for k in ("board", "snap", "screw") if k in model.bodies]
    write_bodies(d, bodies)
    board, snap = model.bodies["board"], model.bodies["snap"]
    screw = model.bodies.get("screw")
    factor = 0.25 if spec.symmetry == "quarter" else 0.5

    # --- surfaces, contact, ties
    h_ref = 0.45 * spec.mesh_scale
    kc = contact_stiffness(mat, h_ref) * spec.k_scale
    d.add("*SURFACE INTERACTION, NAME=SI")
    d.add("*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR", f"{kc:.6g}")
    if spec.friction > 0.0:
        d.add("*FRICTION", f"{spec.friction:g}, {kc * spec.stick_ratio:.6g}")
    for pair in model.pairs:
        write_surface(d, f"S_{pair.name}_S", pair.slave[0], pair.slave[1])
        write_surface(d, f"S_{pair.name}_M", pair.master[0], pair.master[1])
        d.add("*CONTACT PAIR, INTERACTION=SI, TYPE=SURFACE TO SURFACE", f"S_{pair.name}_S, S_{pair.name}_M")
    for tie in model.ties:
        write_surface(d, f"S_{tie.name}_S", tie.slave[0], tie.slave[1])
        write_surface(d, f"S_{tie.name}_M", tie.master[0], tie.master[1])
        d.add(f"*TIE, NAME={tie.name}, POSITION TOLERANCE={tie.tolerance:g}", f"S_{tie.name}_S, S_{tie.name}_M")

    # --- boundary conditions: symmetry planes, clamped patch edge
    for body in bodies:
        nodes = body.mesh.nodes
        x0 = np.nonzero(np.abs(nodes[:, 0]) < SYM_TOL)[0]
        if len(x0):
            write_nset(d, f"SYMX_{body.name.upper()}", body, x0)
            d.add("*BOUNDARY", f"SYMX_{body.name.upper()}, 1, 1")
        if spec.symmetry == "quarter":
            y0 = np.nonzero(np.abs(nodes[:, 1]) < SYM_TOL)[0]
            if len(y0):
                write_nset(d, f"SYMY_{body.name.upper()}", body, y0)
                d.add("*BOUNDARY", f"SYMY_{body.name.upper()}, 2, 2")
    write_nset(d, "NCLAMP", board, model.clamp_nodes)
    d.add("*BOUNDARY", "NCLAMP, 1, 3")

    nsets: dict[str, tuple[str, NDArray[np.int64]]] = {}
    info = DeckInfo([], nsets, 1, factor)
    step_load: list[str] = []
    zoff = model.zoff

    # --- loading (one *STEP per output frame; amplitudes are functions of total time, one time unit per step)
    if spec.kind == "ins" and spec.radial:
        sm = snap.mesh
        reach, half_w = cfg.ledge_reach, cfg.leg_width / 2.0 + 0.5
        led_y = np.nonzero((sm.nodes[:, 1] >= reach - 0.03) & (sm.nodes[:, 0] <= half_w))[0]
        led_x = np.nonzero((sm.nodes[:, 0] >= reach - 0.03) & (sm.nodes[:, 1] <= half_w))[0]
        bottom = np.nonzero(np.abs(sm.nodes[:, 2] - zoff) < 1e-3)[0]
        write_nset(d, "NLEDY", snap, led_y)
        write_nset(d, "NLEDX", snap, led_x)
        write_nset(d, "NBOT", snap, bottom)
        delta = reach - 12.45
        info.nsteps = INS_RADIAL_STEPS
        info.amplitude = [(0.0, 0.0), (float(INS_RADIAL_STEPS), delta)]
        d.add("*BOUNDARY", "NBOT, 3, 3")
        d.add("*AMPLITUDE, NAME=AINS, TIME=TOTAL TIME")
        d.lines.extend(f"{t:g}, {v:g}," for t, v in info.amplitude)
        step_load = ["*BOUNDARY, AMPLITUDE=AINS", "NLEDY, 2, 2, -1.", "NLEDX, 1, 1, -1."]
        lift_nodes = _sample(bottom, SAMPLE_NODES)
    elif spec.kind == "ins":
        sm = snap.mesh
        top = (np.abs(sm.tri_centroid[:, 2] - zoff - cfg.height) < 0.02) & (sm.tri_normal[:, 2] > 0.9)
        top_nodes = np.unique(sm.tris[top])
        write_nset(d, "NTOP", snap, top_nodes)
        nsets["NTOP"] = ("snap", top_nodes)
        info.nsteps = INS_STEPS
        info.amplitude = [(0.0, 0.0), (float(INS_STEPS), spec.ins_start)]
        d.add("*AMPLITUDE, NAME=AINS, TIME=TOTAL TIME")
        d.lines.extend(f"{t:g}, {v:g}," for t, v in info.amplitude)
        step_load = ["*BOUNDARY, AMPLITUDE=AINS", "NTOP, 3, 3, -1."]
        lift_nodes = _sample(np.nonzero(np.abs(sm.nodes[:, 2] - zoff) < 1e-3)[0], SAMPLE_NODES)
    else:
        assert screw is not None
        cm = screw.mesh
        head_mask = model.masks["screw:head"]
        if spec.kind == "overload":
            levels = spec.levels
        else:
            levels = tuple(spec.pull * (i + 1) / SERVICE_STEPS for i in range(SERVICE_STEPS))
        table = [(0.0, 0.0)] + [(float(i + 1), float(v)) for i, v in enumerate(levels)]
        info.amplitude = table
        info.nsteps = len(levels)
        d.add("*AMPLITUDE, NAME=APULL, TIME=TOTAL TIME")
        d.lines.extend(f"{t:g}, {v:g}," for t, v in table)
        # pull: unit traction resultant (1 N * symmetry factor) along +z, area-weighted over the flange underside
        pull_loads = consistent_face_loads(screw, head_mask, (0.0, 0.0, factor))
        step_load = ["*CLOAD, AMPLITUDE=APULL"]
        step_load.extend(f"{int(screw.gid(n))}, 3, {f[2]:.9g}" for n, f in pull_loads.items())
        if spec.shear > 0.0:
            shear_mask = head_mask & (cm.tri_centroid[:, 1] > 0.0)
            shear_table = [(0.0, 0.0), (float(len(levels)), spec.shear)]
            d.add("*AMPLITUDE, NAME=ASHEAR, TIME=TOTAL TIME")
            d.lines.extend(f"{t:g}, {v:g}," for t, v in shear_table)
            shear_loads = consistent_face_loads(screw, shear_mask, (0.0, -factor, 0.0))
            step_load.append("*CLOAD, AMPLITUDE=ASHEAR")
            step_load.extend(f"{int(screw.gid(n))}, 2, {f[1]:.9g}" for n, f in shear_loads.items())
        # stabiliser springs at the head node nearest the axis (outer face)
        axis_dist = np.hypot(cm.nodes[:, 0], cm.nodes[:, 1])
        cand = np.nonzero(axis_dist < 1e-6)[0]
        if len(cand) == 0:
            cand = np.nonzero(axis_dist < 0.5)[0]
        spring_local = int(cand[np.argmax(cm.nodes[cand, 2])])
        info.spring_node = spring_local
        dofs = [(screw, 3)] + ([(screw, 2)] if spec.shear > 0.0 else [])
        write_springs(d, bodies, dofs, [int(screw.gid(spring_local))], SPRING_K)
        nsets["NHEAD"] = ("screw", _sample(np.unique(cm.tris[head_mask]), SAMPLE_NODES))
        sm = snap.mesh
        lift_nodes = _sample(np.nonzero(np.abs(sm.nodes[:, 2] - zoff) < 1e-3)[0], SAMPLE_NODES)
    nsets["NLIFT"] = ("snap", lift_nodes)
    for name, (bname, ids) in nsets.items():
        if name != "NTOP":
            write_nset(d, name, model.bodies[bname], ids)

    # --- steps
    for k in range(info.nsteps):
        last_step = k == info.nsteps - 1
        d.add("*STEP, NLGEOM, INC=1000")
        if spec.kind == "ins" and spec.radial:
            d.add("*STATIC", "0.5, 1., 1e-5, 1.")
        elif spec.kind == "ins":
            d.add("*STATIC", "0.1, 1., 1e-5, 0.2")
        elif spec.kind == "service":
            d.add("*STATIC", f"{0.25 if k else 0.1:g}, 1., 1e-5, 0.5")
        else:
            d.add("*STATIC", f"{0.25 if k else 0.1:g}, 1., 1e-5, 0.5")
        if k == 0:
            d.lines.extend(step_load)
        if spec.kind == "ins" and not spec.radial and not last_step:  # intermediate insertion frames: snap only (peak strain search)
            d.add("*NODE FILE, NSET=N_SNAP, FREQUENCY=100000", "U")
            d.add("*EL FILE, ELSET=E_SNAP, FREQUENCY=100000", "S, E, PEEQ")
        else:
            d.add("*NODE FILE, FREQUENCY=100000", "U, RF")
            d.add("*EL FILE, FREQUENCY=100000", "S, E, PEEQ")
            d.add("*CONTACT FILE, FREQUENCY=100000", "CDIS, CSTR")
        for name in nsets:
            d.add(f"*NODE PRINT, NSET={name}", "U")
        d.add("*NODE PRINT, NSET=NCLAMP, TOTALS=ONLY", "RF")
        if spec.kind == "ins" and not spec.radial:
            d.add("*NODE PRINT, NSET=NTOP, TOTALS=ONLY", "RF")
        d.add("*END STEP")
    job = spec.name.replace("-", "_")
    inp = workdir / f"{job}.inp"
    inp.write_text(d.text())
    return inp, info



# --------------------------------------------------------------------------------------
# Post-processing
# --------------------------------------------------------------------------------------


@dataclass
class BodyFields:
    disp: F64  # (n, 3)
    stress: F64  # (n, 6)
    strain: F64  # (n, 6)
    peeq: F64  # (n,)
    present: NDArray[np.bool_]  # nodes with results in this frame


@dataclass
class Frame:
    time: float
    bodies: dict[str, BodyFields]
    label: str = ""


def frames_from_frd(model: Model, frd: FrdResult) -> list[Frame]:
    """Merge result sets with equal time into frames with per-body nodal fields."""

    order: list[float] = []
    merged: dict[float, dict[str, tuple[I64, F64]]] = {}
    for t, fields in zip(frd.times, frd.fields, strict=True):
        key = round(t, 9)
        if key not in merged:
            merged[key] = {}
            order.append(key)
        for name, (ids, vals) in fields.items():
            if name in merged[key]:
                old_ids, old_vals = merged[key][name]
                merged[key][name] = (np.concatenate([old_ids, ids]), np.concatenate([old_vals, vals]))
            else:
                merged[key][name] = (ids, vals)
    frames: list[Frame] = []
    for key in order:
        f = merged[key]
        if not all(k in f for k in ("DISP", "STRESS", "TOSTRAIN", "PE")):
            continue  # incomplete result set (ccx terminated while writing)
        bodies: dict[str, BodyFields] = {}
        for name, body in model.bodies.items():
            n = len(body.mesh.nodes)
            bf = BodyFields(np.zeros((n, 3)), np.zeros((n, 6)), np.zeros((n, 6)), np.zeros(n), np.zeros(n, dtype=bool))

            def put(field_name: str, target: F64, ncomp: int, body: Body = body, bf: BodyFields = bf) -> bool:
                if field_name not in f:
                    return False
                ids, vals = f[field_name]
                local = ids - body.node0 - 1
                ok = (local >= 0) & (local < len(body.mesh.nodes))
                target[local[ok], :ncomp] = vals[ok][:, :ncomp]
                bf.present[local[ok]] = True
                return True

            put("DISP", bf.disp, 3)
            put("STRESS", bf.stress, 6)
            put("TOSTRAIN", bf.strain, 6)
            peeq = np.zeros((n, 1))
            put("PE", peeq, 1)
            bf.peeq = peeq[:, 0]
            bodies[name] = bf
        frames.append(Frame(key, bodies))
    return frames


def sharp_edge_points(mesh: Mesh, symmetry: str) -> F64:
    """Edge-sample points (ends + mid) of boundary edges whose faces meet at more than SHARP_EDGE_DEG."""

    tris = mesh.tris
    e = np.concatenate([tris[:, [0, 1, 3]], tris[:, [1, 2, 4]], tris[:, [2, 0, 5]]])  # a, b, mid
    owner = np.concatenate([np.arange(len(tris))] * 3)
    a, b = np.minimum(e[:, 0], e[:, 1]), np.maximum(e[:, 0], e[:, 1])
    key = a.astype(np.int64) * (len(mesh.nodes) + 1) + b
    order = np.argsort(key, kind="stable")
    ks = key[order]
    same = ks[1:] == ks[:-1]
    first = order[:-1][same]
    second = order[1:][same]
    cosang = np.einsum("ij,ij->i", mesh.tri_normal[owner[first]], mesh.tri_normal[owner[second]])
    sharp = cosang < math.cos(math.radians(SHARP_EDGE_DEG))
    sel = first[sharp]
    ea, eb, em = e[sel, 0], e[sel, 1], e[sel, 2]
    pa, pb, pm = mesh.nodes[ea], mesh.nodes[eb], mesh.nodes[em]
    lying = np.zeros(len(sel), dtype=bool)  # edges lying in a symmetry plane are artefacts of the cut
    lying |= (np.abs(pa[:, 0]) < SYM_TOL) & (np.abs(pb[:, 0]) < SYM_TOL)
    if symmetry == "quarter":
        lying |= (np.abs(pa[:, 1]) < SYM_TOL) & (np.abs(pb[:, 1]) < SYM_TOL)
    keep = ~lying
    return np.concatenate([pa[keep], pm[keep], pb[keep], 0.5 * (pa[keep] + pm[keep]), 0.5 * (pm[keep] + pb[keep])])


@dataclass
class BodyContext:
    """Static (frame-independent) helpers for metric extraction on one body."""

    body: Body
    edge_dist: F64  # distance of every node to the nearest sharp edge
    weight: F64  # corner-node tributary volume
    region: NDArray[np.bool_]  # nodes eligible for metrics (e.g. board: neighbourhood of the centre cell)
    legs: NDArray[np.bool_]  # snap only: leg nodes


def build_contexts(model: Model) -> dict[str, BodyContext]:
    from scipy.spatial import cKDTree  # pyright: ignore[reportAttributeAccessIssue]

    cfg = model.geo.snap_cfg
    ctx: dict[str, BodyContext] = {}
    for name, body in model.bodies.items():
        m = body.mesh
        pts = sharp_edge_points(m, model.spec.symmetry)
        dist = cKDTree(pts).query(m.nodes)[0] if len(pts) else np.full(len(m.nodes), np.inf)
        w = np.zeros(len(m.nodes))
        vols = m.tet_volumes()
        for c in range(4):
            np.add.at(w, m.tets[:, c], vols / 4.0)
        region = np.ones(len(m.nodes), dtype=bool)
        legs = np.zeros(len(m.nodes), dtype=bool)
        if name == "board":
            region = (np.abs(m.nodes[:, 0]) <= 20.0) & (np.abs(m.nodes[:, 1]) <= 20.0)
        if name == "snap":
            zs = m.nodes[:, 2] - model.zoff
            half = cfg.leg_width / 2.0 + 0.3
            ri = cfg.leg_bore_radius
            nx, ny = np.abs(m.nodes[:, 0]), np.abs(m.nodes[:, 1])
            legs = ((nx <= half) & (ny >= ri - 0.05)) | ((ny <= half) & (nx >= ri - 0.05))
            legs &= zs >= cfg.web_thickness - 0.1
        ctx[name] = BodyContext(body, dist, w, region, legs)
    return ctx


def _wpercentile(values: F64, weights: F64, q: float) -> float:
    ok = weights > 0.0
    v, w = values[ok], weights[ok]
    if len(v) == 0:
        return math.nan
    o = np.argsort(v)
    cw = np.cumsum(w[o])
    idx = int(np.searchsorted(cw, q / 100.0 * cw[-1]))
    return float(v[o][min(idx, len(v) - 1)])


def stat_triplet(values: F64, ctx: BodyContext, mask: NDArray[np.bool_] | None = None) -> dict[str, float]:
    """Raw maximum, singularity-excluded ("robust") maximum and the 99.5th volume-weighted percentile."""

    sel = ctx.region if mask is None else (ctx.region & mask)
    if not sel.any():
        return {"raw": math.nan, "robust": math.nan, "p99.5": math.nan}
    far = sel & (ctx.edge_dist >= SINGULAR_DISTANCE)
    return {
        "raw": float(values[sel].max()),
        "robust": float(values[far].max()) if far.any() else math.nan,
        "p99.5": _wpercentile(values[sel], ctx.weight[sel], 99.5),
    }


def frame_metrics(model: Model, frame: Frame, ctxs: dict[str, BodyContext]) -> dict[str, Any]:
    out: dict[str, Any] = {"time": frame.time}
    for name, bf in frame.bodies.items():
        ctx = ctxs[name]
        if not bf.present.any():
            continue
        vm = von_mises(bf.stress)
        szz = bf.stress[:, 2]
        e1 = max_principal(bf.strain)
        out[name] = {
            "von_mises_MPa": stat_triplet(vm, ctx),
            "sigma_zz_MPa": stat_triplet(szz, ctx),
            "max_principal_strain": stat_triplet(e1, ctx),
            "peeq": stat_triplet(bf.peeq, ctx),
        }
        if name == "snap":
            out[name]["legs"] = {
                "von_mises_MPa": stat_triplet(vm, ctx, ctx.legs),
                "sigma_zz_MPa": stat_triplet(szz, ctx, ctx.legs),
                "max_principal_strain": stat_triplet(e1, ctx, ctx.legs),
                "peeq": stat_triplet(bf.peeq, ctx, ctx.legs),
            }
    return out


def curve_from_dat(model: Model, info: DeckInfo, dat: list[DatBlock]) -> dict[str, Any]:
    """Load/lift/head-displacement history per converged increment."""

    times = sorted({b.time for b in dat if b.kind == "disp" and b.set_name == "NLIFT"})
    amp_t = np.array([t for t, _ in info.amplitude])
    amp_v = np.array([v for _, v in info.amplitude])
    lift: list[float] = []
    head: list[float] = []
    rfz: list[float] = []
    force: list[float] = []
    for t in times:
        blocks = [b for b in dat if b.time == t]
        for b in blocks:
            if b.kind == "disp" and b.set_name == "NLIFT":
                lift.append(float(b.data[:, 3].mean()))
            if b.kind == "disp" and b.set_name == "NHEAD":
                head.append(float(b.data[:, 3].mean()))
            if b.kind == "total_force" and b.set_name == "NCLAMP":
                rfz.append(float(b.data[0][-1]))
            if b.kind == "total_force" and b.set_name == "NTOP":
                force.append(-float(b.data[0][-1]) / info.quarter_factor)
    load = np.interp(times, amp_t, amp_v)
    n = len(times)
    return {
        "time": times,
        "load_N": load.tolist(),
        "lift_mm": lift[:n],
        "head_uz_mm": head[:n] if len(head) >= n else [],
        "clamp_rfz_N": rfz[:n] if len(rfz) >= n else [],
        "force_N": force[:n] if len(force) >= n else [],
    }


# --------------------------------------------------------------------------------------
# Plots
# --------------------------------------------------------------------------------------


def _view_limits(ax: Any, pts: F64) -> None:
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    mid = 0.5 * (lo + hi)
    half = 0.5 * float((hi - lo).max())
    ax.set_xlim(mid[0] - half, mid[0] + half)
    ax.set_ylim(mid[1] - half, mid[1] + half)
    ax.set_zlim(mid[2] - half, mid[2] + half)
    ax.set_box_aspect((1, 1, 1))


def draw_surface(
    ax: Any,
    mesh: Mesh,
    values: F64,
    disp: F64,
    scale: float,
    vmin: float,
    vmax: float,
    cmap: str,
    tri_mask: NDArray[np.bool_] | None = None,
    clip: tuple[float, float, float] | None = None,
) -> Any:
    """Contour of a nodal field on the boundary of a (deformed, scaled) mesh."""

    import matplotlib
    from matplotlib.colors import Normalize
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    sel = np.ones(len(mesh.tris), dtype=bool) if tri_mask is None else tri_mask
    tris = mesh.tris[sel]
    pos = mesh.nodes + scale * disp
    # colour each facet by the mean of its three corner-node values
    sub = tris[:, :3]
    val = values[sub].mean(axis=1)
    polys = pos[sub]
    keep = np.ones(len(sub), dtype=bool)
    if clip is not None:
        cen = pos[sub].mean(axis=1)
        keep = (np.abs(cen[:, 0]) <= clip[0]) & (np.abs(cen[:, 1]) <= clip[1]) & (cen[:, 2] >= clip[2] - 1e9)
    norm = Normalize(vmin=vmin, vmax=vmax)
    colors = matplotlib.colormaps[cmap](norm(val[keep]))
    coll = Poly3DCollection(polys[keep], facecolors=colors, edgecolors="none", linewidths=0.0)
    ax.add_collection3d(coll)
    return polys[keep]


def plot_field_maps(model: Model, frame: Frame, case_dir: Path, tag: str, ctxs: dict[str, BodyContext]) -> list[Path]:
    """Contour maps of von Mises, sigma_zz and max-principal strain on snap, screw and board."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm as mcm
    from matplotlib.colors import Normalize

    mats = MATERIALS[model.spec.material]
    specs = [
        ("von_mises", "von Mises [MPa]", lambda bf: von_mises(bf.stress), "turbo", (0.0, mats.yield_stress)),
        ("sigma_zz", "sigma_zz [MPa] (print z)", lambda bf: bf.stress[:, 2], "coolwarm", (-mats.interlayer, mats.interlayer)),
        ("max_principal_strain", "max principal strain [%]", lambda bf: 100.0 * max_principal(bf.strain), "turbo", (0.0, 100.0 * mats.interlayer_strain)),
    ]
    names = [n for n in ("snap", "screw", "board") if n in model.bodies and frame.bodies[n].present.any()]
    umax = max(float(np.linalg.norm(frame.bodies[n].disp, axis=1).max()) for n in names)
    ubody = float(np.linalg.norm(frame.bodies["snap"].disp, axis=1).max()) if "snap" in frame.bodies else umax
    scale = float(min(60.0, max(1.0, 1.0 / max(ubody, 1e-6))))
    az = 225.0 if model.spec.symmetry == "quarter" else 200.0
    out: list[Path] = []
    for key, label, fn, cmap, (lo, hi) in specs:
        fig = plt.figure(figsize=(5.4 * len(names), 5.6), dpi=110)
        for i, n in enumerate(names):
            ax = fig.add_subplot(1, len(names), i + 1, projection="3d")
            bf = frame.bodies[n]
            body = model.bodies[n]
            vals = fn(bf)
            region = ctxs[n].region
            tri_mask = region[body.mesh.tris[:, :3]].all(axis=1)
            if n == "board":
                tri_mask &= body.mesh.tri_centroid[:, 2] > 0.0
            shown = vals[region]
            vmax = float(np.percentile(shown, 99.7)) if key != "sigma_zz" else float(np.percentile(np.abs(shown), 99.7))
            if key == "sigma_zz":
                v_lo, v_hi = -max(vmax, 1e-6), max(vmax, 1e-6)
            else:
                v_lo, v_hi = 0.0, max(vmax, 1e-9)
            polys = draw_surface(ax, body.mesh, vals, bf.disp, scale, v_lo, v_hi, cmap, np.asarray(tri_mask, dtype=bool))
            _view_limits(ax, polys.reshape(-1, 3))
            ax.view_init(elev=24.0, azim=az)
            ax.set_axis_off()
            ax.set_title(f"{n}  (max shown {shown.max():.3g})", fontsize=10)
            sm_ = mcm.ScalarMappable(norm=Normalize(v_lo, v_hi), cmap=cmap)
            fig.colorbar(sm_, ax=ax, shrink=0.55, pad=0.02, label=label)
        fig.suptitle(f"{model.spec.name} [{model.spec.material}] {frame.label}: {label}; deformation x{scale:.0f}; {model.spec.symmetry} model", fontsize=11)
        path = case_dir / f"{tag}_{key}.png"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        out.append(path)
    out.append(_plot_assembly(model, frame, case_dir, tag, ctxs, scale, az))
    return out


def _plot_assembly(model: Model, frame: Frame, case_dir: Path, tag: str, ctxs: dict[str, BodyContext], scale: float, az: float) -> Path:
    """Snap, screw and board together (von Mises), seen from the symmetry-plane side."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm as mcm
    from matplotlib.colors import Normalize

    mat = MATERIALS[model.spec.material]
    fig = plt.figure(figsize=(12, 6), dpi=110)
    pts: list[F64] = []
    for panel, (elev, azim) in enumerate(((24.0, az), (4.0, az))):
        ax = fig.add_subplot(1, 2, panel + 1, projection="3d")
        for n in ("board", "snap", "screw"):
            if n not in model.bodies or not frame.bodies[n].present.any():
                continue
            body, bf = model.bodies[n], frame.bodies[n]
            tri_mask = ctxs[n].region[body.mesh.tris[:, :3]].all(axis=1)
            polys = draw_surface(ax, body.mesh, von_mises(bf.stress), bf.disp, scale, 0.0, mat.yield_stress, "turbo", np.asarray(tri_mask, dtype=bool))
            pts.append(polys.reshape(-1, 3))
        _view_limits(ax, np.concatenate(pts))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        fig.colorbar(mcm.ScalarMappable(norm=Normalize(0.0, mat.yield_stress), cmap="turbo"), ax=ax, shrink=0.55, pad=0.02, label="von Mises [MPa] (scale = yield)")
    fig.suptitle(f"{model.spec.name} [{model.spec.material}] assembly, {frame.label}, deformation x{scale:.0f}", fontsize=11)
    path = case_dir / f"{tag}_assembly.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_curve(case_dir: Path, name: str, curve: dict[str, Any], spec: CaseSpec, extra: dict[str, Any]) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out: list[Path] = []
    load = np.asarray(curve["load_N"])
    lift = np.asarray(curve["lift_mm"])
    if len(lift) == 0:
        return out
    fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=120)
    if spec.kind == "ins":
        if spec.radial or not curve["force_N"]:
            plt.close(fig)
            return out
        ax.plot(load, curve["force_N"], "-o", ms=3)
        ax.set_xlabel("insertion stroke from start [mm]")
        ax.set_ylabel("insertion force per snap [N]")
        ax.axhline(40.0, color="r", ls="--", lw=0.8, label="limit 40 N")
        ax.legend()
    else:
        seat = float(extra.get("seat_lift_mm", 0.0))
        pull = np.concatenate([[0.0], load])
        ax.plot(np.concatenate([[seat], lift + seat]), pull, "-o", ms=3, label="pull vs snap lift (incl. seating play)")
        if len(curve.get("head_uz_mm", [])) == len(load):
            ax.plot(np.concatenate([[seat], np.asarray(curve["head_uz_mm"]) + seat]), pull, "-", lw=0.8, label="pull vs head displacement")
        limit = LIFT_LIMIT_SERVICE if spec.kind == "service" else LIFT_COLLAPSE
        ax.axvline(limit, color="r", ls="--", lw=0.8, label=f"limit {limit:g} mm")
        ax.set_xlabel("lift from seated position [mm]")
        ax.set_ylabel("pull per snap [N]")
        ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_title(f"{name} load-displacement")
    p = case_dir / "load_displacement.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    out.append(p)
    return out


def plot_contact(model: Model, frame: Frame, case_dir: Path, contact: dict[str, tuple[I64, F64]]) -> list[Path]:
    """Contact pressure on the slave surfaces of each pair (grey = no contact)."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm as mcm
    from matplotlib.colors import Normalize

    out: list[Path] = []
    pairs = [p for p in model.pairs if p.name in contact]
    if not pairs:
        return out
    ubody = float(np.linalg.norm(frame.bodies["snap"].disp, axis=1).max())
    scale = float(min(60.0, max(1.0, 1.0 / max(ubody, 1e-6))))
    fig = plt.figure(figsize=(5.2 * len(pairs), 5.4), dpi=110)
    for i, pair in enumerate(pairs):
        ax = fig.add_subplot(1, len(pairs), i + 1, projection="3d")
        body, mask = pair.slave
        ids, vals = contact[pair.name]
        local = ids - body.node0 - 1
        pressure = np.zeros(len(body.mesh.nodes))
        ok = (local >= 0) & (local < len(pressure))
        pressure[local[ok]] = vals[ok]
        vmax = max(float(pressure.max()), 1e-9)
        disp = frame.bodies[body.name].disp
        polys = draw_surface(ax, body.mesh, pressure, disp, scale, 0.0, vmax, "viridis", mask)
        _view_limits(ax, polys.reshape(-1, 3))
        ax.view_init(elev=24.0, azim=225.0 if model.spec.symmetry == "quarter" else 200.0)
        ax.set_axis_off()
        ax.set_title(f"{pair.name}: slave {body.name}, peak {pressure.max():.3g} MPa", fontsize=10)
        fig.colorbar(mcm.ScalarMappable(norm=Normalize(0.0, vmax), cmap="viridis"), ax=ax, shrink=0.55, pad=0.02, label="contact pressure [MPa]")
    fig.suptitle(f"{model.spec.name}: contact status (slave-surface node pressure)")
    p = case_dir / "contact_status.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    out.append(p)
    return out


# --------------------------------------------------------------------------------------
# Case analysis
# --------------------------------------------------------------------------------------

LIFT_LIMIT_SERVICE = 0.3  # mm
LIFT_COLLAPSE = 1.0  # mm, collapse criterion for OVL / UNB
YIELD_PEEQ = 1e-4  # plastic-strain onset threshold
OVL_REQUIRED = 300.0  # N
INS_STRAIN_LIMIT = 0.012
INS_FORCE_LIMIT = 40.0


def contact_from_frd(model: Model, frd: FrdResult) -> dict[str, tuple[I64, F64]]:
    """Contact pressure (CSTR normal component) at slave nodes of each pair, last result set."""

    out: dict[str, tuple[I64, F64]] = {}
    for fields in reversed(frd.fields):
        if "CONTACT" in fields:
            ids, vals = fields["CONTACT"]
            # CONTACT block components: COPEN, CSLIP1, CSLIP2, CPRESS, CSHEAR1, CSHEAR2
            for pair in model.pairs:
                body, mask = pair.slave
                nodes = body.gid(np.unique(body.mesh.tris[mask]))
                sel = np.isin(ids, nodes)
                out[pair.name] = (ids[sel], np.abs(vals[sel][:, 3]))
            break
    return out


def frame_lift(model: Model, frame: Frame) -> dict[str, float]:
    sm = model.bodies["snap"].mesh
    bottom = np.nonzero(np.abs(sm.nodes[:, 2] - model.zoff) < 1e-3)[0]
    d = frame.bodies["snap"].disp[bottom]
    out = {"snap_lift_mm": float(d[:, 2].mean()), "snap_uy_mm": float(d[:, 1].mean())}
    bm = model.bodies["board"].mesh
    r = np.hypot(bm.nodes[:, 0], bm.nodes[:, 1])
    lip = np.nonzero((r > 12.4) & (r < 13.3) & (bm.nodes[:, 2] > model.geo.snap_cfg.board_thickness - 3.0) & (np.abs(bm.nodes[:, 0]) < 3.0))[0]
    if len(lip) and frame.bodies["board"].present.any():
        out["board_lip_uz_mm"] = float(frame.bodies["board"].disp[lip, 2].mean())
        out["board_lip_ur_mm"] = float(frame.bodies["board"].disp[lip, 1].mean())
    if "screw" in frame.bodies:
        cm = model.bodies["screw"].mesh
        top = np.nonzero(cm.nodes[:, 2] > cm.nodes[:, 2].max() - 1e-3)[0]
        dd = frame.bodies["screw"].disp[top]
        out["head_uz_mm"] = float(dd[:, 2].mean())
        out["head_uy_mm"] = float(dd[:, 1].mean())
    return out


def _peak(metrics: dict[str, Any], body: str, fld: str, sub: str = "robust", legs: bool = False) -> float:
    node = metrics.get(body)
    if node is None:
        return math.nan
    if legs:
        node = node["legs"]
    return float(node[fld][sub])


def evaluate_service(model: Model, metrics: dict[str, Any], lift_total: float) -> dict[str, Any]:
    mat = MATERIALS[model.spec.material]
    checks: dict[str, Any] = {}
    limit_vm = mat.yield_stress / 2.0
    limit_zz = mat.interlayer / 2.0
    for body in ("snap", "screw", "board"):
        vm = _peak(metrics, body, "von_mises_MPa")
        zz = _peak(metrics, body, "sigma_zz_MPa")
        checks[f"{body}_von_mises_MPa"] = {"value": vm, "limit": limit_vm, "pass": bool(vm <= limit_vm)}
        checks[f"{body}_sigma_zz_MPa"] = {"value": zz, "limit": limit_zz, "pass": bool(zz <= limit_zz)}
    checks["lift_mm"] = {"value": lift_total, "limit": LIFT_LIMIT_SERVICE, "pass": bool(lift_total <= LIFT_LIMIT_SERVICE)}
    return checks


def last_converged_time(sta: Path) -> float:
    """Total time of the last converged increment in the .sta file."""

    last = 0.0
    if not sta.exists():
        return last
    for line in sta.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].isdigit() and "U" not in parts[2]:
            try:
                last = float(parts[4])
            except ValueError:
                continue
    return last


def lift_exceeded(dat: Path, seat: float) -> bool:
    """True once the last printed NLIFT block shows a total lift above the collapse limit."""

    if not dat.exists() or dat.stat().st_size == 0:
        return False
    with dat.open("rb") as fh:
        fh.seek(max(0, dat.stat().st_size - 30000))
        tail = fh.read().decode(errors="replace")
    idx = tail.rfind("for set NLIFT")
    if idx < 0:
        return False
    rows = []
    for line in tail[idx:].splitlines()[1:]:
        parts = line.split()
        if len(parts) == 4:
            try:
                rows.append(float(parts[3]))
            except ValueError:
                break
        elif rows:
            break
    return bool(rows) and float(np.mean(rows)) + seat > LIFT_COLLAPSE


def _jsonable(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(o, (np.integer, int)) and not isinstance(o, bool):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def run_case(spec: CaseSpec, threads: int, log: Callable[[str], None], keep_frd: bool = False, solve: bool = True) -> dict[str, Any]:
    case_dir = OUT_ROOT / spec.name
    work = case_dir / "ccx"
    if solve:
        if case_dir.exists():
            shutil.rmtree(case_dir)
        work.mkdir(parents=True)
    else:  # re-post-process an earlier solve (needs its .frd/.dat and a deterministic mesh)
        for stale in case_dir.glob("*.png"):
            stale.unlink()
    t_start = time.time()
    log(f"[{spec.name}] {spec.title} ({spec.material}, {spec.symmetry} symmetry, mesh scale {spec.mesh_scale})")
    model = build_model(spec, work, log, reuse_mesh=not solve)
    inp, info = write_case(model, work, threads)
    t_mesh = time.time() - t_start
    log(f"  deck {inp.name}: {sum(len(b.mesh.nodes) for b in model.bodies.values())} nodes; {'running ccx (%d threads)' % threads if solve else 'reusing existing ccx results'}")
    if solve:
        stop = (lambda: lift_exceeded(work / f"{inp.stem}.dat", model.geo.shift_z)) if spec.kind == "overload" else None
        run = run_ccx(work, inp.stem, threads, stop)
    else:
        text = (work / f"{inp.stem}.log").read_text(errors="replace")
        run = RunResult(0, 0.0, "Job finished" in text, "\n".join(text.splitlines()[-25:]))
        prev = case_dir / "result.json"
        if prev.exists():
            run.seconds = float(json.loads(prev.read_text()).get("time_s", {}).get("ccx", 0.0))
    t_solve = run.seconds
    log(f"  ccx finished rc={run.returncode} converged={run.converged} stopped={run.stopped} in {t_solve:.0f} s")
    frd = parse_frd(work / f"{inp.stem}.frd")
    dat = parse_dat(work / f"{inp.stem}.dat")
    frames = frames_from_frd(model, frd)
    amp_t = [t for t, _ in info.amplitude]
    amp_v = [v for _, v in info.amplitude]
    for fr in frames:
        val = float(np.interp(fr.time, amp_t, amp_v))
        fr.label = (f"ledge displacement {val:.2f} mm" if spec.radial else f"stroke {val:.2f} mm") if spec.kind == "ins" else f"pull {val:.0f} N" + (f" + shear {spec.shear * fr.time / info.nsteps:.0f} N" if spec.shear > 0 else "")
    ctxs = build_contexts(model)
    per_frame = [frame_metrics(model, fr, ctxs) for fr in frames]
    curve = curve_from_dat(model, info, dat)
    result: dict[str, Any] = {
        "case": spec.name,
        "title": spec.title,
        "kind": spec.kind,
        "material": spec.material,
        "symmetry": spec.symmetry,
        "spec": asdict(spec),
        "ccx_returncode": run.returncode,
        "ccx_completed": run.converged,
        "ccx_stopped_at_collapse": run.stopped,
        "mesh": {n: {"nodes": len(b.mesh.nodes), "tets": len(b.mesh.tets)} for n, b in model.bodies.items()},
        "seat_lift_mm": model.geo.shift_z,
        "time_s": {"geometry_mesh_deck": t_mesh, "ccx": t_solve},
        "frames": len(frames),
        "curve": curve,
        "config": {
            "snap": asdict(model.geo.snap_cfg),
            "blocking_clearance": model.geo.screw_cfg.blocking_clearance,
        },
    }
    if not frames:
        result["error"] = "no result frames: " + run.log_tail[-400:]
        result["time_s"]["total"] = time.time() - t_start
        (case_dir / "result.json").write_text(json.dumps(_jsonable(result), indent=1))
        return result
    analyse(model, spec, info, frames, per_frame, curve, run, result, contact_from_frd(model, frd), work, inp.stem)
    pngs: list[Path] = []
    plot_frames = result.pop("_plot_frames")
    for tag, idx in plot_frames:
        pngs += plot_field_maps(model, frames[idx], case_dir, tag, ctxs)
    pngs += plot_curve(case_dir, spec.name, curve, spec, result)
    contact = result.pop("_contact", {})
    pngs += plot_contact(model, frames[-1 if spec.kind != "ins" else plot_frames[-1][1]], case_dir, contact)
    result["images"] = [p.name for p in pngs]
    result["time_s"]["total"] = time.time() - t_start
    if not keep_frd:
        for ext in ("frd", "12d"):
            f = work / f"{inp.stem}.{ext}"
            if f.exists():
                f.unlink()
    (case_dir / "result.json").write_text(json.dumps(_jsonable(result), indent=1))
    log(f"  done in {result['time_s']['total']:.0f} s")
    return result


def _interp_cross(x: F64, y: F64, level: float) -> float | None:
    """First x at which y crosses ``level`` (linear interpolation), or None."""

    idx = np.nonzero(y > level)[0]
    if len(idx) == 0:
        return None
    i = int(idx[0])
    if i == 0:
        return float(x[0])
    return float(x[i - 1] + (level - y[i - 1]) * (x[i] - x[i - 1]) / max(y[i] - y[i - 1], 1e-30))


def analyse(
    model: Model,
    spec: CaseSpec,
    info: DeckInfo,
    frames: list[Frame],
    per_frame: list[dict[str, Any]],
    curve: dict[str, Any],
    run: RunResult,
    result: dict[str, Any],
    contact: dict[str, tuple[I64, F64]],
    work_dir: Path,
    job_name: str,
) -> None:
    mat = MATERIALS[spec.material]
    seat = model.geo.shift_z
    last = len(frames) - 1
    lifts = [frame_lift(model, fr) for fr in frames]
    result["contact_peak_MPa"] = {k: float(v[1].max()) if len(v[1]) else 0.0 for k, v in contact.items()}
    result["_contact"] = contact
    if spec.kind == "ins":
        leg_strain = np.array([_peak(m, "snap", "max_principal_strain", "robust", True) for m in per_frame])
        leg_strain_raw = np.array([_peak(m, "snap", "max_principal_strain", "raw", True) for m in per_frame])
        leg_zz = np.array([_peak(m, "snap", "sigma_zz_MPa", "robust", True) for m in per_frame])
        leg_zz_raw = np.array([_peak(m, "snap", "sigma_zz_MPa", "raw", True) for m in per_frame])
        leg_vm = np.array([_peak(m, "snap", "von_mises_MPa", "robust", True) for m in per_frame])
        leg_peeq = np.array([_peak(m, "snap", "peeq", "robust", True) for m in per_frame])
        snap_peeq = np.array([_peak(m, "snap", "peeq", "raw") for m in per_frame])
        board_peeq = np.array([_peak(m, "board", "peeq", "raw") for m in per_frame])
        ipk = int(np.nanargmax(leg_strain)) if len(leg_strain) else last
        force = np.asarray(curve["force_N"]) if curve["force_N"] else np.zeros(0)
        peak_force = float(force.max()) if len(force) else math.nan
        completed = bool(run.converged and abs(frames[-1].time - info.nsteps) < 1e-6)
        result["metrics"] = {
            "peak_leg_strain_robust": float(np.nanmax(leg_strain)),
            "peak_leg_strain_raw": float(np.nanmax(leg_strain_raw)),
            "peak_leg_sigma_zz_robust_MPa": float(np.nanmax(leg_zz)),
            "peak_leg_sigma_zz_raw_MPa": float(np.nanmax(leg_zz_raw)),
            "peak_leg_von_mises_robust_MPa": float(np.nanmax(leg_vm)),
            "peak_leg_peeq_robust": float(np.nanmax(leg_peeq)),
            "peak_snap_peeq_raw": float(np.nanmax(snap_peeq)),
            "peak_board_peeq_raw": float(np.nanmax(board_peeq)) if np.isfinite(board_peeq).any() else math.nan,
            "peak_insertion_force_N": peak_force,
            "frame_of_peak_strain_stroke_mm": spec.ins_start * frames[ipk].time / info.nsteps,
            "completed_stroke": completed,
            "last_time": frames[-1].time / info.nsteps,
            "final_snap_lift_mm": lifts[-1]["snap_lift_mm"] + spec.ins_start,
        }
        result["checks"] = {
            "peak_leg_strain": {"value": float(np.nanmax(leg_strain)), "limit": INS_STRAIN_LIMIT, "pass": bool(np.nanmax(leg_strain) <= INS_STRAIN_LIMIT)},
            "peak_leg_sigma_zz_MPa": {"value": float(np.nanmax(leg_zz)), "limit": mat.interlayer, "pass": bool(np.nanmax(leg_zz) <= mat.interlayer)},
        }
        if not spec.radial:
            result["checks"]["insertion_force_N"] = {"value": peak_force, "limit": INS_FORCE_LIMIT, "pass": bool(peak_force <= INS_FORCE_LIMIT)}
        result["checks"]["stroke_completed"] = {"value": float(frames[-1].time) / info.nsteps, "limit": 1.0, "pass": completed}
        result["_plot_frames"] = [("peak_strain", ipk)] + ([("final", last)] if last != ipk else [])
        result["strain_history"] = {"time": [f.time for f in frames], "leg_strain": leg_strain.tolist(), "leg_sigma_zz": leg_zz.tolist()}
        return
    # axial / shear service and overload cases
    amp = dict(info.amplitude)
    loads = [amp.get(round(fr.time), math.nan) for fr in frames]
    final = per_frame[last]
    result["final_frame"] = final
    result["lift_mm"] = {
        "snap_fea": lifts[last]["snap_lift_mm"],
        "snap_total_incl_seating_play": lifts[last]["snap_lift_mm"] + seat,
        "head_total": lifts[last].get("head_uz_mm", math.nan) + seat,
        "board_lip_uz_mm": lifts[last].get("board_lip_uz_mm", math.nan),
        "board_lip_radial_mm": lifts[last].get("board_lip_ur_mm", math.nan),
        "snap_relative_to_lip_total": lifts[last]["snap_lift_mm"] - lifts[last].get("board_lip_uz_mm", 0.0) + seat,
        "snap_uy_mm": lifts[last]["snap_uy_mm"],
        "head_uy_mm": lifts[last].get("head_uy_mm", math.nan),
    }
    # reaction balance at the last frame
    cl = curve["clamp_rfz_N"]
    if cl:
        applied = loads[last] * info.quarter_factor
        node = info.spring_node
        spring = 0.0
        if node is not None:
            spring = SPRING_K * float(frames[last].bodies["screw"].disp[node, 2])
        resid = (-cl[-1] + spring - applied) / max(applied, 1e-9)
        result["equilibrium"] = {
            "applied_N_model": applied,
            "clamp_reaction_z_N_model": cl[-1],
            "spring_force_N": spring,
            "balance_error_pct": 100.0 * resid,
        }
    if spec.kind == "service":
        total = lifts[last]["snap_lift_mm"] + seat
        result["checks"] = evaluate_service(model, final, total)
        result["checks"]["completed"] = {"value": float(frames[-1].time) / info.nsteps, "limit": 1.0, "pass": bool(run.converged and abs(frames[-1].time - info.nsteps) < 1e-6)}
        result["_plot_frames"] = [("final", last)]
        return
    # overload
    ttl = np.array(curve["lift_mm"]) + seat
    ld = np.array(curve["load_N"])
    cap = _interp_cross(ld, ttl, LIFT_COLLAPSE) if len(ld) else None
    if cap is not None:
        kind = f"lift exceeded {LIFT_COLLAPSE} mm"
    elif not run.converged:
        t_last = last_converged_time(work_dir / f"{job_name}.sta")
        cap = float(np.interp(t_last, [t for t, _ in info.amplitude], [v for _, v in info.amplitude]))
        kind = "no equilibrium beyond this load (solver diverged)"
    else:
        cap = float(ld[-1])
        kind = f"not reached up to {cap:g} N (capacity >= this load)"
    # first yield / interlayer exceedance per body (robust metric)
    onset: dict[str, Any] = {}
    for body in ("snap", "screw", "board"):
        pe = np.array([_peak(m, body, "peeq", "robust") for m in per_frame])
        zz = np.array([_peak(m, body, "sigma_zz_MPa", "robust") for m in per_frame])
        pe_raw = np.array([_peak(m, body, "peeq", "raw") for m in per_frame])
        t_pe = _interp_cross(np.array(loads), np.nan_to_num(pe), YIELD_PEEQ)
        t_pe_raw = _interp_cross(np.array(loads), np.nan_to_num(pe_raw), YIELD_PEEQ)
        t_zz = _interp_cross(np.array(loads), np.nan_to_num(zz), mat.interlayer)
        onset[body] = {"first_yield_N": t_pe, "first_yield_raw_N": t_pe_raw, "first_interlayer_exceedance_N": t_zz}
    result["capacity"] = {"load_N": cap, "criterion": kind, "onset": onset, "required_N": OVL_REQUIRED}
    result["history"] = {
        "load_N": loads,
        "snap_total_lift_mm": [lf["snap_lift_mm"] + seat for lf in lifts],
        "snap_vm_robust": [_peak(m, "snap", "von_mises_MPa") for m in per_frame],
        "snap_szz_robust": [_peak(m, "snap", "sigma_zz_MPa") for m in per_frame],
        "snap_peeq_robust": [_peak(m, "snap", "peeq") for m in per_frame],
        "screw_vm_robust": [_peak(m, "screw", "von_mises_MPa") for m in per_frame],
        "board_vm_robust": [_peak(m, "board", "von_mises_MPa") for m in per_frame],
    }
    result["checks"] = {}
    sel = [("final", last)]
    near = int(np.argmin(np.abs(np.array(loads) - OVL_REQUIRED)))
    if near != last:
        sel.insert(0, (f"load_{int(loads[near])}N", near))
    result["_plot_frames"] = sel


# --------------------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------------------


def _fmt(v: Any, nd: int = 3) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, np.integer)):
        return str(v)
    if isinstance(v, (float, np.floating)):
        if math.isnan(float(v)):
            return "n/a"
        if abs(v) >= 100:
            return f"{v:.0f}"
        return f"{v:.{nd}g}"
    return str(v)


def load_results() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in sorted(OUT_ROOT.glob("*/result.json")):
        out[p.parent.name] = json.loads(p.read_text())
    return out


def thread_shear_check(res: dict[str, Any], capacity: float) -> dict[str, Any]:
    from opengrid_build123 import opengrid as og

    snap = res["config"]["snap"]
    proxy = og._blocking_thread_proxy_radius(og.SnapThreadConfig())
    engaged = snap["hub_height"] - 0.2
    mat = MATERIALS[res["material"]]
    cyl = math.pi * 2.0 * proxy * engaged
    out: dict[str, Any] = {"load_N": capacity, "diameter_mm": 2.0 * proxy, "engaged_mm": engaged, "cylinder_area_mm2": cyl}
    for k, label in ((1.0, "full_cylinder"), (0.5, "thread_form_50pct")):
        tau = capacity / (cyl * k)
        out[label] = {"area_fraction": k, "tau_MPa": tau, "limit_MPa": mat.yield_stress / math.sqrt(3.0), "pass": bool(tau <= mat.yield_stress / math.sqrt(3.0))}
    return out


def acceptance(results: dict[str, dict[str, Any]], validation: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(group: str, name: str, value: Any, limit: str, passed: bool | None) -> None:
        rows.append({"case": group, "criterion": name, "value": value, "limit": limit, "pass": passed})

    headline = {"cantilever": "error_vs_EB_pct", "contact": "balance_error_z_pct", "tie": "balance_error_pct"}
    for name, v in validation.items():
        key = headline.get(name, "")
        add("VAL", f"{name}: {v.get('detail', '')} [{key} %]", v.get("metrics", {}).get(key), "<= 5 % (cantilever), <= 1 % (balance)", v["passed"])
    ins = results.get("INS")
    if ins and "checks" in ins:
        c = ins["checks"]
        add("INS", "peak insertion force [N] (contact run, mesh 1.4)", c["insertion_force_N"]["value"], "<= 40", c["insertion_force_N"]["pass"])
        add("INS", "stroke completed", c["stroke_completed"]["value"], "= 1", c["stroke_completed"]["pass"])
        add("INS", "peak leg strain, contact run (mesh 1.4; information, gate is INS-R)", c["peak_leg_strain"]["value"], "<= 0.012", None)
    insr, insf = results.get("INS-R"), results.get("INS-R-fine")
    for tag, r in (("INS-R", insr), ("INS-R-fine", insf)):
        if r and "checks" in r:
            c = r["checks"]
            add(tag, "peak leg max-principal strain (no-contact radial bound)", c["peak_leg_strain"]["value"], "<= 0.012", c["peak_leg_strain"]["pass"])
            add(tag, "peak leg sigma_zz [MPa] (no-contact radial bound)", c["peak_leg_sigma_zz_MPa"]["value"], "<= 25", c["peak_leg_sigma_zz_MPa"]["pass"])
    if insr and insf and "metrics" in insr and "metrics" in insf:
        for fld in ("peak_leg_strain_robust", "peak_leg_sigma_zz_robust_MPa"):
            va, vb = insr["metrics"][fld], insf["metrics"][fld]
            change = abs(vb - va) / max(abs(vb), 1e-9)
            add("INS-R", f"mesh convergence 1.0 vs 0.7: {fld}", change, "< 0.10", bool(change < 0.10))
    for key in ("SVC-A", "SVC-C", "PLA-SVC-A"):
        r = results.get(key)
        if r and "checks" in r:
            for ck, cv in r["checks"].items():
                add(key, ck, cv["value"], f"<= {_fmt(cv['limit'])}", cv["pass"])
    ovl, unb = results.get("OVL"), results.get("UNB")
    if ovl and "capacity" in ovl:
        cap = ovl["capacity"]["load_N"]
        add("OVL", "pull-out capacity [N]", cap, ">= 300", bool(cap >= OVL_REQUIRED))
        ts = thread_shear_check(ovl, cap)
        add("OVL", "thread proxy shear at capacity [MPa] (50 % thread-form area)", ts["thread_form_50pct"]["tau_MPa"], f"<= {_fmt(ts['thread_form_50pct']['limit_MPa'])}", ts["thread_form_50pct"]["pass"])
    if ovl and unb and "capacity" in ovl and "capacity" in unb:
        ratio = unb["capacity"]["load_N"] / ovl["capacity"]["load_N"]
        add("UNB", "unblocked / blocked capacity", ratio, "<= 0.5 (well below)", bool(ratio <= 0.5))
    m0, m1, m2 = results.get("SVC-A-mesh14"), results.get("SVC-A-mesh10"), results.get("SVC-A-mesh07")
    if m1 and m2 and "final_frame" in m1 and "final_frame" in m2:
        pairs = [("lift [mm]", m1["lift_mm"]["snap_total_incl_seating_play"], m2["lift_mm"]["snap_total_incl_seating_play"])]
        for body in ("snap", "screw", "board"):
            pairs.append((f"{body} von Mises, 99.5th pct", m1["final_frame"][body]["von_mises_MPa"]["p99.5"], m2["final_frame"][body]["von_mises_MPa"]["p99.5"]))
        pairs.append(("snap sigma_zz, robust max", m1["final_frame"]["snap"]["sigma_zz_MPa"]["robust"], m2["final_frame"]["snap"]["sigma_zz_MPa"]["robust"]))
        for name, va, vb in pairs:
            change = abs(vb - va) / max(abs(vb), 1e-9)
            add("MESH", f"{name}: mesh 1.0 vs 0.7", change, "< 0.10", bool(change < 0.10))
    if m0 and m1 and "final_frame" in m0 and "final_frame" in m1:
        for body in ("snap", "screw", "board"):
            va, vb = m0["final_frame"][body]["von_mises_MPa"]["robust"], m1["final_frame"][body]["von_mises_MPa"]["robust"]
            add("MESH", f"{body} von Mises, robust max: mesh 1.4 vs 1.0 (information)", abs(vb - va) / max(abs(vb), 1e-9), "< 0.10", None)
    for name in ("SVC-C-mu0", "SVC-C-nogap", "SVC-C-stiffboard"):
        r = results.get(name)
        if r and "lift_mm" in r:
            add("BOUND", f"{name}: total lift [mm] (evidence, not gated)", r["lift_mm"]["snap_total_incl_seating_play"], "<= 0.3", None)
    r = results.get("OVL-mu0")
    if r and "capacity" in r:
        add("BOUND", "OVL-mu0: frictionless pull-out capacity [N] (evidence, not gated)", r["capacity"]["load_N"], ">= 300", None)
    return rows


def overload_table(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Capacity / lift summary of the overload-type cases (OVL, UNB, SENS-*)."""

    out: list[dict[str, Any]] = []
    for name in ("OVL", "UNB", "SENS-010", "SENS-020", "OVL-mu0"):
        r = results.get(name)
        if not r or "capacity" not in r:
            continue
        h = r["history"]
        load = np.asarray(h["load_N"], dtype=float)
        lift = np.asarray(h["snap_total_lift_mm"], dtype=float)
        ok = np.isfinite(load) & np.isfinite(lift)
        lift100 = float(np.interp(100.0, load[ok], lift[ok])) if ok.any() and load[ok].max() >= 100.0 else math.nan
        lift300 = float(np.interp(300.0, load[ok], lift[ok])) if ok.any() and load[ok].max() >= 300.0 else math.nan
        onset = r["capacity"]["onset"]
        out.append(
            {
                "case": name,
                "blocking_clearance": r["config"]["blocking_clearance"] if r["spec"]["shank"] else None,
                "shank": r["spec"]["shank"],
                "friction": r["spec"]["friction"],
                "capacity_N": r["capacity"]["load_N"],
                "criterion": r["capacity"]["criterion"],
                "lift_at_100N_mm": lift100,
                "lift_at_300N_mm": lift300,
                "first_yield_snap_N": onset["snap"]["first_yield_N"],
                "first_yield_board_N": onset["board"]["first_yield_N"],
                "first_interlayer_snap_N": onset["snap"]["first_interlayer_exceedance_N"],
            }
        )
    return out


def write_reports(results: dict[str, dict[str, Any]], validation: dict[str, Any]) -> None:
    rows = acceptance(results, validation)
    ovl_rows = overload_table(results)
    petg_pass = all(r["pass"] for r in rows if r["pass"] is not None)
    summary = {
        "overall_pass": petg_pass,
        "materials": {k: asdict(v) for k, v in MATERIALS.items()},
        "rules": {
            "singular_exclusion": f"nodes closer than {SINGULAR_DISTANCE} mm to a sharp edge (dihedral > {SHARP_EDGE_DEG} deg) are excluded from the 'robust' peak",
            "yield_onset_peeq": YIELD_PEEQ,
            "collapse_lift_mm": LIFT_COLLAPSE,
        },
        "validation": validation,
        "acceptance": rows,
        "overload_table": ovl_rows,
        "cases": {k: {kk: vv for kk, vv in v.items() if kk not in ("curve",)} for k, v in results.items()},
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "summary.json").write_text(json.dumps(_jsonable(summary), indent=1))

    info_file = OUT_ROOT / "run_info.json"
    run_info = json.loads(info_file.read_text()) if info_file.exists() else {}
    md: list[str] = ["# Blocking-pin snap FEA summary", "", f"Overall PETG acceptance: **{'PASS' if petg_pass else 'FAIL'}**", ""]
    if run_info:
        md += [f"Run: `{run_info['command']}`; wall time {run_info['wall_s'] / 3600:.2f} h ({run_info['wall_s']:.0f} s), {run_info['jobs']} jobs x {run_info['threads_per_job']} threads.", ""]
    md += ["## Acceptance", "", "| Case | Criterion | Value | Limit | Result |", "|---|---|---|---|---|"]
    for r in rows:
        res = "n/a" if r["pass"] is None else ("PASS" if r["pass"] else "**FAIL**")
        md.append(f"| {r['case']} | {r['criterion']} | {_fmt(r['value'])} | {r['limit']} | {res} |")
    if ovl_rows:
        md += ["", "## Overload / blocking / sensitivity", "", "| Case | Shank | Clearance [mm] | mu | Capacity [N] | Criterion | Lift @100 N [mm] | Lift @300 N [mm] | First yield snap / board [N] | First interlayer exceedance snap [N] |", "|---|---|---|---|---|---|---|---|---|---|"]
        for o in ovl_rows:
            md.append(
                f"| {o['case']} | {_fmt(o['shank'])} | {_fmt(o['blocking_clearance'])} | {_fmt(o['friction'])} | {_fmt(o['capacity_N'])} | {o['criterion']} | {_fmt(o['lift_at_100N_mm'])} | {_fmt(o['lift_at_300N_mm'])} | {_fmt(o['first_yield_snap_N'])} / {_fmt(o['first_yield_board_N'])} | {_fmt(o['first_interlayer_snap_N'])} |"
            )
    md += ["", "## Cases", "", "| Case | Material | Nodes | ccx time [s] | Key results |", "|---|---|---|---|---|"]
    for name, r in results.items():
        nodes = sum(v["nodes"] for v in r.get("mesh", {}).values())
        key = ""
        if "capacity" in r:
            key = f"capacity {_fmt(r['capacity']['load_N'])} N ({r['capacity']['criterion']})"
        elif r.get("kind") == "ins" and "metrics" in r:
            m = r["metrics"]
            key = f"peak leg strain {_fmt(100 * m['peak_leg_strain_robust'])} %, sigma_zz {_fmt(m['peak_leg_sigma_zz_robust_MPa'])} MPa, force {_fmt(m['peak_insertion_force_N'])} N"
        elif "lift_mm" in r:
            key = f"lift {_fmt(r['lift_mm']['snap_total_incl_seating_play'])} mm"
        md.append(f"| {name} | {r.get('material')} | {nodes} | {_fmt(r['time_s']['ccx'])} | {key} |")
    (OUT_ROOT / "summary.md").write_text("\n".join(md) + "\n")

    h: list[str] = [
        "<!doctype html><meta charset='utf-8'><title>Blocking-pin snap FEA</title>",
        "<style>body{font-family:sans-serif;margin:2em;max-width:1500px}img{max-width:100%;border:1px solid #ccc;margin:4px}"
        "table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:3px 8px;text-align:left}.fail{color:#b00;font-weight:bold}.pass{color:#080}</style>",
        f"<h1>Blocking-pin snap FEA</h1><p>Overall PETG acceptance: <b class='{'pass' if petg_pass else 'fail'}'>{'PASS' if petg_pass else 'FAIL'}</b>"
        " &mdash; <a href='summary.md'>summary.md</a>, <a href='summary.json'>summary.json</a></p>",
        "<h2>Acceptance</h2><table><tr><th>Case<th>Criterion<th>Value<th>Limit<th>Result</tr>",
    ]
    for r in rows:
        cls = "" if r["pass"] is None else ("pass" if r["pass"] else "fail")
        word = "n/a" if r["pass"] is None else ("PASS" if r["pass"] else "FAIL")
        h.append(f"<tr><td>{html.escape(r['case'])}<td>{html.escape(r['criterion'])}<td>{_fmt(r['value'])}<td>{html.escape(str(r['limit']))}<td class='{cls}'>{word}</tr>")
    h.append("</table><h2>Cases</h2><ul>")
    for name in results:
        h.append(f"<li><a href='#{html.escape(name)}'>{html.escape(name)}</a> &mdash; {html.escape(results[name].get('title', ''))}")
    h.append("</ul>")
    for name, r in results.items():
        h.append(f"<h3 id='{html.escape(name)}'>{html.escape(name)}: {html.escape(r.get('title', ''))} ({r.get('material')})</h3>")
        h.append(f"<p><a href='{html.escape(name)}/result.json'>result.json</a></p>")
        for img in r.get("images", []):
            h.append(f"<a href='{html.escape(name)}/{html.escape(img)}'><img src='{html.escape(name)}/{html.escape(img)}' width='700' title='{html.escape(img)}'></a>")
    (OUT_ROOT / "index.html").write_text("\n".join(h) + "\n")


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

CASE_ORDER = ("OVL", "SVC-C", "SVC-A", "UNB", "SENS", "PLA", "INS", "INSR", "MESH", "BOUND")


def run_validation(threads: int, log: Callable[[str], None]) -> dict[str, Any]:
    work = OUT_ROOT / "validation"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    out: dict[str, Any] = {}
    for fn in (validate_cantilever, validate_contact, validate_tie):
        t0 = time.time()
        try:
            r = fn(work, threads)
            entry = {"passed": r.passed, "metrics": r.metrics, "detail": r.detail, "seconds": time.time() - t0}
        except Exception as exc:  # report, do not hide
            entry = {"passed": False, "metrics": {}, "detail": f"{type(exc).__name__}: {exc}", "seconds": time.time() - t0}
        out[entry_name(fn)] = entry
        log(f"  validation {entry_name(fn)}: {'PASS' if entry['passed'] else 'FAIL'} {json.dumps(_jsonable(entry['metrics']))}")
    (work / "validation.json").write_text(json.dumps(_jsonable(out), indent=1))
    return out


def entry_name(fn: Callable[..., Any]) -> str:
    return fn.__name__.removeprefix("validate_")


def _run_case_worker(args: tuple[CaseSpec, int, bool]) -> dict[str, Any]:
    spec, threads, keep = args
    return run_case(spec, threads, lambda m: print(m, flush=True), keep)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", nargs="+", default=["all"], help=f"case names ({', '.join(CASE_ORDER)}), VALIDATE, or all")
    ap.add_argument("--material", choices=sorted(MATERIALS), help="override the material of the selected cases (case name gets a suffix)")
    ap.add_argument("--threads", type=int, default=os.cpu_count() or 1, help="threads per ccx run (OMP_NUM_THREADS / CCX_NPROC_EQUATION_SOLVER)")
    ap.add_argument("--jobs", type=int, default=1, help="cases solved concurrently (threads are divided between them)")
    ap.add_argument("--mesh-scale", type=float, default=None, help="multiply all mesh sizes (default 1.0)")
    ap.add_argument("--friction", type=float, default=None, help="override the friction coefficient (default 0.3)")
    ap.add_argument("--set", nargs="*", default=[], metavar="FIELD=VALUE", help="override BlockingPinSnapConfig fields (design tuning), e.g. ledge_reach=13.05")
    ap.add_argument("--kscale", type=float, default=None, help="multiply the contact penalty slope")
    ap.add_argument("--stick", type=float, default=None, help="friction stick slope as a fraction of the penalty slope")
    ap.add_argument("--clearance", type=float, default=None, help="override MulticonnectBlockingScrewConfig.blocking_clearance")
    ap.add_argument("--tag", default="", help="suffix for the output case directories (exploration runs)")
    ap.add_argument("--keep-frd", action="store_true", help="keep the (large) .frd result files")
    ap.add_argument("--no-solve", action="store_true", help="re-post-process existing ccx results of the selected cases (needs --keep-frd runs)")
    ap.add_argument("--report-only", action="store_true", help="only regenerate summary / index from existing results")
    args = ap.parse_args(argv)
    t_start = time.time()

    names = list(CASE_ORDER) + ["VALIDATE"] if "all" in args.case else list(args.case)
    reg = case_registry()
    unknown = [n for n in names if n not in reg and n != "VALIDATE"]
    if unknown:
        ap.error(f"unknown case(s): {unknown}")
    log = lambda m: print(m, flush=True)  # noqa: E731
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    vfile = OUT_ROOT / "validation" / "validation.json"
    if not args.report_only:
        if "VALIDATE" in names:
            log("validation cases")
            run_validation(min(args.threads, 8), log)
        specs: list[CaseSpec] = []
        for n in names:
            if n == "VALIDATE":
                continue
            for spec in reg[n]:
                if args.material and args.material != spec.material:
                    spec = replace(spec, name=f"{spec.name}-{args.material}", material=args.material)
                if args.mesh_scale is not None:
                    spec = replace(spec, mesh_scale=args.mesh_scale)
                if args.friction is not None:
                    spec = replace(spec, friction=args.friction)
                if args.kscale is not None:
                    spec = replace(spec, k_scale=args.kscale)
                if args.stick is not None:
                    spec = replace(spec, stick_ratio=args.stick)
                if args.set:
                    extra = tuple((k, float(v)) for k, v in (item.split("=") for item in args.set))
                    spec = replace(spec, snap_overrides=spec.snap_overrides + extra)
                if args.clearance is not None:
                    spec = replace(spec, blocking_clearance=args.clearance)
                if args.tag:
                    spec = replace(spec, name=f"{spec.name}~{args.tag}")
                specs.append(spec)
        if args.jobs <= 1:
            for spec in specs:
                run_case(spec, args.threads, log, args.keep_frd or args.no_solve, not args.no_solve)
        elif specs:
            import multiprocessing as mp
            from concurrent.futures import ProcessPoolExecutor

            per = max(1, args.threads // args.jobs)
            with ProcessPoolExecutor(args.jobs, mp_context=mp.get_context("spawn")) as ex:
                list(ex.map(_run_case_worker, [(sp, per, args.keep_frd) for sp in specs]))
    if not args.report_only:
        (OUT_ROOT / "run_info.json").write_text(
            json.dumps({"command": "examples/simulate_blocking_pin.py " + " ".join(argv if argv is not None else sys.argv[1:]), "wall_s": time.time() - t_start, "jobs": args.jobs, "threads_per_job": max(1, args.threads // max(1, args.jobs))}, indent=1)
        )
    validation = json.loads(vfile.read_text()) if vfile.exists() else {}
    write_reports(load_results(), validation)
    log(f"reports written to {OUT_ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
