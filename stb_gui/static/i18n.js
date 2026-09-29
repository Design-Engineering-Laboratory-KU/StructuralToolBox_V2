// UI language switching (English source strings -> Japanese).
// English text in the DOM stays the source of truth; in Japanese mode a
// MutationObserver rewrites matching text nodes / attributes and remembers the
// original so switching back restores it. Engineering symbols (Nx, Vy, LC, TX,
// SECT, DIAP, ...) are intentionally left untranslated.

const LANG_STORAGE_KEY = "stb_gui_lang";
const ATTRS = ["title", "placeholder", "aria-label"];
const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "TEXTAREA", "PRE", "CODE"]);

const JA = {
  // Toolbar
  "New": "新規",
  "Open": "開く",
  "Save": "保存",
  "Close": "閉じる",
  "Reload": "再読込",
  "Solve": "解析",
  "Input file…": "入力ファイル…",
  "Project…": "プロジェクト…",
  "Loads…": "荷重…",
  "Practice…": "構造指標…",
  "Results": "結果",
  "Options": "オプション",
  "Theme": "テーマ",
  "Dark": "ダーク",
  "Light": "ライト",
  "Axes": "座標軸",
  "View: Perspective": "表示: 透視投影",
  "View: Parallel": "表示: 平行投影",
  "View…": "視点…",
  "Front": "正面",
  "Right": "右",
  "Left": "左",
  "Back": "背面",
  "Top": "上",
  "Bottom": "下",
  "Pick mode": "ピック",
  "Distance": "距離",
  "Loading…": "読み込み中…",
  "Save (Ctrl+S)": "保存 (Ctrl+S)",
  "Solve (F5)": "解析 (F5)",
  "project.json sidecar settings": "project.json の設定",
  "Load and external-force verification": "荷重・外力の検証",
  "Story drift / eccentricity / rigidity ratio": "層間変形角 / 偏心率 / 剛性率",
  "Show/hide results panel": "結果パネルの表示/非表示",
  "Display options": "表示オプション",
  "Show/hide origin XYZ axes": "原点の XYZ 軸を表示/非表示",
  "Switch perspective / parallel (axonometric)": "透視投影 / 平行投影を切り替え",
  "Standard views": "標準視点",
  "Pick mode (P). Nodes (N) / Elements (E) in panel": "ピックモード (P)。パネルで節点 (N) / 要素 (E)",
  "Distance (D)": "距離 (D)",
  "Switch Simple GUI / Advanced GUI (WIP)": "Simple GUI / Advanced GUI (WIP) を切り替え",
  "Switch to Simple GUI (hides Project / Loads / Practice)":
    "Simple GUI に切り替え（プロジェクト / 荷重 / 構造指標 を隠す）",
  "Switch to Advanced GUI (WIP): adds Project / Loads / Practice":
    "Advanced GUI (WIP) に切り替え（プロジェクト / 荷重 / 構造指標 を追加）",

  // Context menu
  "Mode": "モード",
  "Enter pick mode": "ピックモードに入る",
  "Exit pick mode (normal)": "ピックモードを終了（通常）",
  "Member visibility": "部材の表示",
  "Show selected members only": "選択部材のみ表示",
  "Hide selected members": "選択部材を非表示",
  "Show all members": "すべての部材を表示",
  "Delete Member…": "部材を削除…",
  "Support (CONS)": "支点 (CONS)",
  "Fixed": "固定",
  "Pinned": "ピン",
  "Free": "自由",
  "Apply support": "支点を適用",
  "WRW type / multiplier": "WRW 種別 / 倍率",
  "Shear panel": "面材",
  "Brace": "筋かい",
  "Apply": "適用",
  "Floor/roof multiplier (DIAP)": "床・屋根倍率 (DIAP)",
  "Create ELEM (2 nodes)": "ELEM 作成（2 節点）",
  "Beta (deg)": "Beta (度)",
  "Create": "作成",
  "Create DMEM (3+ nodes)": "DMEM 作成（3 節点以上）",
  "Create WRW (4 nodes)": "WRW 作成（4 節点）",
  "Change section": "断面を変更",
  "Change material (SECT MAT)": "材料を変更 (SECT MAT)",
  "Joint (EJNT)": "接合部 (EJNT)",
  "Edit joint…": "接合部を編集…",
  "No DIAP": "DIAP なし",
  "Selected DMEM uses explicit DMAT (SRC=0); multiplier edit unavailable.":
    "選択中の DMEM は DMAT を直接指定（SRC=0）しているため、倍率は編集できません。",

  // Viewport overlays
  "Auto": "自動",
  "Wind loads": "風荷重",
  "■ Windward": "■ 風上",
  "■ Leeward": "■ 風下",
  "→ Wind dir / F_story": "→ 風向 / F_story",
  "Colocated entities": "重複要素",
  "Edit joint (EJNT)": "接合部の編集 (EJNT)",
  "Edit the EJNT input line(s) for the picked element(s). Delete a line to restore the default rigid joint.":
    "選択した要素の EJNT 入力行を編集します。行を削除すると既定の剛接合に戻ります。",
  "Cancel": "キャンセル",
  "No model loaded.": "モデルが読み込まれていません。",

  // Results panel
  "Collapse": "折りたたむ",
  "Output": "出力",
  "Text output…": "テキスト出力…",
  "Load case & display": "荷重ケースと表示",
  "Display choices are saved automatically.": "表示設定は自動で保存されます。",
  "Def. ×": "変形倍率 ×",
  "Disp.": "変位",
  "Deformed shape": "変形図",
  "Displacement contour": "変位コンター",
  "Supports": "支点",
  "Element joints": "要素端の接合",
  "Input loads": "入力荷重",
  "Type": "種別",
  "All": "すべて",
  "Area (ALOD)": "面荷重 (ALOD)",
  "Gravity (GLOD)": "重力 (GLOD)",
  "Diaphragm (DLOD)": "床荷重 (DLOD)",
  "Line + Point": "線 + 点",
  "Load values": "荷重値",
  "Wind (surfaces / F_story)": "風荷重 (面 / F_story)",
  "Wind case": "風荷重ケース",
  "(none)": "（なし）",
  "Reactions": "反力",
  "Reaction values": "反力値",
  "Node IDs": "節点番号",
  "Element IDs": "要素番号",
  "Material": "材料",
  "Section": "断面",
  "Section solids": "断面形状",
  "DXF export": "DXF 出力",
  "Export section solid mesh to DXF (undeformed)": "断面形状メッシュを DXF に出力（変形前）",
  "Diaphragm members": "ダイアフラム要素",
  "Edge": "エッジ",
  "Show diaphragm member edge lines": "ダイアフラム要素のエッジを表示",
  "Wood walls": "木造耐力壁",
  "Show wood wall edge lines": "木造耐力壁のエッジを表示",
  "Informational only — highlights duplicate entities with identical node connectivity":
    "参考表示 — 節点構成が同じ重複要素を強調表示します",
  "Element forces": "部材応力",
  "Component": "成分",
  "None": "なし",
  "Division": "分割数",
  "Diagram ×": "応力図倍率 ×",
  "Show values": "数値を表示",

  // Pick panel
  "Pick": "ピック",
  "Pick target": "ピック対象",
  "Nodes": "節点",
  "Members": "部材",
  "Diaphragm": "ダイアフラム",
  "Wall": "壁",
  "Toggle node pick (N)": "節点ピックの切替 (N)",
  "Toggle member pick (M)": "部材ピックの切替 (M)",
  "Toggle diaphragm pick (I)": "ダイアフラムピックの切替 (I)",
  "Toggle wall pick (W)": "壁ピックの切替 (W)",
  "New ELEM (2 nodes)": "新規 ELEM（2 節点）",
  "Create member": "部材を作成",
  "New DMEM (selected nodes)": "新規 DMEM（選択節点）",
  "Create DMEM mesh": "DMEM メッシュを作成",
  "New WRW (4 nodes)": "新規 WRW（4 節点）",
  "Selected WRW": "選択中の WRW",
  "Apply type change": "種別を変更",
  "Node support (CONS)": "節点の支点 (CONS)",
  "Nothing picked": "未選択",
  "Clear picked": "選択を解除",

  // Options panel
  "Display scale": "表示スケール",
  "Saved automatically. Applies on next redraw.": "自動で保存され、次の再描画で反映されます。",
  "Load arrow": "荷重矢印",
  "Reaction arrow": "反力矢印",
  "Support symbol": "支点記号",
  "Support line": "支点の線",
  "Contour line": "コンター線",
  "Element line": "要素線",
  "Load line": "荷重線",
  "Reaction line": "反力線",
  "Force line": "応力線",
  "Node ID": "節点番号",
  "Elem ID": "要素番号",
  "Load value": "荷重値",
  "Reaction value": "反力値",
  "Force value": "応力値",
  "Section color": "断面の色",
  "Section alpha": "断面の不透明度",

  // Status bar
  "Ready": "準備完了",
  "use New or Open": "「新規」または「開く」を使ってください",
  "Pick one or more elements first": "先に要素を 1 つ以上選択してください",
  "Loading EJNT lines…": "EJNT 行を読み込み中…",
  "Undo/redo history does not match the current model": "元に戻す/やり直しの履歴が現在のモデルと一致しません",
  "Nothing to undo": "元に戻す操作はありません",
  "Nothing to redo": "やり直す操作はありません",
  "undo (Ctrl+Z)": "元に戻しました (Ctrl+Z)",
  "redo (Ctrl+Y)": "やり直しました (Ctrl+Y)",
  "Applying edit…": "編集を適用中…",
  "edit saved": "編集を保存しました",
  "Popup blocked": "ポップアップがブロックされました",
  "allow popups for this site": "このサイトのポップアップを許可してください",
  "saved": "保存しました",
  "project settings opened": "プロジェクト設定を開きました",
  "Open a model before using Loads…": "「荷重…」を使う前にモデルを開いてください",
  "Open a model before using Practice…": "「構造指標…」を使う前にモデルを開いてください",
  "load verification opened": "荷重検証を開きました",
  "structural indices opened": "構造指標を開きました",
  "no changes to save": "保存する変更はありません",
  "input file saved (undo history cleared)": "入力ファイルを保存しました（元に戻す履歴はクリア）",
  "No model open": "モデルが開かれていません",
  "input file opened (editable)": "入力ファイルを開きました（編集可）",
  "output opened in new window": "出力を新しいウィンドウで開きました",
  "Creating new model…": "新規モデルを作成中…",
  "new model": "新規モデル",
  "opened": "開きました",
  "Closing…": "閉じています…",
  "Loading wind overlay…": "風荷重表示を読み込み中…",
  "No wind cases for this model.": "このモデルには風荷重ケースがありません。",
  "CoG / CoR requires analysis": "CoG / CoR の表示には解析が必要です",
  "use Solve (F5) first.": "先に「解析」(F5) を実行してください。",
  "force data unavailable (restart stb gui)": "応力データがありません（stb gui を再起動してください）",
  "Distance: click 2 nodes (0/2)": "距離: 節点を 2 つクリック (0/2)",
  "Distance: click 2nd node (1/2)": "距離: 2 つ目の節点をクリック (1/2)",

  // Dialogs
  "WRW type must be shear panel or brace.": "WRW 種別は面材または筋かいを指定してください。",
  "Enter a positive wall multiplier.": "正の壁倍率を入力してください。",
  "Enter a positive floor/roof multiplier.": "正の床・屋根倍率を入力してください。",
  "Pick at least 3 nodes (no elements / DMEM / WRW) to create DMEM.":
    "DMEM を作成するには節点を 3 つ以上選択してください（要素 / DMEM / WRW は選択しない）。",
  "Select a DIAP for the new DMEM.": "新しい DMEM の DIAP を選んでください。",
  "Pick exactly 2 nodes (no elements / DMEM / WRW) to create a member.":
    "部材を作成するには節点をちょうど 2 つ選択してください（要素 / DMEM / WRW は選択しない）。",
  "Select a section for the new ELEM.": "新しい ELEM の断面を選んでください。",
  "Pick exactly 4 nodes (no elements / DMEM / WRW) to create a WRW wall.":
    "WRW 壁を作成するには節点をちょうど 4 つ選択してください（要素 / DMEM / WRW は選択しない）。",
  "All elements sharing the same section will be affected.": "同じ断面を使うすべての要素に影響します。",
  "Deleting node(s) will also remove connected elements and related records.":
    "節点を削除すると、接続する要素と関連レコードも削除されます。",
  "free (no CONS)": "自由（CONS なし）",
  "no DIAP tie": "DIAP 接続なし",

  // Popup windows (input editor / text output)
  "Save text": "テキストを保存",
  "Save as PDF (A4 landscape)": "PDF で保存（A4 横）",
  "ready": "準備完了",
  "saving...": "保存中...",
  "no changes": "変更なし",
  "save failed": "保存失敗",
  "reloading...": "再読込中...",
  "reloaded": "再読込しました",
  "reload failed": "再読込失敗",
};

