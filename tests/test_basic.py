def test_version():
    import tomli
    from pathlib import Path
    from akita import __version__
    
    # Locate pyproject.toml relative to this test file
    root_dir = Path(__file__).parent.parent
    pyproject_path = root_dir / "pyproject.toml"
    
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomli.load(f)
        
    project_version = pyproject_data["project"]["version"]
    assert __version__ == project_version, "Module version does not match pyproject.toml"

def test_cli_import():
    from akita.cli.main import app
    assert app.registered_commands is not None
