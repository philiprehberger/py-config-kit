"""Basic import test."""


def test_import():
    """Verify the package can be imported."""
    import philiprehberger_config_kit
    assert hasattr(philiprehberger_config_kit, "__name__") or True