const PICK_TARGETS_JA = { node: "節点", member: "部材", diaphragm: "ダイアフラム", wall: "壁" };

function countPhrase(n, noun) {
  const map = {
    node: "節点", element: "要素", member: "部材", diaphragm: "ダイアフラム", wall: "壁",
    "WRW record": "WRW",
  };
  return (map[noun] || noun) + " " + n;
}

function translateCountList(s) {
  const parts = s.split(", ");
  const out = [];
  for (const p of parts) {
    const m = /^(\d+) (node|element|member|diaphragm|wall)s?$/.exec(p);
    if (m) { out.push(countPhrase(m[1], m[2])); continue; }
    if (/^\d+ (DMEM|WRW)$/.test(p)) { out.push(p); continue; }
    return null;
  }
  return out.join("、");
}

const PICK_HINT_TAIL =
  " Toggle Pick target buttons to filter. Click or drag to pick. Shift+click adds. Ctrl+click removes. Right-click = menu. Esc clears.";

// [regex, (match) => translated]; the first match wins.
const PATTERNS = [
  [/^Error: ([\s\S]*)$/, (m) => "エラー: " + m[1]],
  [/^Display error: ([\s\S]*)$/, (m) => "表示エラー: " + m[1]],
  [/^Undo\/redo error: ([\s\S]*)$/, (m) => "元に戻す/やり直しエラー: " + m[1]],
  [/^Edit error: ([\s\S]*)$/, (m) => "編集エラー: " + m[1]],
  [/^Failed to load EJNT lines: ([\s\S]*)$/, (m) => "EJNT 行の読み込みに失敗しました: " + m[1]],
  [/^Undo\/redo failed: ([\s\S]*)$/, (m) => "元に戻す/やり直しに失敗しました: " + m[1]],
  [/^Edit failed: ([\s\S]*)$/, (m) => "編集に失敗しました: " + m[1]],
  [/^Save failed: ([\s\S]*)$/, (m) => "保存に失敗しました: " + m[1]],
  [/^Reload failed: ([\s\S]*)$/, (m) => "再読込に失敗しました: " + m[1]],
  [/^Loading project for (.+)…$/, (m) => m[1] + " のプロジェクトを読み込み中…"],
  [/^Loading (.+)…$/, (m) => m[1] + " を読み込み中…"],
  [/^Saving (.+)…$/, (m) => m[1] + " を保存中…"],
  [/^Solving (.+) for output…$/, (m) => m[1] + " を解析中（出力用）…"],
  [/^Solving (.+)…$/, (m) => m[1] + " を解析中…"],
  [/^Opening (.+)…$/, (m) => m[1] + " を開いています…"],
  [/^(.+) \(solved\)$/, (m) => m[1] + "（解析済み）"],
  [/^(\d+) nodes, (\d+) elements$/, (m) => "節点 " + m[1] + "、要素 " + m[2]],
  [/^no reaction data for LC (.+)$/, (m) => "LC " + m[1] + " の反力データがありません"],
  [/^edit EJNT for element\(s\) (.+)$/, (m) => "要素 " + m[1] + " の EJNT を編集"],
  [/^Distance: (.+)$/, (m) => "距離: " + m[1]],
  [/^(.+) picked$/, (m) => {
    const list = translateCountList(m[1]);
    return list ? list + " を選択中" : null;
  }],
  [/^\.\.\. and (\d+) more$/, (m) => "…ほか " + m[1] + " 件"],
  [/^Nodes (.+) → (\d+)$/, (m) => "節点 " + m[1] + " → " + m[2]],
  [/^Nodes (.+) → wall rectangle$/, (m) => "節点 " + m[1] + " → 壁の矩形"],
  [/^Nodes (.+) → one triangle$/, (m) => "節点 " + m[1] + " → 三角形 1 つ"],
  [/^Nodes (.+) → triangle$/, (m) => "節点 " + m[1] + " → 三角形"],
  [/^(\d+) nodes → auto triangulation inside the picked region$/,
    (m) => "節点 " + m[1] + " → 選択範囲内を自動で三角形分割"],
  [/^(\d+) nodes → auto triangulation$/, (m) => "節点 " + m[1] + " → 自動で三角形分割"],
  [/^Updates DIAP id\(s\): (.+)$/, (m) => "更新する DIAP: " + m[1]],
  [/^ELEMENT FORCE: (.+)$/, (m) => "部材応力: " + m[1]],
  [/^(All targets \(Nodes, Members(, Diaphragm, Wall)?\)\.|Filtered: (.+)\.)( Toggle Pick target.*)$/, (m) => {
    const head = m[3]
      ? "絞り込み: " + m[3].split(", ").map((k) => PICK_TARGETS_JA[k] || k).join("、") + "。"
      : (m[2] ? "すべての対象（節点、部材、ダイアフラム、壁）。" : "すべての対象（節点、部材）。");
    if (m[4] !== PICK_HINT_TAIL) return null;
    return head + "ピック対象ボタンで絞り込めます。クリックまたはドラッグで選択、Shift+クリックで追加、"
      + "Ctrl+クリックで除外、右クリックでメニュー、Esc で解除。";
  }],
  [/^Create ELEM between nodes (\S+) and (\S+) \(SECT (.+)\)\?$/,
    (m) => "節点 " + m[1] + " と " + m[2] + " の間に ELEM（SECT " + m[3] + "）を作成しますか？"],
  [/^Create DMEM on DIAP (\S+) with nodes (.+)\?$/,
    (m) => "節点 " + m[2] + " で DIAP " + m[1] + " に DMEM を作成しますか？"],
  [/^Create DMEM mesh on DIAP (\S+) from (\d+) nodes \(auto triangulation\)\?$/,
    (m) => "節点 " + m[2] + " 個から DIAP " + m[1] + " に DMEM メッシュを作成しますか？（自動三角形分割）"],
  [/^Set support \((.*)\) for (\d+) nodes?\?$/,
    (m) => "節点 " + m[2] + " 個に支点（" + translateString(m[1]) + "）を設定しますか？"],
  [/^Change (\d+) WRW records? to (.+)\?$/,
    (m) => "WRW " + m[1] + " 件を" + translateString(m[2]) + "に変更しますか？"],
  [/^Change material to MATE (.+)\?$/, (m) => "材料を MATE " + m[1] + " に変更しますか？"],
  [/^Delete (\d+) selected members?\?$/, (m) => "選択した " + m[1] + " 件を削除しますか？"],
  [/^\((.+)\)$/, (m) => {
    const list = translateCountList(m[1]);
    return list ? "（" + list + "）" : null;
  }],
  [/^Create WRW \((.+), M=(.+), (.+)\) with nodes (.+)\?$/,
    (m) => "節点 " + m[4] + " で WRW（" + translateString(m[1]) + "、M=" + m[2] + "、"
      + translateString(m[3]) + "）を作成しますか？"],
];

