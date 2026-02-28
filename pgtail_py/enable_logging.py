"""Enable logging_collector for PostgreSQL instances."""

from pathlib import Path
from typing import NamedTuple


class ConfigUpdate(NamedTuple):
    """Result of a configuration update."""

    success: bool
    message: str
    changes: list[str]


def read_postgresql_conf(conf_path: Path) -> dict[str, str]:
    """Parse postgresql.conf into a dictionary.

    Args:
        conf_path: Path to postgresql.conf file.

    Returns:
        Dictionary of setting name -> value (with quotes stripped).

    Raises:
        FileNotFoundError: If conf file doesn't exist.
        PermissionError: If conf file is not readable.
    """
    settings: dict[str, str] = {}

    with conf_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse setting = value
            if "=" in line:
                # Handle inline comments: setting = value # comment
                if "#" in line:
                    line = line[: line.index("#")].strip()

                name, _, value = line.partition("=")
                name = name.strip()
                value = value.strip()

                # Strip quotes from value
                if (
                    value.startswith("'")
                    and value.endswith("'")
                    or value.startswith('"')
                    and value.endswith('"')
                ):
                    value = value[1:-1]

                settings[name] = value

    return settings


def write_postgresql_conf(conf_path: Path, settings: dict[str, str]) -> list[str]:
    """Update postgresql.conf with new settings.

    Preserves existing file structure, only modifying/adding specified settings.

    Args:
        conf_path: Path to postgresql.conf file.
        settings: Dictionary of setting name -> value to set.

    Returns:
        List of changes made (for reporting).

    Raises:
        FileNotFoundError: If conf file doesn't exist.
        PermissionError: If conf file is not writable.
    """
    changes: list[str] = []
    remaining_settings = dict(settings)
    lines: list[str] = []

    with conf_path.open("r", encoding="utf-8") as f:
        original_lines = f.readlines()

    for line in original_lines:
        stripped = line.strip()

        # Check if this is a setting line we need to update
        if "=" in stripped and not stripped.startswith("#"):
            # Extract setting name
            name = stripped.partition("=")[0].strip()

            if name in remaining_settings:
                new_value = remaining_settings.pop(name)
                # Preserve leading whitespace
                indent = line[: len(line) - len(line.lstrip())]
                lines.append(f"{indent}{name} = '{new_value}'\n")
                changes.append(f"Updated {name} = '{new_value}'")
                continue

        # Check for commented-out version of settings we need
        if stripped.startswith("#") and "=" in stripped:
            # Extract setting name from comment
            uncommented = stripped[1:].strip()
            name = uncommented.partition("=")[0].strip()

            if name in remaining_settings:
                new_value = remaining_settings.pop(name)
                indent = line[: len(line) - len(line.lstrip())]
                # Add new line after the commented one
                lines.append(line)
                lines.append(f"{indent}{name} = '{new_value}'\n")
                changes.append(f"Enabled {name} = '{new_value}'")
                continue

        lines.append(line)

    # Append any remaining settings at the end
    if remaining_settings:
        lines.append("\n# Logging settings added by pgtail\n")
        for name, value in remaining_settings.items():
            lines.append(f"{name} = '{value}'\n")
            changes.append(f"Added {name} = '{value}'")

    # Write back
    with conf_path.open("w", encoding="utf-8") as f:
        f.writelines(lines)

    return changes


def enable_logging(data_dir: Path, config_path: Path | None = None) -> ConfigUpdate:
    """Enable logging_collector for a PostgreSQL instance.

    Updates postgresql.conf to set:
    - logging_collector = on
    - log_directory = 'log' (if not set)
    - log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log' (if not set)

    Handles both standard PostgreSQL layout (config in data_dir) and
    Debian/Ubuntu layout (config in /etc/postgresql/<ver>/<cluster>/).

    Args:
        data_dir: PostgreSQL data directory.
        config_path: Explicit path to postgresql.conf (from Instance.config_path).
            If None, uses find_postgresql_conf() to locate it.

    Returns:
        ConfigUpdate with success status, message, and list of changes.
    """
    from pgtail_py.detector import find_postgresql_conf
    from pgtail_py.permission_advice import get_conf_permission_advice

    # Find postgresql.conf - try explicit path, then auto-detect
    conf_path = config_path or find_postgresql_conf(data_dir)

    # Check conf exists
    if conf_path is None or not conf_path.exists():
        # List the paths we checked for a helpful error message
        checked_paths = [str(data_dir / "postgresql.conf")]
        # Also mention Debian path if applicable
        import re

        match = re.search(r"^/var/lib/postgresql/(\d+)/([^/]+)/?$", str(data_dir))
        if match:
            version = match.group(1)
            cluster = match.group(2)
            checked_paths.append(f"/etc/postgresql/{version}/{cluster}/postgresql.conf")
        paths_str = "\n  ".join(checked_paths)
        return ConfigUpdate(
            success=False,
            message=f"postgresql.conf not found.\n\nChecked:\n  {paths_str}",
            changes=[],
        )

    try:
        # Read current settings
        current = read_postgresql_conf(conf_path)
    except PermissionError:
        advice = get_conf_permission_advice(str(conf_path))
        advice_str = "\n".join(advice)
        return ConfigUpdate(
            success=False,
            message=f"Permission denied reading {conf_path}\n\n{advice_str}",
            changes=[],
        )

    # Determine what needs to change
    updates: dict[str, str] = {}

    # Always enable logging_collector
    if current.get("logging_collector") != "on":
        updates["logging_collector"] = "on"

    # Set log_directory if not configured
    if "log_directory" not in current:
        updates["log_directory"] = "log"

    # Set log_filename if not configured
    if "log_filename" not in current:
        updates["log_filename"] = "postgresql-%Y-%m-%d_%H%M%S.log"

    if not updates:
        return ConfigUpdate(
            success=True,
            message="Logging is already enabled",
            changes=[],
        )

    # Apply updates
    try:
        changes = write_postgresql_conf(conf_path, updates)
    except PermissionError:
        advice = get_conf_permission_advice(str(conf_path))
        advice_str = "\n".join(advice)
        return ConfigUpdate(
            success=False,
            message=f"Permission denied writing to {conf_path}\n\n{advice_str}",
            changes=[],
        )

    # Create log directory if needed
    log_dir = data_dir / updates.get("log_directory", current.get("log_directory", "log"))
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True)
            changes.append(f"Created directory {log_dir}")
        except PermissionError:
            changes.append(f"Note: Could not create {log_dir} - you may need to create it manually")

    return ConfigUpdate(
        success=True,
        message="Logging enabled successfully",
        changes=changes,
    )
