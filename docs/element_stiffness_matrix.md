# 要素剛性マトリックスの考え方

本ドキュメントは、本プログラム（`classes/elm.py`）で構築している **1次元梁要素（`Elm1D`）** の剛性マトリックスが、どのような理論・考え方に基づいているかを整理したものです。

実際の解析で使われているのは `mdl.Mdl.CalcElemMatrices()` から呼ばれる **`Elm1D.ElmStiffMX()`** です。

```python
# classes/mdl.py — CalcElemMatrices()
for e in self.elms:
    e.ek  = e.ElmStiffMX()
    e.tm  = e.ElmTransMX()
    e.ekG = np.matmul(np.matmul(e.tm.T, e.ek), e.tm)
```

`elm.py` には剛性マトリックスを作る関数が3つありますが、位置づけは次の通りです。

| 関数 | 内容 | 使用状況 |
| --- | --- | --- |
| `SS0_ElmStiffMX()` | 古典的な Bernoulli-Euler 梁（せん断変形・端部バネなし） | 参照・検証用（未使用） |
| **`ElmStiffMX()`** | **せん断変形＋端部回転バネを考慮した剛性** | **実際に使用中** |
| `SS_ElmStiffMX()` | 端部バネ＋剛域を「柔性行列」経由で組む別実装 | 未使用（剛域対応版） |

> **数式の表示**
>
> - **Cursor の Markdown プレビュー**（`Ctrl+Shift+V`）: 設定 `markdown.math.enabled` を有効にし、拡張機能 **Markdown Math**（`@builtin`）が無効化されていないことを確認してください。表示されない場合は下記 HTML プレビューを使ってください。
> - **HTML プレビュー（推奨・確実）**: ターミナルで `python3 docs/build_stiffness_doc_html.py` を実行し、生成された `docs/element_stiffness_matrix.html` をブラウザで開く。または **Ctrl+Shift+P** → `Tasks: Run Task` → `docs: open stiffness matrix HTML preview`。

---

## 1. 自由度の取り方

各要素は両端 2 節点 × 6 自由度（並進3＋回転3）の計 **12 自由度** をもち、剛性マトリックスは $12 \times 12$ です。要素局所座標系（ECS）での自由度の並びは以下の通りです。

| index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 内容 | $u_{xi}$ | $u_{yi}$ | $u_{zi}$ | $\theta_{xi}$ | $\theta_{yi}$ | $\theta_{zi}$ | $u_{xj}$ | $u_{yj}$ | $u_{zj}$ | $\theta_{xj}$ | $\theta_{yj}$ | $\theta_{zj}$ |

- $x$ : 部材軸方向（軸力・伸縮）
- $y$, $z$ : 断面の主軸方向（曲げ・せん断）
- $\theta_x$ : ねじり、$\theta_y$, $\theta_z$ : 曲げ回転

成分は **軸方向・$z$ 軸まわりの曲げ・$y$ 軸まわりの曲げ・ねじり** の 4 つのブロックに分けて組み立てています。

---

## 2. 基本形：Bernoulli-Euler 梁（`SS0_ElmStiffMX`）

剛域・端部バネ・せん断変形をすべて無視した「教科書通り」の剛性で、現行式の基準となるものです。

- **軸:** $EA/L$
- **ねじり:** $GJ/L$
- **曲げ（$z$ 軸まわり）** — 並進–回転 $2 \times 2$ ブロック（$u_y$–$\theta_z$ 系）:

$$
\begin{bmatrix}
k_{vv} & k_{v\theta} \\
k_{\theta v} & k_{\theta\theta}
\end{bmatrix}
=
\begin{bmatrix}
\dfrac{12 E I_z}{L^3} & \dfrac{6 E I_z}{L^2} \\
\dfrac{6 E I_z}{L^2} & \dfrac{4 E I_z}{L}
\end{bmatrix}
\quad \text{（$y$ 軸まわり曲げは $I_y$ で同形）}
$$

ここで $E$ ヤング係数、$A$ 断面積、$I_y$, $I_z$ 断面二次モーメント、$J$ ねじり定数、$L$ 部材長です。

---

## 3. 実使用版：せん断変形＋端部回転バネ（`ElmStiffMX`）

現行の剛性は基本形に対して、**(a) せん断変形** と **(b) 端部回転バネ（半剛接合）** の 2 つを上乗せしています。

### (a) せん断変形（Timoshenko 梁）

Przemieniecki *Theory of Matrix Structural Analysis* に従い、せん断変形の影響を表す無次元係数 $\Phi$ を導入します。

```python
# classes/elm.py
PHIy = 12.0 * E * Iz / (G * Asy * L**2)
PHIz = 12.0 * E * Iy / (G * Asz * L**2)
```

$$
\Phi_y = \frac{12 E I_z}{G A_{sy} L^2},
\qquad
\Phi_z = \frac{12 E I_y}{G A_{sz} L^2}
$$