function translateAtom(s) {
  if (Object.prototype.hasOwnProperty.call(JA, s)) return JA[s];
  for (const [re, fn] of PATTERNS) {
    const m = re.exec(s);
    if (!m) continue;
    const out = fn(m);
    if (out != null) return out;
  }
  if (s.includes(" + ")) {
    const parts = s.split(" + ");
    if (parts.every((p) => Object.prototype.hasOwnProperty.call(JA, p))) {
      return parts.map((p) => JA[p]).join(" + ");
    }
  }
  return null;
}

function translateLine(line) {
  const lead = line.match(/^\s*/)[0];
  const trail = line.match(/\s*$/)[0];
  const core = line.slice(lead.length, line.length - trail.length);
  if (!core || !/[A-Za-z]/.test(core)) return line;
  let out = translateAtom(core);
  if (out == null && core.includes(" — ")) {
    const parts = core.split(" — ");
    const mapped = parts.map((p) => translateAtom(p));
    if (mapped.some((p) => p != null)) {
      out = parts.map((p, i) => (mapped[i] != null ? mapped[i] : p)).join(" — ");
    }
  }
  return out == null ? line : lead + out + trail;
}

export function translateString(s) {
  if (currentLang !== "ja" || typeof s !== "string" || !s) return s;
  if (!s.includes("\n")) return translateLine(s);
  return s.split("\n").map(translateLine).join("\n");
}

