# 教員用 — Mac インストーラの作成

> 実際に通した手順とエラー対策のまとめ: [教員用_インストーラ作成_手順まとめ.md](教員用_インストーラ作成_手順まとめ.md)

学生には、Windows の Setup.exe と同様に **Python 同梱のインストーラ**を渡せます。システムに入っている Python は使いません。

---

## 配布物

| 作る場所 | 出力 | 学生の操作 |
| --- | --- | --- |
| **Windows / Linux / Mac** | `student/dist/StructuralToolbox_Mac_Setup_YYYYMMDD.tar.gz` | 展開 → `インストール.command` を右クリックして開く |
| **Mac のみ** | 同じ日付の `.dmg` と `StructuralToolbox_Setup_Mac_YYYYMMDD.pkg` | .pkg をダブルクリック（推奨） |

中身は同じです（relocatable Python 3.12 の Apple シリコン版と Intel 版、解析ライブラリの wheels、`.venv` 作成、`stb gui`、Grasshopper プラグイン）。学生側はインターネットなしでインストールできます。

インストール時に、その Mac で使わない CPU 向けの Python と wheels は削除されます。

対応 OS: **macOS 12 以降**（scipy の Apple シリコン版 wheel が macOS 12 以上を要求するため）

インストール先: `~/Library/Application Support/StructuralToolbox`（管理者権限は不要）

起動: デスクトップ / アプリケーションフォルダの **Structural Toolbox**

学生手順: [学生用_インストール_Mac.md](学生用_インストール_Mac.md)

---

## 手順（Windows）

PowerShell でリポジトリ直下から:

```powershell
.\student\build_student_mac.ps1
```

初回は GitHub から macOS 用 Python を、PyPI から wheels を取得します（キャッシュ: `student/dist/_cache/`）。

出力: `student/dist/StructuralToolbox_Mac_Setup_YYYYMMDD.tar.gz`（約 130 MB）

この tar.gz だけで配布できます。同時に `student/dist/StructuralToolbox_Mac_make_pkg_YYYYMMDD.sh` も出力されます。

---

## 手順（Mac）

Windows で作った tar.gz と `make_pkg_YYYYMMDD.sh` を Mac の同じフォルダに置いて実行します（リポジトリ不要）。

```bash
bash StructuralToolbox_Mac_make_pkg_YYYYMMDD.sh
```

リポジトリ全体が Mac にある場合は `./student/build_student_installer_mac.sh` でも作れます。

追加で次が出ます。

- `student/dist/StructuralToolbox_Mac_YYYYMMDD.dmg`
- `student/dist/StructuralToolbox_Setup_Mac_YYYYMMDD.pkg`

.pkg は「このユーザのみ」に入り、インストールの最後に同梱ライブラリのセットアップ（2〜5 分）を実行します。管理者パスワードは不要です。

---

## 署名について

Apple Developer ID で署名・公証していないため、初回起動時に「開発元を確認できません」と出ます。学生には **右クリック → 開く** と伝えてください。手順書にも書いてあります。

---

## Python のバージョン

| ファイル | 内容 |
| --- | --- |
| `student/PYTHON_EMBED_VERSION` | Python の版（Windows 同梱と共通。例: 3.12.10） |
| `student/PYTHON_MAC_RELEASE` | [python-build-standalone](https://github.com/astral-sh/python-build-standalone/releases) のリリース日（例: 20250409） |

版を変えるときは、その Python を含む standalone リリース日に `PYTHON_MAC_RELEASE` を合わせてください。

---

## Grasshopper

ビルド機に .NET SDK がある場合、毎回 `StbGrasshopper.gha` をビルドし直して同梱します（依存 DLL は Rhino 側が提供するため、同梱は `.gha` 1 ファイルのみ）。初回セットアップで `~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)/Libraries` を作成してコピーします。

STB コンポーネントは **Python Exe / Repo Root が空**でも、インストール先の専用 `.venv` を自動で使います。見つからない場合は、PATH 上の Python を使わずエラーにします。

---

## 専用 Python の確認

```bash
"$HOME/Library/Application Support/StructuralToolbox/.venv/bin/stb" doctor --require-bundled
```

`bundled: yes` とライブラリ一覧が出れば正常です（初回セットアップ内でも自動確認します）。

---

## ファイル一覧

| ファイル | 説明 |
| --- | --- |
| `student/build_student_mac.py` | インストーラ作成（共通） |
| `student/build_student_mac.ps1` | Windows からの起動 |
| `student/build_student_installer_mac.sh` | Mac からの起動（dmg / pkg も作成） |
| `student/fetch_wheels.py` | 同梱ライブラリ（wheels）の取得 |
| `student/setup_runtime.py` | 学生機での初回セットアップ本体（Windows と共通） |
| `student/stage_docs.py` | 学生向け手順書の配置 |
| `student/mac/インストール.command` | 学生が実行するインストーラ |
| `student/mac/Install_once.command` | セットアップの起動・再実行 |
| `student/mac/postinstall` | .pkg 用のセットアップ |
