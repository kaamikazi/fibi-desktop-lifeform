; Fibi Chubi v0.30 beta installer script.
; Build manually with Inno Setup Compiler (ISCC.exe) or:
;   python tools/build_installer.py

#define MyAppName "Fibi Chubi"
#define MyAppVersion "0.30.3"
#define MyAppExeName "Fibi Chubi.exe"
#define ProjectRoot "..\.."
#define ReleaseDir ProjectRoot + "\dist\Fibi Chubi"

[Setup]
AppId={{9E711C5B-40B5-4D2A-96C0-FIB1CHUBI030}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Fibi Local Beta
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir={#ProjectRoot}\dist\installers
OutputBaseFilename=Fibi_Chubi_Setup_v0.30.3
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#ReleaseDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "data\*,logs\*,reports\*,exports\*,voice_cache\*,tts_temp\*,voice_models\*,*.env,*.pth,*.index,*.db"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Fibi Chubi"; Flags: nowait postinstall skipifsilent
