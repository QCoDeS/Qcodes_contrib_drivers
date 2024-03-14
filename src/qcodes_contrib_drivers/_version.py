def _get_version() -> str:
    from pathlib import Path

    import versioningit

    import qcodes_contrib_drivers

    path = Path(qcodes_contrib_drivers.__file__).parent
    return versioningit.get_version(project_dir=path.parent.parent)


__version__ = _get_version()
