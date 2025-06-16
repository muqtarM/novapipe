import sys
import types
import pytest
from click.testing import CliRunner
from importlib.metadata import EntryPoint, Distribution

from novapipe.cli import cli
from novapipe.tasks import task_registry, load_plugins, set_plugin_pins


# Setup fake plugins
@pytest.fixture(autouse=True)
def fake_plugins(monkeypatch):
    # Dist A provides fetch_data
    modA = types.ModuleType("fakeA")
    def fetch_data(params): pass
    modA.fetch_data = fetch_data
    sys.modules["fakeA"] = modA
    epA = EntryPoint(name="fetch_data", value="fakeA:fetch_data", group="novapipe.plugins")
    distA = Distribution(name="distA", version="1.0.0")
    monkeypatch.setattr(distA, "entry_points", [epA])

    # Dist B provides load_data
    modB = types.ModuleType("fakeB")
    def load_data(params): pass
    modB.load_data = load_data
    sys.modules["fakeB"] = modB
    epB = EntryPoint(name="load_data", value="fakeB:load_data", group="novapipe.plugins")
    distB = Distribution(name="distB", version="2.0.0")
    monkeypatch.setattr(distB, "entry_points", [epB])

    # Patch distributions()
    monkeypatch.setattr(
        "novapipe.cli.distributions",
        lambda: [distA, distB],
        raising=False,
    )
    # Ensure registry is reset
    task_registry.clear()
    set_plugin_pins({})
    yield
    for m in ("fakeA", "fakeB"):
        sys.modules.pop(m, None)
    task_registry.clear()
    set_plugin_pins({})


def test_list_no_filter_shows_all():
    runner = CliRunner()
    result = runner.invoke(cli, ["plugin", "list"])
    assert result.exit_code == 0
    out = result.output
    assert "distA (v1.0.0)" in out
    assert "fetch_data" in out
    assert "distB (v2.0.0)" in out
    assert "load_data" in out


def test_list_dist_filter():
    runner = CliRunner()
    result = runner.invoke(cli, ["plugin", "list", "--dist", "distA"])
    out = result.output
    assert "distA (v1.0.0)" in out
    assert "fetch_data" in out
    assert "distB" not in out


def test_list_task_filter():
    runner = CliRunner()
    result = runner.invoke(cli, ["plugin", "list", "--task", "load"])
    out = result.output
    assert "distB (v2.0.0)" in out
    assert "load_data" in out
    assert "fetch_data" not in out


def test_list_source_filter():
    runner = CliRunner()
    result = runner.invoke(cli, ["plugin", "list", "--source", "fakeA"])
    out = result.output
    assert "distA (v1.0.0)" in out
    assert "fetch_data" in out
    assert "distB" not in out
