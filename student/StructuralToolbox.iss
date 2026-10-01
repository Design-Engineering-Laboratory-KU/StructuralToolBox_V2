; Structural Toolbox - Windows installer (Inno Setup 6)
; Shortcuts point to Start Structural Toolbox.bat (always present).
; stb.exe is created later by Install_once.bat in [Run].
; Install_once.bat also copies grasshopper\StbGrasshopper.gha to %APPDATA%\Grasshopper\Libraries.

#ifndef StbSourceDir
  #define StbSourceDir "dist\_installer_staging\Payload"
#endif
#ifndef StudentDist
  #define StudentDist "dist"
#endif
#ifndef BuildStamp
  #define BuildStamp GetDateTimeString('yyyyMMdd', '', '')
#endif

#define MyAppName "Structural Toolbox"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Structural Toolbox"
#define MyAppLauncher "Start Structural Toolbox.bat"
#define MyAppId "{{9C4E2A1B-7D3F-4E86-A5B2-1C0D9E8F7A6B}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\StructuralToolbox
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
OutputDir={#StudentDist}
OutputBaseFilename=StructuralToolbox_Setup_{#BuildStamp}
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

[Code]
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
