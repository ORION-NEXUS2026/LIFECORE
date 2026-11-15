# Credits and licenses

## Code
Lifecore source code is released under the [MIT License](LICENSE).

## 3D anatomy (not MIT)
- **BodyParts3D** (c) Database Center for Life Science (DBCLS), licensed **CC BY 4.0**.
  Mitsuhashi N. et al., *BodyParts3D: 3D structure database for anatomical concepts*, Nucleic Acids Research, 2009.
  https://creativecommons.org/licenses/by/4.0/
- The body model (`app/static/hologram/body.bin`, `body.json`) was extracted and simplified from BodyParts3D with
  `tools/build_body.py`, using the atlas packaged by *Human Atlas* (github.com/slorksmo/human-atlas, MIT).
  Changes made: selected structures only, merged into a few groups, genital structures removed, geometry quantized.
- The anatomical heart (`app/static/hologram/heart.glb`) comes from *heart-anatomy-lab*
  (github.com/niyaz-05/heart-anatomy-lab), which is itself derived from the BodyParts3D adult male reference heart.
  Its application code is not used here; only the BodyParts3D-derived model.

If you reuse these models, keep this attribution.

## Libraries
Streamlit, pandas, NumPy, Plotly (Python); Three.js (MIT) for the hologram; esbuild to bundle it.

## Reference values
Heart-rate ranges and spaceflight values are taken from NASA and Mayo Clinic publications. See
[docs/nasa-references.md](docs/nasa-references.md) for the exact numbers and sources.
