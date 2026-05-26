# Checklist

## Feature acceptance criteria

- [x] Implementation satisfies the source-derived behavior and public API contract for the feature.
- [x] Targeted tests cover the changed behavior, edge cases, and expected failure modes.
- [x] Example/config changes are kept in lockstep with generated objects and exported paths.
- [x] Visual verification artifacts are regenerated for affected geometry under `output/verification/<component>/`.
- [x] A visual pass compares generated galleries against source-derived calculations and reference renders when a reference generator exists.
- [x] The top-level verification index links every generated component gallery.
- [x] Numeric SVG/projection or bounding-box checks cover the visual variants added for the feature.
