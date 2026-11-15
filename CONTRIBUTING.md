# Contributing to Lifecore

Lifecore is open source (MIT) and welcomes contributors: software, firmware, hardware (3D-printed enclosures), docs and ideas.

## Ways to help
- **Bugs and ideas:** open an issue (templates provided).
- **Code:** analysis rules, forecasting, the Streamlit pages, the hologram (Three.js), the ESP32 firmware.
- **Hardware:** enclosure designs (`hardware/stl/`), wiring photos, alternative sensors.
- **Docs and translations:** the UI text is in Spanish; an English UI would be a great contribution.
- **Science:** better reference values from NASA or peer-reviewed papers (with links) in `docs/nasa-references.md`.

## Workflow
1. Fork the repository and create a branch: `git checkout -b feature/short-name`.
2. Run the app locally (see the README) and run the tests: `python tests/test_analysis.py`.
3. Keep changes focused. Add or update tests when you change `app/analysis.py` or the synthetic data.
4. Commit with a clear message ("Add X", "Fix Y") and open a pull request using the template.
5. A maintainer reviews it; small fixes are usually merged quickly.

## Ground rules
- **Never commit secrets or personal data:** `firmware/esp32_wifi/secrets.h` and `data/sensor_log.csv` are git-ignored.
- **Keep the honesty labels:** data are synthetic and this is not a medical device. Do not present any value as a clinical measurement.
- **Cite sources** for any physiological value you add, and mark your own assumptions as assumptions.
- **Licenses:** contributions are accepted under the MIT License. 3D anatomy models keep their own license (see CREDITS.md).
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Adding collaborators (maintainers)
Repository **Settings -> Collaborators -> Add people**, or accept pull requests from forks. Protect `main` with
**Settings -> Branches** (require a pull request review before merging) once there are several people.
