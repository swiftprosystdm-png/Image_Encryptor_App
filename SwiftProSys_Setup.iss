; ============================================================================
; SwiftProSys_Setup.iss - Inno Setup installer script for
; Swift-ProSys Image Encryption Studio.
;
; HOW TO BUILD THE INSTALLER:
;   1. Install Inno Setup (free): https://jrsoftware.org/isdl.php
;   2. First build the app .exe:  run build.bat  (creates dist\SwiftProSys_ImageEncryptor.exe)
;   3. Open this file in Inno Setup and click "Compile"
;      (or run from command line: ISCC.exe SwiftProSys_Setup.iss)
;   4. The installer is created at: Output\SwiftProSys_ImageEncryptor_Setup.exe
;
; This installer works on any Windows version from Windows 7 through
; Windows 11 (32-bit and 64-bit), and needs nothing pre-installed on the
; target machine - the app .exe it installs is already fully self-contained.
; ============================================================================

#define MyAppName "Swift-ProSys Image Encryption Studio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Swift-ProSys"
#define MyAppExeName "SwiftProSys_ImageEncryptor.exe"

[Setup]
AppId={{8F2C9A6E-4B1D-4E7A-9C3F-6D2A8B1E5F40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Produces one single Setup.exe with everything embedded
OutputDir=Output
OutputBaseFilename=SwiftProSys_ImageEncryptor_Setup
Compression=lzma2
SolidCompression=yes
; Works on Windows 7 SP1 and later, both 32-bit and 64-bit
MinVersion=6.1
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=Swift_Prosys.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