- $G$ せん断弾性係数、$A_{sy}$, $A_{sz}$ せん断有効断面積。
- 曲げ剛性の各項を $1/(1+\Phi)$ 系の係数で割り引くことで、**せん断変形分だけ柔らかく**なります。
- $\Phi \to 0$（細長い部材／せん断剛性が大）の極限で Bernoulli-Euler 梁に一致します。

### (b) 端部回転バネ（半剛接合）

藤井・松本 *Excel-FEM (2021)* の定式化に基づき、部材両端の曲げ回転に **回転バネ** を入れて半剛接合を表現します。バネ剛性 $R$ を曲げ剛性で無次元化したパラメータ $\lambda$ を使います。

```python
# classes/elm.py
lyi = Ryi / (E * Iy)   # λ_yi
lzi = Rzi / (E * Iz)   # λ_zi
lyj = Ryj / (E * Iy)   # λ_yj
lzj = Rzj / (E * Iz)   # λ_zj
lz1 = 1.0 + lzi + lzj
ly1 = 1.0 + lyi + lyj
cz  = E * Iz / L**3
cy  = E * Iy / L**3
```

$$
\lambda_{zi} = \frac{R_{zi}}{E I_z},
\quad
\lambda_{zj} = \frac{R_{zj}}{E I_z},
\quad
\lambda_{yi} = \frac{R_{yi}}{E I_y},
\quad
\lambda_{yj} = \frac{R_{yj}}{E I_y}
$$

$z$ 軸まわり曲げの代表項（`esm` の $(1,1)$, $(1,5)$, $(5,5)$, $(5,11)$ など）は次の形です（$i$ 端・$j$ 端の $\lambda$ で接合度を制御）。

$$
\begin{aligned}
k_{11} &= \frac{6 c_z \left(\lambda_{zi} + \lambda_{zj} + 4 \lambda_{zi}\lambda_{zj}\right)}{(1+\lambda_{zi}+\lambda_{zj})(1+\Phi_y)} \\
k_{15} &= \frac{6 c_z \lambda_{zi} (1 + 2\lambda_{zj}) L}{(1+\lambda_{zi}+\lambda_{zj})(1+\Phi_y)} \\
k_{55} &= \frac{(4+\Phi_y)}{(1+\Phi_y)} \cdot \frac{c_z \lambda_{zi}(1+\lambda_{zj})}{1+\lambda_{zi}+\lambda_{zj}} \cdot \frac{3}{2} L^2 \\
k_{5,11} &= \frac{(2-\Phi_y)}{(1+\Phi_y)} \cdot \frac{c_z \lambda_{zi}\lambda_{zj}}{1+\lambda_{zi}+\lambda_{zj}} \cdot 3 L^2
\end{aligned}
$$

ここで $c_z = E I_z / L^3$。$y$ 軸まわり曲げは $\Phi_z$, $\lambda_{yi}$, $\lambda_{yj}$, $c_y$ で同様です。

#### $\lambda$ の意味（極限のチェック）

$\lambda$ は **0 = 完全ピン、1 = 完全剛接合** に対応するよう正規化されています（$\Phi = 0$ で確認）。

| 端部条件 | $(\lambda_i, \lambda_j)$ | $k_{11}$ | $k_{15}$ | $k_{55}$ | $k_{5,11}$ |
| --- | --- | --- | --- | --- | --- |
| 両端剛 | $(1, 1)$ | $12EI/L^3$ | $6EI/L^2$ | $4EI/L$ | $2EI/L$ |
| $i$ 端ピン | $(0, 1)$ | $3EI/L^3$ | $0$ | $0$ | $0$ |
| $j$ 端ピン | $(1, 0)$ | $3EI/L^3$ | $6EI/L^2$ | $3EI/L$ | $0$ |

→ $\lambda = 1$ で §2 の Bernoulli-Euler 剛接合に一致し、$\lambda = 0$ で片持ち／ピン支持梁の値（$3EI/L^3$）に一致します。**中間の値を与えれば任意の半剛接合**になります。

### ねじり・軸

ねじり $GJ/L$ と軸 $EA/L$ には端部バネ・せん断の補正は入れていません（純粋に弾性）。

---

## 4. 端部バネ剛性 $R$ の決め方（入力との対応）

$R$（$R_{yi}$, $R_{zi}$, $R_{yj}$, $R_{zj}$）は **EJNT** 入力と既定値から決まります。

```python
# classes/mdl.py — _joint_fixity_R（要約）
if r is None:  R = E * I                  # λ = 1 → 剛接合
elif r == 0:   R = 0                      # λ = 0 → ピン
else:
    gamma = r * L / (E * I)
    R = E * I * gamma / (gamma + 6)       # λ = γ / (γ + 6)
# Ryi, Rzi, Ryj, Rzj はそれぞれ自分の入力欄 (ryi, rzi, ryj, rzj) から決まる
```

