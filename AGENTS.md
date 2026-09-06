# Repository guidance

- Do not push commits unless the user explicitly asks you to push.
- This is a collection. Each `skills/<name>/` is independently installable and must not depend on sibling files or a particular user's home directory.
- Keep the Blender workflow one skill, with conditional references for providers, modeling, rigging, and animation.
- Changes to reference or approval handling need behavioral tests. Never treat test approval fixtures as real user approval.
- Use mocked provider responses for routine tests. Live generation needs an explicitly selected provider and authorized use; never print or commit secrets.
- Run `python3 scripts/validate_skills.py` and `python3 -m unittest discover -s tests -v`. Run `python3 tests/blender_smoke.py --blender blender` for Blender-helper changes when Blender is installed.