let currentLang = "en";
const textRecords = new WeakMap();
const attrRecords = new WeakMap();
const attachedDocs = new Set();

function skipped(node) {
  const elem = node.nodeType === 1 ? node : node.parentElement;
  if (!elem) return true;
  if (SKIP_TAGS.has(elem.tagName)) return true;
  return !!elem.closest("[translate=\"no\"], textarea, pre");
}

function applyText(node) {
  if (skipped(node)) return;
  const current = node.data;
  const rec = textRecords.get(node);
  if (rec && current === rec.out) return;
  const out = translateString(current);
  if (out !== current) {
    textRecords.set(node, { src: current, out: out });
    node.data = out;
  } else {
    textRecords.delete(node);
  }
}

function applyAttr(elem, name) {
  if (skipped(elem)) return;
  const current = elem.getAttribute(name);
  if (current == null) return;
  let recs = attrRecords.get(elem);
  const rec = recs && recs.get(name);
  if (rec && current === rec.out) return;
  const out = translateString(current);
  if (out !== current) {
    if (!recs) { recs = new Map(); attrRecords.set(elem, recs); }
    recs.set(name, { src: current, out: out });
    elem.setAttribute(name, out);
  } else if (recs) {
    recs.delete(name);
  }
}

function restoreText(node) {
  const rec = textRecords.get(node);
  if (rec && node.data === rec.out) node.data = rec.src;
  textRecords.delete(node);
}

