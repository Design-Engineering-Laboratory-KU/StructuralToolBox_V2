(function () {
  "use strict";

  const STORE_KEY = "stb_report_paths_v1";
  const KIND_SUFFIX = { confirmation: "_report", wall_quantity: "_wallcalc" };
  const FORMAT_EXT = { html: ".html", markdown: ".md", pdf: ".pdf" };
  const KIND_ENDPOINT = { confirmation: "/api/report/confirmation", wall_quantity: "/api/report/wall-quantity" };
  const params = new URLSearchParams(window.location.search);
  const modelPath = params.get("path") || "";

  const el = {
    form: document.getElementById("rpForm"),
    input: document.getElementById("rpInput"),
    output: document.getElementById("rpOutput"),
    format: document.getElementById("rpFormat"),
    kind: document.getElementById("rpKind"),
    btnRun: document.getElementById("btnRpRun"),
    btnCurrent: document.getElementById("btnRpCurrent"),
    status: document.getElementById("rpStatus"),
    openRow: document.getElementById("rpOpenRow"),
    btnOpen: document.getElementById("btnRpOpen"),
    outPath: document.getElementById("rpOutPath"),
    warnings: document.getElementById("rpWarnings"),
    warnCount: document.getElementById("rpWarnCount"),
    warnList: document.getElementById("rpWarnList"),
  };

  let lastToken = null;
  let modelDefaults = null;

  function guiApiOrigin() {
    if (window.__stbGuiOrigin && window.__stbGuiOrigin !== "null") return window.__stbGuiOrigin;
    try {
      if (window.opener && window.opener.__stbGuiOrigin) return window.opener.__stbGuiOrigin;
    } catch (_) {
      /* cross-origin */
    }
    return window.location.origin || "";
  }

  function guiApiUrl(path) {
    const origin = guiApiOrigin();
    if (!origin) throw new Error("GUI API の接続先を特定できません。");
    return origin + (path.startsWith("/") ? path : "/" + path);
  }

  function loadStored() {
    try {
      const raw = window.localStorage.getItem(STORE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (_) {
      return null;
    }
  }

  function saveStored() {
    try {
      window.localStorage.setItem(STORE_KEY, JSON.stringify({
        input: el.input.value,
        output: el.output.value,
        format: el.format.value,
        kind: el.kind.value,
      }));
    } catch (_) {
      /* storage unavailable */
    }
  }

  function setStatus(text, kind) {
    el.status.textContent = text || "";
    el.status.className = "loads-verify-status" + (kind ? " rp-status-" + kind : "");
  }

  function clearResult() {
    lastToken = null;
    el.openRow.hidden = true;
    el.warnings.hidden = true;
    el.warnList.textContent = "";
  }

  function applyModelDefaults() {
    if (!modelDefaults || !modelDefaults.input) {
      setStatus("表示中のモデルがありません。パスを入力してください。", "error");
      return;
    }
    el.input.value = modelDefaults.input;
    el.output.value = "";
    if (!modelDefaults.input_exists) {
      setStatus("表示中のモデルに project.json がありません（Project… で作成してください）。", "error");
    } else {
      setStatus("");
    }
  }

  function updateOutputPlaceholder() {
    const text = el.input.value.trim().replace(/^"(.*)"$/, "$1");
    if (!text) {
      el.output.placeholder = "（自動）";
      return;
    }
    const m = text.match(/^(.*?)(\.project\.json|\.[^.\\/]+)?$/i);
    const suffix = KIND_SUFFIX[el.kind.value] || "_report";
    const ext = FORMAT_EXT[el.format.value] || ".html";
    el.output.placeholder = "（自動）" + (m ? m[1] : text) + suffix + ext;
  }

  async function fetchDefaults() {
    if (!modelPath) return;
    try {
      const res = await fetch(guiApiUrl("/api/report/defaults?path=" + encodeURIComponent(modelPath)), { cache: "no-store" });
      if (res.ok) modelDefaults = await res.json();
    } catch (_) {
      modelDefaults = null;
    }
  }

  function renderWarnings(list) {
    el.warnList.textContent = "";
    for (const w of list || []) {
      const li = document.createElement("li");
      li.textContent = w;
      el.warnList.appendChild(li);
    }
    el.warnCount.textContent = String((list || []).length);
    el.warnings.hidden = !(list && list.length);
  }

  function openReport() {
    if (!lastToken) return;
    let url;
    try {
      url = guiApiUrl("/api/report/view?token=" + encodeURIComponent(lastToken));
    } catch (ex) {
      setStatus(ex.message, "error");
      return;
    }
    const w = window.open(url, "stb_report_view", "width=1000,height=900,scrollbars=yes,resizable=yes");
    if (!w) setStatus("ポップアップがブロックされました。このサイトのポップアップを許可してください。", "error");
  }

  async function runReport() {
    const input = el.input.value.trim();
    if (!input) {
      setStatus("入力の project.json のパスを入力してください。", "error");
      el.input.focus();
      return;
    }
    clearResult();
    saveStored();
    el.btnRun.disabled = true;
    setStatus(el.kind.value === "wall_quantity" ? "壁量計算書を作成しています…" : "解析して計算書を作成しています…");
    try {
      const endpoint = KIND_ENDPOINT[el.kind.value] || KIND_ENDPOINT.confirmation;
      const res = await fetch(guiApiUrl(endpoint), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input: input,
          output: el.output.value.trim(),
          format: el.format.value || null,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      lastToken = data.token;
      el.outPath.textContent = data.output;
      el.openRow.hidden = false;
      renderWarnings(data.warnings);
      const judged = data.status ? "判定 " + data.status + "、" : "";
      setStatus("計算書を書き出しました（" + judged + "警告 " + (data.warnings || []).length + " 件）。", "ok");
      openReport();
    } catch (ex) {
      setStatus("計算書を作成できませんでした: " + ex.message, "error");
    } finally {
      el.btnRun.disabled = false;
    }
  }

  el.btnRun.addEventListener("click", runReport);
  el.btnOpen.addEventListener("click", openReport);
  el.btnCurrent.addEventListener("click", applyModelDefaults);
  el.input.addEventListener("input", updateOutputPlaceholder);
  el.kind.addEventListener("change", updateOutputPlaceholder);
  el.format.addEventListener("change", () => {
    // Keep a typed output name in step with the chosen format.
    const ext = FORMAT_EXT[el.format.value];
    const out = el.output.value.trim();
    if (ext && out) el.output.value = out.replace(/\.(html?|md|pdf)("?)$/i, ext + "$2");
    updateOutputPlaceholder();
  });
  el.form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    runReport();
  });
  for (const field of [el.input, el.output]) {
    field.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        runReport();
      }
    });
  }

  (async function init() {
    await fetchDefaults();
    const stored = loadStored();
    if (stored && stored.input) {
      el.input.value = stored.input;
      el.output.value = stored.output || "";
      if (stored.format && FORMAT_EXT[stored.format]) el.format.value = stored.format;
      if (stored.kind && KIND_SUFFIX[stored.kind]) el.kind.value = stored.kind;
    } else if (modelDefaults && modelDefaults.input_exists) {
      el.input.value = modelDefaults.input;
    }
    el.btnCurrent.disabled = !(modelDefaults && modelDefaults.input);
    updateOutputPlaceholder();
  })();
})();
