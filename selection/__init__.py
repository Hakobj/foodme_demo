"""Selection Based Testing (test impact analysis) for the Python e2e suite.

- `impact.py`        records, per e2e test, which front-end modules ran (V8 coverage over CDP),
                     which API endpoints were called (the in-memory mock) and which Python helpers ran
- `backend.py`       maps changed Spring Boot files to the REST endpoints they can affect
- `selector.py`      turns a git diff + the impact map into the list of tests to run
- `evaluate.py`      measures a selection: mutation benchmark, shadow-mode audit, history replay
- `pytest_plugin.py` `--collect-impact` / `--select-from` options for pytest
- `rules.py`         the policy: run-all files, ignored files, fallbacks, always-run smoke tests

Entry point: `python -m selection --help`. See selection/README.md.
"""
