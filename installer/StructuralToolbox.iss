; Structural Toolbox - Windows installer (Inno Setup 6)
; Shortcuts point to Start Structural Toolbox.bat (always present).
; stb.exe is created later by Install_once.bat in [Run].
; Install_once.bat also copies grasshopper\StbGrasshopper.gha to %APPDATA%\Grasshopper\Libraries.

#ifndef StbSourceDir
  #define StbSourceDir "dist\_installer_staging\Payload"
#endif
#ifndef OutputDist
  #define OutputDist "dist"
#endif
#ifndef BuildStamp
  #define BuildStamp GetDateTimeString('yyyyMMdd', '', '')
#endif
; The version comes from the VERSION file at the repository root.
; build_windows_installer.ps1 passes it with /DMyAppVersion=...
#ifndef MyAppVersion
  #define VersionHandle FileOpen(AddBackslash(SourcePath) + "..\VERSION")
  #if VersionHandle == 0
    #error Cannot read ..\VERSION
  #endif
  #define MyAppVersion Trim(FileRead(VersionHandle))
  #expr FileClose(VersionHandle)
#endif

#define MyAppName "Structural Toolbox"
#define MyAppPublisher "Structural Toolbox"
#define MyAppLauncher "Start Structural Toolbox.bat"
#define MyAppId "{{9C4E2A1B-7D3F-4E86-A5B2-1C0D9E8F7A6B}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\StructuralToolbox
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
OutputDir={#OutputDist}
OutputBaseFilename=StructuralToolbox_Setup_{#MyAppVersion}_{#BuildStamp}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
; With RedirectionGuard on, the virtualenv launcher started from [Run] exits with
; 0xC00004BC (STATUS_UNTRUSTED_MOUNT_POINT). Setup never elevates, so there is
; nothing for the mitigation to protect here.
RedirectionGuard=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\python-embed\python.exe
InfoBeforeFile=installer_info_before.txt
InfoAfterFile=installer_info_after.txt
ShowLanguageDialog=no

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加のショートカット:"; Flags: checkedonce

[Files]
; Used only by PrepareToInstall to remove an earlier install.
Source: "clean_old_install.ps1"; Flags: dontcopy
Source: "{#StbSourceDir}\install_manifest.txt"; Flags: dontcopy
Source: "{#StbSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppLauncher}"; WorkingDir: "{app}"; Comment: "3D 構造解析（ブラウザで開きます）"
Name: "{group}\{#MyAppName} (debug)"; Filename: "{app}\Start Structural Toolbox (debug).bat"; WorkingDir: "{app}"; Comment: "ログ付き・コンソールを残す"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppLauncher}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\はじめ方"; Filename: "{app}\はじめ方_インストーラ版.md"; Comment: "使い方（テキスト）"
Name: "{group}\初回セットアップを再実行"; Filename: "{app}\Install_once.bat"; Comment: "ライブラリの再インストール"
Name: "{group}\{#MyAppName} をアンインストール"; Filename: "{uninstallexe}"; Comment: "このアプリを削除"

[Run]
Filename: "{app}\Install_once.bat"; Parameters: "/silent"; WorkingDir: "{app}"; StatusMsg: "同梱のライブラリをセットアップしています（2〜5 分）..."; Flags: waituntilterminated runhidden

[UninstallDelete]
Type: files; Name: "{userappdata}\Grasshopper\Libraries\StbGrasshopper.gha"
Type: files; Name: "{userappdata}\Grasshopper\Libraries\StbGrasshopper.location.txt"

[Code]
const
  // Files inside the install reach about 130 characters below {app}, and
  // Windows cannot load DLLs whose full path exceeds 260 characters.
  // Keep in sync with MAX_INSTALL_DIR_LENGTH in setup_runtime.py.
  MaxInstallDirLength = 100;

function InstallDirTooLongMessage(Dir: string): string;
begin
  Result :=
    'インストール先のフォルダのパスが長すぎます（' + IntToStr(Length(Dir)) + ' 文字）。' + #13#10 +
    IntToStr(MaxInstallDirLength) + ' 文字以内の場所を選んでください。' + #13#10 + #13#10 +
    Dir;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpSelectDir) and (Length(WizardDirValue) > MaxInstallDirLength) then
  begin
    MsgBox(InstallDirTooLongMessage(WizardDirValue), mbError, MB_OK);
    Result := False;
  end;
end;

function PreviousInstallDir: string;
var
  Key: string;
begin
  // MyAppId starts with "{{" (an escaped brace); the registry key uses one.
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + Copy('{#MyAppId}', 2, MaxInt) + '_is1';
  if not RegQueryStringValue(HKCU, Key, 'InstallLocation', Result) then
    if not RegQueryStringValue(HKLM, Key, 'InstallLocation', Result) then
      Result := '';
  Result := RemoveBackslashUnlessRoot(Result);
end;

function CleanLogPath: string;
begin
  Result := ExpandConstant('{%TEMP}\StructuralToolbox_clean.log');
end;

// Removes an earlier install (in {app}, at the previously registered location,
// or where the last first-time setup ran) before the new files are copied.
// .dat/.out/.gh files the user added are kept and gathered into {app}.
function CleanOldInstall: Boolean;
var
  Params: string;
  ResultCode: Integer;
begin
  ExtractTemporaryFile('clean_old_install.ps1');
  ExtractTemporaryFile('install_manifest.txt');
  Params :=
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ' +
    AddQuotes(ExpandConstant('{tmp}\clean_old_install.ps1')) +
    ' -Dir ' + AddQuotes(RemoveBackslashUnlessRoot(ExpandConstant('{app}'))) +
    ' -Manifest ' + AddQuotes(ExpandConstant('{tmp}\install_manifest.txt')) +
    ' -LocationFile ' + AddQuotes(ExpandConstant('{userappdata}\Grasshopper\Libraries\StbGrasshopper.location.txt')) +
    ' -Log ' + AddQuotes(CleanLogPath);
  if PreviousInstallDir <> '' then
    Params := Params + ' -OldDir ' + AddQuotes(PreviousInstallDir);
  Log('clean_old_install.ps1 ' + Params);
  Result :=
    Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params, '',
      SW_HIDE, ewWaitUntilTerminated, ResultCode)
    and (ResultCode = 0);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  // Also covers silent installs, where /DIR= skips the folder page.
  Result := '';
  if Length(ExpandConstant('{app}')) > MaxInstallDirLength then
  begin
    Result := InstallDirTooLongMessage(ExpandConstant('{app}'));
    Exit;
  end;

  if not CleanOldInstall then
    Result :=
      '以前のバージョンを削除できませんでした。' + #13#10 +
      'Structural Toolbox と Rhino を終了してから、もう一度インストールしてください。' + #13#10 + #13#10 +
      '詳細ログ: ' + CleanLogPath;
end;

function StbExePath: string;
begin
  Result := ExpandConstant('{app}\.venv\Scripts\stb.exe');
end;

function InstallLogPath: string;
begin
  Result := ExpandConstant('{app}\install.log');
end;

procedure DeinitializeSetup();
begin
  if WizardSilent then
    Exit;
  if FileExists(StbExePath) then
    Exit;
  MsgBox(
    'ライブラリのセットアップが完了していません。' + #13#10 + #13#10 +
    'スタートメニューの「初回セットアップを再実行」を実行してください。' + #13#10 +
    '（2〜5 分）' + #13#10 + #13#10 +
    '詳細ログ: ' + InstallLogPath,
    mbError, MB_OK);
end;
