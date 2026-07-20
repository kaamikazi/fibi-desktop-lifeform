# Fibi v0.26 Update Prep

v0.26 only prepares local update metadata. It is not an auto-updater.

## Local Manifest

Optional file:

```text
updates/update_manifest.json
```

Supported fields:

- `latest_version`
- `channel`
- `release_date`
- `release_notes`
- `download_url`
- `sha256`
- `required`
- `min_supported_version`

## Commands

- `/update status`
- `/update check local`
- `/update notes`
- `/update safety`

## Safety

Fibi does not check the network, download updates, install updates, or open
download URLs. She only parses the local manifest file if you place one there.
