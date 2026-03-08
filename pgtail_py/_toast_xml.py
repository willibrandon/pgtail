"""Toast notification XML builder with severity-based templates.

Builds XML strings conforming to the Windows toast notification schema.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Expiration time defaults (seconds)
# ---------------------------------------------------------------------------

EXPIRY_SECONDS: dict[str, int | None] = {
    "info": 120,       # 2 minutes
    "warning": 600,    # 10 minutes
    "error": 1800,     # 30 minutes
    "critical": None,  # never expires
}

# ---------------------------------------------------------------------------
# Severity template configuration
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, dict] = {
    "info": {
        "duration": "short",
        "scenario": None,
        "audio_src": "ms-winsoundevent:Notification.Default",
        "audio_loop": False,
        "attribution": None,
    },
    "warning": {
        "duration": "short",
        "scenario": None,
        "audio_src": "ms-winsoundevent:Notification.Default",
        "audio_loop": False,
        "attribution": "Warning",
    },
    "error": {
        "duration": "long",
        "scenario": None,
        "audio_src": "ms-winsoundevent:Notification.Default",
        "audio_loop": False,
        "attribution": "Error",
    },
    "critical": {
        "duration": "long",
        "scenario": "alarm",
        "audio_src": "ms-winsoundevent:Notification.Looping.Alarm",
        "audio_loop": True,
        "attribution": "Critical",
    },
}

# ---------------------------------------------------------------------------
# XML escaping
# ---------------------------------------------------------------------------

_XML_ESCAPE_TABLE = str.maketrans({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
})


def escape_xml(text: str) -> str:
    """Escape text for safe inclusion in XML."""
    return text.translate(_XML_ESCAPE_TABLE)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_toast_xml(
    title: str,
    body: str,
    subtitle: str | None = None,
    severity: str = "info",
) -> str:
    """Build toast notification XML with severity-based template.

    Args:
        title: Notification title.
        body: Notification body text.
        subtitle: Optional subtitle (included in body area).
        severity: One of "info", "warning", "error", "critical".

    Returns:
        Complete toast XML string.
    """
    tmpl = _TEMPLATES.get(severity, _TEMPLATES["info"])

    # Toast element attributes
    toast_attrs = f' duration="{tmpl["duration"]}"'
    if tmpl["scenario"]:
        toast_attrs += f' scenario="{tmpl["scenario"]}"'

    # Visual binding content
    title_escaped = escape_xml(title)
    body_escaped = escape_xml(body)

    text_elements = f'            <text>{title_escaped}</text>\n'
    if subtitle:
        subtitle_escaped = escape_xml(subtitle)
        text_elements += f'            <text>{subtitle_escaped}</text>\n'
    text_elements += f'            <text>{body_escaped}</text>'

    # Attribution text
    attribution = ""
    if tmpl["attribution"]:
        attribution = (
            f'\n            <text placement="attribution">'
            f'{escape_xml(tmpl["attribution"])}</text>'
        )

    # Audio element
    audio_attrs = f'src="{tmpl["audio_src"]}"'
    if tmpl["audio_loop"]:
        audio_attrs += ' loop="true"'

    return (
        f'<toast{toast_attrs}>\n'
        f'    <visual>\n'
        f'        <binding template="ToastGeneric">\n'
        f'{text_elements}{attribution}\n'
        f'        </binding>\n'
        f'    </visual>\n'
        f'    <audio {audio_attrs}/>\n'
        f'</toast>'
    )
