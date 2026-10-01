# 教員用 — Windows インストーラ（Setup.exe）の作成

> 実際に通した手順とエラー対策のまとめ: [教員用_インストーラ作成_手順まとめ.md](教員用_インストーラ作成_手順まとめ.md)

学生には **ZIP + .bat** の代わりに、通常の Windows ソフトのように **Setup.exe** を配布できます。

---

配布物には **Python 本体**と**解析ライブラリ（wheels）**が入るため、学生側はインターネットなしでインストールできます。

## 必要なもの

| 環境 | 用途 |
| --- | --- |
| **Windows 11** | ZIP / Setup.exe のビルド |
| [Inno Setup 6](https://jrsoftware.org/isdl.php) | 無料・インストールのみ |
| **インターネット**（ビルド時のみ） | Python と wheels の取得（`student/dist/_cache/` にキャッシュ） |
| **.NET SDK + Rhino 8**（任意） | Grasshopper プラグイン `.gha` の同梱

---

## 手順

### 1. 配布用フォルダ / ZIP を作る

PowerShell でリポジトリ直下から:

```powershell
.\student\build_student_zip.ps1
```

出力例:

- `student/dist/_build/StructuralToolbox_Windows_YYYYMMDD/`（フォルダ）
- `student/dist/StructuralToolbox_Windows_YYYYMMDD.zip`（任意）

### 2. Setup.exe を作る（Windows）

PowerShell でリポジトリ直下から:

```powershell
.\student\build_student_installer.ps1
```

フォルダを直接指定する場合（ZIP 不要）:

```powershell
.\student\build_student_installer.ps1 -SourceDir student\dist\_build\StructuralToolbox_Windows_20260605
```

最新の `StructuralToolbox_Windows_*.zip` を自動で使います。明示する場合:

```powershell
.\student\build_student_installer.ps1 -ZipPath student\dist\StructuralToolbox_Windows_20260605.zip
```

出力例: `student/dist/StructuralToolbox_Setup_20260929.exe`（約 75 MB）

`build_student_installer.ps1` は、ペイロードに `Install_once.bat` / `setup_runtime.py` / `python-embed` / `wheels` / `.gha` / 学生向け手順書が揃っているかを確認してからビルドします。

### 3. 学生へ配布

- **配布物:** `StructuralToolbox_Setup_YYYYMMDD.exe` のみでよい
- 学生手順: Setup.exe をダブルクリック → ウィザード → 完了後、スタートメニュー／デスクトップの **Structural Toolbox** から起動

詳細は [学生用_インストール_Windows.md](学生用_インストール_Windows.md)

---

## インストール先

既定: `%LOCALAPPDATA%\StructuralToolbox`（管理者権限不要）

アンインストール: Windows の「アプリと機能」またはスタートメニューの Uninstall から。

---

## ZIP 配布との併用

- **Setup.exe** … 推奨（.bat を意識しない）
- **ZIP + Install_once.bat** … 従来方式（インストーラが使えない環境向け）

どちらも中身は同じ（同梱 Python + `.venv` + `stb gui` + Grasshopper `.gha`）。

配布用ペイロードには `grasshopper\StbGrasshopper.gha` が含まれます。Setup.exe
実行時に `%APPDATA%\Grasshopper\Libraries` へ自動コピーされます（フォルダが無ければ作成）。
アンインストール時にはこの `.gha` も削除されます。
Rhino/Grasshopperが起動中でコピーできない場合は、Rhinoを終了してから
インストール先の `Install_once.bat` を再実行してください。

---

## トラブル

| 症状 | 対処 |
| --- | --- |
| Inno Setup が見つからない | 公式サイトからインストール後、PowerShell を開き直す |
| インストール中に失敗 | `%LOCALAPPDATA%\StructuralToolbox\install.log` を確認 |
| セットアップのみ再実行 | スタートメニュー「初回セットアップを再実行」または `Install_once.bat` |
| 専用 Python を使っているか確認 | インストール先で `.venv\Scripts\stb.exe doctor`（`bundled: yes` が正常） |

### インストーラ動作確認（教員機）

```powershell
$dir = "$env:TEMP\stb_verify"
Start-Process .\student\dist\StructuralToolbox_Setup_20260929.exe -ArgumentList "/VERYSILENT","/DIR=$dir" -Wait
& "$dir\.venv\Scripts\stb.exe" doctor --require-bundled
& "$dir\unins000.exe" /VERYSILENT
```

---

## ファイル一覧

| ファイル | 説明 |
| --- | --- |
| `student/StructuralToolbox.iss` | Inno Setup 定義 |
| `student/build_student_installer.ps1` | ZIP → Setup.exe ビルド |
| `student/fetch_wheels.py` | 同梱ライブラリ（wheels）の取得 |
| `student/setup_runtime.py` | 学生機での初回セットアップ本体 |
| `student/stage_docs.py` | 学生向け手順書の配置 |
| `grasshopper\StbGrasshopper.gha` | インストーラーに同梱するGrasshopperプラグイン |
| `student/installer_info_before.txt` | インストール前の説明 |
| `student/installer_info_after.txt` | 完了後の説明 |
