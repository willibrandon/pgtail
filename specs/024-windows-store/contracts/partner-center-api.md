# Partner Center API Contract

**Feature**: 024-windows-store
**Date**: 2026-01-18

## Overview

The Microsoft Store Submission API allows automated app submissions to the Microsoft Store.

**Base URL**: `https://manage.devcenter.microsoft.com/v1.0/my`

## Authentication

### OAuth2 Token Endpoint

```
POST https://login.microsoftonline.com/{tenant_id}/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={client_id}
&client_secret={client_secret}
&resource=https://manage.devcenter.microsoft.com
```

**Response**:
```json
{
  "token_type": "Bearer",
  "expires_in": 3600,
  "access_token": "eyJ0eXAiOiJKV1Q..."
}
```

## Endpoints

### Get Application

```
GET /applications/{app_id}
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "id": "9NBLGGH4R315",
  "primaryName": "pgtail",
  "packageFamilyName": "12345Publisher.pgtail_abc123",
  "pendingApplicationSubmission": {
    "id": "1152921504621243680",
    "resourceLocation": "applications/9NBLGGH4R315/submissions/1152921504621243680"
  }
}
```

### Delete Pending Submission

```
DELETE /applications/{app_id}/submissions/{submission_id}
Authorization: Bearer {access_token}
```

**Response**: `204 No Content`

### Create Submission

```
POST /applications/{app_id}/submissions
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "id": "1152921504621243681",
  "status": "PendingCommit",
  "fileUploadUrl": "https://ingestionworker.blob.core.windows.net/...",
  "applicationPackages": [
    {
      "fileName": "pgtail.msixbundle",
      "fileStatus": "PendingUpload"
    }
  ],
  "listings": {
    "en-us": {
      "baseListing": {
        "title": "pgtail",
        "description": "Interactive PostgreSQL log tailer"
      }
    }
  }
}
```

### Update Submission

```
PUT /applications/{app_id}/submissions/{submission_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "applicationPackages": [
    {
      "fileName": "pgtail.msixbundle",
      "fileStatus": "PendingUpload",
      "minimumDirectXVersion": "None",
      "minimumSystemRam": "None"
    }
  ]
}
```

**Response**: Updated submission object

### Upload Package

```
PUT {fileUploadUrl}
x-ms-blob-type: BlockBlob
Content-Type: application/zip

<binary ZIP content containing MSIXBUNDLE>
```

**Response**: `201 Created`

**Note**: The ZIP must contain the MSIXBUNDLE file at the root level.

### Commit Submission

```
POST /applications/{app_id}/submissions/{submission_id}/commit
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "status": "CommitStarted"
}
```

### Get Submission Status

```
GET /applications/{app_id}/submissions/{submission_id}/status
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "status": "PreProcessing",
  "statusDetails": {
    "errors": [],
    "warnings": [],
    "certificationReports": []
  }
}
```

## Status Values

| Status | Description | Action |
|--------|-------------|--------|
| `PendingCommit` | Submission created, not committed | Upload package, then commit |
| `CommitStarted` | Commit in progress | Poll until changes |
| `PreProcessing` | Package validation | Wait for certification |
| `Certification` | Under review | Wait for completion |
| `Release` | Published to Store | Success! |
| `Failed` | Submission failed | Review errors, resubmit |

## Error Handling

### Common Errors

| HTTP Code | Error | Cause | Resolution |
|-----------|-------|-------|------------|
| 401 | Unauthorized | Invalid/expired token | Refresh OAuth token |
| 404 | NotFound | Invalid app/submission ID | Verify IDs |
| 409 | Conflict | Pending submission exists | Delete pending first |
| 429 | TooManyRequests | Rate limited | Back off and retry |

### Retry Strategy

```powershell
$maxRetries = 3
$delays = @(30, 60, 120)  # Exponential backoff in seconds

for ($i = 0; $i -lt $maxRetries; $i++) {
    try {
        $result = Invoke-RestMethod @params
        break
    } catch {
        if ($i -eq $maxRetries - 1) { throw }
        Start-Sleep -Seconds $delays[$i]
    }
}
```

## Required Secrets

| Secret Name | Description | Source |
|-------------|-------------|--------|
| `STORE_CLIENT_ID` | Azure AD application ID | Azure Portal → App registrations |
| `STORE_CLIENT_SECRET` | Azure AD client secret | Azure Portal → Certificates & secrets |
| `STORE_TENANT_ID` | Azure AD tenant ID | Azure Portal → Overview |
| `STORE_APP_ID` | Partner Center app ID | Partner Center → App overview |

## Workflow Integration

```yaml
update-store:
  runs-on: windows-latest
  needs: [build-msix]
  steps:
    - name: Get OAuth token
      id: auth
      run: |
        $token = Get-StoreToken
        echo "token=$token" >> $env:GITHUB_OUTPUT

    - name: Submit to Store
      env:
        TOKEN: ${{ steps.auth.outputs.token }}
      run: |
        Submit-ToStore -Token $env:TOKEN -Package pgtail.msixbundle
```

## References

- [Microsoft Store Submission API](https://learn.microsoft.com/en-us/windows/uwp/monetize/manage-app-submissions)
- [Create and manage submissions](https://learn.microsoft.com/en-us/windows/uwp/monetize/create-and-manage-submissions-using-windows-store-services)
- [Python code examples](https://learn.microsoft.com/en-us/windows/uwp/monetize/python-code-examples-for-the-windows-store-submission-api)
