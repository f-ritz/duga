; Duga Installer (Inno Setup 6+)
; Version 0.1.0 "Berkut"
; Compile with Inno Setup Compiler to produce DugaSetup-0.1.0-Berkut.exe

#define MyAppName "Duga"
#define MyAppVersion "0.1.0"
#define MyAppVerName "Duga 0.1.0 \"Berkut\""
#define MyAppPublisher "Duga Project"
#define MyAppExeName "Duga.exe"

[Setup]
AppId={{8F3E2A1B-9C4D-4E5F-8A7B-1C2D3E4F5A6B}}   ; <-- Change this GUID for your releases (use Tools > Generate GUID)
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppVerName}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
OutputDir=..\dist
OutputBaseFilename=DugaSetup-0.1.0-Berkut
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; If you have a separate icon file for the installer
; Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion   ; (copy icon.ico next to DugaInstaller.iss if you want it bundled)

[Icons]
Name: "{group}\Duga"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall Duga"; Filename: "{uninstallexe}"
; Start with tray on login (recommended for background app)
Name: "{userstartup}\Duga"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--minimized"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Duga"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Optional: you can add more registry keys here if needed
  end;
end;
