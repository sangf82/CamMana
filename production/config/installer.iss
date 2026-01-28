[Setup]
AppName=CamMana
AppVersion=2.0.0
DefaultDirName={autopf}\CamMana
DefaultGroupName=CamMana
UninstallDisplayIcon={app}\CamMana.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
OutputBaseFilename=CamMana_Setup
SetupIconFile=..\assets\icon.ico
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
Name: "addtopath"; Description: "Add to PATH (requires shell restart)"; GroupDescription: "Other:"
Name: "openwith"; Description: "Add 'Open with CamMana' action to Windows Explorer context menu"; GroupDescription: "Other:"

[Files]
; Source: Point this to the single executable created by Nuitka in production/
Source: "..\CamMana.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\CamMana"; Filename: "{app}\CamMana.exe"
Name: "{autodesktop}\CamMana"; Filename: "{app}\CamMana.exe"; Tasks: desktopicon

[Registry]
; Add to PATH
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath

; Context Menu - Directory
Root: HKCR; Subkey: "Directory\shell\CamMana"; ValueType: string; ValueName: ""; ValueData: "Open with CamMana"; Tasks: openwith
Root: HKCR; Subkey: "Directory\shell\CamMana"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\CamMana.exe"; Tasks: openwith
Root: HKCR; Subkey: "Directory\shell\CamMana\command"; ValueType: string; ValueName: ""; ValueData: """{app}\CamMana.exe"" ""%1"""; Tasks: openwith

; Context Menu - Background
Root: HKCR; Subkey: "Directory\Background\shell\CamMana"; ValueType: string; ValueName: ""; ValueData: "Open with CamMana"; Tasks: openwith
Root: HKCR; Subkey: "Directory\Background\shell\CamMana"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\CamMana.exe"; Tasks: openwith
Root: HKCR; Subkey: "Directory\Background\shell\CamMana\command"; ValueType: string; ValueName: ""; ValueData: """{app}\CamMana.exe"" ""%V"""; Tasks: openwith

[Run]
Filename: "{app}\CamMana.exe"; Description: "{cm:LaunchProgram,CamMana}"; Flags: nowait postinstall skipifsilent
