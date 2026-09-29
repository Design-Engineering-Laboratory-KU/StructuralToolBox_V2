# Structural Toolbox — 学生用（Windows・インストーラ版）

**Python のインストールは不要**です。教員から受け取った **Setup.exe** を実行するだけです。解析ライブラリも同梱されているので、**インターネットも不要**です。

---

## 用意するもの

- **Windows 10 / 11**（64 ビット）
- **空きディスク** 約 1 GB

---

## 1. インストール（初回だけ）

1. **`StructuralToolbox_Setup_YYYYMMDD.exe`** をダブルクリックする。
2. 画面の指示に従う（インストール先はそのままで問題ありません）。
3. 「ライブラリをセットアップしています」と表示されたら、**完了まで待つ**（2〜5 分）。
4. 完了メッセージを読んでウィザードを閉じる。

**黒い画面が一瞬出ることがあります** — セットアップ用です。操作は不要です。

---

## 2. 毎回の使い方

1. **スタートメニュー** または **デスクトップ** の **「Structural Toolbox」** を開く。
2. **黒い画面（コマンドプロンプト）** が開き、しばらくすると **ブラウザ** が開く。
3. モデル（.dat）を選び、**Solve** で解析する。
4. 終了するときは、**黒い画面を閉じる**。

**解析中は黒い画面を閉じないでください**（ログとサーバーがここで動きます）。

### デバッグ・ログを見たいとき（教員・開発向け）

- スタートメニューの **「Structural Toolbox (debug)」** を使う  
  またはインストール先の **`Start Structural Toolbox (debug).bat`**
- コンソールが残り、同じフォルダに **`stb_gui.log`** も保存されます。

---

## 3. 最初に試すモデル

| モデル | 説明 |
| --- | --- |
| `examples/cantilever.dat` | いちばん簡単な片持ち梁 |

ファイルの場所（参考）:

`C:\Users\（あなたの名前）\AppData\Local\StructuralToolbox\examples\`

（エクスプローラーのアドレス欄に `%LOCALAPPDATA%\StructuralToolbox` と入力しても開けます。）

---

## 4. よくあるトラブル

| 症状 | 対処 |
| --- | --- |
| インストールが途中で失敗 | Setup.exe を再実行。直らない場合は `%LOCALAPPDATA%\StructuralToolbox\install.log` を教員に見せる |
| ブラウザが開かない | ショートカットを再実行。`http://127.0.0.1:8765/` を手で開く |
| 「初回セットアップがまだ」 / stb.exe がない | スタートメニューの **「初回セットアップを再実行」** を実行（2〜5 分待つ） |
| ショートカットが stb.exe を探す | 新しい Setup.exe で再インストールするか、ショートカットの代わりにフォルダ内の **Start Structural Toolbox.bat** を実行 |
| Solve でエラー | 教員に `.dat` の行番号とメッセージを伝える |

### 専用の Python が使われているか確かめる

黒い画面に表示される `python: ...\StructuralToolbox\.venv\Scripts\python.exe (bundled)` が目印です。

コマンドで確かめる場合は、エクスプローラのアドレス欄に `%LOCALAPPDATA%\StructuralToolbox` を入れて開き、そこで次を実行します。

```
.venv\Scripts\stb.exe doctor
```

`bundled: yes` と、ライブラリの一覧が表示されれば正常です。

---

## 5. ZIP 版を使っている場合

教員が ZIP を配布した場合は [学生用_はじめ方_Windows.md](学生用_はじめ方_Windows.md) を参照してください（`Install_once.bat` / `Start Structural Toolbox.bat`）。

---

## 6. アンインストール（削除）

スタートメニューに「アンインストール」が無い場合でも、次のいずれかで削除できます。

1. **Windows の設定** → **アプリ** → **インストールされているアプリ** → **Structural Toolbox** → **アンインストール**
2. エクスプローラのアドレス欄に次を貼り付けて Enter → **`unins000.exe`** をダブルクリック:
   ```
   %LOCALAPPDATA%\StructuralToolbox
   ```

削除の前に、動いている **黒い画面（サーバー）を閉じて** ください。

新しいインストーラでは、スタートメニューに **「Structural Toolbox をアンインストール」** も追加されます。

---

## 7. Grasshopper を使う場合

インストール時に Grasshopper が見つかれば、プラグイン `StbGrasshopper.gha` を自動で配置します（`%APPDATA%\Grasshopper\Libraries`）。

- Rhino を起動中だった場合は、Rhino を終了してスタートメニューの **「初回セットアップを再実行」** を実行する
- STB コンポーネントの **Python Exe** と **Repo Root** は **空のまま**でよい（インストール先の専用 Python を自動で使います）
- 解析後、コンポーネントの **Summary** に使われた Python のパスが表示されます

---

## 8. やらなくてよいこと

- python.org から Python を入れる
- Git やコマンドの手入力
- インストール先フォルダ内の `python-embed`、`wheels`、`.venv` を削除する
