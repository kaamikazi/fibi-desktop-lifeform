# Reset And Uninstall Fibi

Fibi v0.24 stores packaged user data outside the bundled app folder.

## Normal Packaged Mode

User data lives here:

`%APPDATA%\Fibi Chubi\`

## Portable Mode

If `portable_mode.txt` exists beside `Fibi Chubi.exe`, user data lives here:

`<release folder>\data\`

## Reset Fibi Data

1. Close Fibi.
2. Delete the user data folder:
   - normal mode: `%APPDATA%\Fibi Chubi\`
   - portable mode: `<release folder>\data\`
3. Start Fibi again.

Fibi will recreate safe default settings on first run.

## Uninstall Zip Release

1. Close Fibi.
2. Delete the extracted `Fibi Chubi` release folder.
3. Optionally delete `%APPDATA%\Fibi Chubi\` if you want to remove local user data too.

The zip uninstall does not automatically remove user data, Start Menu shortcuts,
Desktop shortcuts, or manually installed voice model files.

