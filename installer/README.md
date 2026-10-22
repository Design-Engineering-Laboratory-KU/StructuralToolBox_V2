# インストーラ作成用（同梱 Python + インストーラ）

Windows 11 / Mac 向けの配布物を作るためのメモです。

## 配布方式（2通り）

| 方式 | 受け取るもの | 体感 |
| --- | --- | --- |
| **推奨: インストーラ** | `StructuralToolbox_Setup_YYYYMMDD.exe` | 通常の Windows ソフトと同様 |
| ZIP + .bat | `StructuralToolbox_Windows_YYYYMMDD.zip` | 解凍 → `.bat` 実行 |

中身は同じ（同梱 Python + `.venv` + `stb gui` + Grasshopper `.gha`）。

初回セットアップ時に `StbGrasshopper.gha` を Grasshopper のライブラリフォルダ
（Windows: `%APPDATA%\Grasshopper\Libraries`、Mac: `~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-…)/Libraries`）
へ自動配置します。フォルダが無ければ作成します。Rhinoが起動中で
配置できない場合は、Rhinoを終了して `Install_once.bat` を再実行してください。

---

## 推奨: Setup.exe の作り方

### 1. ZIP を作る（Windows）

```powershell
.\installer\build_windows_zip.ps1
```

出力: `installer/dist/StructuralToolbox_Windows_YYYYMMDD.zip`

### 2. インストーラを作る（Windows）

ZIP だけ作る:

```powershell
.\installer\build_windows_zip.ps1
```

インストーラ（要 [Inno Setup 6](https://jrsoftware.org/isdl.php)）:

```powershell
.\installer\build_windows_installer.ps1
# または
.\installer\build_windows_installer.ps1 -SourceDir installer\dist\_build\StructuralToolbox_Windows_YYYYMMDD
```
出力: `installer/dist/StructuralToolbox_Setup_YYYYMMDD.exe`

詳細: [docs/インストーラ作成.md](../docs/インストーラ作成.md)

### 3. 配布

- **Setup.exe** のみ渡す
- 手順: [docs/インストール.md](../docs/インストール.md)

インストール先（既定）: `%LOCALAPPDATA%\StructuralToolbox`  
起動: スタートメニュー / デスクトップの **Structural Toolbox**

---

## ZIP 方式（従来）

### 特徴

- **Windows embeddable Python**（既定 3.12.10, 64-bit）を ZIP に同梱
- 受け取った PC の **システム Python は使わない**
- 初回 `Install_once.bat` で `.venv` を作成（`virtualenv` 使用）

バージョン変更: `installer/PYTHON_EMBED_VERSION` を編集してから ZIP を再ビルド。

### ZIP を作る

```powershell
.\installer\build_windows_zip.ps1
```

- **ビルド時のみインターネット必須**（Python と wheels を取得）
- キャッシュ: `installer/dist/_cache/`
- 出力: `installer/dist/StructuralToolbox_Windows_YYYYMMDD.zip`

### 受け取った PC での流れ（ZIP）

1. ZIP をローカルに解凍
2. `Install_once.bat`（初回のみ。wheels を同梱しているのでネット不要）
3. `Start Structural Toolbox.bat`（毎回）

手順: [docs/インストール.md](../docs/インストール.md) の付録

---

## 関連ファイル

| ファイル | 説明 |
| --- | --- |
| `installer/StructuralToolbox.iss` | Inno Setup 定義 |
| `installer/build_windows_installer.ps1` | ZIP → Setup.exe |
| `installer/build_windows_zip.ps1` | Windows 用 ZIP / 配布フォルダ |
| `installer/build_mac.py` | Mac インストーラ（tar.gz。Mac 上では dmg / pkg も） |
| `Install_once.bat` | 初回セットアップ（`/silent` でインストーラから実行） |
| `Start Structural Toolbox.bat` | ZIP 版の毎回起動 |

---

## Mac

Windows 用 ZIP / Setup.exe は使えません。Mac 用は別のインストーラです。

```powershell
.\installer\build_mac.ps1
```

出力: `installer/dist/StructuralToolbox_Mac_Setup_YYYYMMDD.tar.gz`

Windows でビルドすると `installer/dist/StructuralToolbox_Mac_make_pkg_YYYYMMDD.sh` も出力されます。
これと tar.gz を Mac の同じフォルダに置いて `bash StructuralToolbox_Mac_make_pkg_YYYYMMDD.sh`
を実行すると、リポジトリなしで `.dmg` と `.pkg` ができます。

リポジトリ全体を Mac に置いた場合は、同じスクリプトを Mac 上で実行しても `.dmg` と `.pkg` が作られます。

```bash
./installer/build_mac_installer.sh
```

インストール手順: [docs/インストール.md](../docs/インストール.md)  
作成手順: [docs/インストーラ作成.md](../docs/インストーラ作成.md)

インストール先: `~/Library/Application Support/StructuralToolbox`  
起動: アプリケーションフォルダ / デスクトップの **Structural Toolbox**

## 更新時

- 新しい ZIP / Setup.exe を配布
- インストーラ版: 再インストール（上書き可）
- ZIP 版: 新フォルダに解凍し `Install_once.bat` を再実行
