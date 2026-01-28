[Setup]
AppName=CamMana
AppVersion=2.0.0
DefaultDirName={autopf}\CamMana
DefaultGroupName=CamMana
UninstallDisplayIcon={app}\CamMana.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
OutputBaseFilename=CamMana_Setup
SetupIconFile=..\assets\icon.ico
DisableProgramGroupPage=yes
; Require admin for Program Files install
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
Name: "addtopath"; Description: "Add to PATH (requires shell restart)"; GroupDescription: "Other:"

[Files]
; Source: The entire dist folder from Nuitka standalone build
; recursesubdirs copies the whole folder structure with all DLLs
Source: "..\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CamMana"; Filename: "{app}\CamMana.exe"
Name: "{autodesktop}\CamMana"; Filename: "{app}\CamMana.exe"; Tasks: desktopicon

[Registry]
; Add to PATH
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath

[Run]
Filename: "{app}\CamMana.exe"; Description: "{cm:LaunchProgram,CamMana}"; Flags: nowait postinstall skipifsilent
