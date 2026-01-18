# Quickstart: Windows Store Distribution Setup

**Feature**: 024-windows-store
**Date**: 2026-01-18

## Overview

This guide walks through the one-time setup required to enable Microsoft Store distribution for pgtail.

## Prerequisites

- Microsoft account (personal or work)
- GitHub repository admin access
- Azure account (free tier sufficient)

## Phase 1: Developer Account Registration

### Step 1.1: Register at Microsoft Store

1. Go to [storedeveloper.microsoft.com](https://storedeveloper.microsoft.com)
   - **Important**: Use this exact URL for free registration
   - Other entry points may charge $19

2. Sign in with your Microsoft account

3. Complete identity verification:
   - Upload government-issued ID photo
   - Take selfie for verification
   - Wait for approval (minutes to hours)

### Step 1.2: Reserve App Name

1. Go to [Partner Center](https://partner.microsoft.com/dashboard)
2. Navigate to **Apps and games** → **New product** → **MSIX or PWA app**
3. Reserve the name **"pgtail"**
4. Note these values from the app overview:
   - **Package Identity Name**: `12345Publisher.pgtail`
   - **Publisher CN**: `CN=12345678-ABCD-...`

## Phase 2: Azure AD App Setup

### Step 2.1: Create App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**:
   - Name: `pgtail-store-submission`
   - Supported account types: **Single tenant**
   - Redirect URI: Leave blank
4. Click **Register**
5. Note these values:
   - **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### Step 2.2: Create Client Secret

1. In the app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Description: `GitHub Actions`
4. Expiration: Choose appropriate duration (remember to rotate before expiry)
5. Click **Add**
6. **Copy the secret value immediately** (only shown once)

### Step 2.3: Link to Partner Center

1. Go to [Partner Center](https://partner.microsoft.com/dashboard)
2. Navigate to **Account settings** → **User management** → **Azure AD applications**
3. Click **Add Azure AD applications**
4. Search for `pgtail-store-submission` or enter the Application ID
5. Select and click **Save**
6. Grant **Developer** role

## Phase 3: GitHub Secrets Configuration

Add these secrets to your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each:

| Secret Name | Value | Source |
|-------------|-------|--------|
| `STORE_CLIENT_ID` | Application (client) ID | Azure AD app |
| `STORE_CLIENT_SECRET` | Client secret value | Azure AD app |
| `STORE_TENANT_ID` | Directory (tenant) ID | Azure AD app |
| `STORE_APP_ID` | App ID | Partner Center |

## Phase 4: Update Manifest Placeholders

Update `msix/AppxManifest.xml` with Partner Center values:

```xml
<Identity
  Name="YOUR_PACKAGE_IDENTITY_NAME"
  Publisher="YOUR_PUBLISHER_CN"
  ...
/>
```

Replace:
- `YOUR_PACKAGE_IDENTITY_NAME` → Package Identity Name from Partner Center
- `YOUR_PUBLISHER_CN` → Publisher CN from Partner Center

## Phase 5: First Submission (Manual)

The first Store submission requires manual completion in Partner Center:

1. Build MSIX locally or trigger a test release
2. Upload MSIX bundle to Partner Center
3. Complete Store listing:
   - Description
   - Screenshots (optional for CLI tools)
   - Category: **Developer tools**
   - Privacy policy URL (required)
4. Set pricing: **Free**
5. Submit for certification

After first approval, subsequent releases are automated.

## Verification

### Test Workflow Locally

```powershell
# Verify secrets are configured
gh secret list

# Trigger a test release
git tag v0.0.0-test
git push origin v0.0.0-test

# Watch workflow
gh run watch
```

### Verify Store Submission

1. Check Partner Center for new submission
2. Monitor certification status (1-3 business days)
3. Receive email notification on completion

## Troubleshooting

### "Package identity mismatch"

- Verify `Identity.Name` and `Identity.Publisher` in AppxManifest.xml match Partner Center exactly
- Publisher CN must include `CN=` prefix

### "Authentication failed"

- Verify Azure AD app is linked to Partner Center
- Check client secret hasn't expired
- Confirm tenant ID is correct

### "Pending submission exists"

- Workflow automatically deletes pending submissions
- If manual cleanup needed, delete in Partner Center

### "Certification failed"

- Check Partner Center for detailed error report
- Common issues:
  - Missing privacy policy
  - Crash during testing (run with no args must exit cleanly)
  - Invalid manifest structure

## Secret Rotation

Azure AD client secrets expire. Before expiry:

1. Create new secret in Azure Portal
2. Update `STORE_CLIENT_SECRET` in GitHub
3. Delete old secret from Azure Portal

Set a calendar reminder for rotation based on your chosen expiration.