- **EJNT 指定なし・空欄（既定）** → $R = EI$、$\lambda = 1$ で **完全剛接合**。
- **EJNT に 0** → $\lambda = 0$ で **ピン接合**。
- **EJNT に正の値 $r$**（kN·m/rad、`io.py` で N·m/rad に換算）→ $\gamma = rL/(EI)$ として $\lambda = \gamma/(\gamma+6)$。
  §3 の剛性式は、この $\lambda$ で「部材端に回転バネ $r$ を直列に付けた」物理モデルと一致します
  （$\Phi = 0$ で $k_{11}$, $k_{15}$, $k_{55}$ を確認）。$r \to \infty$ で剛接合に近づき、剛接合を超えることはありません。
- 負の値はエラーになります。

### 部材荷重の固定端力

ELOD / ALOD / GLOD の等価節点力は、まず両端剛接の公式で求めた後、`classes/solve.py` の
`_release_fixed_end_forces` で端部バネを通して縮約します（部材内部の端回転を静的縮約）。
ピン端では固定端モーメントが 0 になり、せん断が再配分されます（例：一端ピンの等分布荷重で $5wL/8$, $3wL/8$, $wL^2/8$）。
部材力の算出にも同じ補正後の値が使われます。

> **入力単位の注意:** `EJNT` の値は `io.py` 側で $\times 10^3$（kN·m/rad → N·m/rad）の換算を受けます。

---

## 5. 剛域（Rigid Zone）について

「端部バネ」は **実装され使用中** ですが、**剛域は現行の `ElmStiffMX()` には含まれていません**。

剛域に対応する実装は **`SS_ElmStiffMX()`**（青山・武村の理論に基づく別実装、**現状未使用**）にあります。剛性を直接書き下すのではなく、**柔性行列 $\mathbf{F}$ を組んでから反転** して剛性を得ます。剛域は平衡（移動）行列 $\mathbf{H}$ の中で部材長 $L$ のオフセットとして表現されます。

```python
# classes/elm.py — SS_ElmStiffMX()（要約）
H[4, 2] = -L
H[5, 1] =  L
F     = H.T @ Fci @ H + Fm + Fcj
K11   = H @ inv(F) @ H.T
K12   = -H @ inv(F)
K22   = inv(F)
```

$$
\mathbf{F} = \mathbf{H}^{\mathsf{T}} \mathbf{F}_{ci} \mathbf{H} + \mathbf{F}_m + \mathbf{F}_{cj}
$$

$$
\mathbf{K} =
\begin{bmatrix}
\mathbf{K}_{11} & \mathbf{K}_{12} \\
\mathbf{K}_{21} & \mathbf{K}_{22}
\end{bmatrix}
=
\begin{bmatrix}
\mathbf{H}\mathbf{F}^{-1}\mathbf{H}^{\mathsf{T}} & -\mathbf{H}\mathbf{F}^{-1} \\
-\mathbf{F}^{-1}\mathbf{H}^{\mathsf{T}} & \mathbf{F}^{-1}
\end{bmatrix}
$$

- $\mathbf{F}_{ci}$, $\mathbf{F}_{cj}$ : 両端 6 自由度ぶんの接合バネ（並進＋回転）の柔性
- $\mathbf{H}$ : 剛域長ぶんモーメント・せん断を端点へ移す平衡行列
- $\mathbf{F}_m$ : 部材本体の柔性（せん断変形項を含む）

**剛域を有効化したい場合**は `SS_ElmStiffMX()` 系へ切り替え、$\mathbf{H}$ の $L$ を実際の剛域長に置き換える構成です。標準解析パスは `ElmStiffMX()`（端部バネ＋せん断変形のみ）です。

---

## 6. 局所→全体への変換

要素剛性は ECS で組み立て、座標変換マトリックス $\mathbf{T}$（`ElmTransMX()`）で全体座標系（GCS）へ写します。

$$
\mathbf{K}_{\mathrm{global}} = \mathbf{T}^{\mathsf{T}} \, \mathbf{k}_{\mathrm{local}} \, \mathbf{T}
$$

$\mathbf{T}$ は方向余弦 $(l, m, n)$ と部材回転角 $\beta$（`theta`）から作る $3 \times 3$ ブロックを対角に 4 つ並べた $12 \times 12$ 行列です。部材が $Z$ 軸に平行な場合（$lm \approx 0$）は分岐して特異点を回避しています。

---

## 7. まとめ

- 現行の要素剛性 **`ElmStiffMX()`** は **Timoshenko 梁（せん断変形）＋端部回転バネ（半剛接合）** を考慮している。
- 端部バネは無次元パラメータ $\lambda = R/(EI)$ で表現し、**$\lambda = 1$ で剛接合、$\lambda = 0$ でピン**、中間値で半剛接合。既定値は $R = EI$（＝剛接合）。
- **剛域は現行の標準パスには未反映**。剛域対応は柔性行列方式の **`SS_ElmStiffMX()`**（$\mathbf{H}$ 行列の $L$ オフセット）に実装されているが現状は未使用。
- 軸・ねじりは弾性のみ。要素剛性は ECS で組み、$\mathbf{K}_{\mathrm{global}} = \mathbf{T}^{\mathsf{T}} \mathbf{k} \mathbf{T}$ で全体座標へ変換する。
