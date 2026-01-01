# Contract: GitHub Releases API

**Branch**: `019-distribution` | **Date**: 2026-01-01

## Overview

pgtail uses the GitHub Releases API to check for available updates. This contract defines the expected request/response format and error handling.

---

## Endpoint

### Get Latest Release

**URL**: `GET https://api.github.com/repos/willibrandon/pgtail/releases/latest`

**Authentication**: None required (public repository)

**Headers**:
```
Accept: application/vnd.github+json
User-Agent: pgtail/{version}
```

---

## Request

### Python Implementation

```python
import urllib.request
import json
from typing import TypedDict

RELEASES_URL = "https://api.github.com/repos/willibrandon/pgtail/releases/latest"
TIMEOUT = 5  # seconds

class ReleaseAsset(TypedDict):
    name: str
    browser_download_url: str
    size: int
    content_type: str

class ReleaseResponse(TypedDict):
    tag_name: str
    name: str
    body: str
    html_url: str
    assets: list[ReleaseAsset]
    published_at: str

def fetch_latest_release() -> ReleaseResponse | None:
    """Fetch latest release from GitHub API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"pgtail/{get_version()}",
    }
    req = urllib.request.Request(RELEASES_URL, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception:
        return None
```

---

## Response

### Success (200 OK)

```json
{
  "tag_name": "v0.2.0",
  "name": "v0.2.0",
  "body": "## What's Changed\n\n* Feature X by @user in #123\n* Bug fix Y by @user in #124\n\n**Full Changelog**: https://github.com/willibrandon/pgtail/compare/v0.1.0...v0.2.0",
  "html_url": "https://github.com/willibrandon/pgtail/releases/tag/v0.2.0",
  "published_at": "2026-01-15T10:30:00Z",
  "assets": [
    {
      "name": "pgtail-macos-arm64",
      "browser_download_url": "https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-macos-arm64",
      "size": 15728640,
      "content_type": "application/octet-stream"
    },
    {
      "name": "pgtail-macos-x86_64",
      "browser_download_url": "https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-macos-x86_64",
      "size": 16252928,
      "content_type": "application/octet-stream"
    },
    {
      "name": "pgtail-linux-x86_64",
      "browser_download_url": "https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-linux-x86_64",
      "size": 18350080,
      "content_type": "application/octet-stream"
    },
    {
      "name": "pgtail-linux-arm64",
      "browser_download_url": "https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-linux-arm64",
      "size": 17301504,
      "content_type": "application/octet-stream"
    },
    {
      "name": "pgtail-windows-x86_64.exe",
      "browser_download_url": "https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-windows-x86_64.exe",
      "size": 19398656,
      "content_type": "application/octet-stream"
    }
  ]
}
```

### Error Responses

| Status | Condition | pgtail Behavior |
|--------|-----------|-----------------|
| 404 | No releases exist | Return None, silent |
| 403 | Rate limit exceeded | Return None, silent |
| 5xx | Server error | Return None, silent |
| Timeout | Network timeout | Return None, silent |

---

## Response Field Extraction

### Version Parsing

```python
def parse_version(tag_name: str) -> str:
    """Extract version from tag name."""
    # Remove 'v' prefix if present
    return tag_name.lstrip("v")

# Examples:
# "v0.1.0" -> "0.1.0"
# "0.1.0" -> "0.1.0"
# "v1.0.0-beta.1" -> "1.0.0-beta.1"
```

### Asset Selection

```python
import platform

def get_asset_for_platform(assets: list[ReleaseAsset]) -> ReleaseAsset | None:
    """Get the binary asset for the current platform."""
    os_name = "windows" if platform.system() == "Windows" else platform.system().lower()
    arch = "arm64" if platform.machine() in ("arm64", "aarch64") else "x86_64"

    expected_name = f"pgtail-{os_name}-{arch}"
    if os_name == "windows":
        expected_name += ".exe"

    for asset in assets:
        if asset["name"] == expected_name:
            return asset

    return None
```

---

## Rate Limiting

### Limits

| Type | Limit | Reset |
|------|-------|-------|
| Unauthenticated | 60 requests/hour | Rolling window |
| Authenticated | 5,000 requests/hour | Rolling window |

### pgtail Rate Limit Strategy

1. **Startup check**: At most once per 24 hours
2. **Explicit check**: Always allowed (user-initiated)
3. **Failure handling**: Silent, no retry

### Rate Limit Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 58
X-RateLimit-Reset: 1704067200
```

---

## Caching Strategy

### Config-Based Caching

```toml
[updates]
last_check = "2026-01-01T00:00:00Z"
last_version = "0.2.0"
```

### Check Interval Logic

```python
from datetime import datetime, timedelta, timezone

CHECK_INTERVAL = timedelta(hours=24)

def should_check_update(config: Config) -> bool:
    """Determine if enough time has passed for a new check."""
    if not config.get("updates", {}).get("check", True):
        return False

    last_check_str = config.get("updates", {}).get("last_check", "")
    if not last_check_str:
        return True

    try:
        last_check = datetime.fromisoformat(last_check_str.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - last_check >= CHECK_INTERVAL
    except ValueError:
        return True
```

---

## Error Handling Contract

### Silent Failures

pgtail MUST NOT:
- Display error messages for network failures
- Delay startup due to API timeouts
- Crash if API returns unexpected data

pgtail MUST:
- Continue normal operation on any API error
- Log errors only in debug mode
- Handle malformed JSON gracefully

### Explicit Check Errors

For `--check-update`, pgtail MAY:
- Display "Unable to check for updates" on failure
- Return non-zero exit code on failure

---

## Testing Contract

### Mock Server Responses

```python
# Test: Newer version available
MOCK_NEWER_RELEASE = {
    "tag_name": "v99.0.0",
    "html_url": "https://github.com/willibrandon/pgtail/releases/tag/v99.0.0",
    "assets": []
}

# Test: Current version (no update)
MOCK_CURRENT_RELEASE = {
    "tag_name": f"v{get_version()}",
    "html_url": "https://github.com/willibrandon/pgtail/releases/tag/v0.1.0",
    "assets": []
}

# Test: Prerelease (should be ignored by /latest endpoint)
# Note: /latest automatically excludes prereleases

# Test: No releases
# HTTP 404 response
```