function restoreAttrs(elem) {
  const recs = attrRecords.get(elem);
  if (!recs) return;
  for (const [name, rec] of recs) {
    if (elem.getAttribute(name) === rec.out) elem.setAttribute(name, rec.src);
  }
  attrRecords.delete(elem);
}

function walk(root, onText, onElem) {
  if (!root) return;
  if (root.nodeType === 3) { onText(root); return; }
  if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
  if (root.nodeType === 1) onElem(root);
  const doc = root.ownerDocument || root;
  const tw = doc.createTreeWalker(root, 1 | 4);
  let n = tw.nextNode();
  while (n) {
    if (n.nodeType === 3) onText(n); else onElem(n);
    n = tw.nextNode();
  }
}

function translateTree(root) {
  walk(root, applyText, (e) => { for (const a of ATTRS) if (e.hasAttribute(a)) applyAttr(e, a); });
}

function restoreTree(root) {
  walk(root, restoreText, restoreAttrs);
}

function onMutations(records) {
  if (currentLang !== "ja") return;
  for (const r of records) {
    if (r.type === "characterData") applyText(r.target);
    else if (r.type === "attributes") applyAttr(r.target, r.attributeName);
    else for (const n of r.addedNodes) translateTree(n);
  }
}

export function attachI18n(doc) {
  if (!doc || attachedDocs.has(doc)) {
    if (doc && currentLang === "ja") translateTree(doc.body);
    return;
  }
  attachedDocs.add(doc);
  const win = doc.defaultView || window;
  const observer = new win.MutationObserver(onMutations);
  observer.observe(doc.documentElement, {
    subtree: true, childList: true, characterData: true,
    attributes: true, attributeFilter: ATTRS,
  });
  if (win !== window) win.addEventListener("unload", () => attachedDocs.delete(doc));
  if (currentLang === "ja") translateTree(doc.body);
}

export function getLanguage() {
  return currentLang;
}

export function setLanguage(lang) {
  currentLang = lang === "ja" ? "ja" : "en";
  try { localStorage.setItem(LANG_STORAGE_KEY, currentLang); } catch (e) { /* ignore */ }
  for (const doc of attachedDocs) {
    doc.documentElement.lang = currentLang;
    if (currentLang === "ja") translateTree(doc.body); else restoreTree(doc.body);
  }
  const select = document.getElementById("optLanguage");
  if (select) select.value = currentLang;
}

function initialLanguage() {
  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    if (saved === "ja" || saved === "en") return saved;
  } catch (e) { /* ignore */ }
  return (navigator.language || "").toLowerCase().startsWith("ja") ? "ja" : "en";
}

for (const name of ["alert", "confirm", "prompt"]) {
  const native = window[name].bind(window);
  window[name] = (msg, ...rest) => native(translateString(msg == null ? msg : String(msg)), ...rest);
}

attachI18n(document);
setLanguage(initialLanguage());
const languageSelect = document.getElementById("optLanguage");
if (languageSelect) {
  languageSelect.addEventListener("change", () => setLanguage(languageSelect.value));
}
