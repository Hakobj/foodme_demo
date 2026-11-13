"""Unit tests for the infrastructure helpers: support/config.py (env overrides), support/servers.py
(health check, dev-server start/stop) and the folder -> marker mapping (support/markers.py).
Network and processes are mocked."""

import importlib
from unittest.mock import MagicMock

import pytest
import requests

from support import config, servers
from support.markers import suite_markers

# ---- support/config.py --------------------------------------------------------------------


@pytest.fixture
def reload_config(monkeypatch):
    """Reloads support.config with the env the test sets, then restores the real values."""
    for name in ("VITE_API_BASE_URL", "PLAYWRIGHT_BASE_URL", "ADMIN_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    yield lambda: importlib.reload(config)
    monkeypatch.undo()
    importlib.reload(config)


def test_config_defaults_point_to_local_ports(reload_config):
    cfg = reload_config()

    assert cfg.API_BASE_URL == "http://localhost:8081"
    assert cfg.WEB_BASE_URL == "http://localhost:5180"
    assert cfg.ADMIN_BASE_URL == "http://localhost:5174"


def test_config_env_override_strips_trailing_slash(monkeypatch, reload_config):
    monkeypatch.setenv("VITE_API_BASE_URL", "https://api.example.com/")
    monkeypatch.setenv("ADMIN_BASE_URL", "https://admin.example.com//")

    cfg = reload_config()

    assert cfg.API_BASE_URL == "https://api.example.com"
    assert cfg.ADMIN_BASE_URL == "https://admin.example.com"


# ---- support/servers.is_up ----------------------------------------------------------------


@pytest.mark.parametrize(("status", "expected"), [(200, True), (404, True), (499, True), (500, False), (503, False)])
def test_is_up_treats_only_5xx_as_down(monkeypatch, status, expected):
    get = MagicMock(return_value=MagicMock(status_code=status))
    monkeypatch.setattr(servers.requests, "get", get)

    assert servers.is_up("http://x.test/health") is expected
    get.assert_called_once_with("http://x.test/health", timeout=2)


@pytest.mark.parametrize("error", [requests.ConnectionError, requests.Timeout])
def test_is_up_returns_false_on_network_error(monkeypatch, error):
    monkeypatch.setattr(servers.requests, "get", MagicMock(side_effect=error()))

    assert servers.is_up("http://x.test") is False


# ---- support/servers.ensure_dev_server / stop -------------------------------------------


def test_ensure_dev_server_already_up_starts_nothing(monkeypatch):
    spawn = MagicMock()
    monkeypatch.setattr(servers, "is_up", lambda url: True)
    monkeypatch.setattr(servers, "_spawn", spawn)

    assert servers.ensure_dev_server("http://localhost:5180", app="web", port=5180) is None
    spawn.assert_not_called()


def test_ensure_dev_server_without_node_modules_raises(monkeypatch, tmp_path):
    (tmp_path / "apps" / "web").mkdir(parents=True)
    monkeypatch.setattr(servers, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(servers, "is_up", lambda url: False)

    with pytest.raises(RuntimeError, match="node_modules is missing"):
        servers.ensure_dev_server("http://localhost:5180", app="web", port=5180)


def test_ensure_dev_server_spawns_vite_on_strict_port_and_returns_process(monkeypatch, tmp_path):
    app_dir = tmp_path / "apps" / "admin"
    (app_dir / "node_modules").mkdir(parents=True)
    monkeypatch.setattr(servers, "REPO_ROOT", tmp_path)
    checks = iter([False, True])  # down before start, up on the first poll
    monkeypatch.setattr(servers, "is_up", lambda url: next(checks))
    proc = MagicMock()
    spawn = MagicMock(return_value=proc)
    monkeypatch.setattr(servers, "_spawn", spawn)

    assert servers.ensure_dev_server("http://localhost:5174", app="admin", port=5174) is proc
    spawn.assert_called_once_with("npm run dev -- --port 5174 --strictPort", app_dir)


def test_ensure_dev_server_process_exit_raises_with_code(monkeypatch, tmp_path):
    (tmp_path / "apps" / "web" / "node_modules").mkdir(parents=True)
    monkeypatch.setattr(servers, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(servers, "is_up", lambda url: False)
    proc = MagicMock(returncode=1)
    proc.poll.return_value = 1
    monkeypatch.setattr(servers, "_spawn", MagicMock(return_value=proc))

    with pytest.raises(RuntimeError, match="exited with code 1"):
        servers.ensure_dev_server("http://localhost:5180", app="web", port=5180)


def test_ensure_dev_server_timeout_stops_process_and_raises(monkeypatch, tmp_path):
    (tmp_path / "apps" / "web" / "node_modules").mkdir(parents=True)
    monkeypatch.setattr(servers, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(servers, "is_up", lambda url: False)
    proc = MagicMock()
    proc.poll.return_value = None
    monkeypatch.setattr(servers, "_spawn", MagicMock(return_value=proc))
    stop = MagicMock()
    monkeypatch.setattr(servers, "stop", stop)

    with pytest.raises(RuntimeError, match="did not start"):
        servers.ensure_dev_server("http://localhost:5180", app="web", port=5180, timeout=0)
    stop.assert_called_once_with(proc)


def test_stop_none_does_nothing(monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(servers.subprocess, "run", run)

    servers.stop(None)

    run.assert_not_called()


def test_stop_already_exited_process_does_nothing(monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(servers.subprocess, "run", run)
    proc = MagicMock()
    proc.poll.return_value = 0

    servers.stop(proc)

    run.assert_not_called()


def test_stop_on_windows_kills_the_process_tree(monkeypatch):
    monkeypatch.setattr(servers.sys, "platform", "win32")
    run = MagicMock()
    monkeypatch.setattr(servers.subprocess, "run", run)
    proc = MagicMock(pid=1234)
    proc.poll.return_value = None

    servers.stop(proc)

    run.assert_called_once_with(["taskkill", "/PID", "1234", "/T", "/F"], capture_output=True, check=False)


# ---- support/markers.suite_markers -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("parts", "expected"),
    [
        (("unit", "test_x.py"), ("unit",)),
        (("integration", "test_order_api.py"), ("integration", "api")),
        (("e2e", "web", "test_layout.py"), ("e2e", "web")),
        (("e2e", "admin", "test_admin_flows.py"), ("e2e", "admin")),
        (("e2e", "test_loose.py"), ()),
        (("other", "test_x.py"), ()),
    ],
)
def test_suite_markers_follow_the_folder(parts, expected):
    assert suite_markers(parts) == expected
