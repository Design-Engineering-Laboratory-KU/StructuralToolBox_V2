# Structural Toolbox — 学生用（Mac・インストーラ版）

**Python のインストールは不要**です。教員から受け取った配布ファイルを開くだけです。解析ライブラリも同梱されているので、**インターネットも不要**です。

---

## 用意するもの

- **macOS 12 以降**（Apple シリコン / Intel のどちらでも可）
- **空きディスク** 約 1 GB

---

## 1. インストール（初回だけ）

配布の形は次のいずれかです。中身の操作は同じです。

| 受け取ったファイル | 最初にすること |
| --- | --- |
| `StructuralToolbox_Setup_Mac_YYYYMMDD.pkg` | ダブルクリックして、画面の指示に従う |
| `StructuralToolbox_Mac_YYYYMMDD.dmg` | 開き、中の **`インストール.command`** を右クリック → **開く** |
| `StructuralToolbox_Mac_Setup_YYYYMMDD.tar.gz` | ダブルクリックで展開し、フォルダ内の **`インストール.command`** を右クリック → **開く** |

`インストール.command` のとき:

1. 初回は「開発元を確認できません」と出ることがあります。**開く** を選んでください。
2. 「インストール」を押す。
3. ターミナルに「ライブラリをインストールしています」と出たら、**完了まで待つ**（2〜5 分）。
4. 「インストールが完了しました」と出たら閉じてよいです。

**.pkg** のときも、セットアップが終わるまで待ちます。管理者パスワードは不要です。

---

## 2. 毎回の使い方

1. **デスクトップ** または **アプリケーション** フォルダの **「Structural Toolbox」** を開く。
2. **ターミナル** が開き、しばらくすると **ブラウザ** が開く。
3. モデル（.dat）を選び、**Solve** で解析する。
4. 終了するときは、**ターミナルのウィンドウを閉じる**。

**解析中はターミナルを閉じないでください**（ログとサーバーがここで動きます）。

### デバッグ・ログを見たいとき（教員・開発向け）

- アプリケーションフォルダの **「Structural Toolbox (debug)」** を使う
- インストール先に **`stb_gui.log`** も保存されます

---

## 3. 最初に試すモデル

| モデル | 説明 |
| --- | --- |
| `examples/cantilever.dat` | いちばん簡単な片持ち梁 |

ファイルの場所（参考）:

`~/Library/Application Support/StructuralToolbox/examples/`

（Finder の「移動」→「フォルダへ移動」に、上のパスを貼り付けても開けます。）

---

## 4. よくあるトラブル

| 症状 | 対処 |
| --- | --- |
| 「開発元を確認できません」 | 右クリック → **開く**。またはターミナルで `bash インストール.command` |
| インストールが途中で失敗 | `インストール.command` または .pkg を再実行。直らない場合は `~/Library/Application Support/StructuralToolbox/install.log` を教員に見せる |
| ブラウザが開かない | ショートカットを再実行。`http://127.0.0.1:8765/` を手で開く |
| 「初回セットアップがまだ」 | インストール先の **`Install_once.command`** を実行（2〜5 分待つ） |
| Solve でエラー | 教員に `.dat` の行番号とメッセージを伝える |

### 専用の Python が使われているか確かめる

ターミナルに表示される `python: ~/Library/Application Support/StructuralToolbox/.venv/bin/python3 (bundled)` が目印です。

コマンドで確かめる場合:

```bash
"$HOME/Library/Application Support/StructuralToolbox/.venv/bin/stb" doctor
```

`bundled: yes` と、ライブラリの一覧が表示されれば正常です。

---

## 5. Grasshopper を使う場合

インストール時に Grasshopper が見つかれば、プラグイン `StbGrasshopper.gha` を自動で配置します（`~/Library/Application Support/Grasshopper/Libraries`）。

- Rhino を起動中だった場合は、Rhino を終了して `Install_once.command` を実行する
- STB コンポーネントの **Python Exe** と **Repo Root** は **空のまま**でよい（インストール先の専用 Python を自動で使います）
- 解析後、コンポーネントの **Summary** に使われた Python のパスが表示されます

---

## 6. アンインストール（削除）

1. 動いている **ターミナル（サーバー）を閉じる**
2. アプリケーションフォルダの **「Structural Toolbox をアンインストール」** を実行する

手動で消す場合は、次の 3 つを削除します。

- `~/Applications/Structural Toolbox.app`
- `~/Desktop/Structural Toolbox`
- `~/Library/Application Support/StructuralToolbox`

インストール先に保存したモデルも一緒に消えます。必要な `.dat` は先に別の場所へコピーしてください。

---

## 7. やらなくてよいこと

- python.org から Python を入れる
- Git やコマンドの手入力（右クリックで開けないときの `bash インストール.command` を除く）
- インストール先フォルダ内の `python-standalone-*`、`wheels`、`.venv` を削除する
