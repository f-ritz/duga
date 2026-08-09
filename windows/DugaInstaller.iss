; Duga Installer (Inno Setup 6+)
; Version 1.1.1 'Berkut-AM'
; 
; Build the app first with: python windows\build_exe.py
; Then compile this .iss to produce DugaSetup-1.1.1-Berkut-AM.exe
; The installer packages the onedir distribution from dist\Duga\
;
; Update support:
;   - Same AppId must be kept across versions
;   - Newer installer will automatically uninstall older version first
;   - Then installs cleanly over the same directory
;   - CloseApplications helps close the running app (including tray) before update
;   - restartreplace flag (see [Files]) allows replacement of in-use files if needed

#define MyAppName "Duga"
#define MyAppVersion "1.1.1"
#define MyAppVerName "Duga 1.1.1 'Berkut-AM'"
#define MyAppPublisher "Fritz Wolfram"
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
OutputBaseFilename=DugaSetup-1.1.1-Berkut-AM
PrivilegesRequired=lowest
CloseApplications=yes
CloseApplicationsFilter=Duga.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\Duga\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion restartreplace
; Note: restartreplace tells Inno Setup to use restart-replace for files that are locked by the running app.
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
function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UnInstallOldVersion(): Integer;
var
  sUnInstallString: String;
  iResultCode: Integer;
begin
  Result := 0;
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := 1;
  end;
end;

function InitializeSetup(): Boolean;
begin
  // Silently uninstall any previous version (makes updating easy:
  // just run the new installer over the old one)
  if IsUpgrade() then
  begin
    UnInstallOldVersion();
  end;
  Result := True;
end;
