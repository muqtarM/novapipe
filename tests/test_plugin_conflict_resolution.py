import sys
import types
import pytest
from importlib.metadata import EntryPoint

from novapipe.tasks import (
    task_registry,
    load_plugins,
    set_plugin_pins,
)

# --- Helpers to simulate distributions and entry-points ---


class DummyDist:
    def __init__(self, name, version, entry_points):
        # mimic importlib.metadata.Distribution
        self.name = name
        self.version = version
        self.metadata = {"Name": name}
        self._eps = entry_points

    @property
    def entry_points(self):
        return self._eps


@pytest.fixture(autouse=True)
def fake_distributions(monkeypatch):
    """
    Monkey-patch novapipe.tasks.distributions() to return our dummy dists.
    Each dist registers an entry-point group 'novapipe.plugins'.
    """
    def _fake_distributions():
        # Module A
        modA = types.ModuleType("fake_mod_a")
        def foo_a(params): return "from A"
        modA.foo = foo_a
        sys.modules["fake_mod_a"] = modA
        epA = EntryPoint(name="foo", value="fake_mod_a:foo", group="novapipe.plugins")

        # Module B
        modB = types.ModuleType("fake_mod_b")
        def foo_b(params): return "from B"
        modB.foo = foo_b
        sys.modules["fake_mod_b"] = modB
        epB = EntryPoint(name="foo", value="fake_mod_b:foo", group="novapipe.plugins")

        distA = DummyDist("pluginA", "1.0.0", [epA])
        distB = DummyDist("pluginB", "2.0.0", [epB])
        return [distA, distB]

    # Patch the distributions function in novapipe.tasks
    monkeypatch.setattr(
        "novapipe.tasks.distributions",
        _fake_distributions,
        raising=True,
    )
    # Ensure task_registry is clean before each test
    task_registry.clear()
    # Also clear any previous pins
    set_plugin_pins({})
    yield
    # cleanup
    task_registry.clear()
    set_plugin_pins({})
    for m in ("fake_mod_a", "fake_mod_b"):
        sys.modules.pop(m, None)


def test_conflict_without_pin_raises():
    # No pins set → load_plugins should error on foo collision
    with pytest.raises(RuntimeError) as exc:
        load_plugins()
    msg = str(exc.value)
    assert "Task 'foo' is provided by multiple plugins" in msg
    assert "pluginA==1.0.0" in msg and "pluginB==2.0.0" in msg


def test_conflict_with_correct_pin(monkeypatch):
    # Pin pluginA==1.0.0, so foo should come from fake_mod_a.foo
    set_plugin_pins({"pluginA": "1.0.0"})
    load_plugins()
    assert "foo" in task_registry
    assert task_registry["foo"].__module__ == "fake_mod_a"
    # Calling it works:
    assert task_registry["foo"]({}) == "from A"


def test_conflict_with_wrong_pin_raises():
    # Pin pluginA to a non-existent version
    set_plugin_pins({"pluginA": "9.9.9"})
    with pytest.raises(RuntimeError) as exc:
        load_plugins()
    msg = str(exc.value)
    assert "Pin one with --plugin-version" in msg


def test_no_conflict_registers_normally(monkeypatch):
    # Simulate only one plugin providing 'bar'
    def one_dist():
        modC = types.ModuleType("fake_mod_c")
        def bar(params): return "C"
        modC.bar = bar
        sys.modules["fake_mod_c"] = modC
        ep = EntryPoint(name="bar", value="fake_mod_c:bar", group="novapipe.plugins")
        return [DummyDist("pluginC", "3.0.0", [ep])]

    monkeypatch.setattr("novapipe.tasks.distributions", one_dist, raising=True)
    task_registry.clear()
    set_plugin_pins({})
    load_plugins()
    assert "bar" in task_registry
    assert task_registry["bar"].__module__ == "fake_mod_c"
    assert task_registry["bar"]({}) == "C"
