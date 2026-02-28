"""Tests for pgtail_py.instance module."""

from pathlib import Path

from pgtail_py.instance import DetectionSource, Instance


class TestInstanceConfigPath:
    """Tests for Instance.config_path field."""

    def test_config_path_defaults_to_none(self) -> None:
        """config_path defaults to None when not specified."""
        inst = Instance(
            id=0,
            version="17",
            data_dir=Path("/var/lib/postgresql/17/main"),
            log_path=None,
            log_directory=None,
            source=DetectionSource.KNOWN_PATH,
            running=False,
        )
        assert inst.config_path is None

    def test_config_path_can_be_set(self) -> None:
        """config_path can be set to a Path."""
        conf = Path("/etc/postgresql/17/main/postgresql.conf")
        inst = Instance(
            id=0,
            version="17",
            data_dir=Path("/var/lib/postgresql/17/main"),
            log_path=None,
            log_directory=None,
            source=DetectionSource.KNOWN_PATH,
            running=False,
            config_path=conf,
        )
        assert inst.config_path == conf

    def test_file_only_has_no_config_path(self) -> None:
        """Instance.file_only() creates instance with config_path=None."""
        inst = Instance.file_only(Path("/tmp/test.log"))
        assert inst.config_path is None

    def test_backward_compat_existing_fields(self) -> None:
        """Adding config_path doesn't break existing field access."""
        inst = Instance(
            id=0,
            version="16",
            data_dir=Path("/data"),
            log_path=Path("/data/log/pg.log"),
            log_directory=Path("/data/log"),
            source=DetectionSource.PROCESS,
            running=True,
            pid=1234,
            port=5432,
            logging_enabled=True,
        )
        assert inst.id == 0
        assert inst.version == "16"
        assert inst.running is True
        assert inst.pid == 1234
        assert inst.port == 5432
        assert inst.logging_enabled is True
        assert inst.config_path is None
