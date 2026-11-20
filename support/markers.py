"""Maps a test's folder (unit/, integration/, e2e/...) to its pytest markers (used by the root conftest)."""

# Folder -> markers. `api` / `web` / `admin` are kept so existing commands still work.
SUITE_MARKERS = {
    ("unit",): ("unit",),
    ("integration",): ("integration", "api"),
    ("e2e", "web"): ("e2e", "web"),
    ("e2e", "admin"): ("e2e", "admin"),
}


def suite_markers(parts: tuple[str, ...]) -> tuple[str, ...]:
    """Markers for a test file, from its path parts relative to tests-python/ (e.g. ("e2e", "web", "test_x.py"))."""
    for prefix, markers in SUITE_MARKERS.items():
        if parts[: len(prefix)] == prefix:
            return markers
    return ()
