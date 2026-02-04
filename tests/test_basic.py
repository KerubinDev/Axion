def test_version():
    from akita import __version__
    assert __version__ == "1.1.0"

def test_cli_import():
    from akita.cli.main import app
    assert app.registered_commands is not None
