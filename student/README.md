# 学生配布用（同梱 Python + インストーラ）

教員が **Windows 11 学生**向けに配布物を作るためのメモです。

## 配布方式（2通り）

| 方式 | 学生が受け取るもの | 体感 |
| --- | --- | --- |
| **推奨: インストーラ** | `StructuralToolbox_Setup_YYYYMMDD.exe` | 通常の Windows ソフトと同様 |
| ZIP + .bat | `StructuralToolbox_Windows_YYYYMMDD.zip` | 解凍 → `.bat` 実行 |

中身は同じ（同梱 Python + `.venv` + `stb gui` + Grasshopper `.gha`）。

Grasshopperがインストール済みで `%APPDATA%\Grasshopper\Libraries` が存在する場合、
初回セットアップ時に `StbGrasshopper.gha` を自動配置します。Rhinoが起動中で
配置できない場合は、Rhinoを終了して `Install_once.bat` を再実行してください。

---

## 推奨: Setup.exe の作り方

### 1. Linux で ZIP を作る

```bash
cd /path/to/stb_0_1
./student/build_student_zip.sh
```

出力: `student/dist/StructuralToolbox_Windows_YYYYMMDD.zip`

### 2. Windows で ZIP + インストーラを作る（Linux が無い場合）

ZIP だけ作る:

```powershell
.\student\build_student_zip.ps1
```

インストーラ（要 [Inno Setup 6](https://jrsoftware.org/isdl.php)）:

```powershell
.\student\build_student_installer.ps1
# または
.\student\build_student_installer.ps1 -SourceDir student\dist\_build\StructuralToolbox_Windows_YYYYMMDD
```

Linux で ZIP を作った場合は、その ZIP を Windows にコピーして `.\student\build_student_installer.ps1` でも可。

出力: `student/dist/StructuralToolbox_Setup_YYYYMMDD.exe`

詳細: [docs/教員用_インストーラ作成_Windows.md](../docs/教員用_インストーラ作成_Windows.md)

### 3. 学生への配布

- **Setup.exe** のみ渡す
- 手順: [docs/学生用_インストール_Windows.md](../docs/学生用_インストール_Windows.md)

インストール先（既定）: `%LOCALAPPDATA%\StructuralToolbox`  
起動: スタートメニュー / デスクトップの **Structural Toolbox**

---

## ZIP 方式（従来）

### 特徴

- **Windows embeddable Python**（既定 3.12.10, 64-bit）を ZIP に同梱
- 学生 PC の **システム Python は使わない**
- 初回 `Install_once.bat` で `.venv` を作成（`virtualenv` 使用）

バージョン変更: `student/PYTHON_EMBED_VERSION` を編集してから ZIP を再ビルド。

### Linux から ZIP を作る

```bash
./student/build_student_zip.sh
```

- **初回はインターネット必須**（python.org から embed パッケージを取得）
- キャッシュ: `student/dist/_cache/`
- 出力: `student/dist/StructuralToolbox_Windows_YYYYMMDD.zip`

### 学生 PC 上の流れ（ZIP）

1. ZIP をローカルに解凍
2. `Install_once.bat`（初回のみ・要ネット）
3. `Start Structural Toolbox.bat`（毎回）

手順: [docs/学生用_はじめ方_Windows.md](../docs/学生用_はじめ方_Windows.md)

---

## 関連ファイル

| ファイル | 説明 |
| --- | --- |
| `student/StructuralToolbox.iss` | Inno Setup 定義 |
| `student/build_student_installer.ps1` | ZIP → Setup.exe |
| `student/build_student_zip.sh` | Linux → ZIP |
| `student/build_student_mac.py` | Mac インストーラ（tar.gz。Mac 上では dmg / pkg も） |
| `Install_once.bat` | 初回セットアップ（`/silent` でインストーラから実行） |
| `Start Structural Toolbox.bat` | ZIP 版の毎回起動 |

---

## Mac 学生

Windows 用 ZIP / Setup.exe は使えません。Mac 用は別のインストーラです。

```powershell
.\student\build_student_mac.ps1
```

出力: `student/dist/StructuralToolbox_Mac_Setup_YYYYMMDD.tar.gz`

Mac 上で同じスクリプトを実行すると `.dmg` と `.pkg` も作られます。

```bash
./student/build_student_installer_mac.sh
```

学生手順: [docs/学生用_インストール_Mac.md](../docs/学生用_インストール_Mac.md)  
教員手順: [docs/教員用_インストーラ作成_Mac.md](../docs/教員用_インストーラ作成_Mac.md)

インストール先: `~/Library/Application Support/StructuralToolbox`  
起動: アプリケーションフォルダ / デスクトップの **Structural Toolbox**

## 更新時

- 新しい ZIP / Setup.exe を配布
- インストーラ版: 再インストール（上書き可）
- ZIP 版: 新フォルダに解凍し `Install_once.bat` を再実行
