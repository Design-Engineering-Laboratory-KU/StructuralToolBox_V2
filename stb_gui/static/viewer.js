import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { attachI18n } from "./i18n.js";

const COLORS = {
  background: 0xe1dee4,
  element: 0x333333,
  node: 0x333333,
  supportTrans: 0xBF3434,
  supportRot: 0x618FCD,
  supportAnchor: 0x374151,
  load: 0xd45087,
  reaction: 0x0d9488,
  reactionMoment: 0x9333ea,
  ejnt: 0xff8c00,
  selected: 0xff8c00,
  selectedNode: 0xe85d5d,
  distance: 0x2563eb,
  deform: 0x4E8AC6,
  membraneFill: 0x9e9e9e,
  membraneEdge: 0x616161,
  woodWallFill: 0x8e8e8e,
  woodWallEdge: 0x525252,
  nodeLabel: 0x000000,
  force: 0x4D829E,
  windWindward: 0xe08040,
  windLeeward: 0x4080c0,
  windFlow: 0x5a48a8,
  windStoryForce: 0x8fd4a0,
  windFootprint: 0x5a5a68,
  centerOfMass: 0xff4f7b,
  centerOfRigidity: 0x2dd4bf,
  colocated: 0xd97706,
};

const PRES_ZERO = 1e-10;
const FORCE_LABELS = ["", "Nx", "Vy", "Vz", "Mx", "My", "Mz"];
const FORCE_UNITS = ["", "kN", "kN", "kN", "kNm", "kNm", "kNm"];
const DISP_COMPONENTS = {
  mag: { label: "|U|", index: null },
  ux: { label: "UX", index: 0 },
  uy: { label: "UY", index: 1 },
  uz: { label: "UZ", index: 2 },
};

const ALPHA = {
  labelElem: 1.0,
  labelMaterial: 1.0,
  labelSection: 1.0,
  labelLoad: 1.0,
  labelReactionForce: 1.0,
  labelReactionMoment: 1.0,
  labelDefaultBg: 1.0,
  forceValueBg: 1.0,
  elementGhost: 0.18,
  membraneFill: 0.32,
  membraneEdge: 0.9,
  woodWallFill: 0.35,
  woodWallEdge: 0.9,
  opaque: 1.0,
  windWall: 0.38,
  windFootprint: 0.2,
  dlodEnvelopeEdge: 1.0,
};

const OPTIONS_STORAGE_KEY = "stb_gui_options";
const THEME_STORAGE_KEY = "stb_gui_theme";
const GUI_MODE_STORAGE_KEY = "stb_gui_mode";
let guiMode = "simple";
const RESULTS_DISPLAY_STORAGE_KEY = "stb_gui_results_display";
const MODEL_STORAGE_KEY = "stb_gui_last_model";
const WRW_CREATE_MODEL_KEY = "stb_gui_wwll_create_model";
const LABEL_BG = {
  elem: "rgba(47, 75, 124, 1.0)",
  material: "rgba(150, 95, 35, " + ALPHA.labelMaterial + ")",
  section: "rgba(45, 95, 175, " + ALPHA.labelSection + ")",
  load: "rgba(20, 83, 45, " + ALPHA.labelLoad + ")",
  reactionForce: "rgba(13, 120, 110, " + ALPHA.labelReactionForce + ")",
  reactionMoment: "rgba(147, 51, 234, " + ALPHA.labelReactionMoment + ")",
};

const OPTIONS_DEFAULTS = {
  loadArrowSize: 1.0,
  reactionArrowSize: 1.0,
  inputLoadType: "all",
  supportGizmoSize: 25,
  axesSize: 100,
  supportLineWidth: 2,
  dispContourLineWidth: 2.5,
  elementLineWidth: 2.0,
  loadLineWidth: 2.0,
  reactionLineWidth: 2.0,
  forceLineWidth: 1.0,
  nodeLabelSize: 1.0,
  elemLabelSize: 1.0,
  materialLabelSize: 1.2,
  sectionLabelSize: 1.0,
  loadLabelSize: 1.0,
  reactionLabelSize: 1.0,
  forceLabelSize: 1.5,
  sectionSolidOpacity: 1.0,
  sectionSolidColor: "#c9cdd3",
};

const OPTIONS_LIMITS = {
  loadArrowSize: { min: 0.1, max: 5.0 },
  reactionArrowSize: { min: 0.1, max: 5.0 },
  supportGizmoSize: { min: 20, max: 100 },
  axesSize: { min: 20, max: 200 },
  supportLineWidth: { min: 0.5, max: 3 },
  dispContourLineWidth: { min: 0.5, max: 3 },
  elementLineWidth: { min: 0.5, max: 3 },
  loadLineWidth: { min: 0.5, max: 3 },
  reactionLineWidth: { min: 0.5, max: 3 },
  forceLineWidth: { min: 0.5, max: 3 },
  nodeLabelSize: { min: 0.1, max: 2.0 },
  elemLabelSize: { min: 0.1, max: 2.0 },
  materialLabelSize: { min: 0.1, max: 2.0 },
  sectionLabelSize: { min: 0.1, max: 2.0 },
  loadLabelSize: { min: 0.1, max: 2.0 },
  reactionLabelSize: { min: 0.1, max: 2.0 },
  forceLabelSize: { min: 0.1, max: 2.5 },
  sectionSolidOpacity: { min: 0.1, max: 1.0 },
};

const RESULTS_DISPLAY_DEFAULTS = {
  defFactor: 50,
  deformed: false,
  dispContour: false,
  dispComponent: "mag",
  supports: true,
  ejnt: false,
  loads: true,
  loadValues: false,
  windLoads: false,
  practiceCenters: false,
  reactions: false,
  reactionValues: false,
  nodeLabels: false,
  elemLabels: false,
  material: false,
  section: false,
  sectionSolids: false,
  membrane: true,
  membraneEdge: true,
  woodWall: true,
  woodWallEdge: true,
  colocated: false,
  forceComponent: 0,
  forceDiv: 8,
  forceFactor: 10,
  forceValues: true,
  loadCase: null,
  windCaseId: null,
  dispContourMin: "",
  dispContourMax: "",
  showWorldAxes: true,
};

function clampViewerOption(key, value) {
  const lim = OPTIONS_LIMITS[key];
  if (!lim || typeof value !== "number" || !isFinite(value)) return value;
  return Math.min(lim.max, Math.max(lim.min, value));
}

function clampAllViewerOptions() {
  for (const key of Object.keys(OPTIONS_LIMITS)) {
    if (typeof viewerOptions[key] === "number") {
      viewerOptions[key] = clampViewerOption(key, viewerOptions[key]);
    }
  }
}

const el = {
  viewport: document.getElementById("viewport"),
  btnNew: document.getElementById("btnNew"),
  btnOpen: document.getElementById("btnOpen"),
  btnSave: document.getElementById("btnSave"),
  btnClose: document.getElementById("btnClose"),
  modelPath: document.getElementById("modelPath"),
  openFileInput: document.getElementById("openFileInput"),
  btnReload: document.getElementById("btnReload"),
  btnSolve: document.getElementById("btnSolve"),
  btnInput: document.getElementById("btnInput"),
  btnProject: document.getElementById("btnProject"),
  btnLoads: document.getElementById("btnLoads"),
  btnPractice: document.getElementById("btnPractice"),
  btnOutput: document.getElementById("btnOutput"),
  lcSelect: document.getElementById("lcSelect"),
  defFactor: document.getElementById("defFactor"),
  dispComponent: document.getElementById("dispComponent"),
  chkDeformed: document.getElementById("chkDeformed"),
  chkDispContour: document.getElementById("chkDispContour"),
  dispLegendOverlay: document.getElementById("dispLegendOverlay"),
  dispLegendTitle: document.getElementById("dispLegendTitle"),
  dispLegendLc: document.getElementById("dispLegendLc"),
  dispLegendBar: document.getElementById("dispLegendBar"),
  dispLegendTicks: document.getElementById("dispLegendTicks"),
  viewerInfoOverlay: document.getElementById("viewerInfoOverlay"),
  dispContourMin: document.getElementById("dispContourMin"),
  dispContourMax: document.getElementById("dispContourMax"),
  btnDispContourAuto: document.getElementById("btnDispContourAuto"),
  chkSupports: document.getElementById("chkSupports"),
  chkEJnt: document.getElementById("chkEJnt"),
  chkLoads: document.getElementById("chkLoads"),
  loadTypeFilter: document.getElementById("loadTypeFilter"),
  chkLoadValues: document.getElementById("chkLoadValues"),
  chkWindLoads: document.getElementById("chkWindLoads"),
  chkPracticeCenters: document.getElementById("chkPracticeCenters"),
  windCaseSelect: document.getElementById("windCaseSelect"),
  windLegendOverlay: document.getElementById("windLegendOverlay"),
  windLegendCase: document.getElementById("windLegendCase"),
  chkReactions: document.getElementById("chkReactions"),
  chkReactionValues: document.getElementById("chkReactionValues"),
  chkLabels: document.getElementById("chkLabels"),
  chkElemLabels: document.getElementById("chkElemLabels"),
  chkMaterial: document.getElementById("chkMaterial"),
  chkSection: document.getElementById("chkSection"),
  chkSectionSolids: document.getElementById("chkSectionSolids"),
  btnExportSectionSolidsDxf: document.getElementById("btnExportSectionSolidsDxf"),
  chkMembrane: document.getElementById("chkMembrane"),
  chkMembraneEdge: document.getElementById("chkMembraneEdge"),
  chkWoodWall: document.getElementById("chkWoodWall"),
  chkWoodWallEdge: document.getElementById("chkWoodWallEdge"),
  chkColocated: document.getElementById("chkColocated"),
  colocatedLegendOverlay: document.getElementById("colocatedLegendOverlay"),
  colocatedLegendCount: document.getElementById("colocatedLegendCount"),
  colocatedLegendList: document.getElementById("colocatedLegendList"),
  chkForceValues: document.getElementById("chkForceValues"),
  forceSelect: document.getElementById("forceSelect"),
  frcDiv: document.getElementById("frcDiv"),
  frcDivVal: document.getElementById("frcDivVal"),
  frcFactor: document.getElementById("frcFactor"),
  frcFactorVal: document.getElementById("frcFactorVal"),
  forceLegend: document.getElementById("forceLegend"),
  resultsPanel: document.getElementById("resultsPanel"),
  resultsPanelHeader: document.getElementById("resultsPanelHeader"),
  btnPanelCollapse: document.getElementById("btnPanelCollapse"),
  btnTogglePanel: document.getElementById("btnTogglePanel"),
  optionsPanel: document.getElementById("optionsPanel"),
  optionsPanelHeader: document.getElementById("optionsPanelHeader"),
  btnOptionsCollapse: document.getElementById("btnOptionsCollapse"),
  btnToggleOptions: document.getElementById("btnToggleOptions"),
  optTheme: document.getElementById("optTheme"),
  btnGuiMode: document.getElementById("btnGuiMode"),
  btnViewProjection: document.getElementById("btnViewProjection"),
  viewPreset: document.getElementById("viewPreset"),
  btnToggleAxes: document.getElementById("btnToggleAxes"),
  btnToggleSelect: document.getElementById("btnToggleSelect"),
  btnToggleDistance: document.getElementById("btnToggleDistance"),
  distanceOverlay: document.getElementById("distanceOverlay"),
  selectionMarquee: document.getElementById("selectionMarquee"),
  selectionPanel: document.getElementById("selectionPanel"),
  selectionPanelHeader: document.getElementById("selectionPanelHeader"),
  selectionPanelTitle: document.getElementById("selectionPanelTitle"),
  btnSelectionCollapse: document.getElementById("btnSelectionCollapse"),
  pickModeNode: document.getElementById("pickModeNode"),
  pickModeMember: document.getElementById("pickModeMember"),
  pickModeDiaphragm: document.getElementById("pickModeDiaphragm"),
  pickModeWall: document.getElementById("pickModeWall"),
  pickModeHint: document.getElementById("pickModeHint"),
  pickElemCreateOptions: document.getElementById("pickElemCreateOptions"),
  pickElemCreateSection: document.getElementById("pickElemCreateSection"),
  pickElemCreateBeta: document.getElementById("pickElemCreateBeta"),
  pickElemCreateHint: document.getElementById("pickElemCreateHint"),
  btnPickElemCreate: document.getElementById("btnPickElemCreate"),
  selectionSummary: document.getElementById("selectionSummary"),
  selectionList: document.getElementById("selectionList"),
  btnClearSelection: document.getElementById("btnClearSelection"),
  pickWrwCreateOptions: document.getElementById("pickWrwCreateOptions"),
  pickWrwCreateModel: document.getElementById("pickWrwCreateModel"),
  pickDmemCreateOptions: document.getElementById("pickDmemCreateOptions"),
  pickDmemCreateDiap: document.getElementById("pickDmemCreateDiap"),
  pickDmemCreateHint: document.getElementById("pickDmemCreateHint"),
  btnPickDmemCreate: document.getElementById("btnPickDmemCreate"),
  pickWrwEditOptions: document.getElementById("pickWrwEditOptions"),
  pickWrwEditModel: document.getElementById("pickWrwEditModel"),
  pickNodeSupportOptions: document.getElementById("pickNodeSupportOptions"),
  pickConsTx: document.getElementById("pickConsTx"),
  pickConsTy: document.getElementById("pickConsTy"),
  pickConsTz: document.getElementById("pickConsTz"),
  pickConsRx: document.getElementById("pickConsRx"),
  pickConsRy: document.getElementById("pickConsRy"),
  pickConsRz: document.getElementById("pickConsRz"),
  btnPickConsFixed: document.getElementById("btnPickConsFixed"),
  btnPickConsPinned: document.getElementById("btnPickConsPinned"),
  btnPickConsFree: document.getElementById("btnPickConsFree"),
  btnPickConsApply: document.getElementById("btnPickConsApply"),
  contextMenuNodeSupport: document.getElementById("contextMenuNodeSupport"),
  contextMenuConsTx: document.getElementById("contextMenuConsTx"),
  contextMenuConsTy: document.getElementById("contextMenuConsTy"),
  contextMenuConsTz: document.getElementById("contextMenuConsTz"),
  contextMenuConsRx: document.getElementById("contextMenuConsRx"),
  contextMenuConsRy: document.getElementById("contextMenuConsRy"),
  contextMenuConsRz: document.getElementById("contextMenuConsRz"),
  btnPickWrwApplyModel: document.getElementById("btnPickWrwApplyModel"),
  elemContextMenu: document.getElementById("elemContextMenu"),
  contextMenuTitle: document.getElementById("contextMenuTitle"),
  contextMenuSections: document.getElementById("contextMenuSections"),
  contextMenuMaterials: document.getElementById("contextMenuMaterials"),
  contextMenuDeleteMember: document.getElementById("contextMenuDeleteMember"),
  contextMenuWrwEdits: document.getElementById("contextMenuWrwEdits"),
  contextMenuDmemEdits: document.getElementById("contextMenuDmemEdits"),
  contextMenuDmemCreate: document.getElementById("contextMenuDmemCreate"),
  contextMenuDmemCreateDiap: document.getElementById("contextMenuDmemCreateDiap"),
  contextMenuDmemCreateHint: document.getElementById("contextMenuDmemCreateHint"),
  contextMenuElemCreate: document.getElementById("contextMenuElemCreate"),
  contextMenuElemCreateSection: document.getElementById("contextMenuElemCreateSection"),
  contextMenuElemCreateBeta: document.getElementById("contextMenuElemCreateBeta"),
  contextMenuElemCreateHint: document.getElementById("contextMenuElemCreateHint"),
  contextMenuWrwCreate: document.getElementById("contextMenuWrwCreate"),
  contextMenuWrwCreateMultiplier: document.getElementById("contextMenuWrwCreateMultiplier"),
  contextMenuWrwCreateModel: document.getElementById("contextMenuWrwCreateModel"),
  contextMenuWrwCreateDiap: document.getElementById("contextMenuWrwCreateDiap"),
  contextMenuWrwCreateHint: document.getElementById("contextMenuWrwCreateHint"),
  contextMenuWrwModel: document.getElementById("contextMenuWrwModel"),
  contextMenuWrwMultiplier: document.getElementById("contextMenuWrwMultiplier"),
  contextMenuDiapMultiplier: document.getElementById("contextMenuDiapMultiplier"),
  contextMenuDiapHint: document.getElementById("contextMenuDiapHint"),
  contextMenuElemEdits: document.getElementById("contextMenuElemEdits"),
  contextMenuTogglePick: document.getElementById("contextMenuTogglePick"),
  contextMenuShowMembersOnly: document.getElementById("contextMenuShowMembersOnly"),
  contextMenuHideMembers: document.getElementById("contextMenuHideMembers"),
  contextMenuShowAllMembers: document.getElementById("contextMenuShowAllMembers"),
  contextMenuPickSection: document.getElementById("contextMenuPickSection"),
  ejntEditPanel: document.getElementById("ejntEditPanel"),
  ejntEditText: document.getElementById("ejntEditText"),
  btnEjntEditApply: document.getElementById("btnEjntEditApply"),
  btnEjntEditCancel: document.getElementById("btnEjntEditCancel"),
  btnEjntEditClose: document.getElementById("btnEjntEditClose"),
  optLoadArrow: document.getElementById("optLoadArrow"),
  optLoadArrowVal: document.getElementById("optLoadArrowVal"),
  optReactionArrow: document.getElementById("optReactionArrow"),
  optReactionArrowVal: document.getElementById("optReactionArrowVal"),
  optSupportGizmo: document.getElementById("optSupportGizmo"),
  optSupportGizmoVal: document.getElementById("optSupportGizmoVal"),
  optAxesSize: document.getElementById("optAxesSize"),
  optAxesSizeVal: document.getElementById("optAxesSizeVal"),
  optSupportLineWidth: document.getElementById("optSupportLineWidth"),
  optDispContourLineWidth: document.getElementById("optDispContourLineWidth"),
  optElementLineWidth: document.getElementById("optElementLineWidth"),
  optLoadLineWidth: document.getElementById("optLoadLineWidth"),
  optReactionLineWidth: document.getElementById("optReactionLineWidth"),
  optForceLineWidth: document.getElementById("optForceLineWidth"),
  optNodeLabel: document.getElementById("optNodeLabel"),
  optNodeLabelVal: document.getElementById("optNodeLabelVal"),
  optElemLabel: document.getElementById("optElemLabel"),
  optElemLabelVal: document.getElementById("optElemLabelVal"),
  optMaterialLabel: document.getElementById("optMaterialLabel"),
  optMaterialLabelVal: document.getElementById("optMaterialLabelVal"),
  optSectionLabel: document.getElementById("optSectionLabel"),
  optSectionLabelVal: document.getElementById("optSectionLabelVal"),
  optLoadLabel: document.getElementById("optLoadLabel"),
  optLoadLabelVal: document.getElementById("optLoadLabelVal"),
  optReactionLabel: document.getElementById("optReactionLabel"),
  optReactionLabelVal: document.getElementById("optReactionLabelVal"),
  optForceLabel: document.getElementById("optForceLabel"),
  optForceLabelVal: document.getElementById("optForceLabelVal"),
  optSectionSolidColor: document.getElementById("optSectionSolidColor"),
  optSectionSolidOpacity: document.getElementById("optSectionSolidOpacity"),
  optSectionSolidOpacityVal: document.getElementById("optSectionSolidOpacityVal"),
  status: document.getElementById("status"),
};

const CAMERA_FOV = 45;
const STANDARD_VIEWS = {
  front: {
    offset: (span) => new THREE.Vector3(0, -span * 1.8, 0),
    up: () => new THREE.Vector3(0, 0, 1),
  },
  back: {
    offset: (span) => new THREE.Vector3(0, span * 1.8, 0),
    up: () => new THREE.Vector3(0, 0, 1),
  },
  right: {
    offset: (span) => new THREE.Vector3(span * 1.8, 0, 0),
    up: () => new THREE.Vector3(0, 0, 1),
  },
  left: {
    offset: (span) => new THREE.Vector3(-span * 1.8, 0, 0),
    up: () => new THREE.Vector3(0, 0, 1),
  },
  top: {
    offset: (span) => new THREE.Vector3(0, 0, span * 1.8),
    up: () => new THREE.Vector3(0, 1, 0),
  },
  bottom: {
    offset: (span) => new THREE.Vector3(0, 0, -span * 1.8),
    up: () => new THREE.Vector3(0, -1, 0),
  },
};

let scene, camera, renderer, controls;
let cameraProjectionMode = "perspective";
let orthoViewHeight = 10;
let modelGroup, labelGroup, forceGroup, forceLabelGroup, axesGroup, selectionGroup, distanceGroup;
let practiceCenterGroup;
let colocatedGroup;
let windGroup, windLabelGroup;
let uiTheme = "dark";
let currentModel = null;
let selectionModeActive = false;
let pickSubModes = new Set();
const PICK_SUB_MODE_STORAGE_KEY = "stb_gui_pick_sub_modes";
const PICK_SUB_MODE_LEGACY_KEY = "stb_gui_pick_sub_mode";
const PICK_SUB_MODES = ["node", "member", "diaphragm", "wall"];
let distanceModeActive = false;
let distanceNodeIds = [];
let distanceMeters = null;
let selectedElementIds = new Set();
let selectedNodeIds = new Set();
let selectedDmemIds = new Set();
let selectedWrwIds = new Set();
let memberVisibilityFilter = "all";
let visibilityElementIds = new Set();
let visibilityDmemIds = new Set();
let visibilityWrwIds = new Set();
let visibleNodeIdsCache = null;
let selectionDrag = null;
let viewportRightDrag = null;
const _worldProj = new THREE.Vector3();
const _ndcScratch = new THREE.Vector3();
const _ndcP0 = new THREE.Vector3();
const _ndcP1 = new THREE.Vector3();
const _viewPosScratch = new THREE.Vector3();
const _gizmoCenterScratch = new THREE.Vector3();
const _screenDirScratch = new THREE.Vector3();
const _viewToCenterScratch = new THREE.Vector3();
const REACTION_TRANS_COLORS = [0xff0000, 0x00ff00, 0x0000ff];
const REACTION_TRANS_AXES = [
  new THREE.Vector3(1, 0, 0),
  new THREE.Vector3(0, 1, 0),
  new THREE.Vector3(0, 0, 1),
];
const _leaderStart = new THREE.Vector3();
const _leaderEnd = new THREE.Vector3();
const _leaderDir = new THREE.Vector3();
const _camRight = new THREE.Vector3();
const _camUp = new THREE.Vector3();
const _labelNdc = new THREE.Vector3();
const SELECTION_PICK_PX = 10;
const SELECTION_NODE_PICK_PX = 14;
const SELECTION_DRAG_MIN_PX = 4;
const VIEWPORT_CONTEXT_MENU_DRAG_PX = 4;
const SELECTION_LIST_LIMIT = 80;
const MAX_EDIT_UNDO = 50;
const WIND_FLOW_SURFACE_GAP_RATIO = 0.06;
const WIND_FLOW_ARROW_LEN_RATIO = 0.12;
const WIND_FLOW_LABEL_PAD_RATIO = 0.035;
const WIND_FLOW_MIN_SURFACE_GAP_M = 0.35;
const WIND_FLOW_MIN_ARROW_LEN_M = 0.22;
const WIND_FLOW_MIN_LABEL_PAD_M = 0.1;
let editUndoStack = [];
let editRedoStack = [];
let editHistoryBusy = false;
let currentResultsText = null;
let viewerOptions = Object.assign({}, OPTIONS_DEFAULTS);
let displayPrefs = Object.assign({}, RESULTS_DISPLAY_DEFAULTS);
let wideLineMaterials = new Set();
let dispContourScaleKey = null;
let supportGizmoEntries = [];
let reactionForceEntries = [];
let nodeLabelEntries = [];
let elemLabelEntries = [];
let forceLabelEntries = [];
let _nodeLabelLeaderMat = null;
let currentModelPath = null;
const inputEditors = new Map();
let showWorldAxes = RESULTS_DISPLAY_DEFAULTS.showWorldAxes;
const _supportDiscTexCache = new Map();
const _sectionProfileCache = new Map();
const _sectionSolidGeometryCache = new Map();
const SECTION_SOLID_SEGMENTS = 24;
const SECTION_SOLID_MAX_ELEMENTS = 2500;

const THEME_RENDER_COLORS = {
  light: {
    background: 0xf4f5f7,
    element: 0x333333,
    node: 0x333333,
    membraneEdge: 0x616161,
    woodWallEdge: 0x525252,
    nodeLabel: 0x000000,
    supportOutline: "#000000",
  },
  dark: {
    background: 0x262b34,
    element: 0xc9cdd3,
    node: 0xe5e7eb,
    membraneEdge: 0xcdd5df,
    woodWallEdge: 0xd5dde7,
    nodeLabel: 0xe5e7eb,
    supportOutline: "#cbd5e1",
  },
};
let _nodePointTexture = null;
let windVisualData = null;
let windVisualStatus = "idle";
let practiceSummaryData = null;
let colocatedSitesCache = null;
let selectedWindCaseId = null;

function saveLastModelPath(path) {
  setCurrentModelPath(path);
}

function getCurrentModelPath() {
  return currentModelPath;
}

function setCurrentModelPath(path) {
  currentModelPath = normalizeModelPath(path);
  if (el.modelPath) {
    el.modelPath.textContent = currentModelPath || "";
    el.modelPath.title = currentModelPath || "";
  }
  if (!currentModelPath) return;
  try {
    localStorage.setItem(MODEL_STORAGE_KEY, currentModelPath);
  } catch (e) { /* ignore */ }
}

function normalizeModelPath(path) {
  if (!path) return null;
  let p = String(path).trim().replace(/\\/g, "/");
  while (p.startsWith("./")) p = p.slice(2);
  return p;
}

function modelInList(models, path) {
  const p = normalizeModelPath(path);
  if (!p) return null;
  return models.indexOf(p) >= 0 ? p : null;
}

function launchFileFromUrl() {
  try {
    const file = new URLSearchParams(window.location.search).get("file");
    if (!file) return null;
    return normalizeModelPath(decodeURIComponent(file));
  } catch (e) {
    return null;
  }
}

function clearLaunchFileFromUrl() {
  try {
    const url = new URL(window.location.href);
    if (!url.searchParams.has("file")) return;
    url.searchParams.delete("file");
    const next = url.pathname + url.search + url.hash;
    window.history.replaceState(null, "", next);
  } catch (e) { /* ignore */ }
}

function resolveInitialModel(models, serverDefault) {
  const launchFile = modelInList(models, launchFileFromUrl());
  if (launchFile) return launchFile;

  const server = modelInList(models, serverDefault);
  if (server) return server;

  let saved = null;
  try {
    saved = localStorage.getItem(MODEL_STORAGE_KEY);
  } catch (e) { /* ignore */ }
  const remembered = modelInList(models, saved);
  if (remembered) return remembered;

  if (models.length > 0) return models[0];
  return null;
}

function setStatus(msg) {
  el.status.textContent = msg;
}

function analysisComplete(model) {
  if (!model) return false;
  if (model.solved) return true;
  for (const n of model.nodes || []) {
    if (n.disps && Object.keys(n.disps).length > 0) return true;
  }
  if (model.results_text && model.results_text.indexOf("REAC,") >= 0) return true;
  if (model.reactions && model.reactions.length > 0) return true;
  for (const s of model.supports || []) {
    if (s.reacts && Object.keys(s.reacts).length > 0) return true;
  }
  return false;
}

function parseReactionsFromResultsText(text) {
  const out = [];
  if (!text) return out;
  for (const line of text.split("\n")) {
    const t = line.trim();
    if (!t.startsWith("REAC,")) continue;
    const parts = t.split(",").map(function (s) { return s.trim(); });
    if (parts.length < 8) continue;
    const node = parseInt(parts[2], 10);
    if (!isFinite(node)) continue;
    const vals = [];
    let ok = true;
    for (let i = 3; i < 9; i++) {
      const v = parseFloat(parts[i]);
      if (!isFinite(v)) ok = false;
      vals.push(v);
    }
    if (!ok) continue;
    out.push({ node: node, lc: String(parts[1]), values: vals });
  }
  return out;
}

function reactionRecordToArray(r) {
  if (r == null) return null;
  if (Array.isArray(r)) return r;
  if ("mx" in r || "my" in r || "mz" in r) {
    return [r.rx || 0, r.ry || 0, r.rz || 0, r.mx || 0, r.my || 0, r.mz || 0];
  }
  if ("tx" in r || "ty" in r || "tz" in r) {
    return [r.tx || 0, r.ty || 0, r.tz || 0, r.rx || 0, r.ry || 0, r.rz || 0];
  }
  return [r.rx || 0, r.ry || 0, r.rz || 0, 0, 0, 0];
}

function enrichModelReactions(model) {
  if (!model) return model;
  if (!model.supports) model.supports = [];

  for (const r of model.reactions || []) {
    let s = model.supports.find(function (x) { return x.node === r.node; });
    if (!s) {
      s = { node: r.node, fixed: [false, false, false, false, false, false] };
      model.supports.push(s);
    }
    if (!s.reacts) s.reacts = {};
    const lcKey = String(r.lc);
    if (!s.reacts[lcKey]) {
      s.reacts[lcKey] = reactionRecordToArray(r);
    }
  }

  for (const r of parseReactionsFromResultsText(model.results_text || "")) {
    let s = model.supports.find(function (x) { return x.node === r.node; });
    if (!s) {
      s = { node: r.node, fixed: [false, false, false, false, false, false] };
      model.supports.push(s);
    }
    if (!s.reacts) s.reacts = {};
    if (!s.reacts[r.lc]) s.reacts[r.lc] = r.values;
  }

  if (analysisComplete(model)) model.solved = true;
  return model;
}

function rebuildScene() {
  if (!currentModel) return;
  try {
    enrichModelReactions(currentModel);
    buildModelScene(currentModel);
    updateViewerInfoOverlay(currentModel);
  } catch (ex) {
    console.error(ex);
    setStatus("Display error: " + ex.message);
  }
}

function getSceneDisplayState() {
  const lc = el.lcSelect.value;
  const defFac = parseFloat(el.defFactor.value) || 0;
  const complete = currentModel && analysisComplete(currentModel);
  const deformed = !!(el.chkDeformed && el.chkDeformed.checked && complete);
  return { lc, defFac, deformed };
}

function applyViewerInteractionControls() {
  if (!controls) return;
  if (selectionModeActive || distanceModeActive) {
    // Left click = pick; right drag = orbit (left is disabled, not enableRotate).
    controls.mouseButtons.LEFT = null;
    controls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
    controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
  } else {
    controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
  }
  controls.enableRotate = true;
}

function setSelectionMode(active) {
  selectionModeActive = !!active;
  if (selectionModeActive) {
    setDistanceMode(false, { skipInteractionUpdate: true });
  }
  if (el.btnToggleSelect) {
    el.btnToggleSelect.classList.toggle("active", selectionModeActive);
  }
  applyViewerInteractionControls();
  updatePickModeUI();
  updateSelectionPanelVisibility();
}

function normalizePickSubMode(mode) {
  if (mode === "element") return "member";
  return PICK_SUB_MODES.includes(mode) ? mode : "node";
}

function hasPickTargetFilter() {
  return pickSubModes.size > 0;
}

function isPickTargetEnabled(mode) {
  const m = normalizePickSubMode(mode);
  if ((m === "diaphragm" || m === "wall") && !isAdvancedGui()) return false;
  if (!hasPickTargetFilter()) return true;
  return pickSubModes.has(m);
}

function loadPickSubMode() {
  pickSubModes = new Set();
  try {
    let stored = localStorage.getItem(PICK_SUB_MODE_STORAGE_KEY);
    if (!stored) stored = localStorage.getItem(PICK_SUB_MODE_LEGACY_KEY);
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        for (const m of parsed) pickSubModes.add(normalizePickSubMode(m));
        return;
      }
    } catch (e) { /* legacy single string */ }
    pickSubModes.add(normalizePickSubMode(stored));
  } catch (e) { /* ignore */ }
}

function savePickSubMode() {
  try {
    localStorage.setItem(
      PICK_SUB_MODE_STORAGE_KEY,
      JSON.stringify(Array.from(pickSubModes).sort())
    );
  } catch (e) { /* ignore */ }
}

function togglePickSubMode(mode) {
  const next = normalizePickSubMode(mode);
  if ((next === "diaphragm" || next === "wall") && !isAdvancedGui()) return;
  const updated = new Set(pickSubModes);
  if (updated.has(next)) updated.delete(next);
  else updated.add(next);
  pickSubModes = updated;
  savePickSubMode();
  updatePickModeUI();
}

function pickModeTitle() {
  if (!hasPickTargetFilter()) return "Pick — All";
  const labels = [];
  if (pickSubModes.has("node")) labels.push("Nodes");
  if (pickSubModes.has("member")) labels.push("Members");
  if (pickSubModes.has("diaphragm") && isAdvancedGui()) labels.push("Diaphragm");
  if (pickSubModes.has("wall") && isAdvancedGui()) labels.push("Wall");
  if (labels.length === 0) return "Pick — All";
  return "Pick — " + labels.join(" + ");
}

function pickModeHintText() {
  const active = Array.from(pickSubModes).filter((m) => isPickTargetEnabled(m));
  let filter;
  if (active.length > 0) {
    filter = "Filtered: " + active.join(", ") + ".";
  } else {
    filter = isAdvancedGui()
      ? "All targets (Nodes, Members, Diaphragm, Wall)."
      : "All targets (Nodes, Members).";
  }
  return filter + " Toggle Pick target buttons to filter. Click or drag to pick. Shift+click adds. Ctrl+click removes. Right-click = menu. Esc clears.";
}

function updatePickModeUI() {
  const pickButtons = [
    { el: el.pickModeNode, id: "node" },
    { el: el.pickModeMember, id: "member" },
    { el: el.pickModeDiaphragm, id: "diaphragm" },
    { el: el.pickModeWall, id: "wall" },
  ];
  for (const btn of pickButtons) {
    if (!btn.el) continue;
    const active = pickSubModes.has(btn.id);
    btn.el.classList.toggle("active", active);
    btn.el.setAttribute("aria-pressed", active ? "true" : "false");
  }
  if (el.selectionPanelTitle) {
    el.selectionPanelTitle.textContent = pickModeTitle();
  }
  if (el.pickModeHint) {
    el.pickModeHint.textContent = pickModeHintText();
  }
  updatePickWrwOptions();
}

function clearDistanceMeasurement() {
  distanceNodeIds = [];
  distanceMeters = null;
  updateDistanceVisual();
  updateDistanceOverlay();
}

function setDistanceMode(active, opts) {
  const skipInteractionUpdate = !!(opts && opts.skipInteractionUpdate);
  distanceModeActive = !!active;
  if (distanceModeActive) {
    selectionModeActive = false;
    if (el.btnToggleSelect) el.btnToggleSelect.classList.remove("active");
  }
  if (el.btnToggleDistance) {
    el.btnToggleDistance.classList.toggle("active", distanceModeActive);
  }
  if (!distanceModeActive) {
    clearDistanceMeasurement();
  } else {
    updateDistanceOverlay();
  }
  if (!skipInteractionUpdate) {
    applyViewerInteractionControls();
  }
}

function formatLengthValue(meters) {
  const av = Math.abs(meters);
  if (av < 1e-9) return "0 m";
  if (av < 0.01) return meters.toFixed(4) + " m";
  if (av < 1) return meters.toFixed(3) + " m";
  if (av < 100) return meters.toFixed(2) + " m";
  return meters.toFixed(1) + " m";
}

function nodeWorldPositionById(nodeId) {
  if (!currentModel) return null;
  const nm = nodeMap(currentModel);
  const n = nm[nodeId];
  if (!n) return null;
  const display = getSceneDisplayState();
  return nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
}

function computeDistanceBetweenNodes(id0, id1) {
  const p0 = nodeWorldPositionById(id0);
  const p1 = nodeWorldPositionById(id1);
  if (!p0 || !p1) return null;
  return p0.distanceTo(p1);
}

function addDistancePick(nodeId) {
  if (distanceNodeIds.length >= 2) {
    distanceNodeIds = [nodeId];
    distanceMeters = null;
  } else {
    distanceNodeIds.push(nodeId);
    if (distanceNodeIds.length === 2) {
      distanceMeters = computeDistanceBetweenNodes(distanceNodeIds[0], distanceNodeIds[1]);
    }
  }
  updateDistanceVisual();
  updateDistanceOverlay();
}

function updateDistanceOverlay() {
  if (!el.distanceOverlay) return;
  if (!distanceModeActive) {
    el.distanceOverlay.hidden = true;
    el.distanceOverlay.textContent = "";
    return;
  }
  el.distanceOverlay.hidden = false;
  if (distanceNodeIds.length === 0) {
    el.distanceOverlay.textContent = "Distance: click 2 nodes (0/2)";
    return;
  }
  if (distanceNodeIds.length === 1) {
    el.distanceOverlay.textContent = "Distance: click 2nd node (1/2) — N" + distanceNodeIds[0];
    return;
  }
  const n0 = distanceNodeIds[0];
  const n1 = distanceNodeIds[1];
  const distText = distanceMeters == null ? "?" : formatLengthValue(distanceMeters);
  el.distanceOverlay.textContent = "Distance: N" + n0 + " → N" + n1 + " = " + distText;
}

function updateDistanceVisual() {
  clearGroup(distanceGroup);
  if (!currentModel || distanceNodeIds.length === 0) return;

  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  const nodePts = [];
  const positions = [];
  for (const id of distanceNodeIds) {
    const n = nm[id];
    if (!n) continue;
    const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
    nodePts.push(p.x, p.y, p.z);
    positions.push(p);
  }
  if (nodePts.length > 0) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(nodePts, 3));
    const mat = nodePointsMaterial({
      color: COLORS.distance,
      size: 14,
      sizeAttenuation: false,
      depthTest: true,
    });
    const points = new THREE.Points(geo, mat);
    points.renderOrder = 22;
    distanceGroup.add(points);
  }
  if (positions.length === 2) {
    const p0 = positions[0];
    const p1 = positions[1];
    addWideLineSegmentsFromPts(
      [p0.x, p0.y, p0.z, p1.x, p1.y, p1.z],
      COLORS.distance,
      distanceGroup,
      23,
      elementLineWidthPx() + 2,
      ALPHA.opaque
    );
    const mid = p0.clone().add(p1).multiplyScalar(0.5);
    const span = modelSpan(currentModel);
    const label = makeTextSprite(formatLengthValue(distanceMeters || 0), span, {
      fg: "#1d4ed8",
      bg: "rgba(255, 255, 255, 0.9)",
      pad: 4,
    });
    label.position.copy(mid);
    label.renderOrder = 24;
    distanceGroup.add(label);
  }
}

function hasPickSelection() {
  return selectedElementIds.size > 0 || selectedNodeIds.size > 0
    || selectedDmemIds.size > 0 || selectedWrwIds.size > 0;
}

function clearSelection() {
  if (!hasPickSelection()) return;
  selectedElementIds = new Set();
  selectedNodeIds = new Set();
  selectedDmemIds = new Set();
  selectedWrwIds = new Set();
  updateSelectionHighlight();
  updateSelectionPanel();
}

function invalidateGeometryVisibilityCache() {
  visibleNodeIdsCache = null;
}

function isGeometryItemVisible(itemId, targetIds) {
  if (memberVisibilityFilter === "all") return true;
  const inSet = targetIds.has(itemId);
  if (memberVisibilityFilter === "only") return inSet;
  if (memberVisibilityFilter === "hide") return !inSet;
  return true;
}

function isElementVisible(elemId) {
  return isGeometryItemVisible(elemId, visibilityElementIds);
}

function isDmemVisible(dmemId) {
  return isGeometryItemVisible(dmemId, visibilityDmemIds);
}

function isWrwVisible(wrwId) {
  return isGeometryItemVisible(wrwId, visibilityWrwIds);
}

function buildVisibleNodeIds(model) {
  const ids = new Set();
  if (!model) return ids;
  if (memberVisibilityFilter === "all") {
    for (const n of model.nodes) ids.add(n.id);
    return ids;
  }
  for (const e of model.elements) {
    if (!isElementVisible(e.id)) continue;
    ids.add(e.n0);
    ids.add(e.n1);
  }
  for (const mem of model.membrane_elements || []) {
    if (!isDmemVisible(mem.id)) continue;
    for (const nid of mem.nodes || []) ids.add(nid);
  }
  for (const wall of model.wood_rated_walls || []) {
    if (!isWrwVisible(wall.id)) continue;
    for (const nid of wall.nodes || []) ids.add(nid);
  }
  return ids;
}

function isNodeVisible(nodeId) {
  if (memberVisibilityFilter === "all") return true;
  if (!currentModel) return true;
  if (visibleNodeIdsCache == null) {
    visibleNodeIdsCache = buildVisibleNodeIds(currentModel);
  }
  return visibleNodeIdsCache.has(nodeId);
}

function isMemberElementVisible(elemId) {
  return isElementVisible(elemId);
}

function resetMemberVisibilityFilter() {
  memberVisibilityFilter = "all";
  visibilityElementIds = new Set();
  visibilityDmemIds = new Set();
  visibilityWrwIds = new Set();
  invalidateGeometryVisibilityCache();
}

function pruneMemberVisibilityFilter() {
  if (!currentModel || memberVisibilityFilter === "all") return;
  const validElems = new Set(currentModel.elements.map(function (e) { return e.id; }));
  const validDmem = new Set((currentModel.membrane_elements || []).map(function (m) { return m.id; }));
  const validWrw = new Set((currentModel.wood_rated_walls || []).map(function (w) { return w.id; }));
  visibilityElementIds = new Set(
    Array.from(visibilityElementIds).filter(function (id) { return validElems.has(id); })
  );
  visibilityDmemIds = new Set(
    Array.from(visibilityDmemIds).filter(function (id) { return validDmem.has(id); })
  );
  visibilityWrwIds = new Set(
    Array.from(visibilityWrwIds).filter(function (id) { return validWrw.has(id); })
  );
  invalidateGeometryVisibilityCache();
  if (memberVisibilityFilter === "hide"
    && visibilityElementIds.size === 0
    && visibilityDmemIds.size === 0
    && visibilityWrwIds.size === 0) {
    resetMemberVisibilityFilter();
    if (currentModel) buildModelScene(currentModel);
  }
}

function addMemberVisibilityIds(elemIds, dmemIds, wrwIds) {
  if (memberVisibilityFilter !== "only") return false;
  let changed = false;
  for (const id of elemIds || []) {
    if (!visibilityElementIds.has(id)) {
      visibilityElementIds.add(id);
      changed = true;
    }
  }
  for (const id of dmemIds || []) {
    if (!visibilityDmemIds.has(id)) {
      visibilityDmemIds.add(id);
      changed = true;
    }
  }
  for (const id of wrwIds || []) {
    if (!visibilityWrwIds.has(id)) {
      visibilityWrwIds.add(id);
      changed = true;
    }
  }
  if (changed) invalidateGeometryVisibilityCache();
  return changed;
}

function applyMemberVisibilityFilter(mode) {
  if (mode === "all") {
    resetMemberVisibilityFilter();
  } else {
    const hasSel = selectedElementIds.size > 0
      || selectedDmemIds.size > 0
      || selectedWrwIds.size > 0;
    if (!hasSel) return;
    if (mode === "hide" && memberVisibilityFilter === "hide") {
      selectedElementIds.forEach(function (id) { visibilityElementIds.add(id); });
      selectedDmemIds.forEach(function (id) { visibilityDmemIds.add(id); });
      selectedWrwIds.forEach(function (id) { visibilityWrwIds.add(id); });
    } else {
      memberVisibilityFilter = mode;
      visibilityElementIds = new Set(selectedElementIds);
      visibilityDmemIds = new Set(selectedDmemIds);
      visibilityWrwIds = new Set(selectedWrwIds);
    }
    invalidateGeometryVisibilityCache();
  }
  if (mode === "hide") clearSelection();
  hideContextMenu();
  if (currentModel) buildModelScene(currentModel);
}

function setSelectedWrwIds(ids, mode) {
  const next = mode === "replace" ? new Set() : new Set(selectedWrwIds);
  for (const id of ids) {
    if (mode === "remove") {
      next.delete(id);
    } else if (mode === "toggle") {
      if (next.has(id)) next.delete(id);
      else next.add(id);
    } else {
      next.add(id);
    }
  }
  selectedWrwIds = next;
  updateSelectionHighlight();
  updateSelectionPanel();
}

function setSelectedDmemIds(ids, mode) {
  const next = mode === "replace" ? new Set() : new Set(selectedDmemIds);
  for (const id of ids) {
    if (mode === "remove") {
      next.delete(id);
    } else if (mode === "toggle") {
      if (next.has(id)) next.delete(id);
      else next.add(id);
    } else {
      next.add(id);
    }
  }
  selectedDmemIds = next;
  updateSelectionHighlight();
  updateSelectionPanel();
}

function setSelectedElementIds(ids, mode) {
  const next = mode === "replace" ? new Set() : new Set(selectedElementIds);
  for (const id of ids) {
    if (mode === "remove") {
      next.delete(id);
    } else if (mode === "toggle") {
      if (next.has(id)) next.delete(id);
      else next.add(id);
    } else {
      next.add(id);
    }
  }
  selectedElementIds = next;
  updateSelectionHighlight();
  updateSelectionPanel();
}

function setSelectedNodeIds(ids, mode) {
  const next = mode === "replace" ? new Set() : new Set(selectedNodeIds);
  for (const id of ids) {
    if (mode === "remove") {
      next.delete(id);
    } else if (mode === "toggle") {
      if (next.has(id)) next.delete(id);
      else next.add(id);
    } else {
      next.add(id);
    }
  }
  selectedNodeIds = next;
  updateSelectionHighlight();
  updateSelectionPanel();
}

function replacePickSelection(nodeIds, elemIds, dmemIds, wrwIds) {
  setSelectedNodeIds(nodeIds, "replace");
  setSelectedElementIds(elemIds, "replace");
  setSelectedDmemIds(dmemIds == null ? [] : dmemIds, "replace");
  setSelectedWrwIds(wrwIds == null ? [] : wrwIds, "replace");
}

function addPickSelection(nodeIds, elemIds, dmemIds, wrwIds) {
  setSelectedNodeIds(nodeIds, "add");
  setSelectedElementIds(elemIds, "add");
  setSelectedDmemIds(dmemIds == null ? [] : dmemIds, "add");
  setSelectedWrwIds(wrwIds == null ? [] : wrwIds, "add");
}

function removePickSelection(nodeIds, elemIds, dmemIds, wrwIds) {
  setSelectedNodeIds(nodeIds, "remove");
  setSelectedElementIds(elemIds, "remove");
  setSelectedDmemIds(dmemIds == null ? [] : dmemIds, "remove");
  setSelectedWrwIds(wrwIds == null ? [] : wrwIds, "remove");
}

function viewportMousePoint(ev) {
  const rect = el.viewport.getBoundingClientRect();
  return {
    x: ev.clientX - rect.left,
    y: ev.clientY - rect.top,
  };
}

function worldToScreenPoint(worldVec) {
  _worldProj.copy(worldVec).project(camera);
  const w = el.viewport.clientWidth || 1;
  const h = el.viewport.clientHeight || 1;
  return {
    x: (_worldProj.x * 0.5 + 0.5) * w,
    y: (-_worldProj.y * 0.5 + 0.5) * h,
  };
}

function distPointToSegment2d(px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const lenSq = dx * dx + dy * dy;
  if (lenSq < 1e-12) return Math.hypot(px - ax, py - ay);
  let t = ((px - ax) * dx + (py - ay) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  const qx = ax + t * dx;
  const qy = ay + t * dy;
  return Math.hypot(px - qx, py - qy);
}

function pointInRect(px, py, x0, y0, x1, y1) {
  const minX = Math.min(x0, x1);
  const maxX = Math.max(x0, x1);
  const minY = Math.min(y0, y1);
  const maxY = Math.max(y0, y1);
  return px >= minX && px <= maxX && py >= minY && py <= maxY;
}

function segmentsIntersect2d(ax, ay, bx, by, cx, cy, dx, dy) {
  function orient(px, py, qx, qy, rx, ry) {
    return (qy - py) * (rx - qx) - (qx - px) * (ry - qy);
  }
  function onSeg(px, py, qx, qy, rx, ry) {
    return Math.min(px, qx) <= rx && rx <= Math.max(px, qx) &&
      Math.min(py, qy) <= ry && ry <= Math.max(py, qy);
  }
  const o1 = orient(ax, ay, bx, by, cx, cy);
  const o2 = orient(ax, ay, bx, by, dx, dy);
  const o3 = orient(cx, cy, dx, dy, ax, ay);
  const o4 = orient(cx, cy, dx, dy, bx, by);
  if (o1 * o2 < 0 && o3 * o4 < 0) return true;
  if (Math.abs(o1) < 1e-9 && onSeg(ax, ay, bx, by, cx, cy)) return true;
  if (Math.abs(o2) < 1e-9 && onSeg(ax, ay, bx, by, dx, dy)) return true;
  if (Math.abs(o3) < 1e-9 && onSeg(cx, cy, dx, dy, ax, ay)) return true;
  if (Math.abs(o4) < 1e-9 && onSeg(cx, cy, dx, dy, bx, by)) return true;
  return false;
}

function segmentIntersectsRect(ax, ay, bx, by, x0, y0, x1, y1) {
  if (pointInRect(ax, ay, x0, y0, x1, y1) || pointInRect(bx, by, x0, y0, x1, y1)) {
    return true;
  }
  const minX = Math.min(x0, x1);
  const maxX = Math.max(x0, x1);
  const minY = Math.min(y0, y1);
  const maxY = Math.max(y0, y1);
  const edges = [
    [minX, minY, maxX, minY],
    [maxX, minY, maxX, maxY],
    [maxX, maxY, minX, maxY],
    [minX, maxY, minX, minY],
  ];
  for (const e of edges) {
    if (segmentsIntersect2d(ax, ay, bx, by, e[0], e[1], e[2], e[3])) return true;
  }
  return false;
}

function segmentInsideRect(ax, ay, bx, by, x0, y0, x1, y1) {
  return pointInRect(ax, ay, x0, y0, x1, y1) && pointInRect(bx, by, x0, y0, x1, y1);
}

function polygonInsideRect(verts, x0, y0, x1, y1) {
  if (!verts || verts.length === 0) return false;
  for (const v of verts) {
    if (!pointInRect(v.x, v.y, x0, y0, x1, y1)) return false;
  }
  return true;
}

function pointInTriangle2d(px, py, ax, ay, bx, by, cx, cy) {
  function sign(p1x, p1y, p2x, p2y, p3x, p3y) {
    return (p1x - p3x) * (p2y - p3y) - (p2x - p3x) * (p1y - p3y);
  }
  const d1 = sign(px, py, ax, ay, bx, by);
  const d2 = sign(px, py, bx, by, cx, cy);
  const d3 = sign(px, py, cx, cy, ax, ay);
  const hasNeg = d1 < 0 || d2 < 0 || d3 < 0;
  const hasPos = d1 > 0 || d2 > 0 || d3 > 0;
  return !(hasNeg && hasPos);
}

function distToPolygonEdges2d(px, py, verts) {
  let best = Infinity;
  for (let i = 0; i < verts.length; i++) {
    const a = verts[i];
    const b = verts[(i + 1) % verts.length];
    const d = distPointToSegment2d(px, py, a.x, a.y, b.x, b.y);
    if (d < best) best = d;
  }
  return best;
}

function polygonIntersectsRect(verts, x0, y0, x1, y1) {
  for (const v of verts) {
    if (pointInRect(v.x, v.y, x0, y0, x1, y1)) return true;
  }
  for (let i = 0; i < verts.length; i++) {
    const a = verts[i];
    const b = verts[(i + 1) % verts.length];
    if (segmentIntersectsRect(a.x, a.y, b.x, b.y, x0, y0, x1, y1)) return true;
  }
  return false;
}

function membraneScreenVerts(mem, nm, display) {
  const ids = mem.nodes;
  if (!ids || ids.length !== 3) return null;
  const verts = [];
  for (let i = 0; i < 3; i++) {
    const n = nm[ids[i]];
    if (!n) return null;
    const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
    verts.push(worldToScreenPoint(p));
  }
  return verts;
}

function woodWallScreenVerts(wall, nm, display) {
  const ids = wall.nodes;
  if (!ids || ids.length !== 4) return null;
  const verts = [];
  for (let i = 0; i < 4; i++) {
    const n = nm[ids[i]];
    if (!n) return null;
    const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
    verts.push(worldToScreenPoint(p));
  }
  return verts;
}

function pickMembraneAtScreen(px, py, thresholdPx) {
  if (!currentModel || !membraneShown()) return null;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  let bestId = null;
  let bestScore = thresholdPx;
  for (const mem of currentModel.membrane_elements || []) {
    if (!isDmemVisible(mem.id)) continue;
    const verts = membraneScreenVerts(mem, nm, display);
    if (!verts) continue;
    const inside = pointInTriangle2d(
      px, py,
      verts[0].x, verts[0].y,
      verts[1].x, verts[1].y,
      verts[2].x, verts[2].y
    );
    const edgeDist = distToPolygonEdges2d(px, py, verts);
    const score = inside ? 0 : edgeDist;
    if (score < bestScore) {
      bestScore = score;
      bestId = mem.id;
    }
  }
  return bestId == null ? null : { id: bestId, score: bestScore };
}

function pickWoodWallAtScreen(px, py, thresholdPx) {
  if (!currentModel || !woodWallShown()) return null;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  let bestId = null;
  let bestScore = thresholdPx;
  for (const wall of currentModel.wood_rated_walls || []) {
    if (!isWrwVisible(wall.id)) continue;
    const verts = woodWallScreenVerts(wall, nm, display);
    if (!verts) continue;
    const inside = pointInTriangle2d(px, py, verts[0].x, verts[0].y, verts[1].x, verts[1].y, verts[2].x, verts[2].y)
      || pointInTriangle2d(px, py, verts[0].x, verts[0].y, verts[2].x, verts[2].y, verts[3].x, verts[3].y);
    const edgeDist = distToPolygonEdges2d(px, py, verts);
    const score = inside ? 0 : edgeDist;
    if (score < bestScore) {
      bestScore = score;
      bestId = wall.id;
    }
  }
  return bestId == null ? null : { id: bestId, score: bestScore };
}

function membranesInScreenRect(x0, y0, x1, y1, windowMode) {
  const ids = [];
  if (!currentModel || !membraneShown()) return ids;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  for (const mem of currentModel.membrane_elements || []) {
    if (!isDmemVisible(mem.id)) continue;
    const verts = membraneScreenVerts(mem, nm, display);
    if (!verts) continue;
    const hit = windowMode
      ? polygonInsideRect(verts, x0, y0, x1, y1)
      : polygonIntersectsRect(verts, x0, y0, x1, y1);
    if (hit) ids.push(mem.id);
  }
  return ids;
}

function woodWallsInScreenRect(x0, y0, x1, y1, windowMode) {
  const ids = [];
  if (!currentModel || !woodWallShown()) return ids;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  for (const wall of currentModel.wood_rated_walls || []) {
    if (!isWrwVisible(wall.id)) continue;
    const verts = woodWallScreenVerts(wall, nm, display);
    if (!verts) continue;
    const hit = windowMode
      ? polygonInsideRect(verts, x0, y0, x1, y1)
      : polygonIntersectsRect(verts, x0, y0, x1, y1);
    if (hit) ids.push(wall.id);
  }
  return ids;
}

function elementScreenSegment(elem, nm, display) {
  const n0 = nm[elem.n0];
  const n1 = nm[elem.n1];
  if (!n0 || !n1) return null;
  const p0 = nodePosition(n0, currentModel, display.lc, display.defFac, display.deformed);
  const p1 = nodePosition(n1, currentModel, display.lc, display.defFac, display.deformed);
  const s0 = worldToScreenPoint(p0);
  const s1 = worldToScreenPoint(p1);
  return { s0, s1 };
}

function pickElementAtScreen(px, py, thresholdPx) {
  if (!currentModel) return null;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  let bestId = null;
  let bestDist = thresholdPx;
  for (const e of currentModel.elements) {
    if (!isElementVisible(e.id)) continue;
    const seg = elementScreenSegment(e, nm, display);
    if (!seg) continue;
    const d = distPointToSegment2d(px, py, seg.s0.x, seg.s0.y, seg.s1.x, seg.s1.y);
    if (d < bestDist) {
      bestDist = d;
      bestId = e.id;
    }
  }
  return bestId == null ? null : { id: bestId, score: bestDist };
}

function elementsInScreenRect(x0, y0, x1, y1, windowMode) {
  const ids = [];
  if (!currentModel) return ids;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  for (const e of currentModel.elements) {
    if (!isElementVisible(e.id)) continue;
    const seg = elementScreenSegment(e, nm, display);
    if (!seg) continue;
    const hit = windowMode
      ? segmentInsideRect(seg.s0.x, seg.s0.y, seg.s1.x, seg.s1.y, x0, y0, x1, y1)
      : segmentIntersectsRect(seg.s0.x, seg.s0.y, seg.s1.x, seg.s1.y, x0, y0, x1, y1);
    if (hit) ids.push(e.id);
  }
  return ids;
}

function nodesInScreenRect(x0, y0, x1, y1) {
  const ids = [];
  if (!currentModel) return ids;
  const display = getSceneDisplayState();
  const minX = Math.min(x0, x1);
  const maxX = Math.max(x0, x1);
  const minY = Math.min(y0, y1);
  const maxY = Math.max(y0, y1);
  for (const n of currentModel.nodes) {
    if (!isNodeVisible(n.id)) continue;
    const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
    const s = worldToScreenPoint(p);
    if (s.x >= minX && s.x <= maxX && s.y >= minY && s.y <= maxY) {
      ids.push(n.id);
    }
  }
  return ids;
}

function pickNodeAtScreen(px, py, thresholdPx) {
  if (!currentModel) return null;
  const display = getSceneDisplayState();
  const limit = thresholdPx == null ? SELECTION_NODE_PICK_PX : thresholdPx;
  let bestNode = null;
  let bestNodeDist = limit;
  for (const n of currentModel.nodes) {
    if (!isNodeVisible(n.id)) continue;
    const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
    const s = worldToScreenPoint(p);
    const d = Math.hypot(px - s.x, py - s.y);
    if (d < bestNodeDist) {
      bestNodeDist = d;
      bestNode = n.id;
    }
  }
  return bestNode;
}

function pickBestFromCandidates(candidates, bestNode, bestNodeDist) {
  if (bestNode != null && bestNodeDist <= SELECTION_NODE_PICK_PX) {
    if (candidates.length === 0 || bestNodeDist <= SELECTION_PICK_PX * 0.75) {
      return { kind: "node", id: bestNode };
    }
  }
  if (candidates.length > 0) {
    const kindPriority = { dmem: 0, wrw: 1, elem: 2 };
    candidates.sort(function (a, b) {
      if (a.score !== b.score) return a.score - b.score;
      return (kindPriority[a.kind] || 9) - (kindPriority[b.kind] || 9);
    });
    return candidates[0];
  }
  if (bestNode != null) return { kind: "node", id: bestNode };
  return null;
}

function pickCandidatesAtScreen(px, py, enabledModes) {
  const candidates = [];
  let bestNode = null;
  let bestNodeDist = SELECTION_NODE_PICK_PX;

  if (!enabledModes || enabledModes.has("node")) {
    bestNode = pickNodeAtScreen(px, py, SELECTION_NODE_PICK_PX);
    if (bestNode != null) {
      const display = getSceneDisplayState();
      const nm = nodeMap(currentModel);
      const n = nm[bestNode];
      if (n) {
        const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
        const s = worldToScreenPoint(p);
        bestNodeDist = Math.hypot(px - s.x, py - s.y);
      }
    }
  }
  if (!enabledModes || enabledModes.has("diaphragm")) {
    const bestDmem = pickMembraneAtScreen(px, py, SELECTION_PICK_PX);
    if (bestDmem != null) candidates.push(Object.assign({ kind: "dmem" }, bestDmem));
  }
  if (!enabledModes || enabledModes.has("wall")) {
    const bestWrw = pickWoodWallAtScreen(px, py, SELECTION_PICK_PX);
    if (bestWrw != null) candidates.push(Object.assign({ kind: "wrw" }, bestWrw));
  }
  if (!enabledModes || enabledModes.has("member")) {
    const bestElem = pickElementAtScreen(px, py, SELECTION_PICK_PX);
    if (bestElem != null) candidates.push(Object.assign({ kind: "elem" }, bestElem));
  }

  return pickBestFromCandidates(candidates, bestNode, bestNodeDist);
}

function pickTargetForMode(px, py) {
  if (!currentModel) return null;
  if (!hasPickTargetFilter()) return pickCandidatesAtScreen(px, py, null);
  return pickCandidatesAtScreen(px, py, pickSubModes);
}

function pickTargetAtScreen(px, py) {
  if (!currentModel) return null;
  return pickCandidatesAtScreen(px, py, null);
}

function elementIJArrowLength(model, elemLen) {
  const span = modelSpan(model);
  const minLen = Math.max(span * 0.012, 0.04);
  const maxLen = Math.max(span * 0.06, minLen * 2);
  return THREE.MathUtils.clamp(elemLen * 0.42, minLen, Math.min(maxLen, elemLen * 0.85));
}

function addElementIJDirectionArrow(p0, p1, model, group, color, lineWidthPx) {
  const dir = p1.clone().sub(p0);
  const len = dir.length();
  if (len < 1e-12) return;
  dir.normalize();
  const arrowLen = elementIJArrowLength(model, len);
  const mid = p0.clone().add(p1).multiplyScalar(0.5);
  const half = arrowLen * 0.5;
  const tail = mid.clone().addScaledVector(dir, -half);
  const head = mid.clone().addScaledVector(dir, half);
  addDirectedArrow(tail, head, group, color, lineWidthPx, 0.95, 22);
}

function updateSelectionHighlight() {
  clearGroup(selectionGroup);
  if (!currentModel || !hasPickSelection()) return;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  const pts = [];
  for (const e of currentModel.elements) {
    if (!selectedElementIds.has(e.id)) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0 = nodePosition(n0, currentModel, display.lc, display.defFac, display.deformed);
    const p1 = nodePosition(n1, currentModel, display.lc, display.defFac, display.deformed);
    pts.push(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z);
  }
  if (pts.length > 0) {
    addWideLineSegmentsFromPts(
      pts,
      COLORS.selected,
      selectionGroup,
      20,
      elementLineWidthPx() + 2.5,
      ALPHA.opaque
    );
  }
  const arrowWidth = elementLineWidthPx() + 1.5;
  for (const e of currentModel.elements) {
    if (!selectedElementIds.has(e.id)) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0 = nodePosition(n0, currentModel, display.lc, display.defFac, display.deformed);
    const p1 = nodePosition(n1, currentModel, display.lc, display.defFac, display.deformed);
    addElementIJDirectionArrow(
      p0, p1, currentModel, selectionGroup, COLORS.selected, arrowWidth
    );
  }
  if (selectedNodeIds.size > 0) {
    const nodePts = [];
    for (const n of currentModel.nodes) {
      if (!selectedNodeIds.has(n.id)) continue;
      const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
      nodePts.push(p.x, p.y, p.z);
    }
    if (nodePts.length > 0) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(nodePts, 3));
      const mat = nodePointsMaterial({
        color: COLORS.selectedNode,
        size: 12,
        sizeAttenuation: false,
        depthTest: true,
      });
      const points = new THREE.Points(geo, mat);
      points.renderOrder = 21;
      selectionGroup.add(points);
    }
  }

  const selFillPos = [];
  const selEdgePts = [];
  for (const mem of currentModel.membrane_elements || []) {
    if (!selectedDmemIds.has(mem.id)) continue;
    const ids = mem.nodes;
    if (!ids || ids.length !== 3) continue;
    const p0 = nodePosition(nm[ids[0]], currentModel, display.lc, display.defFac, display.deformed);
    const p1 = nodePosition(nm[ids[1]], currentModel, display.lc, display.defFac, display.deformed);
    const p2 = nodePosition(nm[ids[2]], currentModel, display.lc, display.defFac, display.deformed);
    if (!p0 || !p1 || !p2) continue;
    selFillPos.push(
      p0.x, p0.y, p0.z,
      p1.x, p1.y, p1.z,
      p2.x, p2.y, p2.z
    );
    selEdgePts.push(
      p0.x, p0.y, p0.z, p1.x, p1.y, p1.z,
      p1.x, p1.y, p1.z, p2.x, p2.y, p2.z,
      p2.x, p2.y, p2.z, p0.x, p0.y, p0.z
    );
  }
  for (const wall of currentModel.wood_rated_walls || []) {
    if (!selectedWrwIds.has(wall.id)) continue;
    const ids = wall.nodes;
    if (!ids || ids.length !== 4) continue;
    const pts = ids.map(function (nid) {
      const n = nm[nid];
      return n ? nodePosition(n, currentModel, display.lc, display.defFac, display.deformed) : null;
    });
    if (pts.some(function (p) { return !p; })) continue;
    selFillPos.push(
      pts[0].x, pts[0].y, pts[0].z,
      pts[1].x, pts[1].y, pts[1].z,
      pts[2].x, pts[2].y, pts[2].z,
      pts[0].x, pts[0].y, pts[0].z,
      pts[2].x, pts[2].y, pts[2].z,
      pts[3].x, pts[3].y, pts[3].z
    );
    selEdgePts.push(
      pts[0].x, pts[0].y, pts[0].z, pts[1].x, pts[1].y, pts[1].z,
      pts[1].x, pts[1].y, pts[1].z, pts[2].x, pts[2].y, pts[2].z,
      pts[2].x, pts[2].y, pts[2].z, pts[3].x, pts[3].y, pts[3].z,
      pts[3].x, pts[3].y, pts[3].z, pts[0].x, pts[0].y, pts[0].z
    );
  }
  if (selFillPos.length > 0) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(selFillPos, 3));
    geo.computeVertexNormals();
    const mat = new THREE.MeshBasicMaterial({
      color: COLORS.selected,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.renderOrder = 20;
    selectionGroup.add(mesh);
  }
  if (selEdgePts.length > 0) {
    addWideLineSegmentsFromPts(
      selEdgePts,
      COLORS.selected,
      selectionGroup,
      22,
      elementLineWidthPx() + 2.5,
      ALPHA.opaque
    );
  }
}

function elementSummaryText(elem) {
  const sec = elem.section || ("SEC " + (elem.section_id != null ? elem.section_id : "?"));
  const mat = elem.material_name || "";
  return mat ? sec + " / " + mat : sec;
}

function formatOutInt(v) {
  const s = String(v);
  return s.length >= 6 ? s : s.padStart(6, " ");
}

function formatOutScientific(val) {
  if (!isFinite(val)) return "         ?";
  if (val === 0 || Math.abs(val) < PRES_ZERO) return " 0.000e+00";
  const neg = val < 0;
  const av = Math.abs(val);
  let exp = Math.floor(Math.log10(av));
  let mant = av / Math.pow(10, exp);
  if (mant >= 10) {
    mant /= 10;
    exp += 1;
  }
  const m = (neg ? -mant : mant).toFixed(3);
  const e = (exp >= 0 ? "+" : "-") + String(Math.abs(exp)).padStart(2, "0");
  return (m + "e" + e).padStart(10, " ");
}

const NDSP_OUT_HEADER = [
  "# --- NODAL DISPLACEMENT ---",
  "#        LC,  NODE,         X,         Y,         Z,   Theta X,   Theta Y,   Theta Z",
  "#                          (m)        (m)        (m)      (rad)      (rad)      (rad)",
];

const EFRC_OUT_HEADER = [
  "# --- ELEMENT FORCE ---",
  "#        LC,  ELEM,        Ni,       Qyi,       Qzi,       Mxi,       Myi,       Mzi         Nj,       Qyj,       Qzj,       Mxj,       Myj,       Mzj,       Myc,       Mzc",
  "#                         (kN)       (kN)       (kN)      (kNm)      (kNm)      (kNm)       (kN)       (kN)       (kN)      (kNm)      (kNm)      (kNm)      (kNm)      (kNm)",
];

function formatNdspOutLine(lc, nodeId, disps) {
  const props = ["NDSP", formatOutInt(lc), formatOutInt(nodeId)];
  for (let i = 0; i < 6; i++) {
    props.push(formatOutScientific(disps[i]));
  }
  return props.join(",");
}

function formatEfrcOutLine(lc, elemId, forces) {
  const props = ["EFRC", formatOutInt(lc), formatOutInt(elemId)];
  for (let i = 0; i < 14; i++) {
    const raw = forces[i] || 0;
    const v = Math.abs(raw) < PRES_ZERO ? 0 : raw;
    props.push(formatOutScientific(v * 1e-3));
  }
  return props.join(",");
}

function nodeNdspOutBlock(model, nodeId, lcKey) {
  const nm = {};
  for (const n of model.nodes || []) nm[n.id] = n;
  const n = nm[nodeId];
  if (!n || !n.disps) return null;
  const disps = n.disps[String(lcKey)];
  if (!disps || disps.length < 6) return null;
  return NDSP_OUT_HEADER.join("\n") + "\n" + formatNdspOutLine(lcKey, nodeId, disps);
}

function elementEfrcOutBlock(model, elemId, lcKey) {
  const byId = {};
  for (const e of model.elements || []) byId[e.id] = e;
  const e = byId[elemId];
  if (!e || !e.forces) return null;
  const forces = e.forces[String(lcKey)];
  if (!forces || forces.length < 14) return null;
  return EFRC_OUT_HEADER.join("\n") + "\n" + formatEfrcOutLine(lcKey, elemId, forces);
}

function updateSelectionPanelVisibility() {
  if (!el.selectionPanel) return;
  const show = selectionModeActive;
  el.selectionPanel.classList.toggle("hidden", !show);
}

function updateSelectionPanel() {
  if (!el.selectionSummary || !el.selectionList) return;
  const elemCount = selectedElementIds.size;
  const nodeCount = selectedNodeIds.size;
  const dmemCount = selectedDmemIds.size;
  const wrwCount = selectedWrwIds.size;
  if (!hasPickSelection()) {
    el.selectionSummary.textContent = "Nothing picked";
    el.selectionList.innerHTML = "";
    updatePickWrwOptions();
    updateSelectionPanelVisibility();
    return;
  }
  const parts = [];
  if (elemCount > 0) {
    parts.push(elemCount + " element" + (elemCount === 1 ? "" : "s"));
  }
  if (nodeCount > 0) {
    parts.push(nodeCount + " node" + (nodeCount === 1 ? "" : "s"));
  }
  if (dmemCount > 0) {
    parts.push(dmemCount + " DMEM");
  }
  if (wrwCount > 0) {
    parts.push(wrwCount + " WRW");
  }
  let summary = parts.join(", ") + " picked";
  if (elemCount > 0 && currentModel) {
    const byId = {};
    for (const e of currentModel.elements) {
      byId[e.id] = e;
    }
    const sectionCounts = {};
    for (const id of selectedElementIds) {
      const e = byId[id];
      if (!e) continue;
      const key = elementSummaryText(e);
      sectionCounts[key] = (sectionCounts[key] || 0) + 1;
    }
    const breakdown = Object.keys(sectionCounts).sort().map(function (k) {
      return sectionCounts[k] + "× " + k;
    });
    if (breakdown.length > 0 && breakdown.length <= 5) {
      summary += " — " + breakdown.join(", ");
    }
  }
  el.selectionSummary.textContent = summary;
  el.selectionList.innerHTML = "";

  const rows = [];
  for (const id of Array.from(selectedNodeIds).sort((a, b) => a - b)) {
    rows.push({ kind: "node", id: id });
  }
  for (const id of Array.from(selectedDmemIds).sort((a, b) => a - b)) {
    rows.push({ kind: "dmem", id: id });
  }
  for (const id of Array.from(selectedWrwIds).sort((a, b) => a - b)) {
    rows.push({ kind: "wrw", id: id });
  }
  for (const id of Array.from(selectedElementIds).sort((a, b) => a - b)) {
    rows.push({ kind: "elem", id: id });
  }
  const byElem = {};
  for (const e of currentModel ? currentModel.elements : []) {
    byElem[e.id] = e;
  }
  const byNode = {};
  for (const n of currentModel ? currentModel.nodes : []) {
    byNode[n.id] = n;
  }
  const byDmem = {};
  for (const m of currentModel ? currentModel.membrane_elements || [] : []) {
    byDmem[m.id] = m;
  }
  const byWrw = {};
  for (const w of currentModel ? currentModel.wood_rated_walls || [] : []) {
    byWrw[w.id] = w;
  }
  const byDiap = {};
  for (const d of currentModel ? currentModel.diaphragms || [] : []) {
    byDiap[d.id] = d;
  }
  const solved = currentModel && analysisComplete(currentModel);
  const lcKey = String(el.lcSelect ? el.lcSelect.value : "");
  const show = rows.slice(0, SELECTION_LIST_LIMIT);
  for (const row of show) {
    const li = document.createElement("li");
    if (row.kind === "node") {
      const n = byNode[row.id];
      const pos = n
        ? " (" + n.x.toFixed(2) + ", " + n.y.toFixed(2) + ", " + n.z.toFixed(2) + ")"
        : "";
      const title = document.createElement("div");
      title.className = "selection-row-title";
      title.textContent = "NODE " + row.id + pos;
      li.appendChild(title);
      if (solved) {
        const outLine = document.createElement("div");
        outLine.className = "selection-out-line";
        const line = nodeNdspOutBlock(currentModel, row.id, lcKey);
        outLine.textContent = line != null
          ? line
          : "(no NDSP for LC " + lcKey + ")";
        li.appendChild(outLine);
      }
      li.addEventListener("click", function () {
        replacePickSelection([row.id], [], [], []);
      });
    } else if (row.kind === "dmem") {
      const m = byDmem[row.id];
      const diap = m ? byDiap[m.diaphragm_id] : null;
      const title = document.createElement("div");
      title.className = "selection-row-title";
      let label = "DMEM " + row.id;
      if (m) label += " — DIAP " + m.diaphragm_id;
      if (diap && diap.timber_multiplier != null) {
        label += " (MAG " + diap.timber_multiplier + ")";
      }
      title.textContent = label;
      li.appendChild(title);
      li.addEventListener("click", function () {
        replacePickSelection([], [], [row.id], []);
      });
    } else if (row.kind === "wrw") {
      const w = byWrw[row.id];
      const title = document.createElement("div");
      title.className = "selection-row-title";
      let label = "WRW " + row.id;
      if (w) {
        label += " — " + (w.name || "?") + " (" + wwllModelLabelFromWall(w) + ", M " + w.multiplier + ")";
      }
      title.textContent = label;
      li.appendChild(title);
      li.addEventListener("click", function () {
        replacePickSelection([], [], [], [row.id]);
      });
    } else {
      const e = byElem[row.id];
      const title = document.createElement("div");
      title.className = "selection-row-title";
      title.textContent = "ELEM " + row.id + " — " + (e ? elementSummaryText(e) : "?");
      li.appendChild(title);
      if (solved) {
        const outLine = document.createElement("div");
        outLine.className = "selection-out-line";
        const line = elementEfrcOutBlock(currentModel, row.id, lcKey);
        outLine.textContent = line != null
          ? line
          : "(no EFRC for LC " + lcKey + ")";
        li.appendChild(outLine);
      }
      li.addEventListener("click", function () {
        replacePickSelection([], [row.id], [], []);
      });
    }
    el.selectionList.appendChild(li);
  }
  if (rows.length > SELECTION_LIST_LIMIT) {
    const li = document.createElement("li");
    li.className = "selection-more";
    li.textContent = "... and " + (rows.length - SELECTION_LIST_LIMIT) + " more";
    el.selectionList.appendChild(li);
  }
  updatePickWrwOptions();
  updateSelectionPanelVisibility();
}

function updateSelectionMarquee(x0, y0, x1, y1) {
  if (!el.selectionMarquee) return;
  const left = Math.min(x0, x1);
  const top = Math.min(y0, y1);
  const width = Math.abs(x1 - x0);
  const height = Math.abs(y1 - y0);
  el.selectionMarquee.style.left = left + "px";
  el.selectionMarquee.style.top = top + "px";
  el.selectionMarquee.style.width = width + "px";
  el.selectionMarquee.style.height = height + "px";
  el.selectionMarquee.hidden = width < 1 && height < 1;
  const windowMode = (x1 - x0) >= 0;
  el.selectionMarquee.classList.toggle("selection-marquee-window", windowMode);
  el.selectionMarquee.classList.toggle("selection-marquee-cross", !windowMode);
}

function hideSelectionMarquee() {
  if (!el.selectionMarquee) return;
  el.selectionMarquee.hidden = true;
  el.selectionMarquee.style.width = "0";
  el.selectionMarquee.style.height = "0";
}

function replacePickSelectionForKind(kind, ids) {
  if (kind === "node") setSelectedNodeIds(ids, "replace");
  else if (kind === "elem") setSelectedElementIds(ids, "replace");
  else if (kind === "dmem") setSelectedDmemIds(ids, "replace");
  else if (kind === "wrw") setSelectedWrwIds(ids, "replace");
}

function targetsInScreenRect(x0, y0, x1, y1, windowMode) {
  const nodeIds = [];
  const elemIds = [];
  const dmemIds = [];
  const wrwIds = [];
  if (isPickTargetEnabled("node")) {
    nodeIds.push.apply(nodeIds, nodesInScreenRect(x0, y0, x1, y1));
  }
  if (isPickTargetEnabled("member")) {
    elemIds.push.apply(elemIds, elementsInScreenRect(x0, y0, x1, y1, windowMode));
  }
  if (isPickTargetEnabled("diaphragm")) {
    dmemIds.push.apply(dmemIds, membranesInScreenRect(x0, y0, x1, y1, windowMode));
  }
  if (isPickTargetEnabled("wall")) {
    wrwIds.push.apply(wrwIds, woodWallsInScreenRect(x0, y0, x1, y1, windowMode));
  }
  return { nodeIds, elemIds, dmemIds, wrwIds };
}

function applyPickedTarget(picked, addToSelection, removeFromSelection) {
  if (picked == null) return false;
  if (removeFromSelection) {
    if (picked.kind === "node") setSelectedNodeIds([picked.id], "remove");
    else if (picked.kind === "elem") setSelectedElementIds([picked.id], "remove");
    else if (picked.kind === "dmem") setSelectedDmemIds([picked.id], "remove");
    else if (picked.kind === "wrw") setSelectedWrwIds([picked.id], "remove");
    return true;
  }
  if (addToSelection) {
    if (picked.kind === "node") setSelectedNodeIds([picked.id], "add");
    else if (picked.kind === "elem") setSelectedElementIds([picked.id], "add");
    else if (picked.kind === "dmem") setSelectedDmemIds([picked.id], "add");
    else if (picked.kind === "wrw") setSelectedWrwIds([picked.id], "add");
    return true;
  }
  replacePickSelectionForKind(picked.kind, [picked.id]);
  return true;
}

function finishSelectionDrag(ev) {
  if (!selectionDrag) return;
  const drag = selectionDrag;
  selectionDrag = null;
  hideSelectionMarquee();
  if (controls) controls.enabled = true;

  const end = viewportMousePoint(ev);
  const dx = end.x - drag.startX;
  const dy = end.y - drag.startY;
  const addToSelection = !!ev.shiftKey;
  const removeFromSelection = !!(ev.ctrlKey || ev.metaKey);

  if (Math.hypot(dx, dy) < SELECTION_DRAG_MIN_PX) {
    const picked = pickTargetForMode(end.x, end.y);
    if (picked == null) {
      if (!addToSelection && !removeFromSelection) clearSelection();
    } else {
      applyPickedTarget(picked, addToSelection, removeFromSelection);
    }
    return;
  }

  const windowMode = dx >= 0;
  const picked = targetsInScreenRect(drag.startX, drag.startY, end.x, end.y, windowMode);
  const total = picked.nodeIds.length + picked.elemIds.length
    + picked.dmemIds.length + picked.wrwIds.length;
  if (total === 0) {
    if (!addToSelection && !removeFromSelection) clearSelection();
    return;
  }
  if (removeFromSelection) {
    removePickSelection(picked.nodeIds, picked.elemIds, picked.dmemIds, picked.wrwIds);
  } else if (addToSelection) {
    addPickSelection(picked.nodeIds, picked.elemIds, picked.dmemIds, picked.wrwIds);
  } else {
    replacePickSelection(picked.nodeIds, picked.elemIds, picked.dmemIds, picked.wrwIds);
  }
}

function initSelectionInteraction() {
  if (!el.viewport) return;

  el.viewport.addEventListener("mousedown", (ev) => {
    if (!selectionModeActive) return;
    if (ev.button !== 0) return;
    if (isViewerOverlayTarget(ev.target)) return;
    const pt = viewportMousePoint(ev);
    selectionDrag = {
      startX: pt.x,
      startY: pt.y,
      pointerId: ev.pointerId,
    };
    if (controls) controls.enabled = false;
    updateSelectionMarquee(pt.x, pt.y, pt.x, pt.y);
    ev.preventDefault();
    ev.stopPropagation();
  });

  window.addEventListener("mousemove", (ev) => {
    if (!selectionDrag) return;
    const pt = viewportMousePoint(ev);
    updateSelectionMarquee(selectionDrag.startX, selectionDrag.startY, pt.x, pt.y);
  });

  window.addEventListener("mouseup", (ev) => {
    if (!selectionDrag) return;
    if (ev.button !== 0) return;
    finishSelectionDrag(ev);
  });

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !isViewerTextInputTarget(ev.target)) {
      if (distanceModeActive) clearDistanceMeasurement();
      else clearSelection();
    }
  });
}

function initDistanceInteraction() {
  if (!el.viewport) return;

  el.viewport.addEventListener("mousedown", (ev) => {
    if (!distanceModeActive) return;
    if (ev.button !== 0) return;
    if (isViewerOverlayTarget(ev.target)) return;
    const pt = viewportMousePoint(ev);
    const nodeId = pickNodeAtScreen(pt.x, pt.y, SELECTION_NODE_PICK_PX);
    if (nodeId == null) return;
    addDistancePick(nodeId);
    ev.preventDefault();
    ev.stopPropagation();
  });
}

function isViewerOverlayTarget(target) {
  if (!target || !el.viewport) return false;
  if (target === el.viewport || target === renderer.domElement) return false;
  return el.viewport.contains(target);
}

function selectedElementIdList() {
  return Array.from(selectedElementIds).sort(function (a, b) { return a - b; });
}

function selectedNodeIdList() {
  return Array.from(selectedNodeIds).sort(function (a, b) { return a - b; });
}

function selectedDmemIdList() {
  return Array.from(selectedDmemIds).sort(function (a, b) { return a - b; });
}

function selectedWrwIdList() {
  return Array.from(selectedWrwIds).sort(function (a, b) { return a - b; });
}

function isTimberDiaphragm(diap) {
  if (!diap) return false;
  const src = String(diap.source || "").toUpperCase();
  return src === "TIMBER_FLOOR" || src === "TIMBER_ROOF";
}

function findDmemIdByNodes(diapId, nodeIds) {
  if (!currentModel) return null;
  const sorted = nodeIds.slice().sort(function (a, b) { return a - b; });
  for (const m of currentModel.membrane_elements || []) {
    if (m.diaphragm_id !== diapId) continue;
    const mn = (m.nodes || []).slice().sort(function (a, b) { return a - b; });
    if (mn.length !== 3) continue;
    if (mn[0] === sorted[0] && mn[1] === sorted[1] && mn[2] === sorted[2]) {
      return m.id;
    }
  }
  return null;
}

function parseCreatedDmemIdsFromWarnings(warnings) {
  const ids = [];
  for (const w of warnings || []) {
    const m = String(w).match(/^Created DMEM (\d+) for DIAP/);
    if (m) ids.push(parseInt(m[1], 10));
  }
  return ids;
}

function canCreateDmemFromNodePick() {
  const diaps = currentModel ? (currentModel.diaphragms || []) : [];
  return isPickTargetEnabled("node")
    && selectedNodeIds.size >= 3
    && selectedElementIds.size === 0
    && selectedDmemIds.size === 0
    && selectedWrwIds.size === 0
    && diaps.length > 0;
}

function canCreateElemFromNodePick() {
  const sections = currentModel ? (currentModel.sections || []) : [];
  return isPickTargetEnabled("node")
    && selectedNodeIds.size === 2
    && selectedElementIds.size === 0
    && selectedDmemIds.size === 0
    && selectedWrwIds.size === 0
    && sections.length > 0;
}

function parseCreatedElemIdFromWarnings(warnings) {
  for (const w of warnings || []) {
    const m = String(w).match(/^Created ELEM (\d+)/);
    if (m) return parseInt(m[1], 10);
  }
  return null;
}

function findElementIdByNodes(ni, nj) {
  if (!currentModel) return null;
  const pair = new Set([ni, nj]);
  for (const e of currentModel.elements || []) {
    if (pair.has(e.n0) && pair.has(e.n1)) return e.id;
  }
  return null;
}

function populateElemCreateSectionSelect() {
  const targets = [el.contextMenuElemCreateSection, el.pickElemCreateSection];
  if (!currentModel) return;
  const sections = currentModel.sections || [];
  for (const sel of targets) {
    if (!sel) continue;
    const prev = sel.value;
    sel.innerHTML = "";
    for (const s of sections) {
      const opt = document.createElement("option");
      opt.value = String(s.id);
      const mat = s.material_name || ("MAT " + s.material_id);
      opt.textContent = "SECT " + s.id + " — " + s.name + " (" + mat + ")";
      sel.appendChild(opt);
    }
    if (prev && Array.from(sel.options).some(function (o) { return o.value === prev; })) {
      sel.value = prev;
    } else if (sel.options.length) {
      sel.selectedIndex = 0;
    }
  }
}

function getPickElemCreateSectionId() {
  const raw = el.pickElemCreateSection
    ? el.pickElemCreateSection.value
    : (el.contextMenuElemCreateSection ? el.contextMenuElemCreateSection.value : "");
  const sectId = parseInt(raw, 10);
  return isFinite(sectId) ? sectId : null;
}

function getPickElemCreateBeta() {
  const raw = el.pickElemCreateBeta
    ? el.pickElemCreateBeta.value.trim()
    : (el.contextMenuElemCreateBeta ? el.contextMenuElemCreateBeta.value.trim() : "0");
  const beta = parseFloat(raw);
  return isFinite(beta) ? beta : 0;
}

function requestCreateElement(sectionId, beta) {
  if (!canCreateElemFromNodePick()) return;
  const ids = selectedNodeIdList();
  const ok = window.confirm(
    "Create ELEM between nodes " + ids[0] + " and " + ids[1] + " (SECT " + sectionId + ")?"
  );
  if (!ok) return;
  applyModelEdit({ action: "create_element", section_id: sectionId, beta: beta });
}

function requestCreateDmemMesh(diapId) {
  if (!canCreateDmemFromNodePick()) return;
  const ids = selectedNodeIdList();
  const count = ids.length;
  const msg = count === 3
    ? "Create DMEM on DIAP " + diapId + " with nodes " + ids.join(", ") + "?"
    : "Create DMEM mesh on DIAP " + diapId + " from " + count + " nodes (auto triangulation)?";
  if (!window.confirm(msg)) return;
  applyModelEdit({ action: "create_dmem", diap_id: diapId });
}

function findWrwIdByNodes(nodeIds) {
  if (!currentModel) return null;
  const sorted = nodeIds.slice().sort(function (a, b) { return a - b; });
  for (const w of currentModel.wood_rated_walls || []) {
    const wn = (w.nodes || []).slice().sort(function (a, b) { return a - b; });
    if (wn.length !== 4) continue;
    if (wn[0] === sorted[0] && wn[1] === sorted[1]
      && wn[2] === sorted[2] && wn[3] === sorted[3]) {
      return w.id;
    }
  }
  return null;
}

function populateWrwCreateDiapSelect() {
  if (!el.contextMenuWrwCreateDiap || !currentModel) return;
  const sel = el.contextMenuWrwCreateDiap;
  const prev = sel.value;
  sel.innerHTML = "";
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "No DIAP";
  sel.appendChild(none);
  for (const d of currentModel.diaphragms || []) {
    const opt = document.createElement("option");
    opt.value = String(d.id);
    let label = "DIAP " + d.id;
    if (d.name) label += " — " + d.name;
    opt.textContent = label;
    sel.appendChild(opt);
  }
  if (prev && Array.from(sel.options).some(function (o) { return o.value === prev; })) {
    sel.value = prev;
  }
}

function populateDmemCreateDiapSelect() {
  const targets = [el.contextMenuDmemCreateDiap, el.pickDmemCreateDiap];
  if (!currentModel) return;
  const diaps = currentModel.diaphragms || [];
  for (const sel of targets) {
    if (!sel) continue;
    const prev = sel.value;
    sel.innerHTML = "";
    for (const d of diaps) {
      const opt = document.createElement("option");
      opt.value = String(d.id);
      let label = "DIAP " + d.id;
      if (d.name) label += " — " + d.name;
      opt.textContent = label;
      sel.appendChild(opt);
    }
    if (prev && Array.from(sel.options).some(function (o) { return o.value === prev; })) {
      sel.value = prev;
    } else if (sel.options.length) {
      sel.selectedIndex = 0;
    }
  }
}

function timberDiapIdsFromSelectedDmem() {
  if (!currentModel) return [];
  const byDiap = {};
  for (const d of currentModel.diaphragms || []) byDiap[d.id] = d;
  const byDmem = {};
  for (const m of currentModel.membrane_elements || []) byDmem[m.id] = m;
  const ids = new Set();
  for (const dmemId of selectedDmemIds) {
    const mem = byDmem[dmemId];
    if (!mem) continue;
    const diap = byDiap[mem.diaphragm_id];
    if (isTimberDiaphragm(diap)) ids.add(diap.id);
  }
  return Array.from(ids).sort(function (a, b) { return a - b; });
}

function commonNumericValue(values) {
  if (!values.length) return null;
  const first = values[0];
  for (let i = 1; i < values.length; i++) {
    if (Math.abs(values[i] - first) > 1e-9) return null;
  }
  return first;
}

function commonWrwMultiplier() {
  if (!currentModel) return null;
  const byWrw = {};
  for (const w of currentModel.wood_rated_walls || []) byWrw[w.id] = w;
  const vals = [];
  for (const id of selectedWrwIds) {
    const w = byWrw[id];
    if (w && w.multiplier != null) vals.push(Number(w.multiplier));
  }
  return commonNumericValue(vals);
}

function wwllModelCodeFromWall(w) {
  if (!w) return null;
  const m = w.model_requested;
  if (m === "EQUIVALENT_BRACE") return 0;
  if (m === "SHEAR_PANEL") return 1;
  if (m === 0 || m === "0") return 0;
  if (m === 1 || m === "1") return 1;
  return null;
}

function wwllModelLabelFromWall(w) {
  const code = wwllModelCodeFromWall(w);
  if (code === 0) return "Brace";
  if (code === 1) return "Shear panel";
  return "?";
}

function wwllModelLabelFromCode(model) {
  return parseInt(model, 10) === 0 ? "Brace" : "Shear panel";
}

function commonWrwModel() {
  if (!currentModel) return null;
  const byWrw = {};
  for (const w of currentModel.wood_rated_walls || []) byWrw[w.id] = w;
  const vals = [];
  for (const id of selectedWrwIds) {
    const code = wwllModelCodeFromWall(byWrw[id]);
    if (code != null) vals.push(code);
  }
  return commonNumericValue(vals);
}

function getPickWrwCreateModel() {
  const sel = el.pickWrwCreateModel || el.contextMenuWrwCreateModel;
  const raw = sel ? sel.value : "1";
  return parseInt(raw, 10) === 0 ? 0 : 1;
}

function setPickWrwCreateModelValue(model) {
  const v = parseInt(model, 10) === 0 ? "0" : "1";
  if (el.pickWrwCreateModel) el.pickWrwCreateModel.value = v;
  if (el.contextMenuWrwCreateModel) el.contextMenuWrwCreateModel.value = v;
  try {
    localStorage.setItem(WRW_CREATE_MODEL_KEY, v);
  } catch (e) { /* ignore */ }
}

function loadPickWrwCreateModel() {
  let saved = null;
  try {
    saved = localStorage.getItem(WRW_CREATE_MODEL_KEY);
  } catch (e) { /* ignore */ }
  if (saved === "0" || saved === "1") {
    setPickWrwCreateModelValue(parseInt(saved, 10));
  }
}

const CONS_DOF_KEYS = ["tx", "ty", "tz", "rx", "ry", "rz"];
const CONS_PRESET_FIXED = [true, true, true, true, true, true];
const CONS_PRESET_PINNED = [true, true, true, false, false, false];
const CONS_PRESET_FREE = [false, false, false, false, false, false];

function consCheckboxElements(prefix) {
  const cap = prefix.charAt(0).toUpperCase() + prefix.slice(1);
  return CONS_DOF_KEYS.map(function (key) {
    const id = key.charAt(0).toUpperCase() + key.slice(1);
    return el[prefix + "Cons" + id] || el["contextMenuCons" + id];
  });
}

function readConsFixedFromCheckboxes(boxes) {
  return boxes.map(function (input) { return !!(input && input.checked); });
}

function writeConsFixedToCheckboxes(boxes, fixed, indeterminate) {
  for (let i = 0; i < boxes.length; i++) {
    const input = boxes[i];
    if (!input) continue;
    if (indeterminate || fixed == null) {
      input.checked = false;
      input.indeterminate = true;
      continue;
    }
    input.indeterminate = false;
    input.checked = !!fixed[i];
  }
}

function syncConsCheckboxGroups(fixed, indeterminate) {
  writeConsFixedToCheckboxes(consCheckboxElements("pick"), fixed, indeterminate);
  writeConsFixedToCheckboxes(consCheckboxElements("contextMenu"), fixed, indeterminate);
}

function commonNodeSupportFixed() {
  if (!currentModel || selectedNodeIds.size === 0) return null;
  const byNode = {};
  for (const s of currentModel.supports || []) byNode[s.node] = s.fixed;
  let ref = null;
  for (const id of selectedNodeIds) {
    const raw = byNode[id];
    const fixed = raw && raw.length === 6
      ? raw.map(function (v) { return !!v; })
      : CONS_PRESET_FREE.slice();
    if (ref == null) {
      ref = fixed;
      continue;
    }
    for (let i = 0; i < 6; i++) {
      if (fixed[i] !== ref[i]) return null;
    }
  }
  return ref;
}

function consFixedSummary(fixed) {
  const labels = ["TX", "TY", "TZ", "RX", "RY", "RZ"];
  const active = [];
  for (let i = 0; i < labels.length; i++) {
    if (fixed[i]) active.push(labels[i]);
  }
  return active.length ? active.join(", ") : "free (no CONS)";
}

function applyConsPreset(preset) {
  syncConsCheckboxGroups(preset, false);
}

function applyConsChange(fixed) {
  if (selectedNodeIds.size === 0) return;
  const count = selectedNodeIds.size;
  const summary = consFixedSummary(fixed);
  const ok = window.confirm(
    "Set support (" + summary + ") for " + count + " node" + (count === 1 ? "" : "s") + "?"
  );
  if (!ok) return;
  applyModelEdit({ action: "set_cons", fixed: fixed });
}

function updatePickWrwOptions() {
  const nodePickEnabled = isPickTargetEnabled("node");
  if (el.pickElemCreateOptions) {
    const showElem = canCreateElemFromNodePick();
    el.pickElemCreateOptions.hidden = !showElem;
    if (showElem) {
      populateElemCreateSectionSelect();
      if (el.pickElemCreateHint) {
        const ids = selectedNodeIdList();
        el.pickElemCreateHint.textContent = "Nodes " + ids[0] + " → " + ids[1];
      }
    } else if (el.pickElemCreateHint) {
      el.pickElemCreateHint.textContent = "";
    }
  }
  if (el.pickDmemCreateOptions) {
    const showDmem = canCreateDmemFromNodePick();
    el.pickDmemCreateOptions.hidden = !showDmem;
    if (showDmem) {
      populateDmemCreateDiapSelect();
      if (el.pickDmemCreateHint) {
        const count = selectedNodeIds.size;
        el.pickDmemCreateHint.textContent = count === 3
          ? "Nodes " + selectedNodeIdList().join(", ") + " → one triangle"
          : count + " nodes → auto triangulation inside the picked region";
      }
    } else if (el.pickDmemCreateHint) {
      el.pickDmemCreateHint.textContent = "";
    }
  }
  if (el.pickWrwCreateOptions) {
    const showCreate = nodePickEnabled && selectedNodeIds.size === 4
      && selectedElementIds.size === 0 && selectedDmemIds.size === 0
      && selectedWrwIds.size === 0;
    el.pickWrwCreateOptions.hidden = !showCreate;
  }
  if (el.pickWrwEditOptions) {
    const showEdit = isPickTargetEnabled("wall") && selectedWrwIds.size > 0
      && selectedNodeIds.size === 0 && selectedElementIds.size === 0
      && selectedDmemIds.size === 0;
    el.pickWrwEditOptions.hidden = !showEdit;
    if (showEdit && el.pickWrwEditModel) {
      const m = commonWrwModel();
      el.pickWrwEditModel.value = m == null ? "1" : String(m);
    }
  }
  if (el.pickNodeSupportOptions) {
    const showSupport = nodePickEnabled && selectedNodeIds.size > 0
      && selectedElementIds.size === 0 && selectedDmemIds.size === 0
      && selectedWrwIds.size === 0;
    el.pickNodeSupportOptions.hidden = !showSupport;
    if (showSupport) {
      const fixed = commonNodeSupportFixed();
      syncConsCheckboxGroups(fixed, fixed == null);
    }
  }
}

function applyWrwModelChange(model) {
  const m = parseInt(model, 10);
  if (m !== 0 && m !== 1) {
    window.alert("WRW type must be shear panel or brace.");
    return;
  }
  if (selectedWrwIds.size === 0) return;
  const label = wwllModelLabelFromCode(m);
  const count = selectedWrwIds.size;
  const ok = window.confirm(
    "Change " + count + " WRW record" + (count === 1 ? "" : "s") + " to " + label + "?"
  );
  if (!ok) return;
  applyModelEdit({ action: "set_wwll_model", model: m });
}

function commonDiapTimberMultiplier() {
  if (!currentModel) return null;
  const byDiap = {};
  for (const d of currentModel.diaphragms || []) byDiap[d.id] = d;
  const vals = [];
  for (const id of timberDiapIdsFromSelectedDmem()) {
    const d = byDiap[id];
    if (d && d.timber_multiplier != null) vals.push(Number(d.timber_multiplier));
  }
  return commonNumericValue(vals);
}

function hideEjntEditor() {
  if (el.ejntEditPanel) el.ejntEditPanel.hidden = true;
  if (el.ejntEditText) el.ejntEditText.value = "";
}

async function fetchEjntLines(path, elementIds) {
  const ids = elementIds.join(",");
  const url = "/api/model/ejnt-lines?path=" + encodeURIComponent(path)
    + "&element_ids=" + encodeURIComponent(ids);
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(function () { return {}; });
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

async function openEjntEditor() {
  const path = getCurrentModelPath();
  if (!path) return;
  if (selectedElementIds.size === 0) {
    setStatus("Pick one or more elements first");
    return;
  }
  const elemIds = selectedElementIdList();
  hideContextMenu();
  setStatus("Loading EJNT lines…");
  try {
    const data = await fetchEjntLines(path, elemIds);
    const header = data.header || "";
    const lines = (data.lines || []).map(function (row) { return row.line; }).join("\n");
    if (el.ejntEditText) el.ejntEditText.value = header + lines;
    if (el.ejntEditPanel) el.ejntEditPanel.hidden = false;
    if (el.ejntEditText) el.ejntEditText.focus();
    setStatus(path + " — edit EJNT for element(s) " + elemIds.join(", "));
  } catch (ex) {
    setStatus("Error: " + ex.message);
    window.alert("Failed to load EJNT lines: " + ex.message);
  }
}

function applyEjntEditor() {
  if (!el.ejntEditText) return;
  applyModelEdit({
    action: "set_ejnt_lines",
    lines_text: el.ejntEditText.value,
  });
  hideEjntEditor();
}

function hideContextMenu() {
  if (el.elemContextMenu) el.elemContextMenu.hidden = true;
}

function beginViewportRightDrag(ev) {
  viewportRightDrag = {
    startClientX: ev.clientX,
    startClientY: ev.clientY,
    dragged: false,
  };
}

function updateViewportRightDrag(ev) {
  if (!viewportRightDrag || viewportRightDrag.dragged) return;
  const dx = ev.clientX - viewportRightDrag.startClientX;
  const dy = ev.clientY - viewportRightDrag.startClientY;
  if (Math.hypot(dx, dy) >= VIEWPORT_CONTEXT_MENU_DRAG_PX) {
    viewportRightDrag.dragged = true;
    hideContextMenu();
  }
}

function finishViewportRightDrag(ev) {
  if (!viewportRightDrag) return;
  const drag = viewportRightDrag;
  viewportRightDrag = null;

  const dx = ev.clientX - drag.startClientX;
  const dy = ev.clientY - drag.startClientY;
  const moved = drag.dragged || Math.hypot(dx, dy) >= VIEWPORT_CONTEXT_MENU_DRAG_PX;
  if (moved) {
    hideContextMenu();
    return;
  }
  if (ev && ev.preventDefault) ev.preventDefault();
  showViewportContextMenu(ev.clientX, ev.clientY);
}

function isViewportContextMenuArea(target) {
  if (!target) return false;
  if (el.viewport && el.viewport.contains(target)) return true;
  if (el.elemContextMenu && el.elemContextMenu.contains(target)) return true;
  return false;
}

function suppressBrowserContextMenu(ev) {
  if (!isViewportContextMenuArea(ev.target)) return;
  ev.preventDefault();
  ev.stopPropagation();
}

function populateContextMenuCatalog() {
  if (!el.contextMenuSections || !el.contextMenuMaterials || !currentModel) return;
  el.contextMenuSections.innerHTML = "";
  el.contextMenuMaterials.innerHTML = "";

  const sections = currentModel.sections || [];
  for (const s of sections) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "context-menu-item";
    const mat = s.material_name || ("MAT " + s.material_id);
    btn.textContent = "SECT " + s.id + " — " + s.name + " (" + mat + ")";
    btn.addEventListener("click", function () {
      hideContextMenu();
      applyModelEdit({ action: "set_section", section_id: s.id });
    });
    el.contextMenuSections.appendChild(btn);
  }

  const materials = currentModel.materials || [];
  for (const m of materials) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "context-menu-item";
    btn.textContent = "MATE " + m.id + " — " + m.name;
    btn.addEventListener("click", function () {
      hideContextMenu();
      const ok = window.confirm(
        "Change material to MATE " + m.id + " (" + m.name + ")?\n" +
        "All elements sharing the same section will be affected."
      );
      if (!ok) return;
      applyModelEdit({ action: "set_material", material_id: m.id });
    });
    el.contextMenuMaterials.appendChild(btn);
  }
}

function positionContextMenu(clientX, clientY) {
  if (!el.elemContextMenu) return;
  const margin = 8;
  el.elemContextMenu.hidden = false;
  const rect = el.elemContextMenu.getBoundingClientRect();
  let left = clientX;
  let top = clientY;
  if (left + rect.width > window.innerWidth - margin) {
    left = window.innerWidth - rect.width - margin;
  }
  if (top + rect.height > window.innerHeight - margin) {
    top = window.innerHeight - rect.height - margin;
  }
  el.elemContextMenu.style.left = Math.max(margin, left) + "px";
  el.elemContextMenu.style.top = Math.max(margin, top) + "px";
}

function updateViewportContextMenuState() {
  if (el.contextMenuTogglePick) {
    el.contextMenuTogglePick.textContent = selectionModeActive
      ? "Exit pick mode (normal)"
      : "Enter pick mode";
  }
  const hasMemberSel = selectedElementIds.size > 0
    || selectedDmemIds.size > 0
    || selectedWrwIds.size > 0;
  if (el.contextMenuShowMembersOnly) el.contextMenuShowMembersOnly.disabled = !hasMemberSel;
  if (el.contextMenuHideMembers) el.contextMenuHideMembers.disabled = !hasMemberSel;
  if (el.contextMenuPickSection) {
    el.contextMenuPickSection.hidden = !hasPickSelection();
  }
}

function populatePickContextMenu() {
  if (selectedElementIds.size > 0) populateContextMenuCatalog();
  const elemCount = selectedElementIds.size;
  const nodeCount = selectedNodeIds.size;
  const dmemCount = selectedDmemIds.size;
  const wrwCount = selectedWrwIds.size;
  if (el.contextMenuDeleteMember) {
    el.contextMenuDeleteMember.hidden = !hasPickSelection();
  }
  if (el.contextMenuNodeSupport) {
    const showSupport = nodeCount > 0 && elemCount === 0 && dmemCount === 0 && wrwCount === 0;
    el.contextMenuNodeSupport.hidden = !showSupport;
    if (showSupport) {
      const fixed = commonNodeSupportFixed();
      syncConsCheckboxGroups(fixed, fixed == null);
    }
  }
  if (el.contextMenuElemEdits) {
    el.contextMenuElemEdits.hidden = elemCount === 0;
  }
  if (el.contextMenuWrwEdits) {
    el.contextMenuWrwEdits.hidden = wrwCount === 0;
    if (wrwCount > 0) {
      if (el.contextMenuWrwMultiplier) {
        const m = commonWrwMultiplier();
        el.contextMenuWrwMultiplier.value = m == null ? "" : String(m);
      }
      if (el.contextMenuWrwModel) {
        const model = commonWrwModel();
        el.contextMenuWrwModel.value = model == null ? "1" : String(model);
      }
    }
  }
  if (el.contextMenuDmemCreate) {
    const canCreate = canCreateDmemFromNodePick();
    el.contextMenuDmemCreate.hidden = !canCreate;
    if (canCreate) {
      populateDmemCreateDiapSelect();
      if (el.contextMenuDmemCreateHint) {
        const ids = selectedNodeIdList();
        el.contextMenuDmemCreateHint.textContent = ids.length === 3
          ? "Nodes " + ids.join(", ") + " → triangle"
          : ids.length + " nodes → auto triangulation";
      }
    } else if (el.contextMenuDmemCreateHint) {
      el.contextMenuDmemCreateHint.textContent = "";
    }
  }
  if (el.contextMenuElemCreate) {
    const canCreateElem = canCreateElemFromNodePick();
    el.contextMenuElemCreate.hidden = !canCreateElem;
    if (canCreateElem) {
      populateElemCreateSectionSelect();
      if (el.contextMenuElemCreateBeta && el.pickElemCreateBeta) {
        el.contextMenuElemCreateBeta.value = el.pickElemCreateBeta.value;
      }
      if (el.contextMenuElemCreateHint) {
        const ids = selectedNodeIdList();
        el.contextMenuElemCreateHint.textContent = "Nodes " + ids[0] + " → " + ids[1];
      }
    } else if (el.contextMenuElemCreateHint) {
      el.contextMenuElemCreateHint.textContent = "";
    }
  }
  if (el.contextMenuWrwCreate) {
    const canCreateWrw = nodeCount === 4 && elemCount === 0 && dmemCount === 0
      && wrwCount === 0;
    el.contextMenuWrwCreate.hidden = !canCreateWrw;
    if (canCreateWrw) {
      if (el.contextMenuWrwCreateModel && el.pickWrwCreateModel) {
        el.contextMenuWrwCreateModel.value = el.pickWrwCreateModel.value;
      }
      populateWrwCreateDiapSelect();
      if (el.contextMenuWrwCreateHint) {
        const ids = selectedNodeIdList();
        el.contextMenuWrwCreateHint.textContent =
          "Nodes " + ids.join(", ") + " → wall rectangle";
      }
    } else if (el.contextMenuWrwCreateHint) {
      el.contextMenuWrwCreateHint.textContent = "";
    }
  }
  const timberDiapIds = timberDiapIdsFromSelectedDmem();
  if (el.contextMenuDmemEdits) {
    el.contextMenuDmemEdits.hidden = dmemCount === 0 || timberDiapIds.length === 0;
    if (dmemCount > 0 && timberDiapIds.length > 0 && el.contextMenuDiapMultiplier) {
      const m = commonDiapTimberMultiplier();
      el.contextMenuDiapMultiplier.value = m == null ? "" : String(m);
    }
    if (el.contextMenuDiapHint) {
      if (dmemCount > 0 && timberDiapIds.length === 0) {
        el.contextMenuDiapHint.textContent = "Selected DMEM uses explicit DMAT (SRC=0); multiplier edit unavailable.";
      } else if (timberDiapIds.length > 0) {
        el.contextMenuDiapHint.textContent = "Updates DIAP id(s): " + timberDiapIds.join(", ");
      } else {
        el.contextMenuDiapHint.textContent = "";
      }
    }
  }
  if (el.contextMenuTitle) {
    const titleParts = [];
    if (elemCount > 0) {
      titleParts.push(elemCount + " element" + (elemCount === 1 ? "" : "s"));
    }
    if (nodeCount > 0) {
      titleParts.push(nodeCount + " node" + (nodeCount === 1 ? "" : "s"));
    }
    if (dmemCount > 0) {
      titleParts.push(dmemCount + " DMEM");
    }
    if (wrwCount > 0) {
      titleParts.push(wrwCount + " WRW");
    }
    el.contextMenuTitle.textContent = titleParts.join(", ") + " picked";
  }
}

function showViewportContextMenu(clientX, clientY) {
  if (!el.elemContextMenu) return;
  updateViewportContextMenuState();
  if (hasPickSelection()) populatePickContextMenu();
  positionContextMenu(clientX, clientY);
}

function resetEditHistory() {
  editUndoStack = [];
  editRedoStack = [];
}

function pushEditUndoSnapshot(path, text) {
  if (!path || text == null) return;
  editUndoStack.push({ path: path, text: text });
  if (editUndoStack.length > MAX_EDIT_UNDO) {
    editUndoStack.shift();
  }
  editRedoStack = [];
}

function pruneSelectionToModel() {
  if (!currentModel) return;
  const validElems = new Set(currentModel.elements.map(function (e) { return e.id; }));
  const validNodes = new Set(currentModel.nodes.map(function (n) { return n.id; }));
  const validDmem = new Set((currentModel.membrane_elements || []).map(function (m) { return m.id; }));
  const validWrw = new Set((currentModel.wood_rated_walls || []).map(function (w) { return w.id; }));
  selectedElementIds = new Set(
    Array.from(selectedElementIds).filter(function (id) { return validElems.has(id); })
  );
  selectedNodeIds = new Set(
    Array.from(selectedNodeIds).filter(function (id) { return validNodes.has(id); })
  );
  selectedDmemIds = new Set(
    Array.from(selectedDmemIds).filter(function (id) { return validDmem.has(id); })
  );
  selectedWrwIds = new Set(
    Array.from(selectedWrwIds).filter(function (id) { return validWrw.has(id); })
  );
  pruneMemberVisibilityFilter();
  updateSelectionHighlight();
  updateSelectionPanel();
}

async function restoreEditHistoryEntry(snapshot, redoTarget) {
  const path = getCurrentModelPath();
  if (!snapshot || snapshot.path !== path) {
    setStatus("Undo/redo history does not match the current model");
    return false;
  }
  if (editHistoryBusy) return false;
  editHistoryBusy = true;
  hideContextMenu();
  try {
    const current = await fetchInputText(path);
    redoTarget.push({ path: path, text: current });
    await saveInputText(path, snapshot.text);
    await loadSelectedModel(false, {
      keepSelection: true,
      keepCamera: true,
      keepMemberVisibility: true,
    });
    pruneSelectionToModel();
    return true;
  } catch (ex) {
    redoTarget.pop();
    setStatus("Undo/redo error: " + ex.message);
    window.alert("Undo/redo failed: " + ex.message);
    return false;
  } finally {
    editHistoryBusy = false;
  }
}

async function undoModelEdit() {
  if (editUndoStack.length === 0) {
    setStatus("Nothing to undo");
    return;
  }
  const snap = editUndoStack.pop();
  const ok = await restoreEditHistoryEntry(snap, editRedoStack);
  if (ok) {
    setStatus((getCurrentModelPath() || "") + " — undo (Ctrl+Z)");
  } else if (snap) {
    editUndoStack.push(snap);
  }
}

async function redoModelEdit() {
  if (editRedoStack.length === 0) {
    setStatus("Nothing to redo");
    return;
  }
  const snap = editRedoStack.pop();
  const ok = await restoreEditHistoryEntry(snap, editUndoStack);
  if (ok) {
    setStatus((getCurrentModelPath() || "") + " — redo (Ctrl+Y)");
  } else if (snap) {
    editRedoStack.push(snap);
  }
}

function initEditHistoryShortcuts() {
  document.addEventListener("keydown", function (ev) {
    if (isViewerTextInputTarget(ev.target)) return;
    const mod = ev.ctrlKey || ev.metaKey;
    if (!mod) return;
    const key = ev.key;
    if (key === "z" || key === "Z") {
      if (ev.shiftKey) return;
      ev.preventDefault();
      undoModelEdit();
      return;
    }
    if (key === "y" || key === "Y") {
      ev.preventDefault();
      redoModelEdit();
    }
  });
}

function pickSelectionCount() {
  return selectedNodeIds.size + selectedElementIds.size
    + selectedDmemIds.size + selectedWrwIds.size;
}

function pickSelectionDeleteSummary() {
  const parts = [];
  if (selectedNodeIds.size > 0) {
    parts.push(selectedNodeIds.size + " node" + (selectedNodeIds.size === 1 ? "" : "s"));
  }
  if (selectedElementIds.size > 0) {
    parts.push(selectedElementIds.size + " element" + (selectedElementIds.size === 1 ? "" : "s"));
  }
  if (selectedDmemIds.size > 0) {
    parts.push(selectedDmemIds.size + " diaphragm" + (selectedDmemIds.size === 1 ? "" : "s"));
  }
  if (selectedWrwIds.size > 0) {
    parts.push(selectedWrwIds.size + " wall" + (selectedWrwIds.size === 1 ? "" : "s"));
  }
  return parts.join(", ");
}

function confirmDeletePickSelection() {
  if (!hasPickSelection()) return false;
  const total = pickSelectionCount();
  let msg = "Delete " + total + " selected member" + (total === 1 ? "" : "s") + "?";
  const summary = pickSelectionDeleteSummary();
  if (summary) msg += "\n(" + summary + ")";
  if (selectedNodeIds.size > 0) {
    msg += "\nDeleting node(s) will also remove connected elements and related records.";
  }
  return window.confirm(msg);
}

function deletePickSelection() {
  if (!confirmDeletePickSelection()) return;
  applyModelEdit({ action: "delete_selection" });
}

async function applyModelEdit(extra) {
  const path = getCurrentModelPath();
  if (!path) return;
  let payload;
  if (extra.action === "delete_nodes") {
    if (selectedNodeIds.size === 0) return;
    payload = {
      action: "delete_nodes",
      node_ids: selectedNodeIdList(),
    };
  } else if (extra.action === "create_dmem") {
    if (selectedNodeIds.size < 3 || selectedElementIds.size > 0
      || selectedDmemIds.size > 0 || selectedWrwIds.size > 0) return;
    const diapId = parseInt(extra.diap_id, 10);
    if (!isFinite(diapId)) return;
    payload = {
      action: "create_dmem",
      node_ids: selectedNodeIdList(),
      diap_id: diapId,
    };
  } else if (extra.action === "create_element") {
    if (!canCreateElemFromNodePick()) return;
    const sectionId = parseInt(extra.section_id, 10);
    if (!isFinite(sectionId)) return;
    const beta = parseFloat(extra.beta);
    payload = {
      action: "create_element",
      node_ids: selectedNodeIdList(),
      section_id: sectionId,
      beta: isFinite(beta) ? beta : 0,
    };
  } else if (extra.action === "create_wwll") {
    if (selectedNodeIds.size !== 4 || selectedElementIds.size > 0
      || selectedDmemIds.size > 0 || selectedWrwIds.size > 0) return;
    const multiplier = parseFloat(extra.multiplier);
    if (!isFinite(multiplier) || multiplier <= 0) return;
    payload = {
      action: "create_wwll",
      node_ids: selectedNodeIdList(),
      multiplier: multiplier,
      model: extra.model,
      layo: extra.layo,
    };
    if (extra.diap_id !== "" && extra.diap_id != null) {
      const diapId = parseInt(extra.diap_id, 10);
      if (isFinite(diapId)) payload.diap_id = diapId;
    }
  } else if (extra.action === "delete_selection") {
    if (!hasPickSelection()) return;
    payload = {
      action: "delete_selection",
      node_ids: selectedNodeIdList(),
      element_ids: selectedElementIdList(),
      dmem_ids: selectedDmemIdList(),
      wwll_ids: selectedWrwIdList(),
    };
  } else if (extra.action === "delete_dmem") {
    if (selectedDmemIds.size === 0) return;
    payload = {
      action: "delete_dmem",
      dmem_ids: selectedDmemIdList(),
    };
  } else if (extra.action === "delete_wwll") {
    if (selectedWrwIds.size === 0) return;
    payload = {
      action: "delete_wwll",
      wwll_ids: selectedWrwIdList(),
    };
  } else if (extra.action === "set_wwll_multiplier") {
    if (selectedWrwIds.size === 0) return;
    payload = {
      action: "set_wwll_multiplier",
      wwll_ids: selectedWrwIdList(),
      multiplier: extra.multiplier,
    };
  } else if (extra.action === "set_wwll_model") {
    if (selectedWrwIds.size === 0) return;
    const model = parseInt(extra.model, 10);
    if (model !== 0 && model !== 1) return;
    payload = {
      action: "set_wwll_model",
      wwll_ids: selectedWrwIdList(),
      model: model,
    };
  } else if (extra.action === "set_diap_timber_multiplier") {
    const diapIds = timberDiapIdsFromSelectedDmem();
    if (diapIds.length === 0) return;
    payload = {
      action: "set_diap_timber_multiplier",
      diap_ids: diapIds,
      multiplier: extra.multiplier,
    };
  } else if (extra.action === "set_cons") {
    if (selectedNodeIds.size === 0) return;
    const fixed = extra.fixed;
    if (!fixed || fixed.length !== 6) return;
    payload = {
      action: "set_cons",
      node_ids: selectedNodeIdList(),
      fixed: fixed.map(function (v) { return !!v; }),
    };
  } else {
    if (selectedElementIds.size === 0) return;
    payload = Object.assign({ element_ids: selectedElementIdList() }, extra);
  }
  hideContextMenu();
  setStatus("Applying edit…");
  let undoPushed = false;
  try {
    const beforeText = await fetchInputText(path);
    pushEditUndoSnapshot(path, beforeText);
    undoPushed = true;
    const url = "/api/model/edit?path=" + encodeURIComponent(path);
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(function () { return {}; });
      throw new Error(err.detail || res.statusText);
    }
    const body = await res.json();
    const destructive = payload.action === "delete" || payload.action === "delete_nodes"
      || payload.action === "delete_dmem" || payload.action === "delete_wwll"
      || payload.action === "delete_selection";
    const createdDmem = payload.action === "create_dmem";
    const createdWrw = payload.action === "create_wwll";
    const createdElem = payload.action === "create_element";
    const prevElems = new Set(selectedElementIds);
    const prevNodes = new Set(selectedNodeIds);
    const prevDmem = new Set(selectedDmemIds);
    const prevWrw = new Set(selectedWrwIds);
    await loadSelectedModel(false, {
      keepSelection: !destructive && !createdDmem && !createdWrw && !createdElem,
      keepCamera: true,
      keepMemberVisibility: true,
    });
    let visibilityChanged = false;
    if (createdDmem) {
      const createdIds = parseCreatedDmemIdsFromWarnings(body.warnings);
      if (createdIds.length > 1) {
        replacePickSelection([], [], createdIds, []);
        visibilityChanged = addMemberVisibilityIds([], createdIds, []);
      } else if (createdIds.length === 1) {
        replacePickSelection([], [], createdIds, []);
        visibilityChanged = addMemberVisibilityIds([], createdIds, []);
      } else {
        const newId = findDmemIdByNodes(payload.diap_id, payload.node_ids);
        if (newId != null) {
          replacePickSelection([], [], [newId], []);
          visibilityChanged = addMemberVisibilityIds([], [newId], []);
        } else {
          clearSelection();
        }
      }
    } else if (createdWrw) {
      const newId = findWrwIdByNodes(payload.node_ids);
      if (newId != null) {
        replacePickSelection([], [], [], [newId]);
        visibilityChanged = addMemberVisibilityIds([], [], [newId]);
      } else {
        clearSelection();
      }
    } else if (createdElem) {
      const newId = parseCreatedElemIdFromWarnings(body.warnings)
        ?? findElementIdByNodes(payload.node_ids[0], payload.node_ids[1]);
      if (newId != null) {
        replacePickSelection([], [newId], [], []);
        visibilityChanged = addMemberVisibilityIds([newId], [], []);
      } else {
        clearSelection();
      }
    } else if (!destructive) {
      selectedElementIds = prevElems;
      selectedNodeIds = prevNodes;
      selectedDmemIds = prevDmem;
      selectedWrwIds = prevWrw;
      pruneSelectionToModel();
    }
    if (visibilityChanged && currentModel) buildModelScene(currentModel);
    let msg = path + " — edit saved";
    if (body.warnings && body.warnings.length) {
      msg += " (" + body.warnings[0] + ")";
    }
    setStatus(msg);
  } catch (ex) {
    if (undoPushed) editUndoStack.pop();
    setStatus("Edit error: " + ex.message);
    window.alert("Edit failed: " + ex.message);
  }
}

function initContextMenu() {
  if (!el.elemContextMenu || !renderer) return;

  const canvas = renderer.domElement;

  canvas.addEventListener("mousedown", function (ev) {
    if (ev.button !== 2) return;
    hideContextMenu();
    beginViewportRightDrag(ev);
    ev.preventDefault();
    if (selectionModeActive && hasPickSelection()) ev.stopPropagation();
  }, true);

  window.addEventListener("mousemove", function (ev) {
    updateViewportRightDrag(ev);
  });

  window.addEventListener("mouseup", function (ev) {
    if (ev.button !== 2) return;
    finishViewportRightDrag(ev);
  });

  document.addEventListener("contextmenu", suppressBrowserContextMenu, true);
  if (el.viewport) {
    el.viewport.addEventListener("contextmenu", suppressBrowserContextMenu, true);
  }
  el.elemContextMenu.addEventListener("contextmenu", suppressBrowserContextMenu, true);

  el.elemContextMenu.addEventListener("click", function (ev) {
    const btn = ev.target.closest("[data-action]");
    if (!btn) return;
    const action = btn.getAttribute("data-action");
    if (action === "toggle-pick") {
      hideContextMenu();
      setSelectionMode(!selectionModeActive);
      return;
    }
    if (action === "members-only") {
      applyMemberVisibilityFilter("only");
      return;
    }
    if (action === "members-hide") {
      applyMemberVisibilityFilter("hide");
      return;
    }
    if (action === "members-show-all") {
      applyMemberVisibilityFilter("all");
      return;
    }
    if (action === "delete-members") {
      deletePickSelection();
      return;
    }
    if (action === "set-wrw-model") {
      const raw = el.contextMenuWrwModel ? el.contextMenuWrwModel.value : "1";
      applyWrwModelChange(raw);
      return;
    }
    if (action === "set-wrw-multiplier") {
      const raw = el.contextMenuWrwMultiplier ? el.contextMenuWrwMultiplier.value.trim() : "";
      const m = parseFloat(raw);
      if (!isFinite(m) || m <= 0) {
        window.alert("Enter a positive wall multiplier.");
        return;
      }
      applyModelEdit({ action: "set_wwll_multiplier", multiplier: m });
      return;
    }
    if (action === "set-diap-multiplier") {
      const raw = el.contextMenuDiapMultiplier ? el.contextMenuDiapMultiplier.value.trim() : "";
      const m = parseFloat(raw);
      if (!isFinite(m) || m <= 0) {
        window.alert("Enter a positive floor/roof multiplier.");
        return;
      }
      applyModelEdit({ action: "set_diap_timber_multiplier", multiplier: m });
      return;
    }
    if (action === "create-dmem") {
      if (!canCreateDmemFromNodePick()) {
        window.alert("Pick at least 3 nodes (no elements / DMEM / WRW) to create DMEM.");
        return;
      }
      const diapRaw = el.contextMenuDmemCreateDiap ? el.contextMenuDmemCreateDiap.value : "";
      const diapId = parseInt(diapRaw, 10);
      if (!isFinite(diapId)) {
        window.alert("Select a DIAP for the new DMEM.");
        return;
      }
      requestCreateDmemMesh(diapId);
      return;
    }
    if (action === "create-elem") {
      if (!canCreateElemFromNodePick()) {
        window.alert("Pick exactly 2 nodes (no elements / DMEM / WRW) to create a member.");
        return;
      }
      const sectId = getPickElemCreateSectionId();
      if (sectId == null) {
        window.alert("Select a section for the new ELEM.");
        return;
      }
      requestCreateElement(sectId, getPickElemCreateBeta());
      return;
    }
    if (action === "create-wrw") {
      if (selectedNodeIds.size !== 4 || selectedElementIds.size > 0
        || selectedDmemIds.size > 0 || selectedWrwIds.size > 0) {
        window.alert("Pick exactly 4 nodes (no elements / DMEM / WRW) to create a WRW wall.");
        return;
      }
      const multRaw = el.contextMenuWrwCreateMultiplier
        ? el.contextMenuWrwCreateMultiplier.value.trim() : "2";
      const multiplier = parseFloat(multRaw);
      if (!isFinite(multiplier) || multiplier <= 0) {
        window.alert("Enter a positive wall multiplier.");
        return;
      }
      const model = getPickWrwCreateModel();
      const diapRaw = el.contextMenuWrwCreateDiap && isAdvancedGui() ? el.contextMenuWrwCreateDiap.value : "";
      const modelLabel = wwllModelLabelFromCode(model);
      const ids = selectedNodeIdList();
      const diapText = diapRaw ? ("DIAP " + diapRaw) : "no DIAP tie";
      const ok = window.confirm(
        "Create WRW (" + modelLabel + ", M=" + multiplier + ", " + diapText +
        ") with nodes " + ids.join(", ") + "?"
      );
      if (!ok) return;
      applyModelEdit({
        action: "create_wwll",
        multiplier: multiplier,
        model: model,
        diap_id: diapRaw,
        layo: model === 0 ? 1 : 1,
      });
      return;
    }
    if (action === "ejnt-edit") {
      openEjntEditor();
      return;
    }
    if (action === "cons-preset-fixed") {
      applyConsPreset(CONS_PRESET_FIXED);
      return;
    }
    if (action === "cons-preset-pinned") {
      applyConsPreset(CONS_PRESET_PINNED);
      return;
    }
    if (action === "cons-preset-free") {
      applyConsPreset(CONS_PRESET_FREE);
      return;
    }
    if (action === "set-cons") {
      applyConsChange(readConsFixedFromCheckboxes(consCheckboxElements("contextMenu")));
      return;
    }
  });

  if (el.btnEjntEditApply) {
    el.btnEjntEditApply.addEventListener("click", () => applyEjntEditor());
  }
  if (el.btnEjntEditCancel) {
    el.btnEjntEditCancel.addEventListener("click", () => hideEjntEditor());
  }
  if (el.btnEjntEditClose) {
    el.btnEjntEditClose.addEventListener("click", () => hideEjntEditor());
  }

  if (el.pickWrwCreateModel) {
    el.pickWrwCreateModel.addEventListener("change", function () {
      setPickWrwCreateModelValue(getPickWrwCreateModel());
    });
  }
  if (el.contextMenuWrwCreateModel) {
    el.contextMenuWrwCreateModel.addEventListener("change", function () {
      if (el.pickWrwCreateModel) {
        el.pickWrwCreateModel.value = el.contextMenuWrwCreateModel.value;
      }
      setPickWrwCreateModelValue(el.contextMenuWrwCreateModel.value);
    });
  }
  if (el.btnPickDmemCreate) {
    el.btnPickDmemCreate.addEventListener("click", function () {
      const raw = el.pickDmemCreateDiap ? el.pickDmemCreateDiap.value : "";
      const diapId = parseInt(raw, 10);
      if (!isFinite(diapId)) {
        window.alert("Select a DIAP for the new DMEM.");
        return;
      }
      requestCreateDmemMesh(diapId);
    });
  }
  if (el.btnPickElemCreate) {
    el.btnPickElemCreate.addEventListener("click", function () {
      const sectId = getPickElemCreateSectionId();
      if (sectId == null) {
        window.alert("Select a section for the new ELEM.");
        return;
      }
      requestCreateElement(sectId, getPickElemCreateBeta());
    });
  }
  if (el.pickElemCreateSection) {
    el.pickElemCreateSection.addEventListener("change", function () {
      if (el.contextMenuElemCreateSection) {
        el.contextMenuElemCreateSection.value = el.pickElemCreateSection.value;
      }
    });
  }
  if (el.contextMenuElemCreateSection) {
    el.contextMenuElemCreateSection.addEventListener("change", function () {
      if (el.pickElemCreateSection) {
        el.pickElemCreateSection.value = el.contextMenuElemCreateSection.value;
      }
    });
  }
  if (el.pickElemCreateBeta) {
    el.pickElemCreateBeta.addEventListener("change", function () {
      if (el.contextMenuElemCreateBeta) {
        el.contextMenuElemCreateBeta.value = el.pickElemCreateBeta.value;
      }
    });
  }
  if (el.contextMenuElemCreateBeta) {
    el.contextMenuElemCreateBeta.addEventListener("change", function () {
      if (el.pickElemCreateBeta) {
        el.pickElemCreateBeta.value = el.contextMenuElemCreateBeta.value;
      }
    });
  }
  if (el.btnPickWrwApplyModel) {
    el.btnPickWrwApplyModel.addEventListener("click", function () {
      const raw = el.pickWrwEditModel ? el.pickWrwEditModel.value : "1";
      applyWrwModelChange(raw);
    });
  }
  if (el.btnPickConsFixed) {
    el.btnPickConsFixed.addEventListener("click", function () {
      applyConsPreset(CONS_PRESET_FIXED);
    });
  }
  if (el.btnPickConsPinned) {
    el.btnPickConsPinned.addEventListener("click", function () {
      applyConsPreset(CONS_PRESET_PINNED);
    });
  }
  if (el.btnPickConsFree) {
    el.btnPickConsFree.addEventListener("click", function () {
      applyConsPreset(CONS_PRESET_FREE);
    });
  }
  if (el.btnPickConsApply) {
    el.btnPickConsApply.addEventListener("click", function () {
      applyConsChange(readConsFixedFromCheckboxes(consCheckboxElements("pick")));
    });
  }
  consCheckboxElements("pick").forEach(function (input) {
    if (!input) return;
    input.addEventListener("change", function () {
      input.indeterminate = false;
      const fixed = readConsFixedFromCheckboxes(consCheckboxElements("pick"));
      syncConsCheckboxGroups(fixed, false);
    });
  });

  document.addEventListener("mousedown", function (ev) {
    if (!el.elemContextMenu || el.elemContextMenu.hidden) return;
    if (el.elemContextMenu.contains(ev.target)) return;
    if (ev.button !== 0) return;
    hideContextMenu();
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") {
      if (el.ejntEditPanel && !el.ejntEditPanel.hidden) {
        hideEjntEditor();
        ev.stopPropagation();
        return;
      }
      hideContextMenu();
    }
  });
}

function refreshDisplayStatus(model) {
  const path = model.path || getCurrentModelPath() || "";
  const lcKey = String(el.lcSelect.value);
  let extra = analysisComplete(model) ? " (solved)" : "";
  if (analysisComplete(model) && !modelHasForceData(model, lcKey)) {
    extra += " — force data unavailable (restart stb gui)";
  }
  if ((el.chkReactions.checked || el.chkReactionValues.checked) &&
      !modelHasReactionData(model, lcKey)) {
    extra += " — no reaction data for LC " + lcKey;
  }
  setStatus(path + extra + " — " + model.nodes.length + " nodes, " + model.elements.length + " elements");
}

function boolOnOff(v) {
  return v ? "ON" : "OFF";
}

function selectedForceLabel() {
  const id = parseInt(el.forceSelect.value, 10) || 0;
  if (id <= 0 || id >= FORCE_LABELS.length) return "None";
  return FORCE_LABELS[id];
}

function updateViewerInfoOverlay(model) {
  if (!el.viewerInfoOverlay) return;
  if (!model) {
    el.viewerInfoOverlay.textContent = "No model loaded.";
    return;
  }

  const path = normalizeModelPath(model.path || getCurrentModelPath() || "");
  const fileName = path ? path.replace(/^.*\//, "") : "(none)";
  const lc = String(el.lcSelect.value || "");
  const solved = analysisComplete(model);
  const defFac = parseFloat(el.defFactor.value) || 0;
  const dispLabel = dispComponentLabel(currentDispComponent());
  const forceComp = selectedForceLabel();

  const pointLoads = model.point_loads ? model.point_loads.length : 0;
  const elemLoads = model.element_loads ? model.element_loads.length : 0;
  const supports = model.supports ? model.supports.length : 0;

  const displayLines = [];
  if (el.chkDeformed.checked) displayLines.push("deformed shape " + dispLabel + " x" + defFac.toFixed(1));
  if (el.chkDispContour && el.chkDispContour.checked) displayLines.push("disp contour " + dispLabel);
  if (el.chkLoads.checked) {
    displayLines.push("input loads (" + loadTypeFilterValue() + ")");
    if (el.chkLoadValues.checked) displayLines.push("load values");
  }
  if (windLoadsShown() && windVisualData) {
    const wc = windCaseById(windVisualData, selectedWindCaseId);
    if (wc) {
      displayLines.push(
        "wind: " + wc.name + " (" + (wc.direction_label || wc.direction) + ", LC" + wc.load_case + ")"
      );
    }
  }
  if (practiceCentersShown()) displayLines.push("CoG / CoR");
  if (el.chkReactions && el.chkReactions.checked) displayLines.push("reactions");
  if (el.chkReactionValues && el.chkReactionValues.checked) displayLines.push("reaction values");
  if (!el.chkSupports || el.chkSupports.checked) displayLines.push("supports");
  if (el.chkEJnt && el.chkEJnt.checked) displayLines.push("element joints");
  if (el.chkLabels && el.chkLabels.checked) displayLines.push("node IDs");
  if (el.chkElemLabels && el.chkElemLabels.checked) displayLines.push("element IDs");
  if (el.chkMaterial && el.chkMaterial.checked) displayLines.push("material labels");
  if (el.chkSection && el.chkSection.checked) displayLines.push("section labels");
  if (membraneShown()) {
    const nmem = model.membrane_elements ? model.membrane_elements.length : 0;
    displayLines.push("diaphragm members (" + nmem + ")");
  }
  if (woodWallShown()) {
    const nwrw = model.wood_rated_walls ? model.wood_rated_walls.length : 0;
    displayLines.push("wood walls (" + nwrw + ")");
  }
  if (el.chkColocated && el.chkColocated.checked) {
    const nCol = (colocatedSitesCache || buildColocatedSites(model)).length;
    displayLines.push("colocated entities (" + nCol + ")");
  }
  if (forceComp !== "None") {
    displayLines.push(
      "force diagram: " + forceComp +
      " (div " + (el.frcDiv ? el.frcDiv.value : "-") +
      ", x" + (el.frcFactor ? el.frcFactor.value : "-") + ")"
    );
    if (el.chkForceValues && el.chkForceValues.checked) displayLines.push("force values");
  }

  const lines = [
    "[File]",
    "file: " + fileName,
    "path: " + (path || "(none)"),
    "solved: " + boolOnOff(solved),
    "analysis date: " + (model.date_analysis || "-"),
    "LC: " + lc,
  ];

  if (solved) {
    const reactTotals = computeReactionTotals(model, lc);
    if (reactTotals) {
      lines.push(
        "ΣTx/Ty/Tz: "
          + formatReactionValue(reactTotals.tx) + " / "
          + formatReactionValue(reactTotals.ty) + " / "
          + formatReactionValue(reactTotals.tz) + " kN",
        "ΣRx/Ry/Rz: "
          + formatReactionValue(reactTotals.rx) + " / "
          + formatReactionValue(reactTotals.ry) + " / "
          + formatReactionValue(reactTotals.rz) + " kNm"
      );
    } else {
      lines.push("reactions: (none for this LC)");
    }
  }

  lines.push(
    "nodes: " + (model.nodes ? model.nodes.length : 0),
    "elements: " + (model.elements ? model.elements.length : 0),
  );
  if (isAdvancedGui()) {
    lines.push(
      "Diaphragm members: " + (model.membrane_elements ? model.membrane_elements.length : 0),
      "Wood walls: " + (model.wood_rated_walls ? model.wood_rated_walls.length : 0),
    );
  }
  lines.push(
    "supports: " + supports,
    "point loads: " + pointLoads,
    "element loads: " + elemLoads,
  );

  if (displayLines.length > 0) {
    lines.push(
      "",
      "[Display]",
      ...displayLines
    );
  }

  lines.push(
    "",
    "[Options]",
    "load arrow scale: " + Number(viewerOptions.loadArrowSize).toFixed(1),
    "reaction arrow scale: " + Number(viewerOptions.reactionArrowSize).toFixed(1),
    "load label scale: " + Number(viewerOptions.loadLabelSize).toFixed(0),
    "reaction label scale: " + Number(viewerOptions.reactionLabelSize).toFixed(0),
  );

  el.viewerInfoOverlay.textContent = lines.join("\n");
}

function applyZUpView() {
  if (!camera) return;
  camera.up.set(0, 0, 1);
}

function modelCenterAndSpan(model) {
  const b = model && model.bounds;
  if (!b) {
    const target = controls ? controls.target : new THREE.Vector3();
    return { center: target.clone(), span: 10 };
  }
  return {
    center: new THREE.Vector3(
      0.5 * (b[0] + b[1]),
      0.5 * (b[2] + b[3]),
      0.5 * (b[4] + b[5]),
    ),
    span: Math.max(b[1] - b[0], b[3] - b[2], b[5] - b[4], 1.0),
  };
}

function applyOrthoProjection() {
  if (!(camera instanceof THREE.OrthographicCamera)) return;
  const w = el.viewport ? el.viewport.clientWidth : 1;
  const h = el.viewport ? el.viewport.clientHeight : 1;
  const aspect = (w || 1) / (h || 1);
  camera.left = -orthoViewHeight * aspect / 2;
  camera.right = orthoViewHeight * aspect / 2;
  camera.top = orthoViewHeight / 2;
  camera.bottom = -orthoViewHeight / 2;
  camera.updateProjectionMatrix();
}

function updateViewProjectionUi() {
  if (!el.btnViewProjection) return;
  const parallel = cameraProjectionMode === "parallel";
  el.btnViewProjection.textContent = parallel ? "View: Parallel" : "View: Perspective";
  el.btnViewProjection.classList.toggle("active", parallel);
  el.btnViewProjection.title = parallel
    ? "Switch to perspective view"
    : "Switch to parallel (axonometric) view";
}

function updateViewPresetUi(name) {
  if (!el.viewPreset) return;
  el.viewPreset.value = name && STANDARD_VIEWS[name] ? name : "";
}

function setCameraProjectionMode(mode, options) {
  const opts = options || {};
  if (!camera || !controls || mode === cameraProjectionMode) return;

  const position = camera.position.clone();
  const target = controls.target.clone();
  const up = camera.up.clone();
  const near = camera.near;
  const far = camera.far;
  let nextOrthoHeight = orthoViewHeight;

  if (opts.preserveView !== false) {
    const dist = position.distanceTo(target);
    if (mode === "parallel") {
      if (camera instanceof THREE.PerspectiveCamera) {
        const fovRad = camera.fov * Math.PI / 180;
        nextOrthoHeight = 2 * Math.tan(fovRad / 2) * dist;
      }
    } else if (camera instanceof THREE.OrthographicCamera) {
      nextOrthoHeight = orthoViewHeight / Math.max(camera.zoom, 1e-6);
    }
  } else if (opts.orthoViewHeight != null) {
    nextOrthoHeight = opts.orthoViewHeight;
  }

  const w = el.viewport ? el.viewport.clientWidth : 1;
  const h = el.viewport ? el.viewport.clientHeight : 1;
  const aspect = (w || 1) / (h || 1);

  if (mode === "parallel") {
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, near, far);
    orthoViewHeight = nextOrthoHeight;
    camera.zoom = 1;
    applyOrthoProjection();
  } else {
    camera = new THREE.PerspectiveCamera(CAMERA_FOV, aspect, near, far);
    camera.updateProjectionMatrix();
  }

  camera.position.copy(position);
  camera.up.copy(up);
  controls.object = camera;
  cameraProjectionMode = mode;
  controls.update();
  updateViewProjectionUi();
}

function toggleCameraProjectionMode() {
  setCameraProjectionMode(cameraProjectionMode === "parallel" ? "perspective" : "parallel");
}

function setStandardView(name) {
  const view = STANDARD_VIEWS[name];
  if (!view || !camera || !controls) return;

  const { center, span } = modelCenterAndSpan(currentModel);
  controls.target.copy(center);
  camera.position.copy(center).add(view.offset(span));
  camera.up.copy(view.up());
  camera.near = span * 0.001;
  camera.far = span * 100;

  if (camera instanceof THREE.OrthographicCamera) {
    orthoViewHeight = span * 1.35;
    camera.zoom = 1;
    applyOrthoProjection();
  } else {
    const w = el.viewport ? el.viewport.clientWidth : 1;
    const h = el.viewport ? el.viewport.clientHeight : 1;
    camera.aspect = (w || 1) / (h || 1);
    camera.updateProjectionMatrix();
  }

  controls.update();
  updateViewPresetUi(name);
}

function initThree() {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(COLORS.background);

  const w = el.viewport.clientWidth;
  const h = el.viewport.clientHeight;
  camera = new THREE.PerspectiveCamera(CAMERA_FOV, w / h, 0.01, 1e6);
  applyZUpView();
  camera.position.set(8, -8, 6);
  cameraProjectionMode = "perspective";

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(window.devicePixelRatio);
  el.viewport.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.2;
  controls.target.set(0, 0, 0);
  updateViewProjectionUi();

  const amb = new THREE.AmbientLight(0xffffff, 0.65);
  scene.add(amb);
  const dir = new THREE.DirectionalLight(0xffffff, 0.55);
  dir.position.set(5, 10, 7);
  scene.add(dir);

  modelGroup = new THREE.Group();
  scene.add(modelGroup);
  selectionGroup = new THREE.Group();
  scene.add(selectionGroup);
  distanceGroup = new THREE.Group();
  scene.add(distanceGroup);
  labelGroup = new THREE.Group();
  scene.add(labelGroup);
  forceGroup = new THREE.Group();
  scene.add(forceGroup);
  forceLabelGroup = new THREE.Group();
  scene.add(forceLabelGroup);
  windGroup = new THREE.Group();
  scene.add(windGroup);
  windLabelGroup = new THREE.Group();
  scene.add(windLabelGroup);
  practiceCenterGroup = new THREE.Group();
  scene.add(practiceCenterGroup);
  colocatedGroup = new THREE.Group();
  scene.add(colocatedGroup);
  axesGroup = new THREE.Group();
  scene.add(axesGroup);

  window.addEventListener("resize", onResize);
  applyViewerInteractionControls();
  animate();
}

function onResize() {
  const w = el.viewport.clientWidth;
  const h = el.viewport.clientHeight;
  if (camera instanceof THREE.PerspectiveCamera) {
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  } else if (camera instanceof THREE.OrthographicCamera) {
    applyOrthoProjection();
  }
  renderer.setSize(w, h);
  updateWideLineResolution(w, h);
}

function updateWideLineResolution(w, h) {
  for (const mat of wideLineMaterials) {
    mat.resolution.set(w, h);
  }
}

function clearWideLineMaterials() {
  wideLineMaterials.clear();
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  updateSupportGizmoPositions();
  updateReactionForceDisplay();
  updateNodeLabelPositions();
  updateElemLabelPositions();
  updateForceLabelPositions();
  renderer.render(scene, camera);
}

function nodeMap(model) {
  const m = {};
  for (const n of model.nodes) {
    m[n.id] = n;
  }
  return m;
}

function nodePosition(n, model, lc, defFac, deformed, component) {
  let x = n.x, y = n.y, z = n.z;
  if (deformed && n.disps && n.disps[String(lc)]) {
    const d = n.disps[String(lc)];
    const dispComponent = component == null ? currentDispComponent() : component;
    const dv = displacementVectorForComponent(new THREE.Vector3(d[0], d[1], d[2]), dispComponent);
    x += dv.x * defFac;
    y += dv.y * defFac;
    z += dv.z * defFac;
  }
  return new THREE.Vector3(x, y, z);
}

function normalizeDispComponent(component) {
  return Object.prototype.hasOwnProperty.call(DISP_COMPONENTS, component) ? component : "mag";
}

function currentDispComponent() {
  return normalizeDispComponent(el.dispComponent ? el.dispComponent.value : RESULTS_DISPLAY_DEFAULTS.dispComponent);
}

function dispComponentLabel(component) {
  const comp = DISP_COMPONENTS[normalizeDispComponent(component)];
  return comp.label;
}

function displacementComponentValue(vec, component) {
  const comp = DISP_COMPONENTS[normalizeDispComponent(component)];
  if (comp.index == null) return vec.length();
  return vec.getComponent(comp.index);
}

function displacementVectorForComponent(vec, component) {
  const comp = DISP_COMPONENTS[normalizeDispComponent(component)];
  if (comp.index == null) return vec.clone();
  const out = new THREE.Vector3(0, 0, 0);
  out.setComponent(comp.index, vec.getComponent(comp.index));
  return out;
}

function nodeDispValue(n, lc, component) {
  if (!n.disps || !n.disps[String(lc)]) return 0;
  const d = n.disps[String(lc)];
  return displacementComponentValue(new THREE.Vector3(d[0], d[1], d[2]), component);
}

function dispValueRange(model, lc, component) {
  let min = Infinity;
  let max = -Infinity;
  for (const n of model.nodes || []) {
    const v = nodeDispValue(n, lc, component);
    if (v < min) min = v;
    if (v > max) max = v;
  }
  if (!isFinite(max)) return { min: 0, max: 0 };
  if (max - min < 1e-15) max = min + 1e-15;
  return { min: min, max: max };
}

function maxDispNodeInfo(model, lc, defFac, component) {
  let best = null;
  for (const n of model.nodes || []) {
    const value = nodeDispValue(n, lc, component);
    const absValue = Math.abs(value);
    if (!best || absValue > best.absValue) {
      const p0 = nodePosition(n, model, lc, defFac, false);
      const p1 = nodePosition(n, model, lc, defFac, true, component);
      best = { node: n, value: value, absValue: absValue, p0: p0, p1: p1 };
    }
  }
  if (!best) return null;
  return best;
}

function nodeDispVector(n, lc, defFac) {
  if (!n.disps || !n.disps[String(lc)]) return new THREE.Vector3(0, 0, 0);
  const d = n.disps[String(lc)];
  return new THREE.Vector3(d[0], d[1], d[2]);
}

function globalVecToLocal(v, elem) {
  if (!elem || !elem.vx || !elem.vy || !elem.vz) return v.clone();
  const vx = new THREE.Vector3().fromArray(elem.vx);
  const vy = new THREE.Vector3().fromArray(elem.vy);
  const vz = new THREE.Vector3().fromArray(elem.vz);
  return new THREE.Vector3(v.dot(vx), v.dot(vy), v.dot(vz));
}

// Local displacement at t (0..1) of a Timoshenko beam element.
// dl: local end displacements [u,v,w,rx,ry,rz] x 2 where ry/rz are the
// member-end bending rotations. The homogeneous part is exact for end
// displacements/rotations with shear deformation (PHI); the particular part
// adds the fixed-fixed deflection under the mean local member load.
function beamDispLocalAtT(dl, L, t, shape) {
  const u1 = dl[0], v1 = dl[1], w1 = dl[2];
  const ry1 = dl[4], rz1 = dl[5];
  const u2 = dl[6], v2 = dl[7], w2 = dl[8];
  const ry2 = dl[10], rz2 = dl[11];
  const s = shape || {};
  const t2 = t * t, t3 = t2 * t, tt = t - t2;

  function plane(d1, th1, d2, th2, phi) {
    const p = isFinite(phi) && phi > 0 ? phi : 0;
    const k = 1 / (1 + p);
    return k * (
      (1 - 3 * t2 + 2 * t3 + p * (1 - t)) * d1 +
      L * (t - 2 * t2 + t3 + 0.5 * p * tt) * th1 +
      (3 * t2 - 2 * t3 + p * t) * d2 +
      L * (-t2 + t3 - 0.5 * p * tt) * th2
    );
  }
  function particular(q, EI, phi) {
    if (!isFinite(q) || q === 0 || !isFinite(EI) || EI <= 0) return 0;
    const p = isFinite(phi) && phi > 0 ? phi : 0;
    return q * Math.pow(L, 4) / (24 * EI) * (tt * tt + p * tt);
  }

  const wl = s.wl;
  const qy = wl ? 0.5 * (wl[1] + wl[4]) : 0;
  const qz = wl ? 0.5 * (wl[2] + wl[5]) : 0;
  const u = (1 - t) * u1 + t * u2;
  const v = plane(v1, rz1, v2, rz2, s.phiY) + particular(qy, s.EIz, s.phiY);
  const w = plane(w1, -ry1, w2, -ry2, s.phiZ) + particular(qz, s.EIy, s.phiZ);
  return new THREE.Vector3(u, v, w);
}

// Replace nodal rotations by the member-end bending rotations reported by
// the solver (they differ behind EJNT springs/pins), and collect the data
// for the Timoshenko interpolation.
function elemShapeData(dl, e, lcKey) {
  const out = dl.slice();
  const er = e && e.end_rots && e.end_rots[lcKey];
  if (er && er.length >= 4) {
    out[5] = er[0];
    out[11] = er[1];
    out[4] = er[2];
    out[10] = er[3];
  }
  const wl = e && e.local_wloads && e.local_wloads[lcKey];
  return {
    dl: out,
    shape: { phiY: e.PHIy, phiZ: e.PHIz, EIy: e.EIy, EIz: e.EIz, wl: wl || null },
  };
}

function elemDeformedPoints(e, n0, n1, model, lc, defFac, nDiv, component) {
  const lcKey = String(lc);
  const p0u = nodePosition(n0, model, lc, defFac, false);
  const p1u = nodePosition(n1, model, lc, defFac, false);

  const hasShape =
    e.vx && e.vy && e.vz && e.len && e.len > 1e-12 &&
    n0.disps && n1.disps && n0.disps[lcKey] && n1.disps[lcKey];

  if (!hasShape) {
    const p0d = nodePosition(n0, model, lc, defFac, true, component);
    const p1d = nodePosition(n1, model, lc, defFac, true, component);
    return {
      pts: [p0d, p1d],
      values: [nodeDispValue(n0, lc, component), nodeDispValue(n1, lc, component)],
    };
  }

  const d0g = n0.disps[lcKey];
  const d1g = n1.disps[lcKey];
  const t0l = globalVecToLocal(new THREE.Vector3(d0g[0], d0g[1], d0g[2]), e);
  const r0l = globalVecToLocal(new THREE.Vector3(d0g[3], d0g[4], d0g[5]), e);
  const t1l = globalVecToLocal(new THREE.Vector3(d1g[0], d1g[1], d1g[2]), e);
  const r1l = globalVecToLocal(new THREE.Vector3(d1g[3], d1g[4], d1g[5]), e);
  const dl = [
    t0l.x, t0l.y, t0l.z, r0l.x, r0l.y, r0l.z,
    t1l.x, t1l.y, t1l.z, r1l.x, r1l.y, r1l.z,
  ];
  const sd = elemShapeData(dl, e, lcKey);

  const pts = [];
  const values = [];
  for (let i = 0; i <= nDiv; i++) {
    const t = i / nDiv;
    const pl = beamDispLocalAtT(sd.dl, e.len, t, sd.shape);
    const pg = localVecToGlobal(pl, e);
    const pgDisplay = displacementVectorForComponent(pg, component);
    const pBase = elemPointAlong(p0u, p1u, t);
    pts.push(pBase.clone().addScaledVector(pgDisplay, defFac));
    values.push(displacementComponentValue(pg, component));
  }
  return { pts: pts, values: values };
}

function maxDispPointInfo(model, lc, defFac, nm, component) {
  let best = maxDispNodeInfo(model, lc, defFac, component);
  const nDiv = 20;
  for (const e of model.elements || []) {
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1 || !n0.disps || !n1.disps) continue;
    if (!n0.disps[String(lc)] || !n1.disps[String(lc)]) continue;
    if (!e.vx || !e.vy || !e.vz || !e.len || e.len <= 1e-12) continue;

    const d0g = n0.disps[String(lc)];
    const d1g = n1.disps[String(lc)];
    const t0 = new THREE.Vector3(d0g[0], d0g[1], d0g[2]);
    const r0 = new THREE.Vector3(d0g[3], d0g[4], d0g[5]);
    const t1 = new THREE.Vector3(d1g[0], d1g[1], d1g[2]);
    const r1 = new THREE.Vector3(d1g[3], d1g[4], d1g[5]);

    const t0l = globalVecToLocal(t0, e);
    const r0l = globalVecToLocal(r0, e);
    const t1l = globalVecToLocal(t1, e);
    const r1l = globalVecToLocal(r1, e);
    const dl = [
      t0l.x, t0l.y, t0l.z, r0l.x, r0l.y, r0l.z,
      t1l.x, t1l.y, t1l.z, r1l.x, r1l.y, r1l.z,
    ];
    const sd = elemShapeData(dl, e, String(lc));

    const p0u = nodePosition(n0, model, lc, defFac, false);
    const p1u = nodePosition(n1, model, lc, defFac, false);

    for (let i = 1; i < nDiv; i++) {
      const t = i / nDiv;
      const pl = beamDispLocalAtT(sd.dl, e.len, t, sd.shape);
      const pg = localVecToGlobal(pl, e);
      const value = displacementComponentValue(pg, component);
      const absValue = Math.abs(value);
      if (!best || absValue > best.absValue) {
        const pBase = elemPointAlong(p0u, p1u, t);
        const pgDisplay = displacementVectorForComponent(pg, component);
        best = { value: value, absValue: absValue, p0: pBase, p1: pBase.clone().addScaledVector(pgDisplay, defFac), elem: e, t: t };
      }
    }
  }
  return best;
}

function dispContourColor(t) {
  const c = new THREE.Color();
  const u = Math.min(1, Math.max(0, t));
  c.setHSL((1 - u) * 0.66, 1.0, 0.5);
  return c;
}

const DISP_CONTOUR_TICK_FRACTIONS = [0.25, 0.5, 0.75];

function formatDispInputValue(meters) {
  const mm = meters * 1e3;
  const av = Math.abs(mm);
  if (av < 1e-6) return "0";
  if (av < 0.01) return mm.toFixed(3);
  if (av < 1) return mm.toFixed(2);
  if (av < 100) return mm.toFixed(1);
  return mm.toFixed(0);
}

function formatDispTickValueMm(meters) {
  const mm = meters * 1e3;
  const av = Math.abs(mm);
  if (av < 1e-6) return "0";
  if (av < 1) return mm.toFixed(2);
  if (av < 100) return mm.toFixed(1);
  return mm.toFixed(0);
}

function formatDispAbsValue(v) {
  const mm = v * 1e3;
  if (Math.abs(mm) < 1e-6) return "0.0 mm";
  return mm.toFixed(1) + " mm";
}

function dispContourGradientCss() {
  const stops = [];
  const n = 16;
  for (let i = 0; i < n; i++) {
    const t = n > 1 ? i / (n - 1) : 0;
    const c = dispContourColor(t);
    stops.push(colorHex(c.getHex()) + " " + (t * 100) + "%");
  }
  return "linear-gradient(to top, " + stops.join(", ") + ")";
}

function syncDispContourInputs(autoRange, lc, defFac, component, force) {
  if (!el.dispContourMin || !el.dispContourMax) return;
  const key = String(lc) + ":" + defFac + ":" + normalizeDispComponent(component);
  if (force || dispContourScaleKey !== key) {
    dispContourScaleKey = key;
    el.dispContourMin.value = formatDispInputValue(autoRange.min);
    el.dispContourMax.value = formatDispInputValue(autoRange.max);
  }
}

function getDispContourDisplayRange() {
  let minMm = parseFloat(el.dispContourMin && el.dispContourMin.value);
  let maxMm = parseFloat(el.dispContourMax && el.dispContourMax.value);
  if (!isFinite(minMm)) minMm = 0;
  if (!isFinite(maxMm)) maxMm = minMm + 1e-12;
  if (maxMm < minMm) {
    const swap = maxMm;
    maxMm = minMm;
    minMm = swap;
  }
  if (maxMm - minMm < 1e-12) maxMm = minMm + 1e-12;
  return { min: minMm / 1e3, max: maxMm / 1e3 };
}

function updateDispContourTicks(rangeMeters) {
  if (!el.dispLegendTicks) return;
  el.dispLegendTicks.replaceChildren();
  if (!rangeMeters) return;
  const span = rangeMeters.max - rangeMeters.min;
  for (const frac of DISP_CONTOUR_TICK_FRACTIONS) {
    const valueM = rangeMeters.min + frac * span;
    const tick = document.createElement("div");
    tick.className = "viewport-disp-legend-tick";
    tick.style.bottom = (frac * 100) + "%";

    const label = document.createElement("span");
    label.className = "viewport-disp-legend-tick-label";
    label.textContent = formatDispTickValueMm(valueM);

    const line = document.createElement("span");
    line.className = "viewport-disp-legend-tick-line";
    line.setAttribute("aria-hidden", "true");

    tick.append(label, line);
    el.dispLegendTicks.append(tick);
  }
}

function dispContourT(mag, range) {
  const span = range.max - range.min;
  if (span < 1e-15) return 0;
  return Math.min(1, Math.max(0, (mag - range.min) / span));
}

function updateDispContourOverlay(visible, autoRange, lc, defFac, component, syncInputs) {
  if (!el.dispLegendOverlay) return;
  if (!visible || !autoRange || lc == null) {
    el.dispLegendOverlay.classList.remove("visible");
    el.dispLegendOverlay.hidden = true;
    dispContourScaleKey = null;
    updateDispContourTicks(null);
    return;
  }

  const dispComponent = normalizeDispComponent(component);
  if (syncInputs) syncDispContourInputs(autoRange, lc, defFac, dispComponent, false);

  el.dispLegendOverlay.hidden = false;
  el.dispLegendOverlay.classList.add("visible");
  if (el.dispLegendTitle) {
    el.dispLegendTitle.textContent = dispComponentLabel(dispComponent) + " (mm, ×" + defFac + ")";
  }
  if (el.dispLegendLc) {
    el.dispLegendLc.textContent = "LC " + lc;
  }
  if (el.dispLegendBar) {
    el.dispLegendBar.style.background = dispContourGradientCss();
  }
  updateDispContourTicks(getDispContourDisplayRange());
}

function applyDispContourAutoRange() {
  if (!currentModel || !analysisComplete(currentModel)) return;
  const lc = el.lcSelect.value;
  const defFac = parseFloat(el.defFactor.value) || 0;
  const dispComponent = currentDispComponent();
  const autoRange = dispValueRange(currentModel, lc, dispComponent);
  dispContourScaleKey = null;
  syncDispContourInputs(autoRange, lc, defFac, dispComponent, true);
  onResultsDisplayChanged();
  rebuildScene();
}

function addDispContourLineSegments(positions, colors, group) {
  const lineW = dispContourLineWidthPx();
  if (lineW <= 1.01) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    const mat = new THREE.LineBasicMaterial({
      vertexColors: true,
      linewidth: 1,
      depthTest: false,
      depthWrite: false,
    });
    const lines = new THREE.LineSegments(geo, mat);
    lines.frustumCulled = false;
    lines.renderOrder = 31;
    group.add(lines);
    return;
  }

  const segCount = positions.length / 6;
  for (let i = 0; i < segCount; i++) {
    const base = i * 6;
    const pts = positions.slice(base, base + 6);
    const r = (colors[base] + colors[base + 3]) * 0.5;
    const g = (colors[base + 1] + colors[base + 4]) * 0.5;
    const b = (colors[base + 2] + colors[base + 5]) * 0.5;
    const hex = (Math.round(r * 255) << 16) | (Math.round(g * 255) << 8) | Math.round(b * 255);
    addWideLineSegmentsFromPts(pts, hex, group, 31, lineW, ALPHA.opaque, "overlay");
  }
}

function addMaxDisplacementMarker(model, lc, defFac, span, deformed, component, group, labelGroup) {
  if (!deformed) return;
  const nm = nodeMap(model);
  const info = maxDispPointInfo(model, lc, defFac, nm, component);
  if (!info || info.absValue < 1e-12 || !info.p0 || !info.p1) return;

  const p0 = info.p0.clone();
  const p1 = info.p1.clone();
  const dir = p1.clone().sub(p0);
  const dlen = dir.length();
  if (dlen < 1e-12) return;
  const udir = dir.clone().multiplyScalar(1 / dlen);

  const r = Math.max(span * 0.01, 0.02) * 0.4;
  const sphere = new THREE.Mesh(
    new THREE.SphereGeometry(r, 18, 12),
    new THREE.MeshBasicMaterial({ color: 0xff0000, depthTest: true })
  );
  sphere.position.copy(p1);
  sphere.renderOrder = 14;
  group.add(sphere);

  const geo = new THREE.BufferGeometry().setFromPoints([p0, p1]);
  const mat = new THREE.LineDashedMaterial({
    color: 0xff0000,
    dashSize: Math.max(span * 0.02, 0.02),
    gapSize: Math.max(span * 0.012, 0.012),
    depthTest: true,
  });
  const dashed = new THREE.Line(geo, mat);
  dashed.computeLineDistances();
  dashed.frustumCulled = false;
  dashed.renderOrder = 13;
  group.add(dashed);

  const labelPos = p1.clone().addScaledVector(udir, span * 0.012);
  addReactionValueLabel(
    dispComponentLabel(component) + "=" + formatDispAbsValue(info.value),
    labelPos,
    span,
    Math.max(reactionLabelScaleFactor(), 0.03) * 0.4,
    labelGroup,
    "#ff0000"
  );
}

function clearGroup(g) {
  while (g.children.length > 0) {
    const c = g.children[0];
    g.remove(c);
    if (c.geometry) c.geometry.dispose();
    if (c.material) {
      if (Array.isArray(c.material)) c.material.forEach((m) => m.dispose());
      else c.material.dispose();
    }
  }
}

function modelSectionMap(model) {
  const out = {};
  for (const s of model.sections || []) out[s.id] = s;
  return out;
}

function sectionDimsMeters(section) {
  if (!section || !Array.isArray(section.dims) || section.dims.length === 0) return null;
  const dims = [];
  for (const d of section.dims) {
    const v = Number(d) * 1e-3; // mm -> m
    if (!isFinite(v) || v <= 0) return null;
    dims.push(v);
  }
  return dims;
}

function sanitizeHexColor(value, fallback) {
  const fb = fallback || "#c9cdd3";
  const s = String(value || "").trim();
  return /^#[0-9a-fA-F]{6}$/.test(s) ? s.toLowerCase() : fb;
}

function sectionProfileKey(type, dims) {
  const ds = dims.map(function (v) { return v.toFixed(6); }).join(",");
  return String(type) + ":" + ds;
}

function makeRectShape(width, height) {
  const hw = width * 0.5;
  const hh = height * 0.5;
  const shape = new THREE.Shape();
  shape.moveTo(-hw, -hh);
  shape.lineTo(hw, -hh);
  shape.lineTo(hw, hh);
  shape.lineTo(-hw, hh);
  shape.lineTo(-hw, -hh);
  return shape;
}

function makeSectionShape(type, dims) {
  if (type === 0) {
    if (dims.length < 2) return null;
    return makeRectShape(dims[0], dims[1]);
  }
  if (type === 1) {
    if (dims.length < 1) return null;
    const r = dims[0] * 0.5;
    if (r <= 0) return null;
    const shape = new THREE.Shape();
    shape.absarc(0, 0, r, 0, Math.PI * 2, false);
    return shape;
  }
  if (type === 2) {
    if (dims.length < 4) return null;
    const h = dims[0], w = dims[1], tw = dims[2], tf = dims[3];
    if (h <= 0 || w <= 0 || tw <= 0 || tf <= 0) return null;
    if (tw >= w || tf * 2 >= h) return null;
    const shape = makeRectShape(w, h);
    const hw = w * 0.5;
    const hh = h * 0.5;
    const webHalf = tw * 0.5;
    const clearH = h - 2 * tf;
    const holeLeft = new THREE.Path();
    holeLeft.moveTo(-hw, -clearH * 0.5);
    holeLeft.lineTo(-webHalf, -clearH * 0.5);
    holeLeft.lineTo(-webHalf, clearH * 0.5);
    holeLeft.lineTo(-hw, clearH * 0.5);
    holeLeft.lineTo(-hw, -clearH * 0.5);
    const holeRight = new THREE.Path();
    holeRight.moveTo(webHalf, -clearH * 0.5);
    holeRight.lineTo(hw, -clearH * 0.5);
    holeRight.lineTo(hw, clearH * 0.5);
    holeRight.lineTo(webHalf, clearH * 0.5);
    holeRight.lineTo(webHalf, -clearH * 0.5);
    shape.holes.push(holeLeft, holeRight);
    return shape;
  }
  if (type === 3) {
    if (dims.length < 2) return null;
    const d = dims[0], t = dims[1];
    const ro = d * 0.5;
    const ri = ro - t;
    if (ro <= 0 || ri <= 1e-6) return null;
    const shape = new THREE.Shape();
    shape.absarc(0, 0, ro, 0, Math.PI * 2, false);
    const hole = new THREE.Path();
    hole.absarc(0, 0, ri, 0, Math.PI * 2, true);
    shape.holes.push(hole);
    return shape;
  }
  if (type === 4) {
    if (dims.length < 4) return null;
    const h = dims[0], w = dims[1], tw = dims[2], tf = dims[3];
    if (h <= 0 || w <= 0 || tw <= 0 || tf <= 0) return null;
    const innerW = w - 2 * tw;
    const innerH = h - 2 * tf;
    if (innerW <= 1e-6 || innerH <= 1e-6) return null;
    const shape = makeRectShape(w, h);
    const hole = makeRectShape(innerW, innerH);
    shape.holes.push(hole);
    return shape;
  }
  return null;
}

function sectionProfile(type, dims) {
  const key = sectionProfileKey(type, dims);
  if (_sectionProfileCache.has(key)) return _sectionProfileCache.get(key);
  const shape = makeSectionShape(type, dims);
  _sectionProfileCache.set(key, shape || null);
  return shape || null;
}

function sectionSolidGeometry(type, dims) {
  const key = sectionProfileKey(type, dims);
  if (_sectionSolidGeometryCache.has(key)) return _sectionSolidGeometryCache.get(key);
  const profile = sectionProfile(type, dims);
  if (!profile) {
    _sectionSolidGeometryCache.set(key, null);
    return null;
  }
  const geo = new THREE.ExtrudeGeometry(profile, {
    steps: 1,
    depth: 1,
    bevelEnabled: false,
    curveSegments: SECTION_SOLID_SEGMENTS,
  });
  // Profile (x=B, y=H, extrude z) -> element local (vy, vz, vx), matching the
  // solver where H lies along local z (Iy = B*H^3/12 is the strong axis).
  geo.applyMatrix4(new THREE.Matrix4().set(
    0, 0, 1, 0,
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 0, 1,
  ));
  // Normalize local member axis to [0, 1] so start/end can be mapped robustly.
  geo.computeBoundingBox();
  if (geo.boundingBox) {
    const minX = geo.boundingBox.min.x;
    const maxX = geo.boundingBox.max.x;
    const spanX = maxX - minX;
    if (spanX > 1e-9) {
      geo.translate(-minX, 0, 0);
      geo.scale(1 / spanX, 1, 1);
    }
  }
  geo.computeVertexNormals();
  _sectionSolidGeometryCache.set(key, geo);
  return geo;
}

function sectionSolidEndpointMismatch(p0, p1, basis, length) {
  const end = p0.clone().addScaledVector(basis.vx, length);
  const tol = Math.max(length * 1e-4, 1e-6);
  return end.distanceToSquared(p1) > tol * tol;
}

const _sectionSolidExportMaterial = new THREE.MeshBasicMaterial();

function forEachSectionSolidMesh(model, visitor, options) {
  if (!model || !Array.isArray(model.elements) || typeof visitor !== "function") return 0;
  const opts = options || {};
  const lc = opts.lc != null ? opts.lc : (el.lcSelect ? el.lcSelect.value : 1);
  const defFac = opts.defFac != null ? opts.defFac : 0;
  const deformed = !!opts.deformed;
  if (deformed) return 0;

  const nm = nodeMap(model);
  const sectionById = modelSectionMap(model);
  let count = 0;

  for (const e of model.elements) {
    if (!isMemberElementVisible(e.id)) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const sec = sectionById[e.section_id];
    const dims = sectionDimsMeters(sec);
    if (!sec || !dims) continue;

    const p0u = nodePosition(n0, model, lc, defFac, false);
    const p1u = nodePosition(n1, model, lc, defFac, false);
    const axis = p1u.clone().sub(p0u);
    const len = axis.length();
    if (len < 1e-8) continue;

    const geo = sectionSolidGeometry(sec.type, dims);
    if (!geo) continue;

    const basis = elementBasisVectors(e, p0u, p1u);
    if (sectionSolidEndpointMismatch(p0u, p1u, basis, len)) continue;

    const rot = new THREE.Matrix4().makeBasis(basis.vx, basis.vy, basis.vz);
    const q = new THREE.Quaternion().setFromRotationMatrix(rot);
    const mesh = new THREE.Mesh(geo, _sectionSolidExportMaterial);
    mesh.position.copy(p0u);
    mesh.quaternion.copy(q);
    mesh.scale.set(len, 1, 1);
    mesh.updateMatrixWorld(true);
    visitor(mesh, e, sec);
    count += 1;
  }
  return count;
}

function meshWorldTriangles(mesh, layerName) {
  const geo = mesh.geometry;
  const pos = geo.attributes.position;
  if (!pos) return [];
  const matrix = mesh.matrixWorld;
  const index = geo.index;
  const out = [];
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const c = new THREE.Vector3();

  function pushTri(i0, i1, i2) {
    a.fromBufferAttribute(pos, i0).applyMatrix4(matrix);
    b.fromBufferAttribute(pos, i1).applyMatrix4(matrix);
    c.fromBufferAttribute(pos, i2).applyMatrix4(matrix);
    out.push({
      layer: layerName,
      x1: a.x, y1: a.y, z1: a.z,
      x2: b.x, y2: b.y, z2: b.z,
      x3: c.x, y3: c.y, z3: c.z,
    });
  }

  if (index) {
    for (let i = 0; i < index.count; i += 3) {
      pushTri(index.getX(i), index.getX(i + 1), index.getX(i + 2));
    }
  } else {
    for (let i = 0; i < pos.count; i += 3) {
      pushTri(i, i + 1, i + 2);
    }
  }
  return out;
}

function collectSectionSolidTriangles(model) {
  const triangles = [];
  let meshCount = 0;
  forEachSectionSolidMesh(model, function (mesh, elem) {
    triangles.push.apply(triangles, meshWorldTriangles(mesh, "E" + elem.id));
    meshCount += 1;
  });
  return { triangles: triangles, meshCount: meshCount };
}

function dxfLine(code, value) {
  return String(code) + "\r\n" + String(value) + "\r\n";
}

function dxfNum(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0";
  return n.toFixed(6).replace(/-0\.000000$/, "0.000000");
}

function dxfBounds(triangles) {
  let xmin = Infinity;
  let ymin = Infinity;
  let zmin = Infinity;
  let xmax = -Infinity;
  let ymax = -Infinity;
  let zmax = -Infinity;
  triangles.forEach(function (tri) {
    [
      [tri.x1, tri.y1, tri.z1],
      [tri.x2, tri.y2, tri.z2],
      [tri.x3, tri.y3, tri.z3],
    ].forEach(function (p) {
      xmin = Math.min(xmin, p[0]);
      ymin = Math.min(ymin, p[1]);
      zmin = Math.min(zmin, p[2]);
      xmax = Math.max(xmax, p[0]);
      ymax = Math.max(ymax, p[1]);
      zmax = Math.max(zmax, p[2]);
    });
  });
  if (!Number.isFinite(xmin)) {
    return { xmin: 0, ymin: 0, zmin: 0, xmax: 1, ymax: 1, zmax: 1 };
  }
  return { xmin: xmin, ymin: ymin, zmin: zmin, xmax: xmax, ymax: ymax, zmax: zmax };
}

function buildSectionSolidsDxf(triangles) {
  const layers = { "0": true };
  triangles.forEach(function (tri) {
    layers[tri.layer] = true;
  });
  const layerNames = Object.keys(layers).sort();
  const b = dxfBounds(triangles);

  let out = "";
  out += dxfLine(999, "Structural Toolbox section solids");
  out += dxfLine(0, "SECTION");
  out += dxfLine(2, "HEADER");
  out += dxfLine(9, "$ACADVER");
  out += dxfLine(1, "AC1009");
  out += dxfLine(9, "$INSBASE");
  out += dxfLine(10, "0.0");
  out += dxfLine(20, "0.0");
  out += dxfLine(30, "0.0");
  out += dxfLine(9, "$EXTMIN");
  out += dxfLine(10, dxfNum(b.xmin));
  out += dxfLine(20, dxfNum(b.ymin));
  out += dxfLine(30, dxfNum(b.zmin));
  out += dxfLine(9, "$EXTMAX");
  out += dxfLine(10, dxfNum(b.xmax));
  out += dxfLine(20, dxfNum(b.ymax));
  out += dxfLine(30, dxfNum(b.zmax));
  out += dxfLine(0, "ENDSEC");

  out += dxfLine(0, "SECTION");
  out += dxfLine(2, "TABLES");
  out += dxfLine(0, "TABLE");
  out += dxfLine(2, "LTYPE");
  out += dxfLine(70, 1);
  out += dxfLine(0, "LTYPE");
  out += dxfLine(2, "CONTINUOUS");
  out += dxfLine(70, 64);
  out += dxfLine(3, "Solid line");
  out += dxfLine(72, 65);
  out += dxfLine(73, 0);
  out += dxfLine(40, "0.0");
  out += dxfLine(0, "ENDTAB");
  out += dxfLine(0, "TABLE");
  out += dxfLine(2, "LAYER");
  out += dxfLine(70, layerNames.length);
  layerNames.forEach(function (name) {
    out += dxfLine(0, "LAYER");
    out += dxfLine(2, name);
    out += dxfLine(70, 64);
    out += dxfLine(62, 7);
    out += dxfLine(6, "CONTINUOUS");
  });
  out += dxfLine(0, "ENDTAB");
  out += dxfLine(0, "TABLE");
  out += dxfLine(2, "STYLE");
  out += dxfLine(70, 0);
  out += dxfLine(0, "ENDTAB");
  out += dxfLine(0, "ENDSEC");

  out += dxfLine(0, "SECTION");
  out += dxfLine(2, "BLOCKS");
  out += dxfLine(0, "ENDSEC");

  out += dxfLine(0, "SECTION");
  out += dxfLine(2, "ENTITIES");
  triangles.forEach(function (tri) {
    out += dxfLine(0, "3DFACE");
    out += dxfLine(8, tri.layer);
    out += dxfLine(10, dxfNum(tri.x1));
    out += dxfLine(20, dxfNum(tri.y1));
    out += dxfLine(30, dxfNum(tri.z1));
    out += dxfLine(11, dxfNum(tri.x2));
    out += dxfLine(21, dxfNum(tri.y2));
    out += dxfLine(31, dxfNum(tri.z2));
    out += dxfLine(12, dxfNum(tri.x3));
    out += dxfLine(22, dxfNum(tri.y3));
    out += dxfLine(32, dxfNum(tri.z3));
    out += dxfLine(13, dxfNum(tri.x3));
    out += dxfLine(23, dxfNum(tri.y3));
    out += dxfLine(33, dxfNum(tri.z3));
  });
  out += dxfLine(0, "ENDSEC");
  out += dxfLine(0, "EOF");
  return out;
}

function sectionSolidDxfFilename() {
  const path = currentModelPath || "model.dat";
  const base = path.replace(/^.*[\\/]/, "").replace(/\.dat$/i, "") || "model";
  return base + "_section_solids.dxf";
}

function downloadTextFile(filename, text, mimeType) {
  const blob = new Blob([text], { type: mimeType || "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(function () { URL.revokeObjectURL(url); }, 0);
}

function exportSectionSolidsDxf() {
  if (!currentModel) {
    window.alert("モデルが読み込まれていません。");
    return;
  }
  if (el.status) el.status.textContent = "Section solid DXF を生成中…";
  if (el.btnExportSectionSolidsDxf) el.btnExportSectionSolidsDxf.disabled = true;

  window.setTimeout(function () {
    try {
      const result = collectSectionSolidTriangles(currentModel);
      if (!result.meshCount) {
        window.alert("DXF に書き出せる section solid がありません（断面形状未対応、または部材がありません）。");
        return;
      }
      const dxf = buildSectionSolidsDxf(result.triangles);
      downloadTextFile(sectionSolidDxfFilename(), dxf, "application/dxf");
      if (el.status) {
        el.status.textContent = "DXF 出力: " + result.meshCount + " 部材, "
          + result.triangles.length + " 面 (" + sectionSolidDxfFilename() + ")";
      }
    } catch (ex) {
      window.alert("DXF 出力エラー: " + ex.message);
      if (el.status) el.status.textContent = "DXF 出力エラー";
    } finally {
      if (el.btnExportSectionSolidsDxf) el.btnExportSectionSolidsDxf.disabled = !currentModel;
    }
  }, 0);
}

function elementBasisVectors(e, p0, p1) {
  const vx = p1.clone().sub(p0).normalize();
  if (e && Array.isArray(e.vy) && Array.isArray(e.vz)) {
    const vyRaw = new THREE.Vector3(e.vy[0], e.vy[1], e.vy[2]);
    const vzRaw = new THREE.Vector3(e.vz[0], e.vz[1], e.vz[2]);
    if (vyRaw.lengthSq() > 1e-10 && vzRaw.lengthSq() > 1e-10) {
      const vyProj = vyRaw.clone().addScaledVector(vx, -vyRaw.dot(vx));
      if (vyProj.lengthSq() > 1e-10) {
        const vy = vyProj.normalize();
        let vz = new THREE.Vector3().crossVectors(vx, vy).normalize();
        if (vz.dot(vzRaw) < 0) {
          vy.multiplyScalar(-1);
          vz = new THREE.Vector3().crossVectors(vx, vy).normalize();
        }
        return { vx, vy, vz };
      }
    }
  }
  let ref = new THREE.Vector3(0, 0, 1);
  if (Math.abs(vx.dot(ref)) > 0.92) ref = new THREE.Vector3(0, 1, 0);
  const vy = new THREE.Vector3().crossVectors(ref, vx).normalize();
  const vz = new THREE.Vector3().crossVectors(vx, vy).normalize();
  return { vx, vy, vz };
}

function sectionSolidRenderEnabled(model, showSectionSolids, deformed, showDispContour) {
  if (!showSectionSolids || deformed || showDispContour) return false;
  const nElem = model && model.elements ? model.elements.length : 0;
  return nElem <= SECTION_SOLID_MAX_ELEMENTS;
}

function fitCamera(model) {
  const b = model.bounds;
  if (!b) return;
  const cx = 0.5 * (b[0] + b[1]);
  const cy = 0.5 * (b[2] + b[3]);
  const cz = 0.5 * (b[4] + b[5]);
  const span = Math.max(b[1] - b[0], b[3] - b[2], b[5] - b[4], 1.0);
  applyZUpView();
  controls.target.set(cx, cy, cz);
  camera.position.set(cx + span * 1.15, cy - span * 1.15, cz + span * 0.55);
  camera.near = span * 0.001;
  camera.far = span * 100;
  if (camera instanceof THREE.OrthographicCamera) {
    orthoViewHeight = span * 1.35;
    camera.zoom = 1;
    applyOrthoProjection();
  } else {
    const w = el.viewport ? el.viewport.clientWidth : 1;
    const h = el.viewport ? el.viewport.clientHeight : 1;
    camera.aspect = (w || 1) / (h || 1);
    camera.updateProjectionMatrix();
  }
  controls.update();
  updateViewPresetUi("");
}

function captureCameraState() {
  if (!camera || !controls) return null;
  const state = {
    position: camera.position.clone(),
    target: controls.target.clone(),
    up: camera.up.clone(),
    near: camera.near,
    far: camera.far,
    projectionMode: cameraProjectionMode,
  };
  if (camera instanceof THREE.PerspectiveCamera) {
    state.fov = camera.fov;
    state.aspect = camera.aspect;
  } else if (camera instanceof THREE.OrthographicCamera) {
    state.orthoViewHeight = orthoViewHeight;
    state.zoom = camera.zoom;
  }
  return state;
}

function restoreCameraState(state) {
  if (!state || !camera || !controls) return;
  if (state.projectionMode && state.projectionMode !== cameraProjectionMode) {
    setCameraProjectionMode(state.projectionMode, {
      preserveView: false,
      orthoViewHeight: state.orthoViewHeight,
    });
  }
  camera.position.copy(state.position);
  controls.target.copy(state.target);
  if (state.up) camera.up.copy(state.up);
  camera.near = state.near;
  camera.far = state.far;
  if (camera instanceof THREE.PerspectiveCamera) {
    if (state.fov != null) camera.fov = state.fov;
    if (state.aspect != null) camera.aspect = state.aspect;
    camera.updateProjectionMatrix();
  } else if (camera instanceof THREE.OrthographicCamera) {
    if (state.orthoViewHeight != null) orthoViewHeight = state.orthoViewHeight;
    if (state.zoom != null) camera.zoom = state.zoom;
    applyOrthoProjection();
  }
  controls.update();
}

function updateWorldAxes(model) {
  clearGroup(axesGroup);
  if (!showWorldAxes) return;
  const len = worldAxesLength(model);
  const origin = new THREE.Vector3(0, 0, 0);
  const lineW = Math.max(supportLineWidthPx(), 1.5);
  const axes = [
    { dir: new THREE.Vector3(1, 0, 0), color: 0xff3333 },
    { dir: new THREE.Vector3(0, 1, 0), color: 0x33cc33 },
    { dir: new THREE.Vector3(0, 0, 1), color: 0x3366ff },
  ];
  for (const ax of axes) {
    addDirectionArrow(origin, ax.dir, len, axesGroup, ax.color, lineW);
  }
}

function buildModelScene(model) {
  clearGroup(modelGroup);
  clearGroup(labelGroup);
  clearWideLineMaterials();
  supportGizmoEntries = [];
  reactionForceEntries = [];
  nodeLabelEntries = [];
  elemLabelEntries = [];

  enrichModelReactions(model);

  const lc = el.lcSelect.value;
  const lcKey = String(lc);
  const defFac = parseFloat(el.defFactor.value) || 0;
  const dispComponent = currentDispComponent();
  const complete = analysisComplete(model);
  const deformed = el.chkDeformed.checked && complete;
  const showDispContour = el.chkDispContour && el.chkDispContour.checked && complete;
  const showSupports = !el.chkSupports || el.chkSupports.checked;
  const showEJnt = !!(el.chkEJnt && el.chkEJnt.checked);
  const showLoads = el.chkLoads.checked;
  const showLoadValues = el.chkLoadValues.checked;
  const showReactionValues = el.chkReactionValues && el.chkReactionValues.checked && complete;
  const showLabels = el.chkLabels.checked;
  const showElemLabels = el.chkElemLabels.checked;
  const showMaterial = el.chkMaterial.checked;
  const showSection = el.chkSection.checked;
  const showSectionSolids = !!(el.chkSectionSolids && el.chkSectionSolids.checked);
  const showMembrane = membraneShown();
  const showMembraneEdge = showMembrane
    && !!(el.chkMembraneEdge && el.chkMembraneEdge.checked);
  const showWoodWall = woodWallShown();
  const showWoodWallEdge = showWoodWall
    && !!(el.chkWoodWallEdge && el.chkWoodWallEdge.checked);
  const nm = nodeMap(model);
  const em = elemMap(model);
  const sectionById = modelSectionMap(model);
  const span = modelSpan(model);
  const nodeLabelScale = nodeLabelScaleFactor();
  const elemLabelScale = elemLabelScaleFactor();
  const materialLabelScale = materialLabelScaleFactor();
  const sectionLabelScale = sectionLabelScaleFactor();
  const loadLabelScale = loadLabelScaleFactor();
  const reactionLabelScale = reactionLabelScaleFactor();

  const useSectionSolids = sectionSolidRenderEnabled(
    model,
    showSectionSolids,
    deformed,
    showDispContour
  );
  const linePts = [];
  const linePtsDef = [];
  const contourPts = [];
  const contourColors = [];
  let dispAutoRange = null;
  let dispDisplayRange = null;

  if (showDispContour) {
    dispAutoRange = dispValueRange(model, lc, dispComponent);
    syncDispContourInputs(dispAutoRange, lc, defFac, dispComponent, false);
    dispDisplayRange = getDispContourDisplayRange();
    updateDispContourOverlay(true, dispAutoRange, lc, defFac, dispComponent, false);
  } else {
    updateDispContourOverlay(false, null, null, defFac, dispComponent, false);
  }

  const defDiv = 16;
  if (useSectionSolids) {
    const solidColor = sanitizeHexColor(viewerOptions.sectionSolidColor, colorHex(COLORS.element));
    const solidOpacity = clampViewerOption("sectionSolidOpacity", Number(viewerOptions.sectionSolidOpacity));
    const mat = new THREE.MeshStandardMaterial({
      color: solidColor,
      roughness: 0.85,
      metalness: 0.02,
      transparent: solidOpacity < 0.999,
      opacity: solidOpacity,
      side: THREE.DoubleSide,
    });
    forEachSectionSolidMesh(model, function (mesh) {
      mesh.material = mat;
      mesh.renderOrder = 2;
      modelGroup.add(mesh);
    }, { lc: lc, defFac: 0, deformed: false });

    for (const e of model.elements) {
      if (!isMemberElementVisible(e.id)) continue;
      const n0 = nm[e.n0];
      const n1 = nm[e.n1];
      if (!n0 || !n1) continue;
      const sec = sectionById[e.section_id];
      const dims = sectionDimsMeters(sec);
      if (!sec || !dims) {
        const p0u = nodePosition(n0, model, lc, defFac, false);
        const p1u = nodePosition(n1, model, lc, defFac, false);
        linePts.push(p0u.x, p0u.y, p0u.z, p1u.x, p1u.y, p1u.z);
        continue;
      }
      const p0u = nodePosition(n0, model, lc, defFac, false);
      const p1u = nodePosition(n1, model, lc, defFac, false);
      const geo = sectionSolidGeometry(sec.type, dims);
      if (!geo) {
        linePts.push(p0u.x, p0u.y, p0u.z, p1u.x, p1u.y, p1u.z);
        continue;
      }
      const basis = elementBasisVectors(e, p0u, p1u);
      const len = p0u.distanceTo(p1u);
      if (sectionSolidEndpointMismatch(p0u, p1u, basis, len)) {
        linePts.push(p0u.x, p0u.y, p0u.z, p1u.x, p1u.y, p1u.z);
      }
    }
    if (linePts.length > 0) {
      addWideLineSegmentsFromPts(
        linePts,
        COLORS.element,
        modelGroup,
        2,
        elementLineWidthPx(),
        ALPHA.opaque
      );
    }
  } else {
    for (const e of model.elements) {
      if (!isMemberElementVisible(e.id)) continue;
      const n0 = nm[e.n0];
      const n1 = nm[e.n1];
      if (!n0 || !n1) continue;
      const p0u = nodePosition(n0, model, lc, defFac, false);
      const p1u = nodePosition(n1, model, lc, defFac, false);
      linePts.push(p0u.x, p0u.y, p0u.z, p1u.x, p1u.y, p1u.z);

      const needCurve = (deformed && !showDispContour) || (showDispContour && deformed && dispDisplayRange);
      const curve = needCurve ? elemDeformedPoints(e, n0, n1, model, lc, defFac, defDiv, dispComponent) : null;

      if (showDispContour && dispDisplayRange) {
        if (deformed && curve) {
          for (let i = 0; i < curve.pts.length - 1; i++) {
            const a = curve.pts[i];
            const b = curve.pts[i + 1];
            contourPts.push(a.x, a.y, a.z, b.x, b.y, b.z);
            const ca = dispContourColor(dispContourT(curve.values[i], dispDisplayRange));
            const cb = dispContourColor(dispContourT(curve.values[i + 1], dispDisplayRange));
            contourColors.push(ca.r, ca.g, ca.b, cb.r, cb.g, cb.b);
          }
        } else {
          contourPts.push(p0u.x, p0u.y, p0u.z, p1u.x, p1u.y, p1u.z);
          const v0 = nodeDispValue(n0, lc, dispComponent);
          const v1 = nodeDispValue(n1, lc, dispComponent);
          const c0 = dispContourColor(dispContourT(v0, dispDisplayRange));
          const c1 = dispContourColor(dispContourT(v1, dispDisplayRange));
          contourColors.push(c0.r, c0.g, c0.b, c1.r, c1.g, c1.b);
        }
      }

      if (deformed && !showDispContour && curve) {
        for (let i = 0; i < curve.pts.length - 1; i++) {
          const a = curve.pts[i];
          const b = curve.pts[i + 1];
          linePtsDef.push(a.x, a.y, a.z, b.x, b.y, b.z);
        }
      }
    }

    if (linePts.length > 0) {
      addWideLineSegmentsFromPts(
        linePts,
        COLORS.element,
        modelGroup,
        2,
        elementLineWidthPx(),
        (deformed || showDispContour) ? ALPHA.elementGhost : ALPHA.opaque
      );
    }

    if (showDispContour && contourPts.length > 0) {
      addDispContourLineSegments(contourPts, contourColors, modelGroup);
    } else if (deformed && linePtsDef.length > 0) {
      addWideLineSegmentsFromPts(
        linePtsDef,
        COLORS.deform,
        modelGroup,
        30,
        elementLineWidthPx(),
        ALPHA.opaque,
        "overlay"
      );
    }
  }

  const nodePts = [];
  for (const n of model.nodes) {
    if (!isNodeVisible(n.id)) continue;
    const p = nodePosition(n, model, lc, defFac, deformed);
    nodePts.push(p.x, p.y, p.z);
  }
  if (nodePts.length > 0) {
    const ngeo = new THREE.BufferGeometry();
    ngeo.setAttribute("position", new THREE.Float32BufferAttribute(nodePts, 3));
    const nmat = nodePointsMaterial({
      color: COLORS.node,
      size: nodeMarkerSize(model),
      sizeAttenuation: true,
    });
    modelGroup.add(new THREE.Points(ngeo, nmat));
  }

  addMaxDisplacementMarker(model, lc, defFac, span, deformed, dispComponent, modelGroup, labelGroup);

  const supSize = supportGizmoSize(model);
  if (showSupports) {
    for (const s of model.supports) {
      const n = nm[s.node];
      if (!n || !isNodeVisible(n.id)) continue;
      const p = nodePosition(n, model, lc, defFac, deformed);
      const sp = addSupportDisc(
        supportGizmoCenter(p, model, supSize, camera, renderer),
        s.fixed, supSize, modelGroup
      );
      supportGizmoEntries.push({ nodePos: p, gizmoRadius: supSize, sprite: sp });
    }
  }
  if (showEJnt) {
    drawEJntMarkers(model, {
      lc,
      defFac,
      deformed,
      nm,
      group: modelGroup,
    });
  }

  if (showMembrane) {
    drawMembraneElements(model, {
      lc,
      defFac,
      deformed,
      nm,
      group: modelGroup,
      showEdge: showMembraneEdge,
    });
  }

  if (showWoodWall) {
    drawWoodRatedWalls(model, {
      lc,
      defFac,
      deformed,
      nm,
      group: modelGroup,
      showEdge: showWoodWallEdge,
    });
  }

  if (showLoads) {
    const arrowBase = loadArrowLength(model);
    const maxPMag = maxPointLoadMag(model, lc);
    const maxWMag = maxElementLoadMag(model, lc);

    if (model.point_loads && shouldDrawPointLoad()) {
      for (const l of model.point_loads) {
        if (String(l.lc) !== String(lc)) continue;
        const n = nm[l.node];
        if (!n || !isNodeVisible(n.id)) continue;
        const p = nodePosition(n, model, lc, defFac, deformed);
        const fx = l.px, fy = l.py, fz = l.pz;
        const mag = Math.sqrt(fx * fx + fy * fy + fz * fz);
        if (mag < 1e-9) continue;
        const dir = new THREE.Vector3(fx / mag, fy / mag, fz / mag);
        const len = scaledReactionArrowLength(arrowBase, mag, maxPMag);
        const tip = addLoadArrow(p, dir, len, modelGroup);
        if (showLoadValues && tip) {
          const labelText = formatLoadPointValue(l, dir);
          if (labelText) {
            addLoadValueLabel(
              labelText,
              loadValueLabelPoint(p, tip, span, loadLabelScale),
              span,
              loadLabelScale,
              labelGroup
            );
          }
        }
      }
    }

    drawElementInputLoads(model, {
      lc,
      defFac,
      deformed,
      span,
      nm,
      em,
      arrowBase,
      maxWMag,
      showValues: showLoadValues,
      loadLabelScale,
    });

    drawDiaphragmInputLoads(model, {
      lc,
      defFac,
      deformed,
      span,
      nm,
      arrowBase,
      maxWMag: Math.max(maxWMag, maxDiaphragmLoadMag(model, lc)),
      showValues: showLoadValues,
      loadLabelScale,
    });
  }

  const showReactionArrows = complete && el.chkReactions && el.chkReactions.checked;
  const showReactionLabels = complete && (
    el.chkReactionValues && el.chkReactionValues.checked
  );

  drawSupportReactions(model, {
    lc,
    lcKey,
    defFac,
    deformed,
    showArrows: showReactionArrows,
    showValues: showReactionLabels,
    span,
    nm,
    reactionLabelScale,
  });

  if (showLabels) {
    for (const n of model.nodes) {
      if (!isNodeVisible(n.id)) continue;
      const p = nodePosition(n, model, lc, defFac, deformed);
      const sprite = makeTextSprite(String(n.id), span, {
        scaleFactor: nodeLabelScale,
        bg: null,
        fg: colorHex(COLORS.nodeLabel),
      });
      sprite.renderOrder = 16;
      const lineGeo = new THREE.BufferGeometry();
      lineGeo.setAttribute("position", new THREE.Float32BufferAttribute(6, 3));
      const line = new THREE.Line(lineGeo, nodeLabelLeaderMaterial());
      line.frustumCulled = false;
      line.renderOrder = 15;
      const entry = {
        nodePos: p.clone(),
        span: span,
        scaleFactor: nodeLabelScale,
        sprite: sprite,
        line: line,
      };
      updateNodeLabelEntry(entry, model, camera, renderer);
      labelGroup.add(sprite);
      labelGroup.add(line);
      nodeLabelEntries.push(entry);
    }
  }

  for (const e of model.elements) {
    if (!isMemberElementVisible(e.id)) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);

    if (showElemLabels) {
      addElemLabelWithLeader(
        String(e.id),
        elemPointAlong(p0, p1, 0.55),
        p0,
        p1,
        1,
        span,
        elemLabelScale,
        labelGroup,
        LABEL_BG.elem,
        false
      );
    }
    if (showMaterial) {
      const text = elementMaterialText(e);
      if (text) {
        addElemLabelWithLeader(
          text,
          elemPointAlong(p0, p1, 0.67),
          p0,
          p1,
          1,
          span,
          materialLabelScale,
          labelGroup,
          LABEL_BG.material
        );
      }
    }
    if (showSection) {
      const text = elementSectionText(e);
      if (text) {
        addElemLabelWithLeader(
          text,
          elemPointAlong(p0, p1, 0.25),
          p0,
          p1,
          -1,
          span,
          sectionLabelScale,
          labelGroup,
          LABEL_BG.section
        );
      }
    }
  }

  buildForceDiagrams(model);

  clearGroup(windGroup);
  clearGroup(windLabelGroup);
  if (windLoadsShown() && windVisualData) {
    const wc = windCaseById(windVisualData, selectedWindCaseId);
    if (wc) drawWindOverlay(model, windVisualData, wc, span);
  }
  updateWindLegendOverlay();

  clearGroup(practiceCenterGroup);
  if (practiceCentersShown() && practiceSummaryData) {
    drawPracticeCentersOverlay(model, practiceSummaryData, span);
  }

  clearGroup(colocatedGroup);
  if (el.chkColocated && el.chkColocated.checked) {
    drawColocatedOverlay(model, {
      lc,
      defFac,
      deformed,
      span,
      nm,
      group: colocatedGroup,
    });
  } else {
    colocatedSitesCache = null;
  }

  updateWorldAxes(model);
  refreshDisplayStatus(model);
  updateViewerInfoOverlay(model);
  updateColocatedLegendOverlay();
  updateSelectionHighlight();
  updateDistanceVisual();
}

function formatForceValue(val) {
  if (Math.abs(val) < PRES_ZERO) return "0";
  return (val * 1e-3).toFixed(1);
}

function isForceValueDisplayZero(val) {
  if (!isFinite(val) || Math.abs(val) < PRES_ZERO) return true;
  // Match formatForceValue (kN, 1 decimal): |display| < 0.05 → "0.0"
  return Math.abs(val * 1e-3) < 0.05;
}

function forceLabelsAllDisplayZero(labels) {
  return labels.length > 0 && labels.every(function (item) {
    return isForceValueDisplayZero(item.val);
  });
}

function modelSpan(model) {
  const b = model.bounds;
  if (!b) return 1;
  return Math.max(b[1] - b[0], b[3] - b[2], b[5] - b[4], 1e-6);
}

function nodeMarkerSize(model) {
  return Math.max(0.04, (model.bounds ? (model.bounds[1] - model.bounds[0]) * 0.012 : 0.05));
}

function createNodePointTexture() {
  if (_nodePointTexture) return _nodePointTexture;
  const px = 64;
  const canvas = document.createElement("canvas");
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext("2d");
  ctx.beginPath();
  ctx.arc(px / 2, px / 2, px / 2 - 0.5, 0, Math.PI * 2);
  ctx.fillStyle = "#ffffff";
  ctx.fill();
  _nodePointTexture = new THREE.CanvasTexture(canvas);
  _nodePointTexture.needsUpdate = true;
  return _nodePointTexture;
}

function nodePointsMaterial(opts) {
  return new THREE.PointsMaterial({
    color: opts.color,
    size: opts.size,
    sizeAttenuation: opts.sizeAttenuation !== false,
    map: createNodePointTexture(),
    transparent: true,
    alphaTest: 0.05,
    depthTest: opts.depthTest !== false,
  });
}

function supportGizmoSize(model) {
  const span = modelSpan(model);
  const base = Math.max(span * 0.022, 0.07);
  const pct = parseFloat(viewerOptions.supportGizmoSize);
  if (!isFinite(pct) || pct < 1) return base;
  return base * (pct / 100);
}

function worldAxesLength(model) {
  const span = modelSpan(model);
  const base = Math.max(span * 0.1, 0.12);
  const pct = parseFloat(viewerOptions.axesSize);
  if (!isFinite(pct) || pct < 1) return base;
  return base * (pct / 100);
}

function billboardPixelSize(worldPos, worldDiameter, camera, renderer) {
  _viewPosScratch.copy(worldPos).applyMatrix4(camera.matrixWorldInverse);
  const dist = Math.max(-_viewPosScratch.z, 1e-6);
  const height = renderer.domElement.clientHeight;
  const scale = height * camera.projectionMatrix.elements[5] * 0.5 * renderer.getPixelRatio();
  return worldDiameter * (scale / dist);
}

// PointsMaterial map circle: visible diameter is ~half of billboardPixelSize estimate.
const NODE_POINT_RENDER_DIAMETER_SCALE = 0.5;
const SUPPORT_GIZMO_VISUAL_RADIUS_FACTOR =
  (160 / 2 - 6) / (160 / 2);

function nodeMarkerPixelRadius(worldPos, model, camera, renderer) {
  const diameterPx = billboardPixelSize(worldPos, nodeMarkerSize(model), camera, renderer);
  return diameterPx * NODE_POINT_RENDER_DIAMETER_SCALE * 0.5;
}

function supportGizmoPixelRadius(worldPos, gizmoRadius, camera, renderer) {
  const diameterPx = billboardPixelSize(worldPos, gizmoRadius * 2, camera, renderer);
  return diameterPx * 0.5 * SUPPORT_GIZMO_VISUAL_RADIUS_FACTOR;
}

function supportGizmoCenter(nodePos, model, gizmoRadius, camera, renderer, target) {
  const out = target || new THREE.Vector3();
  const nodeSize = nodeMarkerSize(model);
  if (!camera || !renderer || renderer.domElement.clientHeight < 1) {
    return out.copy(nodePos).add(new THREE.Vector3(0, 0, -(nodeSize * 0.5 + gizmoRadius)));
  }

  const offsetPx = nodeMarkerPixelRadius(nodePos, model, camera, renderer)
    + supportGizmoPixelRadius(nodePos, gizmoRadius, camera, renderer);

  _ndcScratch.copy(nodePos).project(camera);
  const height = renderer.domElement.clientHeight;
  _ndcScratch.y -= (offsetPx / height) * 2;
  return out.copy(_ndcScratch).unproject(camera);
}

function nodeLabelLeaderMaterial() {
  if (!_nodeLabelLeaderMat) {
    _nodeLabelLeaderMat = new THREE.LineBasicMaterial({
      color: COLORS.nodeLabel,
      transparent: true,
      opacity: 0.38,
      depthTest: false,
    });
  }
  return _nodeLabelLeaderMat;
}

function computeNodeLabelPlacement(nodePos, model, camera, renderer) {
  const width = renderer.domElement.clientWidth;
  const height = renderer.domElement.clientHeight;
  const leaderStart = nodePos.clone();
  if (width < 1 || height < 1) {
    return {
      labelPos: nodePos.clone().add(new THREE.Vector3(0, nodeMarkerSize(model) * 0.8, 0)),
      leaderStart: leaderStart,
    };
  }

  const nodeRadiusPx = nodeMarkerPixelRadius(nodePos, model, camera, renderer);
  const screenDx = 20;
  const screenDy = 24;
  const dirLen = Math.hypot(screenDx, screenDy) || 1;
  const sx = screenDx / dirLen;
  const sy = screenDy / dirLen;

  _ndcScratch.copy(nodePos).project(camera);

  const labelPx = nodeRadiusPx + 24;
  _labelNdc.set(
    _ndcScratch.x + (sx * labelPx / width) * 2,
    _ndcScratch.y + (sy * labelPx / height) * 2,
    _ndcScratch.z
  );
  _leaderEnd.copy(_labelNdc).unproject(camera);

  return { labelPos: _leaderEnd.clone(), leaderStart: leaderStart };
}

function updateNodeLabelEntry(entry, model, camera, renderer) {
  const placement = computeNodeLabelPlacement(entry.nodePos, model, camera, renderer);
  entry.sprite.position.copy(placement.labelPos);
  const leaderEnd = labelLeaderEnd(
    placement.labelPos,
    placement.leaderStart,
    entry.sprite,
    camera,
    renderer
  );
  const pos = entry.line.geometry.attributes.position;
  pos.setXYZ(0, placement.leaderStart.x, placement.leaderStart.y, placement.leaderStart.z);
  pos.setXYZ(1, leaderEnd.x, leaderEnd.y, leaderEnd.z);
  pos.needsUpdate = true;
  entry.line.geometry.computeBoundingSphere();
}

function updateNodeLabelPositions() {
  if (!camera || !renderer || !currentModel || nodeLabelEntries.length === 0) return;
  for (const entry of nodeLabelEntries) {
    updateNodeLabelEntry(entry, currentModel, camera, renderer);
  }
}

function computeElemLabelPlacement(anchorPos, p0, p1, camera, renderer, side) {
  const width = renderer.domElement.clientWidth;
  const height = renderer.domElement.clientHeight;
  const sign = side >= 0 ? 1 : -1;
  const leaderStart = anchorPos.clone();
  if (width < 1 || height < 1) {
    return {
      labelPos: offsetLabelPoint(anchorPos, p0, p1, sign),
      leaderStart: leaderStart,
    };
  }

  _ndcScratch.copy(anchorPos).project(camera);
  const ndcZ = _ndcScratch.z;
  _ndcP0.copy(p0).project(camera);
  _ndcP1.copy(p1).project(camera);

  let edx = _ndcP1.x - _ndcP0.x;
  let edy = _ndcP1.y - _ndcP0.y;
  const edLen = Math.hypot(edx, edy);
  if (edLen < 1e-8) {
    edx = 20 / width * 2;
    edy = 24 / height * 2;
  } else {
    edx /= edLen;
    edy /= edLen;
  }

  let sx = -edy * sign;
  let sy = edx * sign;
  const sLen = Math.hypot(sx, sy) || 1;
  sx /= sLen;
  sy /= sLen;

  const labelPx = 28;
  _labelNdc.set(
    _ndcScratch.x + (sx * labelPx / width) * 2,
    _ndcScratch.y + (sy * labelPx / height) * 2,
    ndcZ
  );
  _leaderEnd.copy(_labelNdc).unproject(camera);

  return { labelPos: _leaderEnd.clone(), leaderStart: leaderStart };
}

function worldLengthForScreenPixels(px, worldPos, camera, renderer) {
  if (px <= 0) return 0;
  const width = renderer.domElement.clientWidth;
  if (width < 1) return 0;
  _ndcScratch.copy(worldPos).project(camera);
  const ndcZ = _ndcScratch.z;
  _labelNdc.set(_ndcScratch.x + (px / width) * 2, _ndcScratch.y, ndcZ);
  _leaderStart.copy(_labelNdc).unproject(camera);
  return worldPos.distanceTo(_leaderStart);
}

function spriteExtentAlongDirection(sprite, worldDir, camera) {
  const halfW = sprite.scale.x * 0.5;
  const halfH = sprite.scale.y * 0.5;
  _camRight.setFromMatrixColumn(camera.matrixWorld, 0).normalize();
  _camUp.setFromMatrixColumn(camera.matrixWorld, 1).normalize();
  const d = worldDir.lengthSq() > 1e-12 ? worldDir.clone().normalize() : _camRight;
  return halfW * Math.abs(d.dot(_camRight)) + halfH * Math.abs(d.dot(_camUp));
}

function labelLeaderEnd(labelCenter, leaderStart, sprite, camera, renderer) {
  _leaderDir.subVectors(labelCenter, leaderStart);
  const dist = _leaderDir.length();
  if (dist < 1e-8) return labelCenter.clone();
  _leaderDir.divideScalar(dist);
  const inset = spriteExtentAlongDirection(sprite, _leaderDir, camera);
  const gap = worldLengthForScreenPixels(3, labelCenter, camera, renderer);
  return labelCenter.clone().addScaledVector(_leaderDir, -(inset + gap));
}

function updateElemLabelEntry(entry, camera, renderer) {
  const placement = computeElemLabelPlacement(
    entry.anchorPos,
    entry.p0,
    entry.p1,
    camera,
    renderer,
    entry.side
  );
  entry.sprite.position.copy(placement.labelPos);
  const leaderEnd = labelLeaderEnd(
    placement.labelPos,
    placement.leaderStart,
    entry.sprite,
    camera,
    renderer
  );
  const pos = entry.line.geometry.attributes.position;
  pos.setXYZ(0, placement.leaderStart.x, placement.leaderStart.y, placement.leaderStart.z);
  pos.setXYZ(1, leaderEnd.x, leaderEnd.y, leaderEnd.z);
  pos.needsUpdate = true;
  entry.line.geometry.computeBoundingSphere();
}

function updateElemLabelPositions() {
  if (!camera || !renderer || elemLabelEntries.length === 0) return;
  for (const entry of elemLabelEntries) {
    updateElemLabelEntry(entry, camera, renderer);
  }
}

function computeForceLabelPlacement(diagramPt, axisPt, camera, renderer) {
  const width = renderer.domElement.clientWidth;
  const height = renderer.domElement.clientHeight;
  const leaderStart = diagramPt.clone();
  if (width < 1 || height < 1) {
    const out = diagramPt.clone().sub(axisPt);
    if (out.lengthSq() < 1e-12) out.set(0, 1, 0);
    else out.normalize();
    return {
      labelPos: diagramPt.clone().addScaledVector(out, worldLengthForScreenPixels(28, diagramPt, camera, renderer) || 0.05),
      leaderStart: leaderStart,
    };
  }

  _ndcScratch.copy(diagramPt).project(camera);
  const ndcZ = _ndcScratch.z;
  _ndcP0.copy(axisPt).project(camera);

  let sx = _ndcScratch.x - _ndcP0.x;
  let sy = _ndcScratch.y - _ndcP0.y;
  const sLen = Math.hypot(sx, sy);
  if (sLen < 1e-8) {
    sx = 20 / width * 2;
    sy = 24 / height * 2;
  } else {
    sx /= sLen;
    sy /= sLen;
  }

  const labelPx = 30;
  _labelNdc.set(
    _ndcScratch.x + (sx * labelPx / width) * 2,
    _ndcScratch.y + (sy * labelPx / height) * 2,
    ndcZ
  );
  _leaderEnd.copy(_labelNdc).unproject(camera);

  return { labelPos: _leaderEnd.clone(), leaderStart: leaderStart };
}

function updateForceLabelEntry(entry, camera, renderer) {
  const placement = computeForceLabelPlacement(
    entry.diagramPt,
    entry.axisPt,
    camera,
    renderer
  );
  entry.sprite.position.copy(placement.labelPos);
  const leaderEnd = labelLeaderEnd(
    placement.labelPos,
    placement.leaderStart,
    entry.sprite,
    camera,
    renderer
  );
  const pos = entry.line.geometry.attributes.position;
  pos.setXYZ(0, placement.leaderStart.x, placement.leaderStart.y, placement.leaderStart.z);
  pos.setXYZ(1, leaderEnd.x, leaderEnd.y, leaderEnd.z);
  pos.needsUpdate = true;
  entry.line.geometry.computeBoundingSphere();
}

function updateForceLabelPositions() {
  if (!camera || !renderer || forceLabelEntries.length === 0) return;
  for (const entry of forceLabelEntries) {
    updateForceLabelEntry(entry, camera, renderer);
  }
}

function updateSupportGizmoPositions() {
  if (!camera || !renderer || !currentModel || supportGizmoEntries.length === 0) return;
  for (const entry of supportGizmoEntries) {
    supportGizmoCenter(
      entry.nodePos, currentModel, entry.gizmoRadius, camera, renderer, entry.sprite.position
    );
  }
}

function reactionForceDirection(axisIndex, fval) {
  return REACTION_TRANS_AXES[axisIndex].clone().multiplyScalar(fval >= 0 ? 1 : -1);
}

function computeReactionTransArrowEndpoints(gizmoCenter, gizmoRadius, screenDir, arrowLen) {
  const d = screenDir.clone().normalize();
  const head = gizmoCenter.clone().addScaledVector(d, -gizmoRadius);
  const tail = gizmoCenter.clone().addScaledVector(d, -(gizmoRadius + arrowLen));
  return { tail, head };
}

function billboardViewDirection(worldPos, camera, target) {
  const out = target || new THREE.Vector3();
  out.subVectors(camera.position, worldPos);
  if (out.lengthSq() < 1e-18) {
    return out.copy(camera.getWorldDirection(new THREE.Vector3()));
  }
  return out.normalize();
}

function billboardScreenDirection(worldPos, worldDir, camera, target) {
  const out = target || new THREE.Vector3();
  const viewDir = billboardViewDirection(worldPos, camera, _viewToCenterScratch);
  const d = worldDir.clone().normalize();
  out.copy(d).addScaledVector(viewDir, -d.dot(viewDir));
  if (out.lengthSq() < 1e-12) {
    out.copy(camera.up).addScaledVector(viewDir, -camera.up.dot(viewDir));
    if (out.lengthSq() < 1e-12) {
      out.set(1, 0, 0);
    }
  }
  return out.normalize();
}

function reactionArrowLength(model) {
  const span = modelSpan(model);
  const pct = parseFloat(viewerOptions.reactionArrowSize);
  if (!isFinite(pct) || pct <= 0) return span * 0.01;
  return span * (pct / 100);
}

function reactionLineWidthPx(mag, maxMag) {
  const base = clampLineWidthPx(
    viewerOptions.reactionLineWidth, 2, OPTIONS_LIMITS.reactionLineWidth.max
  );
  if (maxMag < 1e-9) return base * 0.25;
  return base * Math.max(0.25, Math.abs(mag) / maxMag);
}

function updateReactionForceLabel(entry, tail, screenDir) {
  if (!entry.labelSprite) return;
  const worldH = entry.span * entry.scaleFactor;
  const gap = worldH * 0.08;
  entry.labelSprite.position.copy(tail).addScaledVector(
    screenDir, -(worldH * 0.5 + gap)
  );
}

function updateReactionZeroLabel(entry, gizmoCenter, screenDir) {
  if (!entry.labelSprite) return;
  const worldH = entry.span * entry.scaleFactor;
  const inset = entry.gizmoRadius * 0.12;
  entry.labelSprite.position.copy(gizmoCenter).addScaledVector(
    screenDir, -(entry.gizmoRadius + inset + worldH * 0.35)
  );
}

function updateReactionForceDisplay() {
  if (!camera || !renderer || !currentModel || reactionForceEntries.length === 0) return;
  for (const entry of reactionForceEntries) {
    const center = supportGizmoCenter(
      entry.nodePos, currentModel, entry.gizmoRadius, camera, renderer, _gizmoCenterScratch
    );
    if (entry.zeroDisplay) {
      const axisDir = REACTION_TRANS_AXES[entry.axisIndex];
      const screenDir = billboardScreenDirection(center, axisDir, camera, _screenDirScratch);
      updateReactionZeroLabel(entry, center, screenDir);
      continue;
    }
    const forceDir = reactionForceDirection(entry.axisIndex, entry.fval);
    const screenDir = billboardScreenDirection(center, forceDir, camera, _screenDirScratch);
    const viewDir = billboardViewDirection(center, camera, _viewToCenterScratch);
    const { tail, head } = computeReactionTransArrowEndpoints(
      center, entry.gizmoRadius, screenDir, entry.arrowLen
    );
    if (entry.lines) {
      updateBillboardDirectedWideArrow(entry.lines, tail, head, viewDir, entry.headScale);
    }
    updateReactionForceLabel(entry, tail, screenDir);
  }
}

function ejntMarkerRadius(model) {
  const span = modelSpan(model);
  const supHalf = supportGizmoSize(model);
  return Math.max(supHalf * 0.3, span * 0.004, 0.012);
}

function ejntByElementId(model) {
  const map = Object.create(null);
  for (const j of model.element_joints || []) {
    if (j && j.elem_id != null) map[j.elem_id] = j;
  }
  return map;
}

function ejntEndHasRelease(j, end) {
  if (!j) return false;
  if (end === "i") return j.ryi != null || j.rzi != null;
  return j.ryj != null || j.rzj != null;
}

function drawEJntMarkers(model, opts) {
  const { lc, defFac, deformed, nm, group } = opts;
  const r = ejntMarkerRadius(model);
  const supportHalf = supportGizmoSize(model);
  const geo = new THREE.SphereGeometry(r, 16, 12);
  const mat = new THREE.MeshBasicMaterial({ color: COLORS.ejnt, depthTest: true });
  const ejntMap = ejntByElementId(model);

  for (const e of model.elements || []) {
    if (!e) continue;
    if (!isMemberElementVisible(e.id)) continue;
    const j = ejntMap[e.id];
    const showI = ejntEndHasRelease(j, "i");
    const showJ = ejntEndHasRelease(j, "j");
    if (!showI && !showJ) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const len = p0.distanceTo(p1);
    if (len < 1e-12) continue;

    const offset = supportHalf + r;
    let t0 = offset / len;
    let t1 = 1 - offset / len;
    if (!(t0 < t1)) {
      t0 = 0.35;
      t1 = 0.65;
    }

    if (showI) {
      const m0 = new THREE.Mesh(geo, mat);
      m0.position.copy(elemPointAlong(p0, p1, t0));
      m0.renderOrder = 9;
      group.add(m0);
    }
    if (showJ) {
      const m1 = new THREE.Mesh(geo, mat);
      m1.position.copy(elemPointAlong(p0, p1, t1));
      m1.renderOrder = 9;
      group.add(m1);
    }
  }
}

function drawWoodRatedWalls(model, opts) {
  const { lc, defFac, deformed, nm, group } = opts;
  const items = model.wood_rated_walls || [];
  if (!items.length) return;

  const fillPos = [];
  const edgePts = [];

  for (const wall of items) {
    if (!isWrwVisible(wall.id)) continue;
    const ids = wall.nodes;
    if (!ids || ids.length !== 4) continue;
    const n0 = nm[ids[0]];
    const n1 = nm[ids[1]];
    const n2 = nm[ids[2]];
    const n3 = nm[ids[3]];
    if (!n0 || !n1 || !n2 || !n3) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const p2 = nodePosition(n2, model, lc, defFac, deformed);
    const p3 = nodePosition(n3, model, lc, defFac, deformed);
    fillPos.push(
      p0.x, p0.y, p0.z,
      p1.x, p1.y, p1.z,
      p2.x, p2.y, p2.z,
      p0.x, p0.y, p0.z,
      p2.x, p2.y, p2.z,
      p3.x, p3.y, p3.z
    );
    edgePts.push(
      p0.x, p0.y, p0.z, p1.x, p1.y, p1.z,
      p1.x, p1.y, p1.z, p2.x, p2.y, p2.z,
      p2.x, p2.y, p2.z, p3.x, p3.y, p3.z,
      p3.x, p3.y, p3.z, p0.x, p0.y, p0.z
    );
  }

  if (fillPos.length === 0) return;

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(fillPos, 3));
  geo.computeVertexNormals();
  const mat = new THREE.MeshBasicMaterial({
    color: COLORS.woodWallFill,
    transparent: true,
    opacity: ALPHA.woodWallFill,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.renderOrder = 3;
  group.add(mesh);

  if (opts.showEdge !== false) {
    addWideLineSegmentsFromPts(
      edgePts,
      COLORS.woodWallEdge,
      group,
      4,
      Math.max(elementLineWidthPx() * 0.9, 0.5),
      ALPHA.woodWallEdge
    );
  }
}

function drawMembraneElements(model, opts) {
  const { lc, defFac, deformed, nm, group } = opts;
  const items = model.membrane_elements || [];
  if (!items.length) return;

  const fillPos = [];
  const edgePts = [];

  for (const mem of items) {
    if (!isDmemVisible(mem.id)) continue;
    const ids = mem.nodes;
    if (!ids || ids.length !== 3) continue;
    const n0 = nm[ids[0]];
    const n1 = nm[ids[1]];
    const n2 = nm[ids[2]];
    if (!n0 || !n1 || !n2) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const p2 = nodePosition(n2, model, lc, defFac, deformed);
    fillPos.push(
      p0.x, p0.y, p0.z,
      p1.x, p1.y, p1.z,
      p2.x, p2.y, p2.z
    );
    edgePts.push(
      p0.x, p0.y, p0.z, p1.x, p1.y, p1.z,
      p1.x, p1.y, p1.z, p2.x, p2.y, p2.z,
      p2.x, p2.y, p2.z, p0.x, p0.y, p0.z
    );
  }

  if (fillPos.length === 0) return;

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(fillPos, 3));
  geo.computeVertexNormals();
  const mat = new THREE.MeshBasicMaterial({
    color: COLORS.membraneFill,
    transparent: true,
    opacity: ALPHA.membraneFill,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.renderOrder = 4;
  group.add(mesh);

  if (opts.showEdge !== false) {
    addWideLineSegmentsFromPts(
      edgePts,
      COLORS.membraneEdge,
      group,
      5,
      Math.max(elementLineWidthPx() * 0.85, 0.5),
      ALPHA.membraneEdge
    );
  }
}

function syncRegionEdgeCheckboxes() {
  const showMembrane = !!(el.chkMembrane && el.chkMembrane.checked);
  const showWoodWall = !!(el.chkWoodWall && el.chkWoodWall.checked);
  if (el.chkMembraneEdge) el.chkMembraneEdge.disabled = !showMembrane;
  if (el.chkWoodWallEdge) el.chkWoodWallEdge.disabled = !showWoodWall;
}

function axisPerpendiculars(d) {
  const dir = d.clone().normalize();
  let u = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 1, 0));
  if (u.lengthSq() < 1e-12) {
    u = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(1, 0, 0));
  }
  u.normalize();
  const v = new THREE.Vector3().crossVectors(dir, u).normalize();
  return { u, v };
}

function arcInPlane(center, axis, radius, startAngle, endAngle, segments) {
  const { u, v } = axisPerpendiculars(axis);
  const pts = [];
  for (let i = 0; i <= segments; i++) {
    const t = startAngle + (endAngle - startAngle) * (i / segments);
    pts.push(center.clone()
      .addScaledVector(u, Math.cos(t) * radius)
      .addScaledVector(v, Math.sin(t) * radius));
  }
  return pts;
}

function addLinePair(p0, p1, pts) {
  pts.push(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z);
}

function addLineSegmentsFromPts(pts, color, group, renderOrder) {
  if (pts.length < 6) return;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  geo.computeBoundingSphere();
  const lines = new THREE.LineSegments(
    geo,
    new THREE.LineBasicMaterial({ color: color, depthTest: true })
  );
  lines.frustumCulled = false;
  lines.renderOrder = renderOrder;
  group.add(lines);
}

function clampLineWidthPx(v, fallback, maxVal) {
  const n = parseFloat(v);
  if (!isFinite(n) || n < 0.5) return fallback;
  return Math.min(n, maxVal != null ? maxVal : OPTIONS_LIMITS.supportLineWidth.max);
}

function supportLineWidthPx() {
  return clampLineWidthPx(viewerOptions.supportLineWidth, 2, OPTIONS_LIMITS.supportLineWidth.max);
}

function dispContourLineWidthPx() {
  return clampLineWidthPx(viewerOptions.dispContourLineWidth, 2.5, OPTIONS_LIMITS.dispContourLineWidth.max);
}

function elementLineWidthPx() {
  return clampLineWidthPx(viewerOptions.elementLineWidth, 1.5, OPTIONS_LIMITS.elementLineWidth.max);
}

function loadLineWidthPx() {
  return clampLineWidthPx(viewerOptions.loadLineWidth, 1.5, OPTIONS_LIMITS.loadLineWidth.max);
}

function forceLineWidthPx() {
  return clampLineWidthPx(viewerOptions.forceLineWidth, 1.5, OPTIONS_LIMITS.forceLineWidth.max);
}

function addWideLineSegmentsFromPts(pts, color, group, renderOrder, lineWidthPx, opacity, opaque) {
  if (pts.length < 6) return null;
  const geo = new LineSegmentsGeometry();
  geo.setPositions(pts);
  const useOpaque = opaque === true;
  const useOverlay = opaque === "overlay";
  const isTransparent = useOverlay || (!useOpaque && opacity != null && opacity < ALPHA.opaque);
  const mat = new LineMaterial({
    color: color,
    linewidth: lineWidthPx,
    worldUnits: false,
    transparent: isTransparent,
    opacity: useOpaque ? 1 : (opacity != null ? opacity : ALPHA.opaque),
    depthTest: (useOpaque || useOverlay) ? false : true,
    depthWrite: (useOpaque || useOverlay) ? false : !isTransparent,
  });
  const w = el.viewport.clientWidth || 1;
  const h = el.viewport.clientHeight || 1;
  mat.resolution.set(w, h);
  wideLineMaterials.add(mat);
  const lines = new LineSegments2(geo, mat);
  lines.frustumCulled = false;
  lines.renderOrder = renderOrder;
  group.add(lines);
  return lines;
}

function supportDiscTextureKey(fixed) {
  return fixed.map(function (f) { return f ? "1" : "0"; }).join("");
}

function fillSupportSector(ctx, cx, cy, r, startAngle, endAngle, fillColor) {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, r, startAngle, endAngle);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();
  ctx.restore();
}

function createSupportDiscTexture(fixed) {
  const key = supportDiscTextureKey(fixed);
  if (_supportDiscTexCache.has(key)) {
    return _supportDiscTexCache.get(key);
  }

  const px = 160;
  const canvas = document.createElement("canvas");
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext("2d");
  const cx = px / 2;
  const cy = px / 2;
  const r = px / 2 - 6;
  const sectorColors = [
    COLORS.supportTrans, COLORS.supportTrans, COLORS.supportTrans,
    COLORS.supportRot, COLORS.supportRot, COLORS.supportRot,
  ];
  const outline = supportDiscOutlineColor();

  ctx.clearRect(0, 0, px, px);

  for (let i = 0; i < 6; i++) {
    const a0 = -Math.PI / 2 + i * (Math.PI / 3);
    const a1 = a0 + Math.PI / 3;
    if (fixed[i]) {
      fillSupportSector(ctx, cx, cy, r, a0, a1, colorHex(sectorColors[i]));
    }
  }

  ctx.strokeStyle = outline;
  ctx.globalAlpha = ALPHA.opaque;
  ctx.lineWidth = 10.0;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.stroke();

  for (let i = 0; i < 6; i++) {
    const a = -Math.PI / 2 + i * (Math.PI / 3);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
    ctx.stroke();
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  _supportDiscTexCache.set(key, tex);
  return tex;
}

function clearSupportDiscTextureCache() {
  for (const tex of _supportDiscTexCache.values()) {
    try {
      tex.dispose();
    } catch (e) { /* ignore */ }
  }
  _supportDiscTexCache.clear();
}

function supportDiscOutlineColor() {
  const palette = THEME_RENDER_COLORS[uiTheme] || THEME_RENDER_COLORS.dark;
  return palette.supportOutline;
}

function addSupportDisc(center, fixed, size, group) {
  const tex = createSupportDiscTexture(fixed);
  const mat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    depthTest: true,
    depthWrite: false,
  });
  const sp = new THREE.Sprite(mat);
  sp.position.copy(center);
  sp.scale.set(size * 2, size * 2, 1);
  sp.renderOrder = 8;
  group.add(sp);
  return sp;
}

function loadArrowLength(model) {
  const span = modelSpan(model);
  const pct = parseFloat(viewerOptions.loadArrowSize);
  if (!isFinite(pct) || pct <= 0) return span * 0.01;
  return span * (pct / 100);
}

function elemPointAlong(p0, p1, t) {
  return new THREE.Vector3().lerpVectors(p0, p1, t);
}

function offsetLabelPoint(p, p0, p1, side) {
  if (!side) return p;
  const along = new THREE.Vector3().subVectors(p1, p0);
  const elemLen = along.length();
  if (elemLen < 1e-12) return p;
  let perp = new THREE.Vector3().crossVectors(along, new THREE.Vector3(0, 1, 0));
  if (perp.lengthSq() < 1e-12) {
    perp = new THREE.Vector3().crossVectors(along, new THREE.Vector3(1, 0, 0));
  }
  perp.normalize().multiplyScalar(elemLen * 0.04 * side);
  return p.clone().add(perp);
}

function elementMaterialText(e) {
  const name = e.material_name != null ? e.material_name : e.material;
  if (name != null && String(name).trim() !== "") return String(name).trim();
  if (e.material_id !== undefined && e.material_id !== null) return String(e.material_id);
  return "";
}

function elementSectionText(e) {
  if (e.section != null && String(e.section).trim() !== "") return String(e.section).trim();
  if (e.section_id !== undefined && e.section_id !== null) return String(e.section_id);
  return "";
}

function formatLoadPointValue(l, dir) {
  const fdot = l.px * dir.x + l.py * dir.y + l.pz * dir.z;
  const fmag = Math.hypot(l.px, l.py, l.pz);
  if (fmag > 1e-6) return formatReactionValue(fdot);
  const mmag = Math.hypot(l.mx, l.my, l.mz);
  if (mmag > 1e-6) return formatReactionValue(mmag);
  return "";
}

const LOAD_DIV_NUM = 8;

function isGravityLoad(ld) {
  return !!(ld && (ld.gravity === true || ld.gravity === 1));
}

function isAreaLoad(ld) {
  return !!(ld && (ld.area_load === true || ld.area_load === 1));
}

function formatLoadDistributedValue(mag, isGravity, isArea, displayValue) {
  if (displayValue) return displayValue;
  if (Math.abs(mag) < 1e-6) return "";
  const text = formatReactionValue(mag);
  if (isGravity) return text + "G";
  if (isArea) return text + "A";
  return text;
}

function distributedLoadAxes(elem, isGlobal) {
  if (isGlobal) {
    return [
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(0, 0, 1),
    ];
  }
  if (!elem || !elem.vx || !elem.vy || !elem.vz) return null;
  return [
    new THREE.Vector3().fromArray(elem.vx),
    new THREE.Vector3().fromArray(elem.vy),
    new THREE.Vector3().fromArray(elem.vz),
  ];
}

function labelWorldHeight(span, scaleFactor, fallback) {
  return span * (scaleFactor != null ? scaleFactor : (fallback != null ? fallback : 0.03));
}

function labelOffsetDistance(span, scaleFactor, fallback) {
  return labelWorldHeight(span, scaleFactor, fallback) * 0.5 * 1.2;
}

function loadValueOffsetDistance(span, scaleFactor) {
  // Requested rule: move by text-height * 1.2 from the shaft end.
  return labelWorldHeight(span, scaleFactor, 0.03) * 1.2;
}

function loadValueLabelPoint(tail, tip, span, scaleFactor) {
  const axis = new THREE.Vector3().subVectors(tip, tail);
  if (axis.lengthSq() < 1e-18) return tail.clone();
  axis.normalize();
  const pad = loadValueOffsetDistance(span, scaleFactor);
  return tail.clone().addScaledVector(axis, -pad);
}

function loadTypeFilterValue() {
  const t = viewerOptions.inputLoadType;
  if (t === "dlod" && !isAdvancedGui()) return "all";
  if (t === "area" || t === "gravity" || t === "linepoint" || t === "dlod") return t;
  return "all";
}

function shouldDrawDiaphragmLoad() {
  if (!isAdvancedGui()) return false;
  const t = loadTypeFilterValue();
  return t === "all" || t === "dlod";
}

function shouldDrawPointLoad() {
  const t = loadTypeFilterValue();
  if (t === "dlod") return false;
  return t === "all" || t === "linepoint";
}

function shouldDrawElementLoad(ld) {
  const t = loadTypeFilterValue();
  if (t === "dlod") return false;
  if (t === "all") return true;
  if (t === "area") return isAreaLoad(ld);
  if (t === "gravity") return isGravityLoad(ld);
  if (t === "linepoint") return !isAreaLoad(ld) && !isGravityLoad(ld);
  return true;
}

function addLoadValueLabel(text, point, span, scaleFactor, group) {
  if (!text) return;
  const sprite = makeLoadValueLabelSprite(text, span, scaleFactor);
  sprite.position.copy(point);
  sprite.renderOrder = 15;
  group.add(sprite);
}

function makeLoadValueLabelSprite(text, span, scaleFactor) {
  const factor = scaleFactor != null ? scaleFactor : 0.06;
  const quality = Math.min(20, Math.max(4, labelTextureQualityScale(factor) * 1.75));
  return makeTextSprite(text, span, {
    bg: "transparent",
    fg: colorHex(COLORS.load),
    pad: 2,
    scaleFactor: factor,
    qualityScale: quality,
    solidAlpha: true,
    crispLabel: true,
    transparent: true,
    alphaTest: 0.5,
  });
}

function elemMap(model) {
  const em = {};
  for (const e of model.elements) em[e.id] = e;
  return em;
}

function localVecToGlobal(v, elem) {
  if (!elem || !elem.vx || !elem.vy || !elem.vz) return v;
  const vx = elem.vx;
  const vy = elem.vy;
  const vz = elem.vz;
  return new THREE.Vector3(
    vx[0] * v.x + vy[0] * v.y + vz[0] * v.z,
    vx[1] * v.x + vy[1] * v.y + vz[1] * v.z,
    vx[2] * v.x + vy[2] * v.y + vz[2] * v.z
  );
}

function elementLoadVector(w, t, elem, isGlobal) {
  const v = new THREE.Vector3(
    w[0] + t * (w[3] - w[0]),
    w[1] + t * (w[4] - w[1]),
    w[2] + t * (w[5] - w[2])
  );
  return isGlobal ? v : localVecToGlobal(v, elem);
}

function elementLoadMagnitude(w) {
  const m0 = Math.hypot(w[0], w[1], w[2]);
  const m1 = Math.hypot(w[3], w[4], w[5]);
  return Math.max(m0, m1);
}

function maxElementLoadMag(model, lc) {
  let max = 0;
  for (const ld of model.element_loads || []) {
    if (String(ld.lc) !== String(lc)) continue;
    max = Math.max(max, elementLoadMagnitude(ld.w));
  }
  return max;
}

function maxPointLoadMag(model, lc) {
  let max = 0;
  for (const l of model.point_loads || []) {
    if (String(l.lc) !== String(lc)) continue;
    max = Math.max(max, Math.hypot(l.px, l.py, l.pz));
  }
  return max;
}

function windCaseById(visual, caseId) {
  const cases = (visual && visual.cases) || [];
  if (!cases.length) return null;
  if (caseId == null) return cases[0];
  return cases.find(function (c) { return c.wind_case_id === caseId; }) || cases[0];
}

function pickWindCaseIdForLc(visual) {
  if (!visual || !visual.cases || !visual.cases.length) return null;
  const lc = String(el.lcSelect.value || "");
  const match = visual.cases.find(function (c) { return String(c.load_case) === lc; });
  return match ? match.wind_case_id : visual.cases[0].wind_case_id;
}

function windFlowDirection3(flow) {
  const ux = flow && flow.ux != null ? Number(flow.ux) : 0;
  const uy = flow && flow.uy != null ? Number(flow.uy) : 0;
  const dir = new THREE.Vector3(ux, uy, 0);
  if (dir.lengthSq() < 1e-12) return new THREE.Vector3(1, 0, 0);
  return dir.normalize();
}

function windSurfaceQuadCenter(corners) {
  const c = new THREE.Vector3();
  for (let i = 0; i < corners.length; i++) {
    c.add(corners[i]);
  }
  return c.multiplyScalar(1 / corners.length);
}

function windWindwardFaceCenter(bbox, windCase, zFallback) {
  const cx = 0.5 * (bbox.x_min + bbox.x_max);
  const cy = 0.5 * (bbox.y_min + bbox.y_max);
  let zMid = zFallback;
  const surfaces = windCase.surfaces || [];
  if (surfaces.length) {
    let zb = Infinity;
    let zt = -Infinity;
    for (const s of surfaces) {
      zb = Math.min(zb, Number(s.z_bottom) || 0);
      zt = Math.max(zt, Number(s.z_top) || 0);
    }
    if (isFinite(zb) && isFinite(zt)) zMid = 0.5 * (zb + zt);
  }
  const face = String(windCase.windward_face || "").toUpperCase();
  const anchor = new THREE.Vector3(cx, cy, zMid);
  if (face === "X_MIN") anchor.set(bbox.x_min, cy, zMid);
  else if (face === "X_MAX") anchor.set(bbox.x_max, cy, zMid);
  else if (face === "Y_MIN") anchor.set(cx, bbox.y_min, zMid);
  else if (face === "Y_MAX") anchor.set(cx, bbox.y_max, zMid);
  return anchor;
}

function windWindwardFlowLayout(bbox, windCase, span, zFallback) {
  const flowDir = windFlowDirection3(windCase.flow);
  const upwindDir = flowDir.clone().negate();
  const surfaceGap = Math.max(span * WIND_FLOW_SURFACE_GAP_RATIO, WIND_FLOW_MIN_SURFACE_GAP_M);
  const arrowLen = Math.max(span * WIND_FLOW_ARROW_LEN_RATIO, WIND_FLOW_MIN_ARROW_LEN_M);
  const labelPad = Math.max(span * WIND_FLOW_LABEL_PAD_RATIO, WIND_FLOW_MIN_LABEL_PAD_M);

  let faceCenter = null;
  for (const s of windCase.surfaces || []) {
    if (s.surface_role !== "WINDWARD") continue;
    const corners = windWallCorners(bbox, s);
    if (!corners) continue;
    faceCenter = windSurfaceQuadCenter(corners);
    break;
  }
  if (!faceCenter) {
    faceCenter = windWindwardFaceCenter(bbox, windCase, zFallback);
  }

  // Head sits surfaceGap upwind of the windward face plane; tail and label are further upwind.
  const flowHead = faceCenter.clone().addScaledVector(upwindDir, surfaceGap);
  const flowTail = flowHead.clone().addScaledVector(upwindDir, arrowLen);
  const labelPos = flowTail.clone().addScaledVector(upwindDir, labelPad);
  return { flowDir, upwindDir, flowTail, flowHead, labelPos, arrowLen, surfaceGap };
}

function windWallCorners(bbox, surface) {
  const zb = Number(surface.z_bottom);
  const zt = Number(surface.z_top);
  const w = Math.max(Number(surface.width) || 0, 1e-6);
  const side = surface.wall_side || "";
  if (side === "x_max") {
    const x = bbox.x_max;
    return [
      new THREE.Vector3(x, bbox.y_min, zb),
      new THREE.Vector3(x, bbox.y_min + w, zb),
      new THREE.Vector3(x, bbox.y_min + w, zt),
      new THREE.Vector3(x, bbox.y_min, zt),
    ];
  }
  if (side === "x_min") {
    const x = bbox.x_min;
    return [
      new THREE.Vector3(x, bbox.y_min, zb),
      new THREE.Vector3(x, bbox.y_min + w, zb),
      new THREE.Vector3(x, bbox.y_min + w, zt),
      new THREE.Vector3(x, bbox.y_min, zt),
    ];
  }
  if (side === "y_max") {
    const y = bbox.y_max;
    return [
      new THREE.Vector3(bbox.x_min, y, zb),
      new THREE.Vector3(bbox.x_min + w, y, zb),
      new THREE.Vector3(bbox.x_min + w, y, zt),
      new THREE.Vector3(bbox.x_min, y, zt),
    ];
  }
  if (side === "y_min") {
    const y = bbox.y_min;
    return [
      new THREE.Vector3(bbox.x_min, y, zb),
      new THREE.Vector3(bbox.x_min + w, y, zb),
      new THREE.Vector3(bbox.x_min + w, y, zt),
      new THREE.Vector3(bbox.x_min, y, zt),
    ];
  }
  return null;
}

function addWindQuadMesh(corners, color, opacity, group) {
  if (!corners || corners.length !== 4) return;
  const pos = [];
  const tri = [0, 1, 2, 0, 2, 3];
  for (let i = 0; i < tri.length; i++) {
    const p = corners[tri[i]];
    pos.push(p.x, p.y, p.z);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geo.computeVertexNormals();
  const mat = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: opacity,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.renderOrder = 6;
  group.add(mesh);
}

function addWindWallOutline(corners, color, group) {
  if (!corners || corners.length !== 4) return;
  const pts = [];
  for (let i = 0; i < 4; i++) {
    addLinePair(corners[i], corners[(i + 1) % 4], pts);
  }
  addWideLineSegmentsFromPts(
    pts,
    color,
    group,
    7,
    Math.max(loadLineWidthPx() * 1.2, 1.5),
    ALPHA.opaque
  );
}

function formatWindForceKn(value) {
  const n = Number(value);
  if (!isFinite(n)) return "—";
  if (Math.abs(n - Math.round(n)) < 1e-6) return String(Math.round(n));
  return n.toFixed(2);
}

function drawWindOverlay(model, visual, windCase, span) {
  const bbox = visual.bbox;
  if (!bbox || !windCase) return;

  const cx = 0.5 * (bbox.x_min + bbox.x_max);
  const cy = 0.5 * (bbox.y_min + bbox.y_max);
  const zGround = model.bounds ? model.bounds[4] : Number(windCase.story_forces[0]?.z_bottom || 0);
  const flowDir = windFlowDirection3(windCase.flow);

  const footPts = [];
  const zf = zGround;
  addLinePair(
    new THREE.Vector3(bbox.x_min, bbox.y_min, zf),
    new THREE.Vector3(bbox.x_max, bbox.y_min, zf),
    footPts
  );
  addLinePair(
    new THREE.Vector3(bbox.x_max, bbox.y_min, zf),
    new THREE.Vector3(bbox.x_max, bbox.y_max, zf),
    footPts
  );
  addLinePair(
    new THREE.Vector3(bbox.x_max, bbox.y_max, zf),
    new THREE.Vector3(bbox.x_min, bbox.y_max, zf),
    footPts
  );
  addLinePair(
    new THREE.Vector3(bbox.x_min, bbox.y_max, zf),
    new THREE.Vector3(bbox.x_min, bbox.y_min, zf),
    footPts
  );
  addWideLineSegmentsFromPts(
    footPts,
    COLORS.windFootprint,
    windGroup,
    5,
    Math.max(elementLineWidthPx() * 0.85, 1.0),
    ALPHA.windFootprint
  );

  (windCase.surfaces || []).forEach(function (s) {
    const corners = windWallCorners(bbox, s);
    if (!corners) return;
    const isWindward = s.surface_role === "WINDWARD";
    const color = isWindward ? COLORS.windWindward : COLORS.windLeeward;
    addWindQuadMesh(corners, color, ALPHA.windWall, windGroup);
    addWindWallOutline(corners, color, windGroup);
  });

  let zTop = zGround;
  (windCase.surfaces || []).forEach(function (s) {
    zTop = Math.max(zTop, Number(s.z_top) || zGround);
  });
  if (model.bounds) zTop = Math.max(zTop, model.bounds[5]);

  const zMidFallback = 0.5 * (zGround + zTop);
  const flowLayout = windWindwardFlowLayout(bbox, windCase, span, zMidFallback);
  addDirectedArrow(
    flowLayout.flowTail,
    flowLayout.flowHead,
    windGroup,
    COLORS.windFlow,
    loadLineWidthPx() * 0.95,
    0.8,
    20,
    true
  );
  const flowLabel = makeTextSprite(windCase.direction_label || "Wind", span, {
    scaleFactor: loadLabelScaleFactor() * 0.72,
    bg: "rgba(90, 72, 168, 1.0)",
    fg: "#ffffff",
    opaque: true,
    transparent: false,
  });
  flowLabel.position.copy(flowLayout.labelPos);
  flowLabel.renderOrder = 21;
  windLabelGroup.add(flowLabel);

  const maxF = Math.max(
    Number(windCase.max_f_story_kN) || 0,
    ...(windCase.tributary_rows || []).map(function (r) { return Math.abs(Number(r.story_wind_force_kN) || 0); }),
    ...(windCase.story_forces || []).map(function (sf) { return Math.abs(Number(sf.f_story_kN) || 0); }),
    1e-6
  );
  const forceRows = (windCase.tributary_rows && windCase.tributary_rows.length)
    ? windCase.tributary_rows
    : (windCase.story_forces || []);
  forceRows.forEach(function (row) {
    const fKn = Number(row.story_wind_force_kN != null ? row.story_wind_force_kN : row.f_story_kN) || 0;
    const len = Math.max(span * 0.035, (Math.abs(fKn) / maxF) * span * 0.2);
    const z = Number(row.diaphragm_level != null ? row.diaphragm_level : row.z_ref);
    const tail = new THREE.Vector3(cx, cy, z);
    const sign = fKn >= 0 ? 1 : -1;
    const head = tail.clone().addScaledVector(flowDir, len * sign);
    addDirectedArrow(
      tail,
      head,
      windGroup,
      COLORS.windStoryForce,
      loadLineWidthPx(),
      0.85,
      8,
      true
    );
    const labelStory = row.story != null ? row.story : String(row.diaphragm_id || "");
    const label = makeTextSprite(
      labelStory + " F=" + formatWindForceKn(fKn) + "kN",
      span,
      {
        scaleFactor: loadLabelScaleFactor() * 0.82,
        bg: "rgba(20, 83, 45, 0.78)",
        fg: "#ffffff",
      }
    );
    label.position.copy(head).add(new THREE.Vector3(0, 0, span * 0.012));
    label.renderOrder = 17;
    windLabelGroup.add(label);
  });

  (windCase.diaphragm_loads || []).forEach(function (dl) {
    const z = Number(dl.load_level_m);
    const sign = Number(dl.sign) >= 0 ? 1 : -1;
    const axis = String(dl.axis || "X").toUpperCase();
    const dir = axis === "Y"
      ? new THREE.Vector3(0, sign, 0)
      : new THREE.Vector3(sign, 0, 0);
    const len = Math.max(span * 0.1, 0.25);
    const origin = new THREE.Vector3(cx, cy, z);
    addDirectionArrow(
      origin,
      dir,
      len,
      windGroup,
      COLORS.load,
      loadLineWidthPx() * 0.9,
      0.7
    );
    const areaLoad = Number(dl.area_load_kN_m2);
    if (isFinite(areaLoad) && Math.abs(areaLoad) > 1e-9) {
      const tip = origin.clone().addScaledVector(dir, len);
      const dlLabel = makeTextSprite(
        "DIAP " + dl.diaphragm_id + " " + formatWindForceKn(areaLoad) + " kN/m²",
        span,
        {
          scaleFactor: loadLabelScaleFactor() * 0.78,
          bg: LABEL_BG.load,
          fg: "#ffffff",
        }
      );
      dlLabel.position.copy(tip).add(new THREE.Vector3(0, 0, span * 0.01));
      dlLabel.renderOrder = 16;
      windLabelGroup.add(dlLabel);
    }
  });
}

function populateWindCaseSelect() {
  if (!el.windCaseSelect) return;
  const sel = el.windCaseSelect;
  sel.innerHTML = "";
  const cases = (windVisualData && windVisualData.cases) || [];
  if (!cases.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(none)";
    sel.appendChild(opt);
    sel.disabled = true;
    return;
  }
  cases.forEach(function (c) {
    const opt = document.createElement("option");
    opt.value = String(c.wind_case_id);
    opt.textContent = c.name + " (" + (c.direction_label || c.direction) + ", LC" + c.load_case + ")";
    if (selectedWindCaseId != null && c.wind_case_id === selectedWindCaseId) {
      opt.selected = true;
    }
    sel.appendChild(opt);
  });
  if (selectedWindCaseId == null) {
    sel.value = String(cases[0].wind_case_id);
    selectedWindCaseId = cases[0].wind_case_id;
  } else {
    sel.value = String(selectedWindCaseId);
  }
  sel.disabled = !(el.chkWindLoads && el.chkWindLoads.checked);
}

function updateWindControlsAvailability() {
  const hasCases = !!(windVisualData && windVisualData.cases && windVisualData.cases.length);
  const knownEmpty = windVisualStatus === "loaded" && !hasCases;
  if (el.chkWindLoads) {
    el.chkWindLoads.disabled = knownEmpty;
    if (knownEmpty) el.chkWindLoads.checked = false;
  }
  if (el.windCaseSelect) {
    el.windCaseSelect.disabled = !hasCases || !(el.chkWindLoads && el.chkWindLoads.checked);
  }
  updateWindLegendOverlay();
}

function updateWindLegendOverlay() {
  if (!el.windLegendOverlay) return;
  const show = windLoadsShown() && !!windVisualData;
  if (!show) {
    el.windLegendOverlay.hidden = true;
    el.windLegendOverlay.classList.remove("visible");
    return;
  }
  const wc = windCaseById(windVisualData, selectedWindCaseId);
  if (!wc) {
    el.windLegendOverlay.hidden = true;
    el.windLegendOverlay.classList.remove("visible");
    return;
  }
  el.windLegendOverlay.hidden = false;
  el.windLegendOverlay.classList.add("visible");
  if (el.windLegendCase) {
    el.windLegendCase.textContent =
      wc.name + " · " + (wc.direction_label || wc.direction) + " · LC" + wc.load_case
      + " — orange=windward / blue=leeward / green=F_story / purple=wind dir";
  }
}

function nodeExactKey(x, y, z) {
  return String(x) + "\0" + String(y) + "\0" + String(z);
}

function uniqueSortedIds(ids) {
  return Array.from(new Set(ids)).sort(function (a, b) { return a - b; });
}

function pushDuplicateGroups(buckets, buildEntry) {
  const entries = [];
  for (const group of Object.values(buckets)) {
    const ids = uniqueSortedIds(group.ids);
    if (ids.length < 2) continue;
    entries.push(buildEntry(ids, group));
  }
  return entries;
}

function buildColocatedSites(model) {
  if (!model) return [];
  const nm = nodeMap(model);
  const entries = [];

  const nodeBuckets = Object.create(null);
  for (const n of model.nodes || []) {
    const k = nodeExactKey(n.x, n.y, n.z);
    if (!nodeBuckets[k]) nodeBuckets[k] = { ids: [], x: n.x, y: n.y, z: n.z };
    nodeBuckets[k].ids.push(n.id);
  }
  entries.push.apply(entries, pushDuplicateGroups(nodeBuckets, function (ids, group) {
    return { kind: "node", ids: ids, x: group.x, y: group.y, z: group.z };
  }));

  const elemBuckets = Object.create(null);
  for (const e of model.elements || []) {
    const k = String(e.n0) + ":" + String(e.n1);
    if (!elemBuckets[k]) elemBuckets[k] = { ids: [], n0: e.n0, n1: e.n1 };
    elemBuckets[k].ids.push(e.id);
  }
  entries.push.apply(entries, pushDuplicateGroups(elemBuckets, function (ids, group) {
    return { kind: "element", ids: ids, n0: group.n0, n1: group.n1 };
  }));

  const wallBuckets = Object.create(null);
  for (const w of model.wood_rated_walls || []) {
    const nodes = uniqueSortedIds(w.nodes || []);
    if (!nodes.length) continue;
    const k = nodes.join(",");
    if (!wallBuckets[k]) wallBuckets[k] = { ids: [], nodes: nodes };
    wallBuckets[k].ids.push(w.id);
  }
  entries.push.apply(entries, pushDuplicateGroups(wallBuckets, function (ids, group) {
    return { kind: "wall", ids: ids, nodes: group.nodes };
  }));

  const dmemBuckets = Object.create(null);
  for (const m of model.membrane_elements || []) {
    const nodes = uniqueSortedIds(m.nodes || []);
    if (!nodes.length) continue;
    const k = nodes.join(",");
    if (!dmemBuckets[k]) dmemBuckets[k] = { ids: [], nodes: nodes };
    dmemBuckets[k].ids.push(m.id);
  }
  entries.push.apply(entries, pushDuplicateGroups(dmemBuckets, function (ids, group) {
    return { kind: "dmem", ids: ids, nodes: group.nodes };
  }));

  const kindOrder = { node: 0, element: 1, wall: 2, dmem: 3 };
  entries.sort(function (a, b) {
    const ka = kindOrder[a.kind] - kindOrder[b.kind];
    if (ka !== 0) return ka;
    return (a.ids[0] || 0) - (b.ids[0] || 0);
  });
  return entries;
}

function colocatedNodeIds(entry) {
  if (entry.kind === "node") return entry.ids.slice();
  if (entry.kind === "element") return [entry.n0, entry.n1];
  return entry.nodes.slice();
}

function colocatedEntryPosition(entry, model, nm, lc, defFac, deformed) {
  const ids = colocatedNodeIds(entry);
  const pts = [];
  for (const nid of ids) {
    const n = nm[nid];
    if (!n) continue;
    pts.push(nodePosition(n, model, lc, defFac, deformed));
  }
  if (!pts.length) return null;
  const out = new THREE.Vector3();
  for (const p of pts) out.add(p);
  out.multiplyScalar(1 / pts.length);
  return out;
}

function colocatedEntrySummary(entry) {
  if (entry.kind === "node") {
    return "Nodes N[" + entry.ids.join(",") + "]";
  }
  if (entry.kind === "element") {
    return "Elements E[" + entry.ids.join(",") + "] (" + entry.n0 + "-" + entry.n1 + ")";
  }
  if (entry.kind === "wall") {
    return "Walls W[" + entry.ids.join(",") + "] nodes[" + entry.nodes.join(",") + "]";
  }
  return "DMEM D[" + entry.ids.join(",") + "] nodes[" + entry.nodes.join(",") + "]";
}

function colocatedEntryLabel(entry, model) {
  const nm = nodeMap(model);
  let coordText = "";
  if (entry.kind === "node") {
    coordText = "(" + formatCoordMm(entry.x) + ", " + formatCoordMm(entry.y) + ", " + formatCoordMm(entry.z) + ") ";
  } else {
    const ids = colocatedNodeIds(entry);
    const anchor = nm[ids[0]];
    if (anchor) {
      coordText = "(" + formatCoordMm(anchor.x) + ", " + formatCoordMm(anchor.y) + ", " + formatCoordMm(anchor.z) + ") ";
    }
  }
  return coordText + colocatedEntrySummary(entry);
}

function formatCoordMm(v) {
  return (Number(v) * 1000).toFixed(1);
}

function drawColocatedOverlay(model, opts) {
  const { lc, defFac, deformed, span, nm, group } = opts;
  const entries = buildColocatedSites(model);
  colocatedSitesCache = entries;
  if (!entries.length) return;

  const r = Math.max(supportGizmoSize(model) * 0.45, span * 0.006, 0.015);
  const geo = new THREE.SphereGeometry(r, 14, 10);
  const mat = new THREE.MeshBasicMaterial({
    color: COLORS.colocated,
    depthTest: true,
    transparent: true,
    opacity: 0.85,
  });

  for (const entry of entries) {
    const p = colocatedEntryPosition(entry, model, nm, lc, defFac, deformed);
    if (!p) continue;
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.copy(p);
    mesh.renderOrder = 20;
    group.add(mesh);
  }
}

function updateColocatedLegendOverlay() {
  if (!el.colocatedLegendOverlay) return;
  const show = !!(el.chkColocated && el.chkColocated.checked);
  if (!show) {
    el.colocatedLegendOverlay.hidden = true;
    el.colocatedLegendOverlay.classList.remove("visible");
    return;
  }
  const entries = colocatedSitesCache || (currentModel ? buildColocatedSites(currentModel) : []);
  el.colocatedLegendOverlay.hidden = false;
  el.colocatedLegendOverlay.classList.add("visible");
  if (el.colocatedLegendCount) {
    el.colocatedLegendCount.textContent = entries.length
      ? entries.length + " duplicate group(s) — exact node connectivity match"
      : "No colocated entities found";
  }
  if (el.colocatedLegendList) {
    el.colocatedLegendList.innerHTML = "";
    for (const entry of entries) {
      const row = document.createElement("div");
      row.className = "colocated-legend-row";
      row.textContent = currentModel
        ? colocatedEntryLabel(entry, currentModel)
        : colocatedEntrySummary(entry);
      el.colocatedLegendList.appendChild(row);
    }
  }
}

async function loadWindVisualForCurrentModel() {
  const path = getCurrentModelPath();
  windVisualData = null;
  selectedWindCaseId = null;
  windVisualStatus = "idle";
  if (!path) {
    windVisualStatus = "loaded";
    populateWindCaseSelect();
    updateWindControlsAvailability();
    return;
  }
  try {
    const view = await fetchApiJson("/api/loads/wind?path=" + encodeURIComponent(path));
    if (view.found && view.visual && view.visual.cases && view.visual.cases.length) {
      windVisualData = view.visual;
      if (displayPrefs.windCaseId != null && windCaseById(windVisualData, displayPrefs.windCaseId)) {
        selectedWindCaseId = displayPrefs.windCaseId;
      } else {
        selectedWindCaseId = pickWindCaseIdForLc(windVisualData);
      }
    }
  } catch (ex) {
    console.warn("Wind visual load failed:", ex.message);
  }
  windVisualStatus = "loaded";
  populateWindCaseSelect();
  updateWindControlsAvailability();
}

async function loadPracticeSummaryForCurrentModel() {
  const path = getCurrentModelPath();
  practiceSummaryData = null;
  if (!path || !currentModel || !analysisComplete(currentModel)) return;
  try {
    const view = await fetchApiJson("/api/practice/summary?path=" + encodeURIComponent(path));
    if (view && view.eccentricity_rows && view.eccentricity_rows.length) {
      practiceSummaryData = view;
    }
  } catch (ex) {
    console.warn("Practice summary load failed:", ex.message);
  }
}

function practiceStoryZMap(practice) {
  const rows = practice && practice.story_rows ? practice.story_rows.slice() : [];
  rows.sort(function (a, b) {
    const za = Number(a.elevation);
    const zb = Number(b.elevation);
    if (isFinite(za) && isFinite(zb) && za !== zb) return za - zb;
    const ra = Number(String(a.story).replace(/[^\d.-]/g, ""));
    const rb = Number(String(b.story).replace(/[^\d.-]/g, ""));
    if (isFinite(ra) && isFinite(rb) && ra !== rb) return ra - rb;
    return String(a.story).localeCompare(String(b.story), "ja", { numeric: true });
  });
  const map = new Map();
  for (let i = 0; i < rows.length; i++) {
    const s = rows[i];
    const story = String(s.story);
    const elev = Number(s.elevation);
    if (!isFinite(elev)) continue;
    const nextElev = i + 1 < rows.length ? Number(rows[i + 1].elevation) : NaN;
    let z;
    if (isFinite(nextElev)) {
      z = 0.5 * (elev + nextElev);
    } else {
      const top = Number(s.top_elevation != null ? s.top_elevation : s.elevation);
      const height = Number(s.height);
      const topElev = isFinite(top) && top !== elev ? top : (isFinite(height) ? elev + height : elev);
      z = 0.5 * (elev + topElev);
    }
    if (isFinite(z)) map.set(story, z);
  }
  return map;
}

function addPracticeCenterMarker(point, color, text, span, group, offsetSign) {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute([point.x, point.y, point.z], 3));
  const mat = nodePointsMaterial({
    color: color,
    size: 16,
    sizeAttenuation: false,
    depthTest: false,
  });
  const marker = new THREE.Points(geo, mat);
  marker.renderOrder = 24;
  group.add(marker);

  const label = makeTextSprite(text, span, {
    scaleFactor: nodeLabelScaleFactor() * 0.9,
    bg: "rgba(0, 0, 0, 1.0)",
    fg: colorHex(color),
  });
  const d = Math.max(span * 0.012, 0.05);
  label.position.copy(point).add(new THREE.Vector3(offsetSign * d, d, d));
  label.renderOrder = 25;
  group.add(label);
}

function isPracticeCenterCoord(value) {
  return value != null && value !== "" && isFinite(Number(value));
}

function isPracticeCenterPoint(x, y, model) {
  if (!isPracticeCenterCoord(x) || !isPracticeCenterCoord(y)) return false;
  if (!model || !Array.isArray(model.bounds) || model.bounds.length < 6) return true;
  const xmin = Number(model.bounds[0]);
  const ymin = Number(model.bounds[1]);
  const xmax = Number(model.bounds[3]);
  const ymax = Number(model.bounds[4]);
  if (![xmin, ymin, xmax, ymax].every(isFinite)) return true;
  const span = Math.max(xmax - xmin, ymax - ymin, 1);
  const margin = span * 2;
  const px = Number(x);
  const py = Number(y);
  return px >= xmin - margin && px <= xmax + margin && py >= ymin - margin && py <= ymax + margin;
}

function drawPracticeCentersOverlay(model, practice, span) {
  if (!practice || !practice.eccentricity_rows || !practice.eccentricity_rows.length) return;
  const zByStory = practiceStoryZMap(practice);
  const zFallback = model.bounds ? model.bounds[5] : 0;
  const lift = Math.max(span * 0.008, 0.03);
  for (const row of practice.eccentricity_rows) {
    const story = String(row.story == null ? "" : row.story);
    const z = (zByStory.has(story) ? zByStory.get(story) : zFallback) + lift;
    if (isPracticeCenterPoint(row.xg, row.yg, model)) {
      addPracticeCenterMarker(
        new THREE.Vector3(Number(row.xg), Number(row.yg), z),
        COLORS.centerOfMass,
        "CoG " + story,
        span,
        practiceCenterGroup,
        -1
      );
    }
    if (isPracticeCenterPoint(row.xs, row.ys, model)) {
      addPracticeCenterMarker(
        new THREE.Vector3(Number(row.xs), Number(row.ys), z),
        COLORS.centerOfRigidity,
        "CoR " + story,
        span,
        practiceCenterGroup,
        1
      );
    }
  }
}

function syncLcToWindCase(windCase) {
  if (!windCase || !el.lcSelect) return;
  const lcVal = String(windCase.load_case);
  if (String(el.lcSelect.value) === lcVal) return;
  const opt = Array.from(el.lcSelect.options).find(function (o) { return o.value === lcVal; });
  if (opt) el.lcSelect.value = lcVal;
}

function drawElementInputLoads(model, opts) {
  const {
    lc, defFac, deformed, span, nm, em, arrowBase, maxWMag,
    showValues, loadLabelScale,
  } = opts;
  const loads = model.element_loads;
  if (!loads || loads.length === 0) return;

  for (const ld of loads) {
    if (String(ld.lc) !== String(lc)) continue;
    if (!shouldDrawElementLoad(ld)) continue;
    const e = em[ld.elem];
    if (!e) continue;
    if (!isMemberElementVisible(e.id)) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;

    const w = ld.w;
    if (elementLoadMagnitude(w) < 1e-9) continue;

    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    drawTrapezoidalDistributedLoad(ld, e, p0, p1, {
      arrowBase,
      maxWMag,
      span,
      loadLabelScale,
      showValues,
    });
  }
}

function diaphragmLoadType(dl) {
  return String(dl && dl.type != null ? dl.type : "").toUpperCase();
}

function diaphragmCentroid(model, diapId, nm, lc, defFac, deformed) {
  const pts = [];
  for (const mem of model.membrane_elements || []) {
    if (mem.diaphragm_id !== diapId) continue;
    for (const nid of mem.nodes || []) {
      const n = nm[nid];
      if (n) pts.push(nodePosition(n, model, lc, defFac, deformed));
    }
  }
  if (pts.length === 0) return null;
  const c = new THREE.Vector3();
  for (const p of pts) c.add(p);
  return c.multiplyScalar(1 / pts.length);
}

function membraneMemberCentroid(model, memberId, nm, lc, defFac, deformed) {
  const mem = (model.membrane_elements || []).find(function (m) { return m.id === memberId; });
  if (!mem || !mem.nodes || mem.nodes.length < 3) return null;
  const pts = [];
  for (const nid of mem.nodes) {
    const n = nm[nid];
    if (n) pts.push(nodePosition(n, model, lc, defFac, deformed));
  }
  if (pts.length === 0) return null;
  const c = new THREE.Vector3();
  for (const p of pts) c.add(p);
  return c.multiplyScalar(1 / pts.length);
}

function maxDiaphragmLoadMag(model, lc) {
  let max = 0;
  for (const dl of model.diaphragm_loads || []) {
    if (String(dl.lc) !== String(lc)) continue;
    const lt = diaphragmLoadType(dl);
    if (lt === "AREA" || lt === "LINE" || lt === "MEMBER_TRANSFER") {
      max = Math.max(max, Math.abs(dl.px), Math.abs(dl.py));
    } else if (lt === "MASS") {
      max = Math.max(max, Math.abs(dl.mass) * Math.max(Math.abs(dl.ax), Math.abs(dl.ay), 1));
    } else if (lt === "WEIGHT") {
      max = Math.max(max, Math.abs(dl.weight) * Math.max(Math.abs(dl.ax), Math.abs(dl.ay), 1));
    }
  }
  return max;
}

function formatDlodPressureLabel(mag) {
  if (Math.abs(mag) < 1e-9) return "";
  return formatReactionValue(mag) + " kN/m²";
}

function quantizeDlodPointKey(p) {
  const q = (v) => Math.round(v * 1e4);
  return q(p.x) + "," + q(p.y) + "," + q(p.z);
}

function dlodEdgeKey(p0, p1) {
  const k0 = quantizeDlodPointKey(p0);
  const k1 = quantizeDlodPointKey(p1);
  return k0 < k1 ? k0 + "|" + k1 : k1 + "|" + k0;
}

function registerDlodTriangleEdge(edgeMap, p0, p1) {
  const key = dlodEdgeKey(p0, p1);
  let entry = edgeMap.get(key);
  if (!entry) {
    entry = { count: 0, a: p0.clone(), b: p1.clone() };
    edgeMap.set(key, entry);
  }
  entry.count += 1;
}

function boundaryEdgesFromMap(edgeMap) {
  const edgePts = [];
  for (const entry of edgeMap.values()) {
    if (entry.count !== 1) continue;
    edgePts.push(
      entry.a.x, entry.a.y, entry.a.z,
      entry.b.x, entry.b.y, entry.b.z
    );
  }
  return edgePts;
}

function collectMembraneEnvelope(model, opts) {
  const { diapId, memberId, nm, lc, defFac, deformed } = opts;
  const edgeMap = new Map();
  for (const mem of model.membrane_elements || []) {
    if (diapId != null && mem.diaphragm_id !== diapId) continue;
    if (memberId != null && mem.id !== memberId) continue;
    const ids = mem.nodes;
    if (!ids || ids.length !== 3) continue;
    const n0 = nm[ids[0]];
    const n1 = nm[ids[1]];
    const n2 = nm[ids[2]];
    if (!n0 || !n1 || !n2) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const p2 = nodePosition(n2, model, lc, defFac, deformed);
    registerDlodTriangleEdge(edgeMap, p0, p1);
    registerDlodTriangleEdge(edgeMap, p1, p2);
    registerDlodTriangleEdge(edgeMap, p2, p0);
  }
  return { edgePts: boundaryEdgesFromMap(edgeMap) };
}

function addDlodEnvelopeOutline(edgePts) {
  if (edgePts.length < 6) return;
  addWideLineSegmentsFromPts(
    edgePts,
    COLORS.load,
    modelGroup,
    6,
    Math.max(loadLineWidthPx() * 1.15, 1.0),
    null,
    true
  );
}

function dlodLineEnvelopeHalfWidth(span) {
  return Math.max(span * 0.012, 0.06);
}

function horizontalPerpToSegment(p0, p1) {
  const along = new THREE.Vector3().subVectors(p1, p0);
  if (along.lengthSq() < 1e-18) return null;
  along.z = 0;
  if (along.lengthSq() < 1e-18) return null;
  along.normalize();
  const perp = new THREE.Vector3(-along.y, along.x, 0);
  if (perp.lengthSq() < 1e-18) return null;
  return perp.normalize();
}

function addDlodLineEnvelope(p0, p1, span) {
  const perp = horizontalPerpToSegment(p0, p1);
  if (!perp) return;
  const halfW = dlodLineEnvelopeHalfWidth(span);
  const off = perp.clone().multiplyScalar(halfW);
  const a = p0.clone().add(off);
  const b = p0.clone().sub(off);
  const c = p1.clone().sub(off);
  const d = p1.clone().add(off);
  const edgePts = [
    a.x, a.y, a.z, b.x, b.y, b.z,
    b.x, b.y, b.z, c.x, c.y, c.z,
    c.x, c.y, c.z, d.x, d.y, d.z,
    d.x, d.y, d.z, a.x, a.y, a.z,
  ];
  addDlodEnvelopeOutline(edgePts);
}

function drawDlodMembraneEnvelope(model, diapId, memberId, nm, lc, defFac, deformed) {
  const env = collectMembraneEnvelope(model, {
    diapId: diapId,
    memberId: memberId,
    nm: nm,
    lc: lc,
    defFac: defFac,
    deformed: deformed,
  });
  if (env.edgePts.length > 0) addDlodEnvelopeOutline(env.edgePts);
}

function addDlodHorizontalArrow(origin, hx, hy, arrowBase, maxMag, span, loadLabelScale, showValues, labelPrefix) {
  const comps = [
    { val: hx, dir: new THREE.Vector3(1, 0, 0), name: "Px" },
    { val: hy, dir: new THREE.Vector3(0, 1, 0), name: "Py" },
  ];
  for (const c of comps) {
    if (Math.abs(c.val) < 1e-9) continue;
    const sign = c.val >= 0 ? 1 : -1;
    const dir = c.dir.clone().multiplyScalar(sign);
    const mag = Math.abs(c.val);
    const len = scaledReactionArrowLength(arrowBase, mag, maxMag);
    const tip = addLoadArrow(origin, dir, len, modelGroup);
    if (showValues && tip) {
      const text = (labelPrefix ? labelPrefix + " " : "") + c.name + " " + formatDlodPressureLabel(mag);
      addLoadValueLabel(
        text,
        loadValueLabelPoint(origin, tip, span, loadLabelScale),
        span,
        loadLabelScale,
        labelGroup
      );
    }
  }
}

function drawDiaphragmInputLoads(model, opts) {
  if (!shouldDrawDiaphragmLoad()) return;
  const {
    lc, defFac, deformed, span, nm, arrowBase, maxWMag, showValues, loadLabelScale,
  } = opts;
  const loads = model.diaphragm_loads;
  if (!loads || loads.length === 0) return;

  for (const dl of loads) {
    if (String(dl.lc) !== String(lc)) continue;
    const lt = diaphragmLoadType(dl);
    const prefix = "DIAP " + dl.diaphragm_id;

    if (lt === "AREA") {
      drawDlodMembraneEnvelope(model, dl.diaphragm_id, null, nm, lc, defFac, deformed);
      const origin = diaphragmCentroid(model, dl.diaphragm_id, nm, lc, defFac, deformed);
      if (!origin) continue;
      addDlodHorizontalArrow(
        origin, dl.px, dl.py, arrowBase, maxWMag, span, loadLabelScale, showValues, prefix
      );
      continue;
    }

    if (lt === "LINE") {
      const ids = dl.nodes || [];
      if (ids.length < 2) continue;
      const n0 = nm[ids[0]];
      const n1 = nm[ids[1]];
      if (!n0 || !n1) continue;
      const p0 = nodePosition(n0, model, lc, defFac, deformed);
      const p1 = nodePosition(n1, model, lc, defFac, deformed);
      addDlodLineEnvelope(p0, p1, span);
      const mid = p0.clone().add(p1).multiplyScalar(0.5);
      addDlodHorizontalArrow(
        mid, dl.px, dl.py, arrowBase, maxWMag, span, loadLabelScale, showValues, prefix + " LINE"
      );
      continue;
    }

    if (lt === "MEMBER_TRANSFER") {
      drawDlodMembraneEnvelope(model, null, dl.member_id, nm, lc, defFac, deformed);
      const origin = membraneMemberCentroid(model, dl.member_id, nm, lc, defFac, deformed)
        || diaphragmCentroid(model, dl.diaphragm_id, nm, lc, defFac, deformed);
      if (!origin) continue;
      addDlodHorizontalArrow(
        origin, dl.px, dl.py, arrowBase, maxWMag, span, loadLabelScale, showValues, prefix + " MBTR"
      );
      continue;
    }

    if (lt === "MASS" || lt === "WEIGHT") {
      drawDlodMembraneEnvelope(model, dl.diaphragm_id, null, nm, lc, defFac, deformed);
      const origin = diaphragmCentroid(model, dl.diaphragm_id, nm, lc, defFac, deformed);
      if (!origin) continue;
      const ax = Number(dl.ax) || 0;
      const ay = Number(dl.ay) || 0;
      const scalar = lt === "MASS" ? Number(dl.mass) || 0 : Number(dl.weight) || 0;
      if (Math.abs(ax) > 1e-9 || Math.abs(ay) > 1e-9) {
        const dir = new THREE.Vector3(ax, ay, 0);
        const mag = dir.length();
        if (mag > 1e-9) {
          dir.multiplyScalar(1 / mag);
          const eff = scalar * mag;
          const len = scaledReactionArrowLength(arrowBase, eff, maxWMag);
          const tip = addLoadArrow(origin, dir, len, modelGroup);
          if (showValues && tip) {
            const kind = lt === "MASS" ? "M" : "W";
            addLoadValueLabel(
              prefix + " " + kind + "=" + formatReactionValue(scalar) + " ax=" + formatReactionValue(ax) + " ay=" + formatReactionValue(ay),
              loadValueLabelPoint(origin, tip, span, loadLabelScale),
              span,
              loadLabelScale,
              labelGroup
            );
          }
        }
      } else if (showValues && Math.abs(scalar) > 1e-9) {
        const kind = lt === "MASS" ? "M" : "W";
        addLoadValueLabel(
          prefix + " " + kind + "=" + formatReactionValue(scalar),
          origin.clone().add(new THREE.Vector3(0, 0, span * 0.01)),
          span,
          loadLabelScale,
          labelGroup
        );
      }
    }
  }
}

function drawTrapezoidalDistributedLoad(ld, e, p0, p1, opts) {
  const { arrowBase, maxWMag, span, loadLabelScale, showValues } = opts;
  const w = ld.w;
  const axes = distributedLoadAxes(e, ld.global);
  if (!axes) {
    drawSingleDistributedLoadArrow(ld, e, p0, p1, opts);
    return;
  }

  const along = new THREE.Vector3().subVectors(p1, p0);
  const elemLen = along.length();
  if (elemLen < 1e-9) return;
  along.normalize();

  const loadColor = COLORS.load;
  const hasProfile = Array.isArray(ld.w_profile) && ld.w_profile.length >= 2;

  for (let axisIdx = 0; axisIdx < 3; axisIdx++) {
    const w0 = hasProfile ? ld.w_profile[0][axisIdx + 1] : w[axisIdx];
    const w1 = hasProfile ? ld.w_profile[ld.w_profile.length - 1][axisIdx + 1] : w[axisIdx + 3];
    if (hasProfile) {
      let maxAbs = 0;
      for (let i = 0; i < ld.w_profile.length; i++) {
        maxAbs = Math.max(maxAbs, Math.abs(ld.w_profile[i][axisIdx + 1]));
      }
      if (maxAbs < PRES_ZERO) continue;
    } else {
      if (Math.abs(w0) < PRES_ZERO && Math.abs(w1) < PRES_ZERO) continue;
    }

    const axis = axes[axisIdx];
    const isParallel = Math.abs(axis.dot(along)) > 0.999;
    const outlineOffsets = [];

    for (let j = 0; j <= LOAD_DIV_NUM; j++) {
      const t = j / LOAD_DIV_NUM;
      const pt = elemPointAlong(p0, p1, t);
      const wAt = hasProfile ? profileAxisValue(ld.w_profile, axisIdx, t) : (w0 + t * (w1 - w0));
      if (Math.abs(wAt) < PRES_ZERO) continue;

      const vOff = distributedLoadOffset(axis, wAt, arrowBase, maxWMag);

      if (isParallel) {
        if (j === LOAD_DIV_NUM) continue;
        const tip = pt.clone().add(vOff);
        addDirectedArrow(pt, tip, modelGroup, loadColor, loadLineWidthPx(), undefined, undefined, true);
      } else {
        const ept = pt.clone().sub(vOff);
        outlineOffsets.push(ept);
        addDirectedArrow(ept, pt, modelGroup, loadColor, loadLineWidthPx(), undefined, undefined, true);
      }
    }

    if (!isParallel && outlineOffsets.length >= 2) {
      const outlinePts = [];
      for (let i = 0; i < outlineOffsets.length - 1; i++) {
        addLinePair(outlineOffsets[i], outlineOffsets[i + 1], outlinePts);
      }
      addWideLineSegmentsFromPts(outlinePts, loadColor, modelGroup, 4, loadLineWidthPx(), null, true);
      if (!isAreaLoad(ld)) {
        addDirectedArrow(outlineOffsets[0], p0, modelGroup, loadColor, loadLineWidthPx(), undefined, undefined, true);
        addDirectedArrow(
          outlineOffsets[outlineOffsets.length - 1],
          p1,
          modelGroup,
          loadColor,
          loadLineWidthPx(),
          undefined,
          undefined,
          true
        );
      } else {
        const endPts = [];
        addLinePair(outlineOffsets[0], p0, endPts);
        addLinePair(outlineOffsets[outlineOffsets.length - 1], p1, endPts);
        addWideLineSegmentsFromPts(endPts, loadColor, modelGroup, 4, loadLineWidthPx(), null, true);
      }
    }
  }

  if (showValues) {
    const t = 0.5;
    const pt = elemPointAlong(p0, p1, t);
    const wGlob = hasProfile ? profileLoadVector(ld.w_profile, e, t, ld.global) : elementLoadVector(w, t, e, ld.global);
    if (wGlob.lengthSq() > 1e-18) {
      const mag = wGlob.length();
      const dir = wGlob.clone().normalize();
      const labelText = formatLoadDistributedValue(
        mag,
        isGravityLoad(ld),
        isAreaLoad(ld),
        ld.display_value
      );
      if (labelText) {
        const seg = distributedArrowSegmentAt(ld, axes, p0, p1, t, hasProfile, w, arrowBase, maxWMag);
        const tail = seg ? seg.tail : pt.clone();
        const tip = seg ? seg.tip : pt.clone().addScaledVector(dir, scaledReactionArrowLength(arrowBase, mag, maxWMag));
        addLoadValueLabel(
          labelText,
          loadValueLabelPoint(tail, tip, span, loadLabelScale),
          span,
          loadLabelScale,
          labelGroup
        );
      }
    }
    drawDistributedEndLabels(ld, e, p0, p1, opts);
  }
}

function drawSingleDistributedLoadArrow(ld, e, p0, p1, opts) {
  const { arrowBase, maxWMag, span, loadLabelScale, showValues } = opts;
  const w = ld.w;
  const t = 0.5;
  const pt = elemPointAlong(p0, p1, t);
  const wGlob = elementLoadVector(w, t, e, ld.global);
  if (wGlob.lengthSq() < 1e-18) return;
  const mag = wGlob.length();
  const dir = wGlob.clone().normalize();
  const len = scaledReactionArrowLength(arrowBase, mag, maxWMag);
  const tip = addLoadArrow(pt, dir, len, modelGroup);
  if (showValues && tip) {
    const labelText = formatLoadDistributedValue(
      mag,
      isGravityLoad(ld),
      isAreaLoad(ld),
      ld.display_value
    );
    if (labelText) {
      addLoadValueLabel(
        labelText,
        loadValueLabelPoint(pt, tip, span, loadLabelScale),
        span,
        loadLabelScale,
        labelGroup
      );
    }
  }
}

function drawDistributedEndLabels(ld, e, p0, p1, opts) {
  const { arrowBase, maxWMag, span, loadLabelScale } = opts;
  const hasProfile = Array.isArray(ld.w_profile) && ld.w_profile.length >= 2;
  const w = ld.w;
  const axes = distributedLoadAxes(e, ld.global);
  let bestAxis = 0;
  let bestMag = 0;
  for (let i = 0; i < 3; i++) {
    let m = 0;
    if (hasProfile) {
      for (let k = 0; k < ld.w_profile.length; k++) {
        m = Math.max(m, Math.abs(ld.w_profile[k][i + 1]));
      }
    } else {
      const wi = w[i];
      const wj = w[i + 3];
      m = Math.max(Math.abs(wi), Math.abs(wj));
    }
    if (m > bestMag) {
      bestMag = m;
      bestAxis = i;
    }
  }
  if (bestMag < 1e-9) return;

  const ends = [
    { t: 0, val: hasProfile ? ld.w_profile[0][bestAxis + 1] : w[bestAxis] },
    { t: 1, val: hasProfile ? ld.w_profile[ld.w_profile.length - 1][bestAxis + 1] : w[bestAxis + 3] },
  ];
  for (const end of ends) {
    const pt = elemPointAlong(p0, p1, end.t);
    const wGlob = hasProfile ? profileLoadVector(ld.w_profile, e, end.t, ld.global) : elementLoadVector(w, end.t, e, ld.global);
    if (wGlob.lengthSq() < 1e-18) continue;
    const seg = distributedArrowSegmentAt(ld, axes, p0, p1, end.t, hasProfile, w, arrowBase, maxWMag);
    const dir = wGlob.clone().normalize();
    const tail = seg ? seg.tail : pt.clone();
    const tip = seg ? seg.tip : pt.clone().addScaledVector(dir, scaledReactionArrowLength(arrowBase, Math.abs(end.val), maxWMag));
    const text = formatReactionValue(end.val);
    addLoadValueLabel(
      text,
      loadValueLabelPoint(tail, tip, span, loadLabelScale),
      span,
      loadLabelScale,
      labelGroup
    );
  }
}

function distributedLoadOffset(axis, wAt, arrowBase, maxWMag) {
  const len = scaledReactionArrowLength(arrowBase, Math.abs(wAt), maxWMag);
  const sgn = wAt >= 0 ? 1 : -1;
  return axis.clone().multiplyScalar(len * sgn);
}

function distributedArrowSegmentAt(ld, axes, p0, p1, t, hasProfile, w, arrowBase, maxWMag) {
  if (!axes) return null;
  const axisIdx = dominantAxisAtT(ld, t, hasProfile, w);
  const axis = axes[axisIdx];
  if (!axis) return null;
  const pt = elemPointAlong(p0, p1, t);
  const wAt = hasProfile ? profileAxisValue(ld.w_profile, axisIdx, t) : (w[axisIdx] + t * (w[axisIdx + 3] - w[axisIdx]));
  if (Math.abs(wAt) < PRES_ZERO) return null;
  const along = new THREE.Vector3().subVectors(p1, p0).normalize();
  const isParallel = Math.abs(axis.dot(along)) > 0.999;
  const vOff = distributedLoadOffset(axis, wAt, arrowBase, maxWMag);
  if (isParallel) {
    return { tail: pt.clone(), tip: pt.clone().add(vOff) };
  }
  const ept = pt.clone().sub(vOff);
  return { tail: ept, tip: pt.clone() };
}

function dominantAxisAtT(ld, t, hasProfile, w) {
  const comps = hasProfile
    ? [
        profileAxisValue(ld.w_profile, 0, t),
        profileAxisValue(ld.w_profile, 1, t),
        profileAxisValue(ld.w_profile, 2, t),
      ]
    : [
        w[0] + t * (w[3] - w[0]),
        w[1] + t * (w[4] - w[1]),
        w[2] + t * (w[5] - w[2]),
      ];
  let idx = 0;
  let best = Math.abs(comps[0]);
  for (let i = 1; i < 3; i++) {
    const a = Math.abs(comps[i]);
    if (a > best) {
      best = a;
      idx = i;
    }
  }
  return idx;
}

function profileAxisValue(profile, axisIdx, t) {
  if (!Array.isArray(profile) || profile.length === 0) return 0;
  if (t <= profile[0][0]) return profile[0][axisIdx + 1];
  for (let i = 0; i < profile.length - 1; i++) {
    const p0 = profile[i];
    const p1 = profile[i + 1];
    if (t > p1[0]) continue;
    const dt = p1[0] - p0[0];
    if (Math.abs(dt) < PRES_ZERO) return p0[axisIdx + 1];
    const r = (t - p0[0]) / dt;
    return p0[axisIdx + 1] + r * (p1[axisIdx + 1] - p0[axisIdx + 1]);
  }
  return profile[profile.length - 1][axisIdx + 1];
}

function profileLoadVector(profile, elem, t, isGlobal) {
  const wx = profileAxisValue(profile, 0, t);
  const wy = profileAxisValue(profile, 1, t);
  const wz = profileAxisValue(profile, 2, t);
  return elementLoadVector([wx, wy, wz, wx, wy, wz], 0, elem, isGlobal);
}

function formatReactionValue(val) {
  if (Math.abs(val) < 1e-6) return "0";
  return val.toFixed(1);
}

function reactionForceIsZeroDisplay(fval) {
  if (Math.abs(fval) < 1e-6) return true;
  return Math.abs(parseFloat(fval.toFixed(1))) < 1e-9;
}

function makeReactionForceLabelSprite(text, span, color, scaleFactor) {
  return makeTextSprite(text, span, {
    bg: "transparent",
    fg: colorHex(color),
    pad: 2,
    scaleFactor: scaleFactor,
    transparent: true,
    alphaTest: 0.01,
    labelPremultiplied: true,
  });
}

function supportReactsForLc(model, s, lcKey) {
  if (s.reacts) {
    if (s.reacts[lcKey]) return s.reacts[lcKey];
    const alt = String(Number(lcKey));
    if (s.reacts[alt]) return s.reacts[alt];
  }
  for (const r of model.reactions || []) {
    if (r.node === s.node && String(r.lc) === lcKey) {
      return reactionRecordToArray(r);
    }
  }
  return null;
}

function modelHasReactionData(model, lcKey) {
  enrichModelReactions(model);
  for (const s of model.supports || []) {
    if (supportReactsForLc(model, s, lcKey)) return true;
  }
  return false;
}

function computeReactionTotals(model, lcKey) {
  enrichModelReactions(model);
  const totals = [0, 0, 0, 0, 0, 0];
  let count = 0;
  for (const s of model.supports || []) {
    const r = supportReactsForLc(model, s, lcKey);
    if (!r) continue;
    count += 1;
    for (let i = 0; i < 6; i++) totals[i] += r[i];
  }
  if (count === 0) return null;
  return {
    tx: totals[0], ty: totals[1], tz: totals[2],
    rx: totals[3], ry: totals[4], rz: totals[5],
    count: count,
  };
}

function orientMeshAxisX(mesh, dir) {
  const xAxis = dir.clone().normalize();
  let refUp = new THREE.Vector3(0, 0, 1);
  if (Math.abs(xAxis.dot(refUp)) > 0.92) {
    refUp = new THREE.Vector3(0, 1, 0);
  }
  const yAxis = new THREE.Vector3().crossVectors(refUp, xAxis).normalize();
  const zAxis = new THREE.Vector3().crossVectors(xAxis, yAxis).normalize();
  mesh.setRotationFromMatrix(new THREE.Matrix4().makeBasis(xAxis, yAxis, zAxis));
}

function createLabelTexture(canvas, premultiplyOnUpload, crisp) {
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  const filt = crisp ? THREE.NearestFilter : THREE.LinearFilter;
  tex.minFilter = filt;
  tex.magFilter = filt;
  // Keep canvas label colors consistent with line/material colors.
  if ("colorSpace" in tex && THREE.SRGBColorSpace) {
    tex.colorSpace = THREE.SRGBColorSpace;
  }
  tex.premultiplyAlpha = !!premultiplyOnUpload;
  if (renderer && renderer.capabilities) {
    tex.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
  }
  return tex;
}

function drawLabelCanvasText(ctx, text, x, y, fg, opts) {
  const quality = opts.quality || 1;
  if (opts.textOutline) {
    ctx.lineJoin = "round";
    ctx.miterLimit = 2;
    ctx.strokeStyle = opts.outlineColor || fg;
    ctx.lineWidth = Math.max(2, quality * 3);
    ctx.strokeText(text, x, y);
  }
  ctx.fillStyle = fg;
  ctx.fillText(text, x, y);
}

function buildLabelCanvas(text, span, opts) {
  opts = opts || {};
  const bgSpecified = Object.prototype.hasOwnProperty.call(opts, "bg");
  const bg = bgSpecified ? opts.bg : "rgba(0,0,0," + ALPHA.labelDefaultBg + ")";
  const fg = opts.fg || "#ffffff";
  const pad = opts.pad != null ? opts.pad : 4;
  const factor = opts.scaleFactor != null ? opts.scaleFactor : 0.06;
  const quality = opts.qualityScale != null
    ? opts.qualityScale
    : labelTextureQualityScale(factor);
  const baseFs = 28;

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const fs = baseFs * quality;
  const padPx = pad * quality;
  const fontSpec = fs + "px monospace";

  ctx.font = fontSpec;
  const textW = ctx.measureText(text).width;
  canvas.width = Math.ceil(textW + padPx * 2);
  canvas.height = fs + padPx * 2;

  ctx.font = fontSpec;
  ctx.imageSmoothingEnabled = true;
  if (ctx.imageSmoothingQuality) {
    ctx.imageSmoothingQuality = "high";
  }
  if (ctx.textRendering) {
    ctx.textRendering = "optimizeLegibility";
  }

  if (bg != null && bg !== "transparent") {
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  const textY = quality * (baseFs + pad - 2);
  drawLabelCanvasText(ctx, text, padPx, textY, fg, { quality: quality, textOutline: opts.textOutline });

  if (opts.solidAlpha) {
    solidifyCanvasForeground(canvas, fg);
  }

  const labelPremultiplied = !!(
    opts.labelPremultiplied
    || opts.textOutline
    || (opts.opaque && (bg == null || bg === "transparent") && !opts.solidAlpha)
  );

  const worldH = span * factor;
  const worldW = worldH * (canvas.width / canvas.height);
  return { canvas, labelPremultiplied, worldW, worldH };
}

function makeTextPlaneMesh(text, span, opts) {
  const { canvas, labelPremultiplied, worldW, worldH } = buildLabelCanvas(text, span, opts);
  const tex = createLabelTexture(canvas, labelPremultiplied, !!opts.crispLabel);
  const mat = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    side: THREE.DoubleSide,
    opacity: ALPHA.opaque,
    premultipliedAlpha: labelPremultiplied,
    alphaTest: labelPremultiplied ? 0.01 : 0,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(worldW, worldH), mat);
  mesh.renderOrder = 15;
  return { mesh, worldW, worldH };
}

function addOrientedReactionLabel(text, contact, axisDir, span, scaleFactor, group, fgColor, fromNodeSign) {
  const d = axisDir.clone().normalize();
  const { mesh, worldW } = makeTextPlaneMesh(text, span, {
    bg: null,
    fg: fgColor,
    pad: 2,
    scaleFactor: scaleFactor,
    labelPremultiplied: true,
  });
  orientMeshAxisX(mesh, d);
  const pad = labelOffsetDistance(span, scaleFactor, 0.03);
  mesh.position.copy(contact).addScaledVector(d, fromNodeSign * (pad + worldW * 0.5));
  group.add(mesh);
}

function drawSupportReactions(model, opts) {
  const {
    lc, lcKey, defFac, deformed, showArrows, showValues, span, nm, reactionLabelScale,
  } = opts;
  if (!showArrows && !showValues) return;
  if (!analysisComplete(model) || !model.supports || model.supports.length === 0) return;

  const arrowLen = reactionArrowLength(model);
  const maxForceMag = maxReactionForceMag(model, lcKey);
  const gizmoRadius = supportGizmoSize(model);

  for (const s of model.supports) {
    const r = supportReactsForLc(model, s, lcKey);
    if (!r) continue;
    const n = nm[s.node];
    if (!n || !isNodeVisible(n.id)) continue;
    const p = nodePosition(n, model, lc, defFac, deformed);
    const tx = r[0], ty = r[1], tz = r[2];
    const rx = r[3], ry = r[4], rz = r[5];
    const forces = [tx, ty, tz];

    const gizmoCenter = supportGizmoCenter(p, model, gizmoRadius, camera, renderer, _gizmoCenterScratch);

    for (let i = 0; i < 3; i++) {
      const fval = forces[i];
      const color = REACTION_TRANS_COLORS[i];
      const zeroDisplay = reactionForceIsZeroDisplay(fval);

      if (zeroDisplay) {
        if (!showArrows && !showValues) continue;
        const axisDir = REACTION_TRANS_AXES[i];
        const screenDir = billboardScreenDirection(gizmoCenter, axisDir, camera, _screenDirScratch);
        const entry = {
          nodePos: p.clone(),
          gizmoRadius: gizmoRadius,
          axisIndex: i,
          fval: fval,
          arrowLen: arrowLen,
          lines: null,
          headScale: 0.85,
          labelSprite: null,
          zeroDisplay: true,
          span: span,
          scaleFactor: reactionLabelScale,
        };
        const sprite = makeReactionForceLabelSprite("0", span, color, reactionLabelScale);
        sprite.renderOrder = 15;
        entry.labelSprite = sprite;
        updateReactionZeroLabel(entry, gizmoCenter, screenDir);
        labelGroup.add(sprite);
        reactionForceEntries.push(entry);
        continue;
      }

      const forceDir = reactionForceDirection(i, fval);
      const screenDir = billboardScreenDirection(gizmoCenter, forceDir, camera, _screenDirScratch);
      const viewDir = billboardViewDirection(gizmoCenter, camera, _viewToCenterScratch);
      const { tail, head } = computeReactionTransArrowEndpoints(
        gizmoCenter, gizmoRadius, screenDir, arrowLen
      );

      const entry = {
        nodePos: p.clone(),
        gizmoRadius: gizmoRadius,
        axisIndex: i,
        fval: fval,
        arrowLen: arrowLen,
        lines: null,
        headScale: 0.85,
        labelSprite: null,
        zeroDisplay: false,
        span: span,
        scaleFactor: reactionLabelScale,
      };

      if (showArrows) {
        const lineW = reactionLineWidthPx(fval, maxForceMag);
        entry.lines = addDirectedArrowWideMutable(
          tail, head, modelGroup, color, lineW, entry.headScale, 7, true, viewDir
        );
      }

      if (showValues) {
        const text = formatReactionValue(fval);
        const sprite = makeReactionForceLabelSprite(text, span, color, reactionLabelScale);
        sprite.renderOrder = 15;
        entry.labelSprite = sprite;
        updateReactionForceLabel(entry, tail, screenDir);
        labelGroup.add(sprite);
      }

      if (showArrows || showValues) {
        reactionForceEntries.push(entry);
      }
    }

    const momentAxes = [
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(0, 0, 1),
    ];
    const moments = [rx, ry, rz];
    const momentLabels = ["Rx", "Ry", "Rz"];
    if (showValues) {
      for (let i = 0; i < 3; i++) {
        const mval = moments[i];
        if (Math.abs(mval) < 1e-9) continue;
        const axisDir = momentAxes[i].clone().multiplyScalar(mval >= 0 ? 1 : -1);
        addOrientedReactionLabel(
          momentLabels[i] + " " + formatReactionValue(mval),
          p,
          axisDir,
          span,
          reactionLabelScale,
          labelGroup,
          colorHex(COLORS.reactionMoment),
          1
        );
      }
    }
  }
}

function maxReactionForceMag(model, lcKey) {
  let max = 0;
  for (const s of model.supports || []) {
    const r = supportReactsForLc(model, s, lcKey);
    if (!r) continue;
    for (let i = 0; i < 3; i++) {
      max = Math.max(max, Math.abs(r[i]));
    }
  }
  return max;
}

function maxReactionMomentMag(model, lcKey) {
  let max = 0;
  for (const s of model.supports || []) {
    const r = supportReactsForLc(model, s, lcKey);
    if (!r) continue;
    for (let i = 3; i < 6; i++) {
      const mag = Math.abs(r[i]);
      if (mag > max) max = mag;
    }
  }
  return max;
}

function scaledReactionArrowLength(baseLen, mag, maxMag) {
  if (maxMag < 1e-9) return baseLen * 0.5;
  return baseLen * Math.max(0.2, mag / maxMag);
}

function colorHex(c) {
  return "#" + (c >>> 0).toString(16).padStart(6, "0");
}

function addReactionValueLabel(text, point, span, scaleFactor, group, fgColor) {
  const sprite = makeTextSprite(text, span, {
    bg: null,
    fg: fgColor,
    pad: 2,
    scaleFactor: scaleFactor,
  });
  sprite.position.copy(point);
  sprite.renderOrder = 15;
  group.add(sprite);
}

function addElemLabel(text, point, span, scaleFactor, group, bg, transparent) {
  const sprite = makeTextSprite(text, span, {
    bg: bg || LABEL_BG.elem,
    fg: "#ffffff",
    pad: 4,
    scaleFactor: scaleFactor,
    transparent: transparent !== false,
  });
  sprite.position.copy(point);
  sprite.renderOrder = 15;
  group.add(sprite);
}

function addElemLabelWithLeader(text, anchorPos, p0, p1, side, span, scaleFactor, group, bg, transparent) {
  const sprite = makeTextSprite(text, span, {
    bg: bg || LABEL_BG.elem,
    fg: "#ffffff",
    pad: 4,
    scaleFactor: scaleFactor,
    transparent: transparent !== false,
  });
  sprite.renderOrder = 16;
  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute("position", new THREE.Float32BufferAttribute(6, 3));
  const line = new THREE.Line(lineGeo, nodeLabelLeaderMaterial());
  line.frustumCulled = false;
  line.renderOrder = 15;
  const entry = {
    anchorPos: anchorPos.clone(),
    p0: p0.clone(),
    p1: p1.clone(),
    side: side,
    sprite: sprite,
    line: line,
  };
  updateElemLabelEntry(entry, camera, renderer);
  group.add(sprite);
  group.add(line);
  elemLabelEntries.push(entry);
}

function addAnnotationLabel(text, point, dir, span, scaleFactor, group, bg) {
  if (!text) return;
  const offset = dir.clone().normalize().multiplyScalar(span * 0.04);
  const pos = point.clone().add(offset);
  addElemLabel(text, pos, span, scaleFactor, group, bg || LABEL_BG.load);
}

function arrowPerpendicular(dir) {
  const d = dir.clone().normalize();
  const ref = Math.abs(d.y) < 0.9
    ? new THREE.Vector3(0, 1, 0)
    : new THREE.Vector3(1, 0, 0);
  return new THREE.Vector3().crossVectors(d, ref).normalize();
}

function directedArrowLinePoints(tail, head, headScale) {
  const d = head.clone().sub(tail);
  const length = d.length();
  if (length < 1e-12) return [];
  const dir = d.clone().normalize();
  const hs = (headScale != null && isFinite(headScale) && headScale > 0) ? headScale : 1.0;
  const headLen = Math.max(length * 0.22 * hs, length * 0.08 * hs);
  const headWide = headLen * 0.55;
  const wingBase = head.clone().addScaledVector(dir, -headLen);
  const perp = arrowPerpendicular(dir);
  const wingA = wingBase.clone().addScaledVector(perp, headWide);
  const wingB = wingBase.clone().addScaledVector(perp, -headWide);
  const pts = [];
  addLinePair(tail, head, pts);
  addLinePair(wingA, head, pts);
  addLinePair(wingB, head, pts);
  return pts;
}

function updateDirectedWideArrow(lines, tail, head, headScale) {
  if (!lines) return;
  const pts = directedArrowLinePoints(tail, head, headScale);
  if (pts.length < 6) return;
  lines.geometry.setPositions(pts);
  lines.geometry.computeBoundingSphere();
}

function billboardArrowPerpendicular(screenDir, viewDir) {
  const perp = new THREE.Vector3().crossVectors(viewDir, screenDir);
  if (perp.lengthSq() < 1e-12) {
    return arrowPerpendicular(screenDir);
  }
  return perp.normalize();
}

function billboardDirectedArrowLinePoints(tail, head, viewDir, headScale) {
  const d = head.clone().sub(tail);
  const length = d.length();
  if (length < 1e-12) return [];
  const dir = d.clone().normalize();
  const hs = (headScale != null && isFinite(headScale) && headScale > 0) ? headScale : 1.0;
  const headLen = Math.max(length * 0.22 * hs, length * 0.08 * hs);
  const headWide = headLen * 0.55;
  const wingBase = head.clone().addScaledVector(dir, -headLen);
  const perp = billboardArrowPerpendicular(dir, viewDir);
  const wingA = wingBase.clone().addScaledVector(perp, headWide);
  const wingB = wingBase.clone().addScaledVector(perp, -headWide);
  const pts = [];
  addLinePair(tail, head, pts);
  addLinePair(wingA, head, pts);
  addLinePair(wingB, head, pts);
  return pts;
}

function updateBillboardDirectedWideArrow(lines, tail, head, viewDir, headScale) {
  if (!lines) return;
  const pts = billboardDirectedArrowLinePoints(tail, head, viewDir, headScale);
  if (pts.length < 6) return;
  lines.geometry.setPositions(pts);
  lines.geometry.computeBoundingSphere();
}

function addDirectedArrowWideMutable(tail, head, group, color, lineWidthPx, headScale, renderOrder, opaque, viewDir) {
  const pts = viewDir
    ? billboardDirectedArrowLinePoints(tail, head, viewDir, headScale)
    : directedArrowLinePoints(tail, head, headScale);
  if (pts.length < 6) return null;
  const ro = (renderOrder != null && isFinite(renderOrder)) ? renderOrder : 5;
  return addWideLineSegmentsFromPts(pts, color, group, ro, lineWidthPx, null, opaque === true);
}

function addDirectedArrow(tail, head, group, color, lineWidthPx, headScale, renderOrder, opaque) {
  const d = head.clone().sub(tail);
  const length = d.length();
  if (length < 1e-12) return head.clone();
  const dir = d.clone().normalize();
  const hs = (headScale != null && isFinite(headScale) && headScale > 0) ? headScale : 1.0;
  const headLen = Math.max(length * 0.22 * hs, length * 0.08 * hs);
  const headWide = headLen * 0.55;
  const wingBase = head.clone().addScaledVector(dir, -headLen);
  const perp = arrowPerpendicular(dir);
  const wingA = wingBase.clone().addScaledVector(perp, headWide);
  const wingB = wingBase.clone().addScaledVector(perp, -headWide);
  const ro = (renderOrder != null && isFinite(renderOrder)) ? renderOrder : 5;

  if (lineWidthPx != null) {
    const pts = directedArrowLinePoints(tail, head, headScale);
    addWideLineSegmentsFromPts(pts, color, group, ro, lineWidthPx, null, opaque === true);
    return head.clone();
  }

  const lineMat = new THREE.LineBasicMaterial({ color: color, depthTest: true });
  const shaftGeo = new THREE.BufferGeometry().setFromPoints([tail, head]);
  shaftGeo.computeBoundingSphere();
  const shaft = new THREE.Line(shaftGeo, lineMat);
  shaft.frustumCulled = false;
  shaft.renderOrder = ro;
  group.add(shaft);

  const headPts = [
    wingA.x, wingA.y, wingA.z, head.x, head.y, head.z,
    wingB.x, wingB.y, wingB.z, head.x, head.y, head.z,
  ];
  const headGeo = new THREE.BufferGeometry();
  headGeo.setAttribute("position", new THREE.Float32BufferAttribute(headPts, 3));
  headGeo.computeBoundingSphere();
  const headLines = new THREE.LineSegments(headGeo, lineMat);
  headLines.frustumCulled = false;
  headLines.renderOrder = ro + 1;
  group.add(headLines);

  return head.clone();
}

function addDirectionArrow(origin, dir, length, group, color, lineWidthPx, headScale, opaque) {
  const d = dir.clone().normalize();
  const tip = origin.clone().addScaledVector(d, length);
  return addDirectedArrow(origin, tip, group, color, lineWidthPx, headScale, undefined, opaque);
}

function addLoadArrow(origin, dir, length, group) {
  // Slightly slimmer load arrows for better readability on dense scenes.
  return addDirectionArrow(origin, dir, length, group, COLORS.load, loadLineWidthPx(), 0.75, true);
}

function nodeLabelScaleFactor() {
  const v = parseFloat(viewerOptions.nodeLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
  return v / 100;
}

function elemLabelScaleFactor() {
  const v = parseFloat(viewerOptions.elemLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
  return v / 100;
}

function materialLabelScaleFactor() {
  const v = parseFloat(viewerOptions.materialLabelSize);
  if (!isFinite(v) || v <= 0) return 0.04;
  return v / 100;
}

function sectionLabelScaleFactor() {
  const v = parseFloat(viewerOptions.sectionLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
  return v / 100;
}

function loadLabelScaleFactor() {
  const v = parseFloat(viewerOptions.loadLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
  return v / 100;
}

function reactionLabelScaleFactor() {
  const v = parseFloat(viewerOptions.reactionLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
  return v / 100;
}

function setForceControlsEnabled(enabled) {
  el.forceSelect.disabled = !enabled;
  el.frcDiv.disabled = !enabled;
  el.frcFactor.disabled = !enabled;
  el.chkForceValues.disabled = !enabled;
  if (!enabled) {
    el.forceSelect.value = "0";
    updateForceLegend(0, null);
  }
}

function setReactionControlsEnabled(enabled) {
  if (!el.chkReactions || !el.chkReactionValues) return;
  if (!enabled) {
    el.chkReactions.checked = false;
    el.chkReactionValues.checked = false;
  }
}

function setDispContourControlsEnabled(enabled) {
  if (!el.chkDispContour) return;
  el.chkDispContour.disabled = !enabled;
  if (el.dispComponent) el.dispComponent.disabled = !enabled;
  if (!enabled) {
    el.chkDispContour.checked = false;
    updateDispContourOverlay(false, null, null, 0, currentDispComponent(), false);
  }
}

function forceLabelScaleFactor() {
  const v = parseFloat(viewerOptions.forceLabelSize);
  if (!isFinite(v) || v <= 0) return 0.06;
  return v / 100;
}

function updateForceLegend(forceId, lc) {
  if (forceId === 0 || lc == null) {
    el.forceLegend.classList.remove("visible");
    el.forceLegend.textContent = "";
    return;
  }
  const unit = FORCE_UNITS[forceId] || "";
  el.forceLegend.classList.add("visible");
  el.forceLegend.textContent =
    "ELEMENT FORCE: " + FORCE_LABELS[forceId] + " [" + unit + "]\n" +
    "LOAD CASE: " + lc;
}

// The solver reports shear and moment of bottom-to-top vertical members with
// flipped signs (classes/solve.py _FORCE_SIGN_VERT); distributed-load terms
// must flip with them.
function memberLoadSign(e) {
  return e.is_vxz && e.vx && e.vx[2] > 0 ? -1 : 1;
}

function computeDispFac(model, forceId, lcKey, frcFactor) {
  const b = model.bounds;
  if (!b) return 1;
  const span = Math.max(b[1] - b[0], b[3] - b[2], b[5] - b[4], 1);
  const rowMap = {
    1: [0, 6],
    2: [1, 7],
    3: [2, 8],
    4: [3, 9],
    5: [4, 10, 12],
    6: [5, 11, 13],
  };
  const rows = rowMap[forceId] || [];
  let overallMax = 0;

  for (const e of model.elements) {
    const f = e.forces && e.forces[lcKey];
    if (!f) continue;
    for (const r of rows) {
      overallMax = Math.max(overallMax, Math.abs(f[r] || 0));
    }
  }

  if (forceId === 5 || forceId === 6) {
    for (const e of model.elements) {
      const f = e.forces && e.forces[lcKey];
      const lds = e.local_wloads && e.local_wloads[lcKey];
      if (!f || !lds) continue;
      const len = e.len || 1;
      const s = memberLoadSign(e);
      const wzi = s * lds[2], wzj = s * lds[5], wyi = s * lds[1], wyj = s * lds[4];
      if (forceId === 5) {
        const qzi = f[2], myi = f[4];
        const wXc = wzi + (wzj - wzi) * 0.5;
        const mXc = myi + qzi * 0.5 * len + (1 / 6) * (2 * wzi + wXc) * (0.5 * len) ** 2;
        overallMax = Math.max(overallMax, Math.abs(mXc));
      } else if (forceId === 6) {
        const qyi = f[1], mzi = f[5];
        const wXc = wyi + (wyj - wyi) * 0.5;
        const mXc = mzi - qyi * 0.5 * len - (1 / 6) * (2 * wyi + wXc) * (0.5 * len) ** 2;
        overallMax = Math.max(overallMax, Math.abs(mXc));
      }
    }
  }

  if (overallMax < PRES_ZERO) return span * 0.01;
  return 0.01 * frcFactor * span / overallMax;
}

function modelHasForceData(model, lcKey) {
  if (!model || !analysisComplete(model) || !model.elements || model.elements.length === 0) {
    return false;
  }
  if (model.schema != null && model.schema < 2) {
    return false;
  }
  return model.elements.some(function (e) {
    return e.forces && e.forces[lcKey] && e.vy && e.vz && e.len != null;
  });
}

function addForceStemAndSpline(stemPts, splinePts, group) {
  const w = forceLineWidthPx();
  if (stemPts.length >= 6) {
    addWideLineSegmentsFromPts(stemPts, COLORS.force, group, 10, w, 1.0);
  }
  if (splinePts.length >= 2) {
    const linePts = [];
    for (let i = 0; i < splinePts.length - 1; i++) {
      addLinePair(splinePts[i], splinePts[i + 1], linePts);
    }
    addWideLineSegmentsFromPts(linePts, COLORS.force, group, 11, w, 1.0);
  }
}

function addForceValueLabelWithLeader(text, diagramPt, axisPt, span, group) {
  const sprite = makeTextSprite(text, span, {
    scaleFactor: forceLabelScaleFactor(),
    bg: null,
    fg: colorHex(COLORS.nodeLabel),
  });
  sprite.renderOrder = 20;
  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute("position", new THREE.Float32BufferAttribute(6, 3));
  const line = new THREE.Line(lineGeo, nodeLabelLeaderMaterial());
  line.frustumCulled = false;
  line.renderOrder = 19;
  const entry = {
    diagramPt: diagramPt.clone(),
    axisPt: axisPt.clone(),
    sprite: sprite,
    line: line,
  };
  updateForceLabelEntry(entry, camera, renderer);
  group.add(sprite);
  group.add(line);
  forceLabelEntries.push(entry);
}

function anchorDiagramValue(rawValue, rawMid, rawEnd, targetMid, targetEnd, t) {
  const midCorrection = (targetMid - rawMid) * 4 * t * (1 - t);
  const endCorrection = (targetEnd - rawEnd) * (2 * t * t - t);
  return rawValue + midCorrection + endCorrection;
}

function buildForceDiagrams(model) {
  clearGroup(forceGroup);
  clearGroup(forceLabelGroup);
  forceLabelEntries = [];

  const forceId = parseInt(el.forceSelect.value, 10) || 0;
  const lcKey = el.lcSelect.value;
  updateForceLegend(forceId, forceId > 0 ? lcKey : null);

  if (forceId === 0 || !analysisComplete(model)) return;
  if (forceId === 4) return;

  if (!modelHasForceData(model, lcKey)) {
    return;
  }

  const lc = lcKey;
  const defFac = parseFloat(el.defFactor.value) || 0;
  const deformed = el.chkDeformed.checked && analysisComplete(model);
  const divNum = parseInt(el.frcDiv.value, 10) || 8;
  const frcFactor = parseFloat(el.frcFactor.value) || 10;
  const dispFac = computeDispFac(model, forceId, lcKey, frcFactor);
  const nm = nodeMap(model);
  const showValues = el.chkForceValues.checked;

  for (const e of model.elements) {
    if (!isMemberElementVisible(e.id)) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    const f = e.forces && e.forces[lcKey];
    if (!n0 || !n1 || !f || e.len == null || !e.vy || !e.vz) continue;

    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const loadSign = memberLoadSign(e);
    const lds = ((e.local_wloads && e.local_wloads[lcKey]) || [0, 0, 0, 0, 0, 0])
      .map(function (w) { return loadSign * w; });
    const stemPts = [];
    const splinePts = [];
    const labels = [];

    if (forceId === 1) {
      let vz = new THREE.Vector3().fromArray(e.vz);
      if (e.is_vxz && e.vx && e.vx[2] < PRES_ZERO) vz.multiplyScalar(-1);
      const ni = f[0], nj = f[6];
      const nXc = 0.5 * ni + 0.5 * nj;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vz, dispFac * nXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const nX = ni + (nj - ni) * t;
        const ptF = pt.clone().addScaledVector(vz, dispFac * nX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      const pMid = new THREE.Vector3().lerpVectors(p0, p1, 0.5);
      labels.push(
        { val: ni, pt: splinePts[0], axisPt: p0 },
        { val: nXc, pt: mp, axisPt: pMid },
        { val: nj, pt: splinePts[splinePts.length - 1], axisPt: p1 },
      );
    } else if (forceId === 2) {
      const vy = new THREE.Vector3().fromArray(e.vy);
      const wyi = lds[1], wyj = lds[4];
      const qyi = f[1], qyj = f[7];
      const wXc = wyi + (wyj - wyi) * 0.5;
      const qXc = -qyi - 0.5 * (wyi + wXc) * 0.5 * e.len;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vy, dispFac * qXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const x = t * e.len;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const wX = wyi + (wyj - wyi) * t;
        const qX = -qyi - 0.5 * (wyi + wX) * x;
        const ptF = pt.clone().addScaledVector(vy, dispFac * qX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      const pMid = new THREE.Vector3().lerpVectors(p0, p1, 0.5);
      labels.push(
        { val: qyi, pt: splinePts[0], axisPt: p0 },
        { val: qXc, pt: mp, axisPt: pMid },
        { val: qyj, pt: splinePts[splinePts.length - 1], axisPt: p1 },
      );
    } else if (forceId === 3) {
      const vz = new THREE.Vector3().fromArray(e.vz);
      const wzi = lds[2], wzj = lds[5];
      const qzi = f[2], qzj = f[8];
      const wXc = wzi + (wzj - wzi) * 0.5;
      const qXc = -qzi - 0.5 * (wzi + wXc) * 0.5 * e.len;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vz, dispFac * qXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const x = t * e.len;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const wX = wzi + (wzj - wzi) * t;
        const qX = -qzi - 0.5 * (wzi + wX) * x;
        const ptF = pt.clone().addScaledVector(vz, dispFac * qX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      const pMid = new THREE.Vector3().lerpVectors(p0, p1, 0.5);
      labels.push(
        { val: qzi, pt: splinePts[0], axisPt: p0 },
        { val: qXc, pt: mp, axisPt: pMid },
        { val: qzj, pt: splinePts[splinePts.length - 1], axisPt: p1 },
      );
    } else if (forceId === 5) {
      let vz = new THREE.Vector3().fromArray(e.vz);
      if (e.is_vxz) vz.multiplyScalar(-1);
      const wzi = lds[2], wzj = lds[5];
      const qzi = f[2], myi = f[4], myj = f[10];
      const wXc = wzi + (wzj - wzi) * 0.5;
      const mXcCalc = myi + qzi * 0.5 * e.len + (1 / 6) * (2 * wzi + wXc) * (0.5 * e.len) ** 2;
      const mXc = Number.isFinite(f[12]) ? f[12] : mXcCalc;
      const mEndCalc = myi + qzi * e.len + (1 / 6) * (2 * wzi + wzj) * e.len * e.len;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vz, -dispFac * mXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const x = t * e.len;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const wX = wzi + (wzj - wzi) * t;
        const mRaw = myi + qzi * x + (1 / 6) * (2 * wzi + wX) * x * x;
        const mX = anchorDiagramValue(mRaw, mXcCalc, mEndCalc, mXc, myj, t);
        const ptF = pt.clone().addScaledVector(vz, -dispFac * mX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      const pMid = new THREE.Vector3().lerpVectors(p0, p1, 0.5);
      labels.push(
        { val: myi, pt: splinePts[0], axisPt: p0 },
        { val: mXc, pt: mp, axisPt: pMid },
        { val: myj, pt: splinePts[splinePts.length - 1], axisPt: p1 },
      );
    } else if (forceId === 6) {
      let vy = new THREE.Vector3().fromArray(e.vy);
      if (e.is_vxz) vy.multiplyScalar(-1);
      const wyi = lds[1], wyj = lds[4];
      const qyi = f[1], mzi = f[5], mzj = f[11];
      const wXc = wyi + (wyj - wyi) * 0.5;
      const mXcCalc = mzi - qyi * 0.5 * e.len - (1 / 6) * (2 * wyi + wXc) * (0.5 * e.len) ** 2;
      const mXc = Number.isFinite(f[13]) ? f[13] : mXcCalc;
      const mEndCalc = mzi - qyi * e.len - (1 / 6) * (2 * wyi + wyj) * e.len * e.len;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vy, dispFac * mXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const x = t * e.len;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const wX = wyi + (wyj - wyi) * t;
        const mRaw = mzi - qyi * x - (1 / 6) * (2 * wyi + wX) * x * x;
        const mX = anchorDiagramValue(mRaw, mXcCalc, mEndCalc, mXc, mzj, t);
        const ptF = pt.clone().addScaledVector(vy, dispFac * mX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      const pMid = new THREE.Vector3().lerpVectors(p0, p1, 0.5);
      labels.push(
        { val: mzi, pt: splinePts[0], axisPt: p0 },
        { val: mXc, pt: mp, axisPt: pMid },
        { val: mzj, pt: splinePts[splinePts.length - 1], axisPt: p1 },
      );
    }

    addForceStemAndSpline(stemPts, splinePts, forceGroup);
    if (showValues && !forceLabelsAllDisplayZero(labels)) {
      const span = modelSpan(model);
      for (const item of labels) {
        addForceValueLabelWithLeader(
          formatForceValue(item.val),
          item.pt,
          item.axisPt,
          span,
          forceLabelGroup
        );
      }
    }
  }
}

function labelTextureQualityScale(scaleFactor) {
  const f = scaleFactor != null ? scaleFactor : 0.06;
  const dpr = typeof window !== "undefined" ? (window.devicePixelRatio || 1) : 1;
  return Math.min(16, Math.max(2, Math.round((f / 0.03) * dpr * 1.5)));
}

function premultiplyCanvasAlpha(canvas) {
  const ctx = canvas.getContext("2d");
  const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    const a = d[i + 3] / 255;
    if (a <= 0) continue;
    d[i] = Math.round(d[i] * a);
    d[i + 1] = Math.round(d[i + 1] * a);
    d[i + 2] = Math.round(d[i + 2] * a);
  }
  ctx.putImageData(img, 0, 0);
}

function solidifyCanvasForeground(canvas, fg, alphaThreshold) {
  const h = String(fg || "#ffffff").replace(/^#/, "");
  let r = 255;
  let g = 255;
  let b = 255;
  if (h.length === 6) {
    r = parseInt(h.slice(0, 2), 16);
    g = parseInt(h.slice(2, 4), 16);
    b = parseInt(h.slice(4, 6), 16);
  }
  const thresh = alphaThreshold != null ? alphaThreshold : 8;
  const ctx = canvas.getContext("2d");
  const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] > thresh) {
      d[i] = r;
      d[i + 1] = g;
      d[i + 2] = b;
      d[i + 3] = 255;
    } else {
      d[i + 3] = 0;
    }
  }
  ctx.putImageData(img, 0, 0);
}

function makeTextSprite(text, span, opts) {
  opts = opts || {};
  const { canvas, labelPremultiplied, worldW, worldH } = buildLabelCanvas(text, span, opts);
  const tex = createLabelTexture(canvas, labelPremultiplied, !!opts.crispLabel);
  const useTransparent = opts.transparent !== false;
  const mat = new THREE.SpriteMaterial({
    map: tex,
    depthTest: false,
    depthWrite: false,
    transparent: useTransparent,
    opacity: ALPHA.opaque,
    premultipliedAlpha: labelPremultiplied,
    alphaTest: opts.alphaTest != null
      ? opts.alphaTest
      : (useTransparent ? (labelPremultiplied ? 0.01 : 0) : 0),
  });
  const sp = new THREE.Sprite(mat);
  sp.scale.set(worldW, worldH, 1);
  return sp;
}

function fillLcSelect(model) {
  el.lcSelect.innerHTML = "";
  const lcs = model.load_cases || [];
  if (lcs.length === 0) {
    const opt = document.createElement("option");
    opt.value = "0";
    opt.textContent = "—";
    el.lcSelect.appendChild(opt);
    return;
  }
  for (const lc of lcs) {
    const opt = document.createElement("option");
    opt.value = String(lc);
    opt.textContent = "LC " + lc;
    el.lcSelect.appendChild(opt);
  }
  const savedLc = displayPrefs.loadCase;
  if (savedLc && Array.from(el.lcSelect.options).some(function (o) { return o.value === savedLc; })) {
    el.lcSelect.value = savedLc;
  }
}

async function fetchModelList() {
  const res = await fetch("/api/models");
  if (!res.ok) throw new Error("Failed to list models");
  return res.json();
}

function guiApiOrigin(targetWindow) {
  const readOrigin = (win) => {
    try {
      if (!win || win.closed) return null;
      if (win.__stbGuiOrigin && win.__stbGuiOrigin !== "null") {
        return win.__stbGuiOrigin;
      }
      const origin = win.location && win.location.origin;
      if (origin && origin !== "null") {
        return origin;
      }
    } catch (_) {
      /* cross-origin opener access may fail */
    }
    return null;
  };

  if (targetWindow) {
    const pinned = readOrigin(targetWindow);
    if (pinned) return pinned;
    const fromOpener = readOrigin(targetWindow.opener);
    if (fromOpener) return fromOpener;
    const fromTarget = readOrigin(targetWindow);
    if (fromTarget) return fromTarget;
  }
  return readOrigin(window) || "";
}

function guiApiUrl(path, targetWindow) {
  const rel = path.startsWith("/") ? path : "/" + path;
  const origin = guiApiOrigin(targetWindow);
  if (!origin || origin === "null") {
    throw new Error("Cannot resolve GUI API origin. Reload the main window.");
  }
  return origin + rel;
}

function primeStbPopupOrigin(popupWin) {
  if (!popupWin || popupWin.closed) return;
  const origin = guiApiOrigin(window);
  if (!origin || origin === "null") return;
  try {
    popupWin.__stbGuiOrigin = origin;
  } catch (_) {
    /* popup may be cross-origin until navigation completes */
  }
}

const childWindows = new Set();
const childWindowRefs = Object.create(null);

const CHILD_WINDOW_NAMES = {
  input: "stb_gui_input",
  project: "stb_gui_project",
  loadsVerify: "stb_loads_verify",
  practiceVerify: "stb_practice_verify",
  results: "stb_gui_results",
};

function getLivingChildWindow(kind) {
  const w = childWindowRefs[kind];
  if (!w) return null;
  if (w.closed) {
    delete childWindowRefs[kind];
    return null;
  }
  return w;
}

function focusChildWindow(w) {
  if (!w || w.closed) return;
  try {
    w.focus();
  } catch (_) {
    /* ignore */
  }
}

function registerChildWindow(win) {
  if (!win) return;
  childWindows.add(win);
}

function pruneClosedChildWindows() {
  for (const w of childWindows) {
    if (!w || w.closed) childWindows.delete(w);
  }
}

function closeAllChildWindows() {
  pruneClosedChildWindows();
  for (const w of childWindows) {
    try {
      if (!w.closed) w.close();
    } catch (_) {
      /* ignore */
    }
  }
  childWindows.clear();
  for (const kind of Object.keys(childWindowRefs)) {
    delete childWindowRefs[kind];
  }
  inputEditors.clear();
}

function openNamedChildPopup(kind, features) {
  pruneClosedChildWindows();
  const existing = getLivingChildWindow(kind);
  if (existing) {
    focusChildWindow(existing);
    return existing;
  }
  const url = guiApiUrl("/static/popup.html", window);
  const w = window.open(url, CHILD_WINDOW_NAMES[kind] || "_blank", features);
  primeStbPopupOrigin(w);
  if (w) {
    childWindowRefs[kind] = w;
    registerChildWindow(w);
  }
  return w;
}

function openNamedChildUrl(kind, url, features) {
  pruneClosedChildWindows();
  const existing = getLivingChildWindow(kind);
  if (existing) {
    try {
      if (existing.location.href !== url) existing.location.href = url;
    } catch (_) {
      /* cross-origin during navigation */
    }
    focusChildWindow(existing);
    return existing;
  }
  const w = window.open(url, CHILD_WINDOW_NAMES[kind] || "_blank", features);
  primeStbPopupOrigin(w);
  if (w) {
    childWindowRefs[kind] = w;
    registerChildWindow(w);
  }
  return w;
}

function runWhenPopupReady(w, initFn) {
  if (!w) return;
  const run = () => {
    primeStbPopupOrigin(w);
    try {
      initFn();
    } catch (ex) {
      setStatus("Error: " + ex.message);
      alert(String(ex.message || ex));
    }
  };
  if (w.document.readyState === "complete" || w.document.readyState === "interactive") {
    run();
    return;
  }
  w.addEventListener("load", run, { once: true });
}

function stbIconHeadHtml(targetWindow) {
  const base = guiApiOrigin(targetWindow) || "";
  return "<meta name=\"theme-color\" content=\"" + uiThemeMetaColor(uiTheme) + "\">"
    + "<meta name=\"color-scheme\" content=\"dark light\">"
    + "<link rel=\"icon\" href=\"" + base + "/static/icons/st-icon-32.png\" type=\"image/png\" sizes=\"32x32\">"
    + "<link rel=\"icon\" href=\"" + base + "/static/icons/st-icon-48.png\" type=\"image/png\" sizes=\"48x48\">"
    + "<link rel=\"icon\" href=\"" + base + "/static/icons/st-icon-256.png\" type=\"image/png\" sizes=\"256x256\">"
    + "<link rel=\"icon\" href=\"" + base + "/static/icons/favicon.ico\" sizes=\"48x48\">"
    + "<link rel=\"apple-touch-icon\" href=\"" + base + "/static/icons/st-icon-192.png\">";
}

async function fetchApiJson(path, targetWindow, options) {
  const url = guiApiUrl(path, targetWindow);
  let res;
  try {
    res = await fetch(url, options);
  } catch (ex) {
    throw new Error("API request failed (" + url + "): " + ex.message);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((d) => d.msg || String(d)).join("; "));
    }
    throw new Error(detail || res.statusText || "request failed");
  }
  return res.json();
}

async function fetchApiText(path, targetWindow) {
  const url = guiApiUrl(path, targetWindow);
  let res;
  try {
    res = await fetch(url);
  } catch (ex) {
    throw new Error("API request failed (" + url + "): " + ex.message);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.text();
}

async function fetchModel(path, solve) {
  const url = "/api/model?path=" + encodeURIComponent(path) + "&solve=" + (solve ? "1" : "0");
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function outputFileName(path) {
  const file = path.replace(/^.*\//, "");
  const stem = file.replace(/\.[^./]+$/i, "");
  const dir = path.includes("/") ? path.slice(0, path.lastIndexOf("/") + 1) : "";
  return dir + stem + ".out";
}

async function fetchProjectView(path, targetWindow) {
  return fetchApiJson("/api/project?path=" + encodeURIComponent(path), targetWindow || window);
}

async function fetchProjectTemplate(path, targetWindow) {
  return fetchApiJson("/api/project/template?path=" + encodeURIComponent(path), targetWindow || window);
}

async function saveProjectJson(datPath, project, targetWindow) {
  return fetchApiJson(
    "/api/project?path=" + encodeURIComponent(datPath),
    targetWindow || window,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project: project }),
    },
  );
}

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const DEFAULT_SEISMIC_RT = 1.0;
const DEFAULT_SEISMIC_TC = 0.6;
const DEFAULT_BASE_MASS_POLICY = "LUMP_TO_ABOVE_DIAPHRAGM";

function deepCloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function deepSet(obj, path, value) {
  const parts = path.split(".");
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const key = parts[i];
    if (cur[key] == null || typeof cur[key] !== "object") {
      cur[key] = {};
    }
    cur = cur[key];
  }
  cur[parts[parts.length - 1]] = value;
}

function parseCsvInts(text) {
  const raw = String(text ?? "").trim();
  if (!raw) return [];
  return raw.split(",").map((s) => s.trim()).filter(Boolean).map((s) => {
    const n = Number(s);
    if (!Number.isFinite(n) || Math.trunc(n) !== n) {
      throw new Error("整数リストの形式が不正です: " + text);
    }
    return n;
  });
}

function parseCsvNumbers(text) {
  const raw = String(text ?? "").trim();
  if (!raw) return [];
  return raw.split(",").map((s) => s.trim()).filter(Boolean).map((s) => {
    const n = Number(s);
    if (!Number.isFinite(n)) {
      throw new Error("数値リストの形式が不正です: " + text);
    }
    return n;
  });
}

function formatCsvInts(values) {
  if (!values || !values.length) return "";
  return values.join(", ");
}

function parseProjectFieldValue(type, raw, path) {
  const text = String(raw ?? "").trim();
  if (type === "optional_int") {
    if (!text || text === "—") return null;
    const n = Number(text);
    if (!Number.isFinite(n) || Math.trunc(n) !== n) {
      throw new Error("整数を入力してください: " + raw);
    }
    return n;
  }
  if (type === "csv_int") {
    return parseCsvInts(text);
  }
  if (type === "csv_number") {
    return parseCsvNumbers(text);
  }
  if (type === "bool") {
    return text === "true" || text === "1" || text === "はい";
  }
  if (type === "select") {
    if (!text) return undefined;
    return text;
  }
  if (type === "number") {
    if (!text) {
      if (
        path === "load_conditions.seismic.ci"
        || path === "load_conditions.seismic.rt"
        || path === "load_conditions.seismic.design_period_s"
        || path === "load_conditions.seismic.height_m"
        || path === "load_conditions.seismic.base_elevation"
      ) {
        return undefined;
      }
      return 0;
    }
    const n = Number(text);
    if (!Number.isFinite(n)) {
      throw new Error("数値を入力してください: " + raw);
    }
    if (path === "load_conditions.seismic.ci" && n <= 0) {
      return undefined;
    }
    return n;
  }
  return text;
}

function parseProjectTableCellValue(type, raw) {
  const text = String(raw ?? "").trim();
  if (type === "number") {
    if (!text) return null;
    const n = Number(text);
    if (!Number.isFinite(n)) {
      throw new Error("数値を入力してください: " + raw);
    }
    return n;
  }
  if (type === "optional_int") {
    if (!text || text === "—") return null;
    const n = Number(text);
    if (!Number.isFinite(n) || Math.trunc(n) !== n) {
      throw new Error("整数を入力してください: " + raw);
    }
    return n;
  }
  if (type === "csv_int") {
    if (!text) return [];
    return parseCsvInts(text);
  }
  if (type === "csv_number") {
    if (!text) return [];
    return parseCsvNumbers(text);
  }
  if (type === "bool") {
    return text === "true" || text === "1" || text === "はい";
  }
  return text;
}

function shouldIncludeProjectTableRow(row, columns) {
  const keyColumn = columns.find((c) => c.path === "name")
    || columns.find((c) => c.path === "id")
    || columns[0];
  if (!keyColumn) return false;
  const value = row[keyColumn.path];
  if (keyColumn.type === "number" || keyColumn.type === "optional_int") {
    return value != null && value !== "" && Number.isFinite(Number(value));
  }
  if (keyColumn.type === "csv_int" || keyColumn.type === "csv_number") {
    return Array.isArray(value) && value.length > 0;
  }
  return String(value ?? "").trim() !== "";
}

function filterEmptyProjectTableRows(project) {
  if (!project || typeof project !== "object") return project;
  if (Array.isArray(project.grids)) {
    project.grids = project.grids.filter((row) => String(row && row.name || "").trim() !== "");
  }
  if (Array.isArray(project.stories)) {
    project.stories = project.stories.filter((row) => String(row && row.name || "").trim() !== "");
  }
  if (Array.isArray(project.member_classes)) {
    project.member_classes = project.member_classes.filter((row) => String(row && row.name || "").trim() !== "");
  }
  const diaps = project.load_conditions && project.load_conditions.diaphragms;
  if (Array.isArray(diaps)) {
    project.load_conditions.diaphragms = diaps.filter((row) => {
      if (!row) return false;
      const id = row.id;
      return id != null && id !== "" && Number.isFinite(Number(id));
    });
  }
  return project;
}

function normalizeSeismicSettings(project) {
  const loadConditions = project.load_conditions;
  if (!loadConditions) return;
  const seismic = loadConditions.seismic;
  if (!seismic || typeof seismic !== "object") return;

  const ci = Number(seismic.ci);
  if (!Number.isFinite(ci) || ci <= 0) {
    delete seismic.ci;
  }
  if (seismic.c0 === "" || seismic.c0 == null) {
    delete seismic.c0;
  } else {
    const c0 = Number(seismic.c0);
    if (!Number.isFinite(c0) || c0 <= 0) {
      delete seismic.c0;
    }
  }
  if (seismic.z === "" || seismic.z == null) {
    delete seismic.z;
  } else {
    const z = Number(seismic.z);
    if (!Number.isFinite(z) || z <= 0) {
      delete seismic.z;
    }
  }
  const rt = Number(seismic.rt);
  if (!Number.isFinite(rt) || rt <= 0) {
    delete seismic.rt;
  }
  if (seismic.base_level != null && String(seismic.base_level).trim() === "") {
    delete seismic.base_level;
  }
  if (seismic.base_mass_policy != null && String(seismic.base_mass_policy).trim() === "") {
    delete seismic.base_mass_policy;
  } else if (seismic.base_mass_policy === DEFAULT_BASE_MASS_POLICY) {
    delete seismic.base_mass_policy;
  }
  if (seismic.base_elevation === "" || seismic.base_elevation == null) {
    delete seismic.base_elevation;
  }
  if (seismic.design_period_s === "" || seismic.design_period_s == null) {
    delete seismic.design_period_s;
  }
  if (seismic.height_m === "" || seismic.height_m == null) {
    delete seismic.height_m;
  }
  const steelRatio = Number(seismic.steel_ratio_alpha);
  if (!Number.isFinite(steelRatio) || steelRatio === 0) {
    delete seismic.steel_ratio_alpha;
  }
  const tc = Number(seismic.tc);
  if (!Number.isFinite(tc) || Math.abs(tc - DEFAULT_SEISMIC_TC) < 1.0e-12) {
    delete seismic.tc;
  }
  const liveLoadFactor = Number(seismic.live_load_factor);
  if (!Number.isFinite(liveLoadFactor) || liveLoadFactor === 0) {
    delete seismic.live_load_factor;
  }
  if (seismic.dead_load_lc === "" || seismic.dead_load_lc == null) {
    delete seismic.dead_load_lc;
  }
  if (seismic.live_load_lc === "" || seismic.live_load_lc == null) {
    delete seismic.live_load_lc;
  }
  if (Array.isArray(seismic.weight_load_cases)) {
    for (const item of seismic.weight_load_cases) {
      if (!item || typeof item !== "object") continue;
      if (item.name != null) {
        item.name = String(item.name).trim();
      }
      if (item.load_case != null && item.load_case !== "") {
        const lc = Number(item.load_case);
        if (Number.isFinite(lc)) item.load_case = Math.trunc(lc);
      }
      if (item.factor === "" || item.factor == null) {
        item.factor = 1.0;
      } else {
        const factor = Number(item.factor);
        if (Number.isFinite(factor)) item.factor = factor;
      }
      if (item.role == null || String(item.role).trim() === "") {
        item.role = "OTHER";
      } else {
        item.role = String(item.role).trim().toUpperCase();
      }
    }
  }
  if (Array.isArray(seismic.weight_load_cases) && seismic.weight_load_cases.length === 0) {
    delete seismic.weight_load_cases;
  }
  if (Array.isArray(seismic.directions)) {
    for (const direction of seismic.directions) {
      if (!direction || typeof direction !== "object") continue;
      if (direction.name != null) {
        direction.name = String(direction.name).trim();
      }
      if (direction.axis != null) {
        direction.axis = String(direction.axis).trim().toLowerCase();
      }
      if (direction.load_case != null && direction.load_case !== "") {
        const lc = Number(direction.load_case);
        if (Number.isFinite(lc)) direction.load_case = Math.trunc(lc);
      }
      if (direction.sign === "" || direction.sign == null) {
        delete direction.sign;
      } else {
        const sign = Number(direction.sign);
        if (Number.isFinite(sign)) direction.sign = sign < 0 ? -1 : 1;
      }
    }
  }
  if (Array.isArray(seismic.directions) && seismic.directions.length === 0) {
    delete seismic.directions;
  }
  if (Object.keys(seismic).length === 0) {
    loadConditions.seismic = {};
  }
}

function normalizeProjectPayload(project) {
  if (!project || typeof project !== "object") return project;
  if (project.schema != null && Number.isFinite(Number(project.schema))) {
    project.schema = Math.trunc(Number(project.schema));
  }
  const diaps = project.load_conditions && project.load_conditions.diaphragms;
  if (Array.isArray(diaps)) {
    for (const item of diaps) {
      if (item && item.id != null && Number.isFinite(Number(item.id))) {
        item.id = Math.trunc(Number(item.id));
      }
    }
  }
  normalizeSeismicSettings(project);
  return filterEmptyProjectTableRows(project);
}

function formatProjectFieldValue(type, value) {
  if (type === "optional_int") {
    return value == null ? "" : String(value);
  }
  if (type === "csv_int") {
    return formatCsvInts(value);
  }
  if (type === "csv_number") {
    return formatCsvInts(value);
  }
  if (type === "bool") {
    return value ? "true" : "false";
  }
  if (type === "number") {
    if (value == null || value === "") return "";
    return String(value);
  }
  return value == null ? "" : String(value);
}

function renderProjectFieldInput(field, inputId) {
  const value = formatProjectFieldValue(field.type, field.value);
  const hint = field.hint ? "<span class=\"proj-hint\">" + escapeHtml(field.hint) + "</span>" : "";
  if (field.type === "bool") {
    return "<select class=\"proj-input\" data-path=\"" + escapeHtml(field.path) + "\" data-type=\"bool\" id=\"" + inputId + "\">"
      + "<option value=\"true\"" + (value === "true" ? " selected" : "") + ">はい</option>"
      + "<option value=\"false\"" + (value === "false" ? " selected" : "") + ">いいえ</option>"
      + "</select>" + hint;
  }
  if (field.type === "select") {
    let html = "<select class=\"proj-input\" data-path=\"" + escapeHtml(field.path) + "\" data-type=\"select\" id=\"" + inputId + "\">";
    for (const opt of field.options || []) {
      html += "<option value=\"" + escapeHtml(opt) + "\"" + (String(opt) === String(field.value) ? " selected" : "") + ">"
        + escapeHtml(projectOptionLabel(field, opt)) + "</option>";
    }
    html += "</select>" + hint;
    return html;
  }
  if (field.type === "number" || field.type === "optional_int") {
    const inputMode = field.type === "optional_int" ? "numeric" : "decimal";
    return "<input class=\"proj-input proj-input-num\" type=\"text\" inputmode=\"" + inputMode + "\" data-path=\""
      + escapeHtml(field.path) + "\" data-type=\"" + escapeHtml(field.type) + "\" id=\"" + inputId + "\" value=\""
      + escapeHtml(value) + "\">" + hint;
  }
  return "<input class=\"proj-input\" type=\"text\" data-path=\""
    + escapeHtml(field.path) + "\" data-type=\"" + escapeHtml(field.type) + "\" id=\"" + inputId + "\" value=\""
    + escapeHtml(value) + "\">" + hint;
}

function projectTableCellTdClass(col) {
  if (col.type === "number" || col.type === "optional_int") return " proj-cell-num";
  if (col.type === "select" || col.type === "bool") return " proj-cell-select";
  return " proj-cell-text";
}

function projectOptionLabel(def, opt) {
  const labels = def && def.option_labels;
  if (labels && Object.prototype.hasOwnProperty.call(labels, opt)) {
    return labels[opt];
  }
  return opt;
}

function renderProjectEditTableCellHtml(col, cellId, val) {
  if (col.type === "csv_int" || col.type === "csv_number") {
    const cellValue = formatCsvInts(val);
    return "<input class=\"proj-cell-input proj-cell-text\" type=\"text\" data-col=\""
      + escapeHtml(col.path) + "\" data-type=\"" + escapeHtml(col.type) + "\" id=\"" + cellId + "\" value=\""
      + escapeHtml(cellValue) + "\">";
  }
  if (col.type === "select") {
    let select = "<select class=\"proj-cell-input\" data-col=\"" + escapeHtml(col.path) + "\" data-type=\"select\" id=\"" + cellId + "\">";
    for (const opt of col.options || []) {
      select += "<option value=\"" + escapeHtml(opt) + "\"" + (String(opt) === String(val) ? " selected" : "") + ">"
        + escapeHtml(projectOptionLabel(col, opt)) + "</option>";
    }
    select += "</select>";
    return select;
  }
  if (col.type === "bool") {
    const checked = val === true || val === "true" || val === 1 || val === "1";
    return "<select class=\"proj-cell-input\" data-col=\"" + escapeHtml(col.path) + "\" data-type=\"bool\" id=\"" + cellId + "\">"
      + "<option value=\"true\"" + (checked ? " selected" : "") + ">はい</option>"
      + "<option value=\"false\"" + (!checked ? " selected" : "") + ">いいえ</option>"
      + "</select>";
  }
  if (col.type === "number" || col.type === "optional_int") {
    const inputMode = col.type === "optional_int" ? "numeric" : "decimal";
    return "<input class=\"proj-cell-input proj-cell-num\" type=\"text\" inputmode=\"" + inputMode + "\" data-col=\""
      + escapeHtml(col.path) + "\" data-type=\"" + escapeHtml(col.type) + "\" id=\"" + cellId + "\" value=\""
      + escapeHtml(formatProjectFieldValue(col.type, val)) + "\">";
  }
  return "<input class=\"proj-cell-input proj-cell-text\" type=\"text\" data-col=\""
    + escapeHtml(col.path) + "\" data-type=\"" + escapeHtml(col.type) + "\" id=\"" + cellId + "\" value=\""
    + escapeHtml(formatProjectFieldValue(col.type, val)) + "\">";
}

function renderProjectEditSectionHtml(section, sectionIndex) {
  let html = "<section class=\"proj-section\" data-section-id=\"" + escapeHtml(section.id) + "\">";
  html += "<h2>" + escapeHtml(section.title) + "</h2>";
  if (section.fields && section.fields.length) {
    html += "<dl class=\"proj-rows\">";
    for (let i = 0; i < section.fields.length; i++) {
      const field = section.fields[i];
      const inputId = "proj-field-" + sectionIndex + "-" + i;
      html += "<dt><label for=\"" + inputId + "\">" + escapeHtml(field.label) + "</label></dt>";
      html += "<dd>" + renderProjectFieldInput(field, inputId) + "</dd>";
    }
    html += "</dl>";
  }
  if (section.readonly && section.readonly.length) {
    html += "<dl class=\"proj-rows proj-readonly\">";
    for (const row of section.readonly) {
      html += "<dt>" + escapeHtml(row.label) + "</dt><dd>";
      html += escapeHtml(row.value == null || row.value === "" ? "—" : row.value);
      if (row.hint) {
        html += "<span class=\"proj-hint\">" + escapeHtml(row.hint) + "</span>";
      }
      html += "</dd>";
    }
    html += "</dl>";
  }
  if (section.table) {
    html += renderProjectEditTableHtml(section.table, sectionIndex);
  }
  html += "</section>";
  return html;
}

function renderProjectEditTableHtml(table, sectionIndex) {
  const tableId = "proj-table-" + sectionIndex;
  let html = "<div class=\"proj-table-wrap\" data-table-path=\"" + escapeHtml(table.path) + "\" id=\"" + tableId + "\">";
  if (table.label) {
    html += "<h3>" + escapeHtml(table.label) + "</h3>";
  }
  html += "<table class=\"proj-edit-table\"><thead><tr>";
  for (const col of table.columns) {
    const thClass = projectTableCellTdClass(col).trim();
    html += "<th" + (thClass ? " class=\"" + thClass + "\"" : "") + ">" + escapeHtml(col.label) + "</th>";
  }
  html += "<th class=\"proj-row-actions\">操作</th></tr></thead><tbody>";
  const rows = table.rows || [];
  if (!rows.length) {
    html += renderProjectEditTableRowHtml(table.columns, {}, sectionIndex, 0);
  } else {
    for (let ri = 0; ri < rows.length; ri++) {
      html += renderProjectEditTableRowHtml(table.columns, rows[ri], sectionIndex, ri);
    }
  }
  html += "</tbody></table>";
  html += "<button type=\"button\" class=\"btn-table-add\" data-table-id=\"" + tableId + "\">行を追加</button>";
  html += "</div>";
  return html;
}

function renderProjectEditTableRowHtml(columns, row, sectionIndex, rowIndex) {
  let html = "<tr data-row-index=\"" + rowIndex + "\">";
  for (let ci = 0; ci < columns.length; ci++) {
    const col = columns[ci];
    const cellId = "proj-cell-" + sectionIndex + "-" + rowIndex + "-" + ci;
    const val = row[col.path];
    const tdClass = projectTableCellTdClass(col).trim();
    html += "<td" + (tdClass ? " class=\"" + tdClass + "\"" : "") + ">"
      + renderProjectEditTableCellHtml(col, cellId, val) + "</td>";
  }
  html += "<td class=\"proj-row-actions\"><button type=\"button\" class=\"btn-table-del\">削除</button></td>";
  html += "</tr>";
  return html;
}

function collectProjectFromFormRoot(formRoot, editForm, baseProject) {
  const out = deepCloneJson(baseProject);
  if (!formRoot || !editForm) return out;

  for (const input of formRoot.querySelectorAll(".proj-input[data-path]")) {
    const path = input.getAttribute("data-path");
    const type = input.getAttribute("data-type") || "text";
    const value = parseProjectFieldValue(type, input.value, path);
    if (value === undefined) {
      continue;
    }
    deepSet(out, path, value);
  }

  for (const wrap of formRoot.querySelectorAll(".proj-table-wrap[data-table-path]")) {
    const path = wrap.getAttribute("data-table-path");
    const section = (editForm.sections || []).find((s) => s.table && s.table.path === path);
    if (!section) continue;
    const columns = section.table.columns;
    const rows = [];
    for (const tr of wrap.querySelectorAll("tbody tr")) {
      const row = {};
      for (const input of tr.querySelectorAll(".proj-cell-input")) {
        const colPath = input.getAttribute("data-col");
        const col = columns.find((c) => c.path === colPath);
        const type = col ? col.type : (input.getAttribute("data-type") || "text");
        row[colPath] = parseProjectTableCellValue(type, input.value);
      }
      if (shouldIncludeProjectTableRow(row, columns)) {
        rows.push(row);
      }
    }
    deepSet(out, path, rows);
  }
  return out;
}

function buildProjectFieldMap(editForm) {
  const map = new Map();
  if (!editForm || !editForm.sections) return map;
  for (const section of editForm.sections) {
    for (const field of section.fields || []) {
      if (field.path) map.set(field.path, field);
    }
  }
  return map;
}

function populateFormFromProject(formRoot, editForm, project) {
  if (!formRoot || !editForm || !project) return;
  const fieldMap = buildProjectFieldMap(editForm);

  for (const input of formRoot.querySelectorAll(".proj-input[data-path]")) {
    const path = input.getAttribute("data-path");
    const type = input.getAttribute("data-type") || "text";
    const parts = path.split(".");
    let cur = project;
    for (const p of parts) {
      cur = cur == null ? undefined : cur[p];
    }
    const fieldDef = fieldMap.get(path);
    if ((cur == null || cur === "") && fieldDef && fieldDef.value != null && fieldDef.value !== "") {
      cur = fieldDef.value;
    }
    if (path === "load_conditions.seismic.rt" && (cur == null || cur === "")) {
      cur = DEFAULT_SEISMIC_RT;
    }
    if (path === "load_conditions.seismic.tc" && (cur == null || cur === "")) {
      cur = 0.6;
    }
    if (path === "load_conditions.seismic.steel_ratio_alpha" && (cur == null || cur === "")) {
      cur = 0.0;
    }
    input.value = formatProjectFieldValue(type, cur);
  }

  for (const wrap of formRoot.querySelectorAll(".proj-table-wrap[data-table-path]")) {
    const path = wrap.getAttribute("data-table-path");
    const section = (editForm.sections || []).find((s) => s.table && s.table.path === path);
    if (!section) continue;
    const parts = path.split(".");
    let cur = project;
    for (const p of parts) {
      cur = cur == null ? undefined : cur[p];
    }
    const rows = Array.isArray(cur) ? cur : [];
    const tbody = wrap.querySelector("tbody");
    if (!tbody) continue;
    tbody.innerHTML = "";
    const sectionIndex = Array.from(formRoot.querySelectorAll(".proj-section")).indexOf(wrap.closest(".proj-section"));
    if (!rows.length) {
      tbody.innerHTML = renderProjectEditTableRowHtml(section.table.columns, {}, sectionIndex, 0);
    } else {
      const html = rows.map((row, ri) =>
        renderProjectEditTableRowHtml(section.table.columns, row, sectionIndex, ri),
      ).join("");
      tbody.innerHTML = html;
    }
  }
}

function showProjectWindow(view) {
  const title = view.project_path || view.title || "project.json";
  const w = openNamedChildPopup("project", "width=980,height=820,scrollbars=yes,resizable=yes");
  if (!w) {
    setStatus("Popup blocked — allow popups for this site");
    return;
  }
  const init = () => initProjectEditorWindow(w, view, title);
  if (w.__stbProjectEditorReady) {
    init();
    return;
  }
  runWhenPopupReady(w, () => {
    w.__stbProjectEditorReady = true;
    init();
  });
}

function initProjectEditorWindow(w, view, title) {
  primeStbPopupOrigin(w);
  const doc = w.document;
  doc.open();
  doc.write("<!DOCTYPE html><html lang=\"ja\"><head><meta charset=\"UTF-8\">");
  doc.write(stbIconHeadHtml(w));
  doc.write("<title>");
  doc.write(escapeHtml(view.title || title));
  doc.write("</title><style>");
  doc.write("html,body{height:100%;margin:0;}");
  doc.write("body{background:#f4f5f7;color:#1a1a22;font-family:'Segoe UI',system-ui,sans-serif;line-height:1.45;display:flex;flex-direction:column;overflow:hidden;}");
  doc.write(".toolbar{padding:10px 16px;background:#252530;color:#e8e6ed;border-bottom:1px solid #3a3a48;display:flex;gap:10px;align-items:center;flex-wrap:wrap;flex-shrink:0;}");
  doc.write(".toolbar button{background:#e1dee4;color:#111;border:none;border-radius:4px;padding:6px 12px;font-weight:600;cursor:pointer;}");
  doc.write(".toolbar button.secondary{background:#3a3a48;color:#e8e6ed;}");
  doc.write(".toolbar .path{font-size:12px;color:#aaa;margin-left:auto;}");
  doc.write(".toolbar .status{font-size:12px;color:#555;}");
  doc.write(".tabs{display:flex;gap:0;background:#252530;padding:0 16px;border-bottom:1px solid #3a3a48;flex-shrink:0;}");
  doc.write(".tab{background:transparent;color:#aaa;border:none;border-bottom:2px solid transparent;padding:10px 16px;font-weight:600;cursor:pointer;}");
  doc.write(".tab.active{color:#e8e6ed;border-bottom-color:#e1dee4;}");
  doc.write(".tab-panels{flex:1;min-height:0;overflow:hidden;}");
  doc.write(".tab-panel{display:none;height:100%;box-sizing:border-box;padding:16px 20px 32px;max-width:960px;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;}");
  doc.write(".tab-panel.active{display:block;}");
  doc.write(".banner{margin-bottom:16px;padding:10px 14px;border-radius:6px;background:#fff3cd;color:#664d03;border:1px solid #ffecb5;}");
  doc.write(".proj-section{margin-bottom:24px;background:#fff;border:1px solid #d8dbe3;border-radius:8px;padding:14px 16px;box-shadow:0 1px 2px rgba(0,0,0,.04);}");
  doc.write(".proj-section h2{margin:0 0 12px;font-size:15px;font-weight:700;color:#111;border-bottom:1px solid #e5e7eb;padding-bottom:8px;}");
  doc.write(".proj-section h3{margin:12px 0 8px;font-size:13px;font-weight:600;color:#374151;}");
  doc.write(".proj-rows{display:grid;grid-template-columns:minmax(140px,34%) 1fr;gap:8px 12px;margin:0;align-items:start;}");
  doc.write(".proj-rows dt{margin:0;font-size:12px;font-weight:600;color:#4b5563;padding-top:6px;}");
  doc.write(".proj-rows dd{margin:0;font-size:13px;color:#111;}");
  doc.write(".proj-readonly dt,.proj-readonly dd{color:#6b7280;}");
  doc.write(".proj-hint{display:block;margin-top:4px;font-size:11px;color:#6b7280;font-weight:400;}");
  doc.write(".proj-input,.proj-cell-input{box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;padding:5px 7px;font:inherit;background:#fff;}");
  doc.write(".proj-input{width:100%;max-width:420px;}");
  doc.write(".proj-table-wrap{margin-top:8px;overflow:auto;max-width:100%;border:1px solid #e5e7eb;border-radius:6px;background:#fafbfc;}");
  doc.write(".proj-edit-table{width:max-content;min-width:100%;border-collapse:separate;border-spacing:0;font-size:12px;}");
  doc.write(".proj-edit-table th,.proj-edit-table td{border-right:1px solid #e5e7eb;border-bottom:1px solid #e5e7eb;padding:5px 7px;vertical-align:middle;}");
  doc.write(".proj-edit-table th:first-child,.proj-edit-table td:first-child{border-left:1px solid #e5e7eb;}");
  doc.write(".proj-edit-table thead th{border-top:1px solid #e5e7eb;background:#eef2f7;font-weight:600;white-space:nowrap;position:sticky;top:0;z-index:1;}");
  doc.write(".proj-edit-table tbody tr:nth-child(even){background:#fff;}");
  doc.write(".proj-edit-table tbody tr:nth-child(odd){background:#f8fafc;}");
  doc.write(".proj-edit-table tbody tr:hover{background:#f1f5f9;}");
  doc.write(".proj-cell-num,.proj-edit-table th.proj-cell-num{text-align:right;}");
  doc.write(".proj-cell-select,.proj-edit-table th.proj-cell-select{text-align:center;}");
  doc.write(".proj-cell-input.proj-cell-num{min-width:4.2em;max-width:7.5em;width:100%;text-align:right;font-variant-numeric:tabular-nums;}");
  doc.write(".proj-cell-input.proj-cell-text{min-width:6.5em;max-width:12em;width:100%;}");
  doc.write(".proj-cell-input{width:100%;}");
  doc.write(".proj-row-actions{width:64px;min-width:64px;text-align:center;white-space:nowrap;}");
  doc.write(".btn-table-add{margin-top:8px;background:#eef2ff;color:#1e3a8a;border:1px solid #c7d2fe;border-radius:4px;padding:5px 10px;font-weight:600;cursor:pointer;}");
  doc.write(".btn-table-del{background:#fee2e2;color:#991b1b;border:1px solid #fecaca;border-radius:4px;padding:3px 8px;font-size:11px;cursor:pointer;}");
  doc.write("#jsonEditor{width:100%;height:100%;min-height:100%;box-sizing:border-box;border:0;outline:none;padding:12px;background:#111319;color:#e8e6ed;font-family:monospace;font-size:12px;line-height:1.35;resize:none;}");
  doc.write("</style></head><body>");
  doc.write("<div class=\"toolbar\">");
  doc.write("<button type=\"button\" id=\"btnSave\">保存</button>");
  doc.write("<button type=\"button\" id=\"btnCreate\" class=\"secondary\">新規作成</button>");
  doc.write("<button type=\"button\" id=\"btnReload\" class=\"secondary\">再読込</button>");
  doc.write("<button type=\"button\" id=\"btnWind4Dir\" class=\"secondary\">風4方向を生成 (WX±/WY±)</button>");
  doc.write("<span class=\"status\" id=\"status\">ready</span>");
  doc.write("<span class=\"path\">");
  doc.write(escapeHtml(view.project_path || ""));
  doc.write("</span></div>");
  doc.write("<div class=\"tabs\">");
  doc.write("<button type=\"button\" class=\"tab active\" data-tab=\"form\">設定</button>");
  doc.write("<button type=\"button\" class=\"tab\" data-tab=\"json\">JSON</button>");
  doc.write("</div>");
  doc.write("<div class=\"tab-panels\">");
  doc.write("<div id=\"tab-form\" class=\"tab-panel active\"></div>");
  doc.write("<div id=\"tab-json\" class=\"tab-panel\"><textarea id=\"jsonEditor\" spellcheck=\"false\"></textarea></div>");
  doc.write("</div>");
  doc.write("</body></html>");
  doc.close();

  const statusEl = doc.getElementById("status");
  const tabForm = doc.getElementById("tab-form");
  const tabJson = doc.getElementById("tab-json");
  const jsonEditor = doc.getElementById("jsonEditor");
  const tabs = doc.querySelectorAll(".tab");
  let activeTab = "form";
  let baseProject = view.raw ? deepCloneJson(view.raw) : null;
  let editForm = view.edit || null;

  function setWinStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  function renderFormTab() {
    if (!editForm) {
      tabForm.innerHTML = "<div class=\"banner\">対応する project.json が見つかりません。ツールバーの「新規作成」から project.json を作成できます。</div>";
      return;
    }
    let html = "";
    for (let i = 0; i < editForm.sections.length; i++) {
      html += renderProjectEditSectionHtml(editForm.sections[i], i);
    }
    tabForm.innerHTML = html;

    tabForm.querySelectorAll(".btn-table-add").forEach((btn) => {
      btn.addEventListener("click", () => {
        const wrap = doc.getElementById(btn.getAttribute("data-table-id"));
        const path = wrap.getAttribute("data-table-path");
        const section = editForm.sections.find((s) => s.table && s.table.path === path);
        if (!section) return;
        const tbody = wrap.querySelector("tbody");
        const sectionIndex = Array.from(tabForm.querySelectorAll(".proj-section")).indexOf(wrap.closest(".proj-section"));
        const rowIndex = tbody.querySelectorAll("tr").length;
        tbody.insertAdjacentHTML("beforeend", renderProjectEditTableRowHtml(section.table.columns, {}, sectionIndex, rowIndex));
      });
    });
  }

  function computeStoryTop(project) {
    const stories = Array.isArray(project && project.stories) ? project.stories : [];
    if (!stories.length) return 9.045;
    let zTop = 0;
    for (const s of stories) {
      const elev = Number(s && s.elevation);
      const h = Number(s && s.height);
      if (!Number.isFinite(elev) || !Number.isFinite(h)) continue;
      zTop = Math.max(zTop, elev + h);
    }
    return zTop > 0 ? zTop : 9.045;
  }

  function pickWidthFromSurfaces(surfaces, axis, fallback) {
    if (!Array.isArray(surfaces)) return fallback;
    const dirs = axis === "x" ? ["X_MIN", "X_MAX", "X_PLUS", "X_MINUS"] : ["Y_MIN", "Y_MAX", "Y_PLUS", "Y_MINUS"];
    const hit = surfaces.find((s) => dirs.includes(String(s && s.face_direction || "").toUpperCase()) && Number.isFinite(Number(s.width)));
    if (!hit) return fallback;
    const w = Number(hit.width);
    return w > 0 ? w : fallback;
  }

  function pickZFromSurfaces(surfaces, key, fallback) {
    if (!Array.isArray(surfaces)) return fallback;
    for (const s of surfaces) {
      const v = Number(s && s[key]);
      if (Number.isFinite(v)) return v;
    }
    return fallback;
  }

  function findOldWindSurface(oldSurfaces, faceDirection, surfaceRole) {
    if (!Array.isArray(oldSurfaces)) return null;
    const fd = String(faceDirection || "").toUpperCase();
    const sr = String(surfaceRole || "").toUpperCase();
    return oldSurfaces.find((s) =>
      String(s && s.face_direction || "").toUpperCase() === fd
      && String(s && s.surface_role || "").toUpperCase() === sr
    ) || null;
  }

  function buildWindSurfaceEntry(spec, oldSurfaces, zFallback, widthFallback) {
    const old = findOldWindSurface(oldSurfaces, spec.face_direction, spec.surface_role);
    const cfDefault = spec.surface_role === "WINDWARD" ? 0.8 : -0.4;
    const zBottom = old && Number.isFinite(Number(old.z_bottom))
      ? Number(old.z_bottom) : zFallback.zBottom;
    const zTop = old && Number.isFinite(Number(old.z_top))
      ? Number(old.z_top) : zFallback.zTop;
    const width = old && Number.isFinite(Number(old.width)) && Number(old.width) > 0
      ? Number(old.width) : widthFallback;
    const cf = old && old.Cf != null && old.Cf !== "" && Number.isFinite(Number(old.Cf))
      ? Number(old.Cf) : cfDefault;
    return {
      id: spec.id,
      name: spec.name,
      wind_case_id: spec.wind_case_id,
      face_direction: spec.face_direction,
      surface_role: spec.surface_role,
      z_bottom: zBottom,
      z_top: zTop,
      width: width,
      Cf: cf,
    };
  }

  function buildWind4Dir(project) {
    const loadConditions = project.load_conditions || (project.load_conditions = {});
    const wind = loadConditions.wind || (loadConditions.wind = {});
    const oldCases = Array.isArray(wind.cases) ? wind.cases : [];
    const oldSurfaces = Array.isArray(wind.surfaces) ? wind.surfaces : [];
    const memberLoads = Array.isArray(wind.member_loads) ? wind.member_loads : [];

    const baseCase = oldCases[0] || {};
    const v0 = Number.isFinite(Number(baseCase.V0)) ? Number(baseCase.V0) : 34.0;
    const roughness = String(baseCase.roughness_category || "III");
    const gf = Number.isFinite(Number(baseCase.Gf)) ? Number(baseCase.Gf) : 2.5;
    const pressureMode = String(baseCase.pressure_mode || "STORY_HEIGHT_KZ");
    const useKz = baseCase.use_Kz == null ? true : !!baseCase.use_Kz;
    const inputMode = String(baseCase.diaphragm_input_mode || "DIAPHRAGM_UNIFORM");
    const storyTop = computeStoryTop(project);
    const zFallback = {
      zBottom: pickZFromSurfaces(oldSurfaces, "z_bottom", 0.0),
      zTop: pickZFromSurfaces(oldSurfaces, "z_top", storyTop),
    };
    const xWidth = pickWidthFromSurfaces(oldSurfaces, "x", 5.46);
    const yWidth = pickWidthFromSurfaces(oldSurfaces, "y", 8.0);

    wind.cases = [
      { id: 1, name: "WX+", direction: "X_PLUS", load_case: 4, V0: v0, roughness_category: roughness, Gf: gf, Cf_default: 0.8, pressure_mode: pressureMode, use_Kz: useKz, diaphragm_input_mode: inputMode },
      { id: 2, name: "WX-", direction: "X_MINUS", load_case: 5, V0: v0, roughness_category: roughness, Gf: gf, Cf_default: 0.8, pressure_mode: pressureMode, use_Kz: useKz, diaphragm_input_mode: inputMode },
      { id: 3, name: "WY+", direction: "Y_PLUS", load_case: 6, V0: v0, roughness_category: roughness, Gf: gf, Cf_default: 0.8, pressure_mode: pressureMode, use_Kz: useKz, diaphragm_input_mode: inputMode },
      { id: 4, name: "WY-", direction: "Y_MINUS", load_case: 7, V0: v0, roughness_category: roughness, Gf: gf, Cf_default: 0.8, pressure_mode: pressureMode, use_Kz: useKz, diaphragm_input_mode: inputMode },
    ];

    const surfaceSpecs = [
      { id: 1, name: "X_plus_windward_wall", wind_case_id: 1, face_direction: "X_MIN", surface_role: "WINDWARD", width: xWidth },
      { id: 2, name: "X_plus_leeward_wall", wind_case_id: 1, face_direction: "X_MAX", surface_role: "LEEWARD", width: xWidth },
      { id: 3, name: "X_minus_windward_wall", wind_case_id: 2, face_direction: "X_MAX", surface_role: "WINDWARD", width: xWidth },
      { id: 4, name: "X_minus_leeward_wall", wind_case_id: 2, face_direction: "X_MIN", surface_role: "LEEWARD", width: xWidth },
      { id: 5, name: "Y_plus_windward_wall", wind_case_id: 3, face_direction: "Y_MIN", surface_role: "WINDWARD", width: yWidth },
      { id: 6, name: "Y_plus_leeward_wall", wind_case_id: 3, face_direction: "Y_MAX", surface_role: "LEEWARD", width: yWidth },
      { id: 7, name: "Y_minus_windward_wall", wind_case_id: 4, face_direction: "Y_MAX", surface_role: "WINDWARD", width: yWidth },
      { id: 8, name: "Y_minus_leeward_wall", wind_case_id: 4, face_direction: "Y_MIN", surface_role: "LEEWARD", width: yWidth },
    ];
    wind.surfaces = surfaceSpecs.map((spec) =>
      buildWindSurfaceEntry(spec, oldSurfaces, zFallback, spec.width)
    );
    wind.member_loads = memberLoads;
    return project;
  }

  if (!tabForm.dataset.boundDelete) {
    tabForm.dataset.boundDelete = "1";
    tabForm.addEventListener("click", (ev) => {
      const btn = ev.target.closest(".btn-table-del");
      if (!btn) return;
      const tr = btn.closest("tr");
      const tbody = tr && tr.parentElement;
      if (!tbody || !tr) return;
      if (tbody.querySelectorAll("tr").length <= 1) {
        for (const input of tr.querySelectorAll(".proj-cell-input")) {
          input.value = "";
        }
        return;
      }
      tr.remove();
    });
  }

  function syncFormToJson() {
    if (!baseProject || !editForm) return;
    const merged = collectProjectFromFormRoot(tabForm, editForm, baseProject);
    jsonEditor.value = JSON.stringify(merged, null, 2);
  }

  function syncJsonToForm() {
    if (!baseProject || !editForm) return;
    const parsed = JSON.parse(jsonEditor.value);
    populateFormFromProject(tabForm, editForm, parsed);
  }

  function switchTab(name) {
    if (name === activeTab) return;
    try {
      if (activeTab === "form") {
        syncFormToJson();
      } else if (activeTab === "json") {
        syncJsonToForm();
      }
    } catch (ex) {
      alert("タブ切替前の反映に失敗しました: " + ex.message);
      return;
    }
    activeTab = name;
    tabs.forEach((t) => t.classList.toggle("active", t.getAttribute("data-tab") === name));
    tabForm.classList.toggle("active", name === "form");
    tabJson.classList.toggle("active", name === "json");
  }

  function getProjectForSave() {
    let project;
    if (activeTab === "json") {
      project = JSON.parse(jsonEditor.value);
    } else if (!editForm || !baseProject) {
      throw new Error("編集可能な project.json がありません");
    } else {
      project = collectProjectFromFormRoot(tabForm, editForm, baseProject);
    }
    return normalizeProjectPayload(project);
  }

  function syncEditorAvailability() {
    const editable = !!(baseProject && editForm);
    jsonEditor.disabled = !editable;
    const jsonTab = doc.querySelector(".tab[data-tab=\"json\"]");
    if (jsonTab) jsonTab.style.display = editable ? "" : "none";
    const btnCreate = doc.getElementById("btnCreate");
    if (btnCreate) btnCreate.style.display = (!view.found && !view.draft) ? "" : "none";
    const btnSave = doc.getElementById("btnSave");
    if (btnSave) btnSave.textContent = (view.draft && !view.found) ? "作成して保存" : "保存";
  }

  function applySavedView(savedView) {
    view = savedView;
    baseProject = savedView.raw ? deepCloneJson(savedView.raw) : null;
    editForm = savedView.edit || null;
    renderFormTab();
    if (baseProject) {
      jsonEditor.value = JSON.stringify(baseProject, null, 2);
      populateFormFromProject(tabForm, editForm, baseProject);
    } else {
      jsonEditor.value = "";
    }
    doc.title = savedView.title || title;
    syncEditorAvailability();
  }

  renderFormTab();
  if (baseProject) {
    jsonEditor.value = JSON.stringify(baseProject, null, 2);
  }
  syncEditorAvailability();

  tabs.forEach((tabBtn) => {
    tabBtn.addEventListener("click", () => switchTab(tabBtn.getAttribute("data-tab")));
  });

  doc.getElementById("btnSave").addEventListener("click", async () => {
    if (!view.found && !view.draft) {
      alert("先に「新規作成」を実行してください。");
      return;
    }
    if (!baseProject || !editForm) {
      alert("編集可能な project.json がありません。");
      return;
    }
    try {
      setWinStatus("saving...");
      const project = getProjectForSave();
      const result = await saveProjectJson(view.dat_path, project, w);
      applySavedView(result.view);
      syncFormToJson();
      setWinStatus("saved");
      setStatus((view.project_path || "project.json") + " — saved");
    } catch (ex) {
      setWinStatus("save failed");
      alert("保存に失敗しました: " + ex.message);
    }
  });

  doc.getElementById("btnCreate").addEventListener("click", async () => {
    if (view.found) return;
    try {
      setWinStatus("creating template...");
      const draftView = await fetchProjectTemplate(view.dat_path, w);
      applySavedView(draftView);
      setWinStatus("新規作成 — 編集してください");
    } catch (ex) {
      setWinStatus("create failed");
      alert("新規作成テンプレートの取得に失敗しました: " + ex.message);
    }
  });

  doc.getElementById("btnReload").addEventListener("click", async () => {
    if (!confirm("未保存の変更は破棄されます。再読込しますか？")) return;
    try {
      setWinStatus("reloading...");
      const latest = await fetchProjectView(view.dat_path, w);
      applySavedView(latest);
      syncFormToJson();
      setWinStatus("reloaded");
    } catch (ex) {
      setWinStatus("reload failed");
      alert("再読込に失敗しました: " + ex.message);
    }
  });

  doc.getElementById("btnWind4Dir").addEventListener("click", () => {
    if (!baseProject || !editForm) {
      alert("project.json が読み込まれていないため実行できません。");
      return;
    }
    try {
      const current = getProjectForSave();
      const updated = normalizeProjectPayload(buildWind4Dir(current));
      baseProject = deepCloneJson(updated);
      renderFormTab();
      jsonEditor.value = JSON.stringify(baseProject, null, 2);
      populateFormFromProject(tabForm, editForm, baseProject);
      setWinStatus("wind 4-direction generated");
    } catch (ex) {
      setWinStatus("generate failed");
      alert("4方向生成に失敗しました: " + ex.message);
    }
  });

  doc.addEventListener("keydown", (ev) => {
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "s" || ev.key === "S")) {
      ev.preventDefault();
      doc.getElementById("btnSave").click();
    }
  });
}

async function openProjectWindow() {
  const path = getCurrentModelPath();
  if (!path) return;

  setStatus("Loading project for " + path + "…");
  try {
    const view = await fetchProjectView(path);
    showProjectWindow(view);
    setStatus(path + " — project settings opened");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

function prefetchLoadsVerifyView(path) {
  if (!path) return;
  try {
    const q = "?path=" + encodeURIComponent(path);
    fetch(guiApiUrl("/api/loads/dead" + q, window)).catch(function () {});
  } catch (_) {
    /* ignore */
  }
}

function openLoadsVerifyWindow() {
  const path = getCurrentModelPath();
  if (!path) {
    setStatus("Open a model before using Loads…");
    return;
  }
  prefetchLoadsVerifyView(path);
  let url;
  try {
    url = guiApiUrl(
      "/static/loads_verify.html?path=" + encodeURIComponent(path),
      window
    );
  } catch (ex) {
    setStatus("Error: " + ex.message);
    return;
  }
  const w = openNamedChildUrl(
    "loadsVerify",
    url,
    "width=1040,height=860,scrollbars=yes,resizable=yes"
  );
  if (!w) {
    setStatus("Popup blocked — allow popups for this site");
    return;
  }
  setStatus(path + " — load verification opened");
}

function openPracticeVerifyWindow() {
  const path = getCurrentModelPath();
  if (!path) {
    setStatus("Open a model before using Practice…");
    return;
  }
  let url;
  try {
    url = guiApiUrl(
      "/static/practice_verify.html?path=" + encodeURIComponent(path),
      window
    );
  } catch (ex) {
    setStatus("Error: " + ex.message);
    return;
  }
  const w = openNamedChildUrl(
    "practiceVerify",
    url,
    "width=1120,height=860,scrollbars=yes,resizable=yes"
  );
  if (!w) {
    setStatus("Popup blocked — allow popups for this site");
    return;
  }
  setStatus(path + " — structural indices opened");
}

window.openProjectWindow = openProjectWindow;
window.reloadCurrentModel = () => loadSelectedModel(false, { keepCamera: true });
window.refreshWindVisual = () => loadWindVisualForCurrentModel().then(function () {
  if (currentModel) rebuildScene();
});

function showTextDocumentWindow(text, title) {
  const pdfName = title.replace(/\.(dat|out)$/i, ".pdf");
  const saveName = title;
  const w = openNamedChildPopup("results", "width=920,height=720,scrollbars=yes,resizable=yes");
  if (!w) {
    setStatus("Popup blocked — allow popups for this site");
    return;
  }
  const init = () => initTextDocumentWindow(w, text, title, pdfName, saveName);
  if (w.__stbTextDocumentReady) {
    init();
    return;
  }
  runWhenPopupReady(w, () => {
    w.__stbTextDocumentReady = true;
    init();
  });
}

function initTextDocumentWindow(w, text, title, pdfName, saveName) {
  const doc = w.document;
  w.__stbTextDocContent = text;
  w.__stbTextDocSaveName = saveName;
  w.__stbTextDocPdfName = pdfName;
  if (w.__stbTextDocumentReady && doc.getElementById("btnSaveTxt")) {
    doc.title = title;
    const titleEl = doc.querySelector("header.doc-title");
    if (titleEl) titleEl.textContent = title;
    const pre = doc.querySelector("pre.doc-content") || doc.querySelector("pre");
    if (pre) pre.textContent = text;
    return;
  }
  doc.open();
  doc.write("<!DOCTYPE html><html><head><meta charset=\"UTF-8\">");
  doc.write(stbIconHeadHtml(w));
  doc.write("<title>");
  doc.write(title);
  doc.write("</title><style>");
  doc.write("html,body{height:100%;margin:0;}");
  doc.write("body{display:flex;flex-direction:column;overflow:hidden;background:#1e1e24;color:#e8e6ed;}");
  doc.write("pre,body{font-family:'Liberation Mono','DejaVu Sans Mono','Nimbus Mono PS','Courier New',Courier,monospace;}");
  doc.write(".toolbar{padding:8px 12px;background:#252530;border-bottom:1px solid #3a3a48;display:flex;gap:8px;align-items:center;flex-wrap:wrap;flex-shrink:0;}");
  doc.write(".toolbar button{background:#e1dee4;color:#111;border:none;border-radius:4px;padding:6px 12px;font-weight:600;cursor:pointer;}");
  doc.write("header.doc-title{padding:8px 12px;font-weight:600;border-bottom:1px solid #3a3a48;font-size:13px;flex-shrink:0;}");
  doc.write("pre.doc-content{flex:1 1 auto;min-height:0;margin:0;padding:12px;font-size:11px;line-height:1.2;white-space:pre;overflow:auto;}");
  doc.write("@page{size:A4 landscape;margin:10mm;}");
  doc.write("@media print{");
  doc.write(".no-print{display:none !important;}");
  doc.write("html,body{height:auto;overflow:visible;background:#fff;color:#000;margin:0;padding:0;}");
  doc.write("header.doc-title{display:none;}");
  doc.write("pre.doc-content{padding:0;margin:0;font-size:6pt;line-height:1.15;white-space:pre;overflow:visible;flex:none;min-height:auto;}");
  doc.write("}");
  doc.write("</style></head><body>");
  doc.write("<div class=\"toolbar no-print\">");
  doc.write("<button type=\"button\" id=\"btnSaveTxt\">Save text</button>");
  doc.write("<button type=\"button\" id=\"btnPdf\">Save as PDF (A4 landscape)</button>");
  doc.write("</div>");
  doc.write("<header class=\"doc-title\">");
  doc.write(title);
  doc.write("</header><pre class=\"doc-content\"></pre></body></html>");
  doc.close();
  attachI18n(doc);
  (doc.querySelector("pre.doc-content") || doc.querySelector("pre")).textContent = text;
  doc.getElementById("btnSaveTxt").onclick = function () {
    const blob = new Blob([w.__stbTextDocContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = doc.createElement("a");
    a.href = url;
    a.download = w.__stbTextDocSaveName;
    doc.body.appendChild(a);
    a.click();
    doc.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 0);
  };
  doc.getElementById("btnPdf").onclick = function () {
    doc.title = w.__stbTextDocPdfName;
    w.print();
  };
}

function showResultsWindow(text, path) {
  showTextDocumentWindow(text, outputFileName(path));
}

async function fetchInputText(path, targetWindow) {
  return fetchApiText("/api/input?path=" + encodeURIComponent(path), targetWindow);
}

function normalizeInputText(text) {
  return String(text ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

async function inputTextMatchesDisk(path, text, targetWindow) {
  const onDisk = await fetchInputText(path, targetWindow);
  return normalizeInputText(text) === normalizeInputText(onDisk);
}

async function saveInputText(path, text, targetWindow) {
  return fetchApiJson(
    "/api/input?path=" + encodeURIComponent(path),
    targetWindow,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: normalizeInputText(text) }),
    },
  );
}

function registerInputEditor(path, win, getText) {
  inputEditors.set(path, { win: win, getText: getText });
  const timer = setInterval(() => {
    if (!win.closed) return;
    clearInterval(timer);
    const entry = inputEditors.get(path);
    if (entry && entry.win === win) inputEditors.delete(path);
  }, 500);
}

function getInputEditorText(path) {
  const entry = inputEditors.get(path);
  if (entry && entry.win && !entry.win.closed) return entry.getText();
  return null;
}

function showInputEditorWindow(text, path) {
  const w = openNamedChildPopup("input", "width=980,height=760,scrollbars=yes,resizable=yes");
  if (!w) {
    setStatus("Popup blocked — allow popups for this site");
    return;
  }
  const init = () => initInputEditorWindow(w, text, path);
  if (w.__stbInputEditorReady) {
    init();
    return;
  }
  runWhenPopupReady(w, () => {
    w.__stbInputEditorReady = true;
    init();
  });
}

function initInputEditorWindow(w, text, path) {
  primeStbPopupOrigin(w);
  w.__stbEditorPath = path;
  const doc = w.document;
  if (w.__stbInputEditorReady && doc.getElementById("txt")) {
    doc.title = path;
    doc.getElementById("txt").value = text;
    registerInputEditor(path, w, () => doc.getElementById("txt").value);
    const statusEl = doc.getElementById("status");
    if (statusEl) statusEl.textContent = "ready";
    return;
  }
  doc.open();
  doc.write("<!DOCTYPE html><html><head><meta charset=\"UTF-8\">");
  doc.write(stbIconHeadHtml(w));
  doc.write("<title>");
  doc.write(path);
  doc.write("</title><style>");
  doc.write("body{margin:0;background:#1e1e24;color:#e8e6ed;font-family:'Segoe UI',system-ui,sans-serif;}");
  doc.write(".toolbar{padding:8px 12px;background:#252530;border-bottom:1px solid #3a3a48;display:flex;gap:8px;align-items:center;}");
  doc.write(".toolbar button{background:#e1dee4;color:#111;border:none;border-radius:4px;padding:6px 12px;font-weight:600;cursor:pointer;}");
  doc.write(".toolbar button.secondary{background:#3a3a48;color:#e8e6ed;}");
  doc.write(".status{margin-left:auto;color:#aaa;font-size:12px;}");
  doc.write("textarea{width:100%;height:calc(100vh - 52px);box-sizing:border-box;border:0;outline:none;padding:12px;background:#111319;color:#e8e6ed;font-family:'Liberation Mono','DejaVu Sans Mono',monospace;font-size:12px;line-height:1.25;resize:none;}");
  doc.write("</style></head><body>");
  doc.write("<div class=\"toolbar\"><button id=\"btnSave\">Save</button><button id=\"btnReload\" class=\"secondary\">Reload</button><span id=\"status\" class=\"status\">ready</span></div>");
  doc.write("<textarea id=\"txt\"></textarea>");
  doc.write("</body></html>");
  doc.close();
  attachI18n(doc);

  const textarea = doc.getElementById("txt");
  const statusEl = doc.getElementById("status");
  textarea.value = text;
  registerInputEditor(path, w, () => textarea.value);

  function setWinStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  doc.getElementById("btnSave").addEventListener("click", async () => {
    const editorPath = w.__stbEditorPath;
    try {
      setWinStatus("saving...");
      if (await inputTextMatchesDisk(editorPath, textarea.value, w)) {
        setWinStatus("no changes");
        setStatus(editorPath + " — no changes to save");
        return;
      }
      const result = await saveInputText(editorPath, textarea.value, w);
      if (result && result.changed === false) {
        setWinStatus("no changes");
        setStatus(editorPath + " — no changes to save");
        return;
      }
      resetEditHistory();
      setWinStatus("saved");
      setStatus(editorPath + " — input file saved (undo history cleared)");
      if (getCurrentModelPath() === editorPath) await loadSelectedModel(false);
    } catch (ex) {
      setWinStatus("save failed");
      setStatus("Error: " + ex.message);
      alert("Save failed: " + ex.message);
    }
  });

  doc.getElementById("btnReload").addEventListener("click", async () => {
    const editorPath = w.__stbEditorPath;
    try {
      setWinStatus("reloading...");
      const latest = await fetchInputText(editorPath, w);
      textarea.value = latest;
      setWinStatus("reloaded");
    } catch (ex) {
      setWinStatus("reload failed");
      alert("Reload failed: " + ex.message);
    }
  });

  doc.addEventListener("keydown", (ev) => {
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "s" || ev.key === "S")) {
      ev.preventDefault();
      doc.getElementById("btnSave").click();
    }
  });
}

async function saveCurrentModel() {
  const path = getCurrentModelPath();
  if (!path) {
    setStatus("No model open");
    return;
  }
  setStatus("Saving " + path + "…");
  try {
    const edited = getInputEditorText(path);
    const text = edited != null ? edited : await fetchInputText(path);
    if (await inputTextMatchesDisk(path, text)) {
      setStatus(path + " — no changes to save");
      return;
    }
    const result = await saveInputText(path, text);
    if (result && result.changed === false) {
      setStatus(path + " — no changes to save");
      return;
    }
    resetEditHistory();
    if (getCurrentModelPath() === path) await loadSelectedModel(false);
    setStatus(path + " — saved");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

async function openInputWindow() {
  const path = getCurrentModelPath();
  if (!path) return;

  setStatus("Loading " + path + "…");
  try {
    const text = await fetchInputText(path);
    showInputEditorWindow(text, path);
    setStatus(path + " — input file opened (editable)");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

async function openResultsWindow() {
  const path = getCurrentModelPath();
  if (!path) return;

  let text = currentResultsText;

  if (text == null || text == "") {
    setStatus("Solving " + path + " for output…");
    try {
      currentModel = await fetchModel(path, true);
      text = currentModel.results_text;
      if (text == null || text == "") {
        throw new Error("No result text from server — restart: stb gui");
      }
      currentResultsText = text;
      fillLcSelect(currentModel);
      enrichModelReactions(currentModel);
      const complete = analysisComplete(currentModel);
      el.chkDeformed.disabled = !complete;
      setForceControlsEnabled(complete);
      setReactionControlsEnabled(complete);
      setDispContourControlsEnabled(complete);
      if (complete) el.chkReactions.checked = true;
      buildModelScene(currentModel);
    } catch (ex) {
      setStatus("Error: " + ex.message);
      return;
    }
  }

  showResultsWindow(text, path);
  setStatus(path + " — output opened in new window");
}

async function createNewModel() {
  setStatus("Creating new model…");
  try {
    const res = await fetch("/api/model/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: guiMode }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    setCurrentModelPath(data.path);
    await loadSelectedModel(false);
    await openInputWindow();
    setStatus(data.path + " — new model");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

function promptOpenModelFile() {
  if (el.openFileInput) el.openFileInput.click();
}

async function openUploadedModelFile(file) {
  if (!file) return;
  setStatus("Opening " + file.name + "…");
  try {
    const text = await file.text();
    const res = await fetch("/api/model/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, text: text }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    setCurrentModelPath(data.path);
    await loadSelectedModel(false);
    setStatus(data.path + " — opened");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

let stbShutdownRequested = false;
let stbPageReloading = false;
let stbExitWithBrowser = false;

function requestServerShutdown() {
  if (stbShutdownRequested) return;
  stbShutdownRequested = true;
  const url = "/api/shutdown";
  if (typeof navigator !== "undefined" && navigator.sendBeacon) {
    navigator.sendBeacon(url, "");
  } else {
    fetch(url, { method: "POST", keepalive: true }).catch(() => {});
  }
}

function markStbPageReload() {
  stbPageReloading = true;
}

function sendGuiHeartbeat() {
  fetch("/api/heartbeat", { method: "POST", keepalive: true }).catch(() => {});
}

function startGuiHeartbeat() {
  sendGuiHeartbeat();
  window.setInterval(sendGuiHeartbeat, 4000);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      sendGuiHeartbeat();
    }
  });
}

async function initGuiLifecycle() {
  try {
    const cfg = await fetchApiJson("/api/gui-config");
    stbExitWithBrowser = !!cfg.exit_with_browser;
  } catch (_) {
    stbExitWithBrowser = false;
  }
  if (stbExitWithBrowser) {
    startGuiHeartbeat();
  }
}

async function closeApplication() {
  setStatus("Closing…");
  closeAllChildWindows();
  requestServerShutdown();
  window.close();
}

window.addEventListener("keydown", (ev) => {
  const key = String(ev.key || "").toLowerCase();
  if (key === "f5" || ((ev.ctrlKey || ev.metaKey) && key === "r")) {
    markStbPageReload();
  }
});

window.addEventListener("pagehide", (ev) => {
  if (!stbExitWithBrowser) return;
  if (ev.persisted || stbPageReloading) {
    stbPageReloading = false;
    return;
  }
  requestServerShutdown();
});

initGuiLifecycle();

async function loadSelectedModel(solve, options) {
  options = options || {};
  const path = getCurrentModelPath();
  if (!path) return;
  const cameraState = options.keepCamera ? captureCameraState() : null;
  if (!options.keepSelection) clearSelection();
  if (!options.keepMemberVisibility) resetMemberVisibilityFilter();
  if (solve) {
    setStatus("Solving " + path + "…");
  } else {
    setStatus("Loading " + path + "…");
    currentResultsText = null;
  }
  try {
    currentModel = await fetchModel(path, solve);
    if (solve) {
      currentResultsText = currentModel.results_text || null;
    }
    enrichModelReactions(currentModel);
    fillLcSelect(currentModel);
    const complete = analysisComplete(currentModel);
    el.chkDeformed.disabled = !complete;
    setForceControlsEnabled(complete);
    setReactionControlsEnabled(complete);
    setDispContourControlsEnabled(complete);
    applyDisplayPrefsToUi();
    if (!complete) {
      el.chkDeformed.checked = false;
      if (el.chkDispContour) el.chkDispContour.checked = false;
    }
    if (displayPrefs.windLoads) {
      await loadWindVisualForCurrentModel();
    } else {
      windVisualData = null;
      selectedWindCaseId = null;
      windVisualStatus = "idle";
      populateWindCaseSelect();
      updateWindControlsAvailability();
    }
    practiceSummaryData = null;
    if (el.chkPracticeCenters && el.chkPracticeCenters.checked && analysisComplete(currentModel)) {
      await loadPracticeSummaryForCurrentModel();
    }
    if (options.keepMemberVisibility) pruneMemberVisibilityFilter();
    buildModelScene(currentModel);
    if (!solve || !complete) {
      if (cameraState) {
        restoreCameraState(cameraState);
      } else {
        fitCamera(currentModel);
      }
    }
    saveLastModelPath(path);
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

async function bootstrap() {
  loadPickWrwCreateModel();
  loadPickSubMode();
  initUiTheme();
  applyGuiMode(loadGuiMode());
  const listPromise = fetchModelList();
  initThree();
  initDisplayPrefs();
  initViewerOptions();
  initSelectionInteraction();
  initDistanceInteraction();
  initContextMenu();
  initEditHistoryShortcuts();
  initDraggablePanel({
    panel: el.selectionPanel,
    header: el.selectionPanelHeader,
    collapseBtn: el.btnSelectionCollapse,
    storageKey: "stb_gui_selection_panel",
    defaultHidden: true,
    autoVisibility: true,
  });
  updateSelectionPanelVisibility();
  updatePickModeUI();
  initDraggablePanel({
    panel: el.resultsPanel,
    header: el.resultsPanelHeader,
    collapseBtn: el.btnPanelCollapse,
    toggleBtn: el.btnTogglePanel,
    storageKey: "stb_gui_results_panel",
    defaultHidden: false,
  });
  initDraggablePanel({
    panel: el.optionsPanel,
    header: el.optionsPanelHeader,
    collapseBtn: el.btnOptionsCollapse,
    toggleBtn: el.btnToggleOptions,
    storageKey: "stb_gui_options_panel",
    defaultHidden: true,
  });
  try {
    const data = await listPromise;
    const launchFile = launchFileFromUrl();
    const initial = resolveInitialModel(data.models, data.default);
    if (initial) {
      setCurrentModelPath(initial);
      if (launchFile && initial === launchFile) clearLaunchFileFromUrl();
      await loadSelectedModel(false);
    } else {
      setCurrentModelPath(null);
      setStatus("Ready — use New or Open");
    }
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

el.btnNew.addEventListener("click", () => createNewModel());
el.btnOpen.addEventListener("click", () => promptOpenModelFile());
el.btnSave.addEventListener("click", () => saveCurrentModel());
el.btnClose.addEventListener("click", () => closeApplication());
if (el.openFileInput) {
  el.openFileInput.addEventListener("change", () => {
    const file = el.openFileInput.files && el.openFileInput.files[0];
    el.openFileInput.value = "";
    openUploadedModelFile(file);
  });
}

el.btnReload.addEventListener("click", () => loadSelectedModel(false));
el.btnSolve.addEventListener("click", () => loadSelectedModel(true));

function isViewerTypingTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === "TEXTAREA" || target.isContentEditable;
}

function isViewerTextInputTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

document.addEventListener("keydown", (ev) => {
  if ((ev.ctrlKey || ev.metaKey) && (ev.key === "s" || ev.key === "S")) {
    if (isViewerTypingTarget(ev.target)) return;
    ev.preventDefault();
    saveCurrentModel();
    return;
  }

  if (isViewerTextInputTarget(ev.target)) return;

  if (ev.key === "F5" || ev.code === "F5") {
    ev.preventDefault();
    loadSelectedModel(true);
    return;
  }

  if (ev.key === "p" || ev.key === "P") {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    ev.preventDefault();
    setSelectionMode(!selectionModeActive);
    return;
  }

  if (selectionModeActive) {
    if (ev.key === "n" || ev.key === "N") {
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      ev.preventDefault();
      togglePickSubMode("node");
      return;
    }
    if (ev.key === "m" || ev.key === "M") {
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      ev.preventDefault();
      togglePickSubMode("member");
      return;
    }
    if (ev.key === "e" || ev.key === "E") {
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      ev.preventDefault();
      togglePickSubMode("member");
      return;
    }
    if (ev.key === "i" || ev.key === "I") {
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      ev.preventDefault();
      togglePickSubMode("diaphragm");
      return;
    }
    if (ev.key === "w" || ev.key === "W") {
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      ev.preventDefault();
      togglePickSubMode("wall");
      return;
    }
    if (ev.key === "Delete" || ev.code === "Delete") {
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      if (!hasPickSelection()) return;
      ev.preventDefault();
      deletePickSelection();
      return;
    }
  }

  if (ev.key === "d" || ev.key === "D") {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    ev.preventDefault();
    setDistanceMode(!distanceModeActive);
  }
});

el.btnToggleAxes.addEventListener("click", () => {
  showWorldAxes = !showWorldAxes;
  displayPrefs.showWorldAxes = showWorldAxes;
  saveDisplayPrefs();
  el.btnToggleAxes.classList.toggle("active", showWorldAxes);
  if (currentModel) {
    updateWorldAxes(currentModel);
  } else {
    clearGroup(axesGroup);
  }
});

if (el.btnToggleSelect) {
  el.btnToggleSelect.addEventListener("click", () => {
    setSelectionMode(!selectionModeActive);
  });
}

if (el.pickModeNode) {
  el.pickModeNode.addEventListener("click", () => {
    togglePickSubMode("node");
  });
}
if (el.pickModeMember) {
  el.pickModeMember.addEventListener("click", () => {
    togglePickSubMode("member");
  });
}
if (el.pickModeDiaphragm) {
  el.pickModeDiaphragm.addEventListener("click", () => {
    togglePickSubMode("diaphragm");
  });
}
if (el.pickModeWall) {
  el.pickModeWall.addEventListener("click", () => {
    togglePickSubMode("wall");
  });
}

if (el.btnToggleDistance) {
  el.btnToggleDistance.addEventListener("click", () => {
    setDistanceMode(!distanceModeActive);
  });
}

if (el.optTheme) {
  el.optTheme.addEventListener("change", () => {
    applyUiTheme(el.optTheme.value);
    saveUiTheme();
  });
}

if (el.btnGuiMode) {
  el.btnGuiMode.addEventListener("click", () => {
    applyGuiMode(guiMode === "simple" ? "advanced" : "simple");
    try {
      localStorage.setItem(GUI_MODE_STORAGE_KEY, guiMode);
    } catch (e) { /* ignore */ }
  });
}

if (el.btnViewProjection) {
  el.btnViewProjection.addEventListener("click", () => {
    toggleCameraProjectionMode();
  });
}

if (el.viewPreset) {
  el.viewPreset.addEventListener("change", () => {
    const name = el.viewPreset.value;
    if (!name) return;
    setStandardView(name);
  });
}

if (el.btnClearSelection) {
  el.btnClearSelection.addEventListener("click", () => clearSelection());
}

el.btnInput.addEventListener("click", () => openInputWindow());
el.btnProject.addEventListener("click", () => openProjectWindow());
el.btnLoads.addEventListener("click", () => openLoadsVerifyWindow());
if (el.btnPractice) {
  el.btnPractice.addEventListener("click", () => openPracticeVerifyWindow());
}
el.btnOutput.addEventListener("click", () => openResultsWindow());
el.lcSelect.addEventListener("change", () => {
  dispContourScaleKey = null;
  onResultsDisplayChanged();
  if (windVisualData && el.chkWindLoads && el.chkWindLoads.checked) {
    selectedWindCaseId = pickWindCaseIdForLc(windVisualData);
    onResultsDisplayChanged();
    populateWindCaseSelect();
  }
  if (currentModel) rebuildScene();
  updateSelectionPanel();
});
el.defFactor.addEventListener("change", () => {
  dispContourScaleKey = null;
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
if (el.dispComponent) {
  el.dispComponent.addEventListener("change", () => {
    dispContourScaleKey = null;
    onResultsDisplayChanged();
    if (currentModel) rebuildScene();
  });
}
el.chkDeformed.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.chkDispContour.addEventListener("change", () => {
  if (currentModel && el.chkDispContour.checked) {
    dispContourScaleKey = null;
  }
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
if (el.dispContourMin) {
  el.dispContourMin.addEventListener("change", () => {
    onResultsDisplayChanged();
    if (currentModel) rebuildScene();
  });
}
if (el.dispContourMax) {
  el.dispContourMax.addEventListener("change", () => {
    onResultsDisplayChanged();
    if (currentModel) rebuildScene();
  });
}
if (el.btnDispContourAuto) {
  el.btnDispContourAuto.addEventListener("click", () => applyDispContourAutoRange());
}
el.chkSupports.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
if (el.chkEJnt) {
  el.chkEJnt.addEventListener("change", () => {
    onResultsDisplayChanged();
    if (currentModel) rebuildScene();
  });
}
el.chkLoads.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.chkLoadValues.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
if (el.chkWindLoads) {
  el.chkWindLoads.addEventListener("change", async () => {
    onResultsDisplayChanged();
    if (el.chkWindLoads.checked && windVisualStatus !== "loaded") {
      setStatus("Loading wind overlay…");
      await loadWindVisualForCurrentModel();
      if (!(windVisualData && windVisualData.cases && windVisualData.cases.length)) {
        el.chkWindLoads.checked = false;
        onResultsDisplayChanged();
        populateWindCaseSelect();
        updateWindControlsAvailability();
        setStatus("No wind cases for this model.");
        return;
      }
    }
    populateWindCaseSelect();
    updateWindControlsAvailability();
    if (el.chkWindLoads.checked && windVisualData) {
      const wc = windCaseById(windVisualData, selectedWindCaseId);
      syncLcToWindCase(wc);
    }
    if (currentModel) rebuildScene();
  });
}
if (el.chkPracticeCenters) {
  el.chkPracticeCenters.addEventListener("change", async () => {
    onResultsDisplayChanged();
    if (el.chkPracticeCenters.checked) {
      if (!currentModel || !analysisComplete(currentModel)) {
        el.chkPracticeCenters.checked = false;
        onResultsDisplayChanged();
        setStatus("CoG / CoR requires analysis — use Solve (F5) first.");
        return;
      }
      if (!practiceSummaryData) {
        await loadPracticeSummaryForCurrentModel();
      }
    } else {
      practiceSummaryData = null;
    }
    if (currentModel) rebuildScene();
  });
}
if (el.windCaseSelect) {
  el.windCaseSelect.addEventListener("change", () => {
    const raw = el.windCaseSelect.value;
    selectedWindCaseId = raw ? Number(raw) : null;
    onResultsDisplayChanged();
    if (el.chkWindLoads && el.chkWindLoads.checked && windVisualData) {
      const wc = windCaseById(windVisualData, selectedWindCaseId);
      syncLcToWindCase(wc);
    }
    if (currentModel) rebuildScene();
  });
}
el.chkReactions.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.chkReactionValues.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.chkLabels.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.chkElemLabels.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.chkMaterial.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.chkSection.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
if (el.chkSectionSolids) {
  el.chkSectionSolids.addEventListener("change", () => {
    onResultsDisplayChanged();
    if (currentModel) rebuildScene();
  });
}
if (el.btnExportSectionSolidsDxf) {
  el.btnExportSectionSolidsDxf.addEventListener("click", exportSectionSolidsDxf);
}
if (el.chkMembrane) {
  el.chkMembrane.addEventListener("change", () => {
    onResultsDisplayChanged();
    syncRegionEdgeCheckboxes();
    if (currentModel) rebuildScene();
  });
}
if (el.chkMembraneEdge) {
  el.chkMembraneEdge.addEventListener("change", () => {
    onResultsDisplayChanged();
    if (currentModel) rebuildScene();
  });
}
if (el.chkWoodWall) {
  el.chkWoodWall.addEventListener("change", () => {
    onResultsDisplayChanged();
    syncRegionEdgeCheckboxes();
    if (currentModel) rebuildScene();
  });
}
if (el.chkWoodWallEdge) {
  el.chkWoodWallEdge.addEventListener("change", () => {
    onResultsDisplayChanged();
    if (currentModel) rebuildScene();
  });
}
if (el.chkColocated) {
  el.chkColocated.addEventListener("change", () => {
    onResultsDisplayChanged();
    if (currentModel) rebuildScene();
  });
}
syncRegionEdgeCheckboxes();
el.forceSelect.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.frcDiv.addEventListener("input", () => {
  el.frcDivVal.textContent = el.frcDiv.value;
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.frcFactor.addEventListener("input", () => {
  el.frcFactorVal.textContent = el.frcFactor.value;
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});
el.chkForceValues.addEventListener("change", () => {
  onResultsDisplayChanged();
  if (currentModel) rebuildScene();
});

function readDisplayPrefsFromUi() {
  displayPrefs.defFactor = parseFloat(el.defFactor.value);
  if (!isFinite(displayPrefs.defFactor)) displayPrefs.defFactor = RESULTS_DISPLAY_DEFAULTS.defFactor;
  displayPrefs.deformed = !!(el.chkDeformed && el.chkDeformed.checked);
  displayPrefs.dispContour = !!(el.chkDispContour && el.chkDispContour.checked);
  displayPrefs.dispComponent = currentDispComponent();
  displayPrefs.supports = !el.chkSupports || el.chkSupports.checked;
  displayPrefs.ejnt = !!(el.chkEJnt && el.chkEJnt.checked);
  displayPrefs.loads = !!(el.chkLoads && el.chkLoads.checked);
  displayPrefs.loadValues = !!(el.chkLoadValues && el.chkLoadValues.checked);
  displayPrefs.windLoads = !!(el.chkWindLoads && el.chkWindLoads.checked);
  displayPrefs.practiceCenters = !!(el.chkPracticeCenters && el.chkPracticeCenters.checked);
  displayPrefs.reactions = !!(el.chkReactions && el.chkReactions.checked);
  displayPrefs.reactionValues = !!(el.chkReactionValues && el.chkReactionValues.checked);
  displayPrefs.nodeLabels = !!(el.chkLabels && el.chkLabels.checked);
  displayPrefs.elemLabels = !!(el.chkElemLabels && el.chkElemLabels.checked);
  displayPrefs.material = !!(el.chkMaterial && el.chkMaterial.checked);
  displayPrefs.section = !!(el.chkSection && el.chkSection.checked);
  displayPrefs.sectionSolids = !!(el.chkSectionSolids && el.chkSectionSolids.checked);
  displayPrefs.membrane = !!(el.chkMembrane && el.chkMembrane.checked);
  displayPrefs.membraneEdge = !!(el.chkMembraneEdge && el.chkMembraneEdge.checked);
  displayPrefs.woodWall = !!(el.chkWoodWall && el.chkWoodWall.checked);
  displayPrefs.woodWallEdge = !!(el.chkWoodWallEdge && el.chkWoodWallEdge.checked);
  displayPrefs.colocated = !!(el.chkColocated && el.chkColocated.checked);
  displayPrefs.forceComponent = parseInt(el.forceSelect.value, 10) || 0;
  displayPrefs.forceDiv = parseInt(el.frcDiv.value, 10) || RESULTS_DISPLAY_DEFAULTS.forceDiv;
  displayPrefs.forceFactor = parseFloat(el.frcFactor.value) || RESULTS_DISPLAY_DEFAULTS.forceFactor;
  displayPrefs.forceValues = !!(el.chkForceValues && el.chkForceValues.checked);
  displayPrefs.loadCase = el.lcSelect && el.lcSelect.value ? String(el.lcSelect.value) : null;
  displayPrefs.windCaseId = selectedWindCaseId;
  if (el.dispContourMin) displayPrefs.dispContourMin = String(el.dispContourMin.value || "");
  if (el.dispContourMax) displayPrefs.dispContourMax = String(el.dispContourMax.value || "");
  displayPrefs.showWorldAxes = showWorldAxes;
}

function applyDisplayPrefsToUi() {
  el.defFactor.value = String(displayPrefs.defFactor);
  if (el.dispComponent) el.dispComponent.value = normalizeDispComponent(displayPrefs.dispComponent);
  if (el.chkDeformed && !el.chkDeformed.disabled) el.chkDeformed.checked = !!displayPrefs.deformed;
  if (el.chkDispContour && !el.chkDispContour.disabled) {
    el.chkDispContour.checked = !!displayPrefs.dispContour;
  }
  if (el.chkSupports) el.chkSupports.checked = !!displayPrefs.supports;
  if (el.chkEJnt) el.chkEJnt.checked = !!displayPrefs.ejnt;
  if (el.chkLoads) el.chkLoads.checked = !!displayPrefs.loads;
  if (el.chkLoadValues) el.chkLoadValues.checked = !!displayPrefs.loadValues;
  if (el.chkWindLoads && !el.chkWindLoads.disabled) el.chkWindLoads.checked = !!displayPrefs.windLoads;
  if (el.chkPracticeCenters) el.chkPracticeCenters.checked = !!displayPrefs.practiceCenters;
  if (el.chkReactions && !el.chkReactions.disabled) el.chkReactions.checked = !!displayPrefs.reactions;
  if (el.chkReactionValues && !el.chkReactionValues.disabled) {
    el.chkReactionValues.checked = !!displayPrefs.reactionValues;
  }
  if (el.chkLabels) el.chkLabels.checked = !!displayPrefs.nodeLabels;
  if (el.chkElemLabels) el.chkElemLabels.checked = !!displayPrefs.elemLabels;
  if (el.chkMaterial) el.chkMaterial.checked = !!displayPrefs.material;
  if (el.chkSection) el.chkSection.checked = !!displayPrefs.section;
  if (el.chkSectionSolids) el.chkSectionSolids.checked = !!displayPrefs.sectionSolids;
  if (el.chkMembrane) el.chkMembrane.checked = !!displayPrefs.membrane;
  if (el.chkMembraneEdge) el.chkMembraneEdge.checked = !!displayPrefs.membraneEdge;
  if (el.chkWoodWall) el.chkWoodWall.checked = !!displayPrefs.woodWall;
  if (el.chkWoodWallEdge) el.chkWoodWallEdge.checked = !!displayPrefs.woodWallEdge;
  if (el.chkColocated) el.chkColocated.checked = !!displayPrefs.colocated;
  if (!el.forceSelect.disabled) el.forceSelect.value = String(displayPrefs.forceComponent);
  if (!el.frcDiv.disabled) {
    el.frcDiv.value = String(displayPrefs.forceDiv);
    el.frcDivVal.textContent = String(displayPrefs.forceDiv);
  }
  if (!el.frcFactor.disabled) {
    el.frcFactor.value = String(displayPrefs.forceFactor);
    el.frcFactorVal.textContent = String(displayPrefs.forceFactor);
  }
  if (!el.chkForceValues.disabled) el.chkForceValues.checked = !!displayPrefs.forceValues;
  if (displayPrefs.loadCase && el.lcSelect) {
    const hasLc = Array.from(el.lcSelect.options).some(function (o) {
      return o.value === displayPrefs.loadCase;
    });
    if (hasLc) el.lcSelect.value = displayPrefs.loadCase;
  }
  if (displayPrefs.windCaseId != null && windVisualData) {
    if (windCaseById(windVisualData, displayPrefs.windCaseId)) {
      selectedWindCaseId = displayPrefs.windCaseId;
    }
  }
  if (el.dispContourMin) el.dispContourMin.value = displayPrefs.dispContourMin || "";
  if (el.dispContourMax) el.dispContourMax.value = displayPrefs.dispContourMax || "";
  syncRegionEdgeCheckboxes();
}

function saveDisplayPrefs() {
  try {
    localStorage.setItem(RESULTS_DISPLAY_STORAGE_KEY, JSON.stringify(displayPrefs));
  } catch (e) { /* ignore */ }
}

function loadDisplayPrefs() {
  try {
    const raw = localStorage.getItem(RESULTS_DISPLAY_STORAGE_KEY);
    if (!raw) return;
    const st = JSON.parse(raw);
    if (typeof st.defFactor === "number" && isFinite(st.defFactor)) displayPrefs.defFactor = st.defFactor;
    if (typeof st.deformed === "boolean") displayPrefs.deformed = st.deformed;
    if (typeof st.dispContour === "boolean") displayPrefs.dispContour = st.dispContour;
    if (typeof st.dispComponent === "string") displayPrefs.dispComponent = normalizeDispComponent(st.dispComponent);
    if (typeof st.supports === "boolean") displayPrefs.supports = st.supports;
    if (typeof st.ejnt === "boolean") displayPrefs.ejnt = st.ejnt;
    if (typeof st.loads === "boolean") displayPrefs.loads = st.loads;
    if (typeof st.loadValues === "boolean") displayPrefs.loadValues = st.loadValues;
    if (typeof st.windLoads === "boolean") displayPrefs.windLoads = st.windLoads;
    if (typeof st.practiceCenters === "boolean") displayPrefs.practiceCenters = st.practiceCenters;
    if (typeof st.reactions === "boolean") displayPrefs.reactions = st.reactions;
    if (typeof st.reactionValues === "boolean") displayPrefs.reactionValues = st.reactionValues;
    if (typeof st.nodeLabels === "boolean") displayPrefs.nodeLabels = st.nodeLabels;
    if (typeof st.elemLabels === "boolean") displayPrefs.elemLabels = st.elemLabels;
    if (typeof st.material === "boolean") displayPrefs.material = st.material;
    if (typeof st.section === "boolean") displayPrefs.section = st.section;
    if (typeof st.sectionSolids === "boolean") displayPrefs.sectionSolids = st.sectionSolids;
    if (typeof st.membrane === "boolean") displayPrefs.membrane = st.membrane;
    if (typeof st.membraneEdge === "boolean") displayPrefs.membraneEdge = st.membraneEdge;
    if (typeof st.woodWall === "boolean") displayPrefs.woodWall = st.woodWall;
    if (typeof st.woodWallEdge === "boolean") displayPrefs.woodWallEdge = st.woodWallEdge;
    if (typeof st.colocated === "boolean") displayPrefs.colocated = st.colocated;
    if (typeof st.forceComponent === "number") displayPrefs.forceComponent = st.forceComponent;
    if (typeof st.forceDiv === "number") displayPrefs.forceDiv = st.forceDiv;
    if (typeof st.forceFactor === "number") displayPrefs.forceFactor = st.forceFactor;
    if (typeof st.forceValues === "boolean") displayPrefs.forceValues = st.forceValues;
    if (typeof st.loadCase === "string" || st.loadCase === null) displayPrefs.loadCase = st.loadCase;
    if (typeof st.windCaseId === "number" || st.windCaseId === null) displayPrefs.windCaseId = st.windCaseId;
    if (typeof st.dispContourMin === "string") displayPrefs.dispContourMin = st.dispContourMin;
    if (typeof st.dispContourMax === "string") displayPrefs.dispContourMax = st.dispContourMax;
    if (typeof st.showWorldAxes === "boolean") displayPrefs.showWorldAxes = st.showWorldAxes;
  } catch (e) { /* ignore */ }
}

function onResultsDisplayChanged() {
  readDisplayPrefsFromUi();
  saveDisplayPrefs();
}

function initDisplayPrefs() {
  loadDisplayPrefs();
  applyDisplayPrefsToUi();
  showWorldAxes = !!displayPrefs.showWorldAxes;
  if (el.btnToggleAxes) {
    el.btnToggleAxes.classList.toggle("active", showWorldAxes);
  }
}

function readOptionsFromUi() {
  viewerOptions.loadArrowSize = clampViewerOption(
    "loadArrowSize", parseFloat(el.optLoadArrow.value) || OPTIONS_DEFAULTS.loadArrowSize);
  viewerOptions.reactionArrowSize = clampViewerOption(
    "reactionArrowSize", parseFloat(el.optReactionArrow.value) || OPTIONS_DEFAULTS.reactionArrowSize);
  viewerOptions.supportGizmoSize = clampViewerOption(
    "supportGizmoSize", parseInt(el.optSupportGizmo.value, 10) || OPTIONS_DEFAULTS.supportGizmoSize);
  if (el.optAxesSize) {
    viewerOptions.axesSize = clampViewerOption(
      "axesSize", parseInt(el.optAxesSize.value, 10) || OPTIONS_DEFAULTS.axesSize);
  }
  viewerOptions.supportLineWidth = clampViewerOption(
    "supportLineWidth", parseFloat(el.optSupportLineWidth.value) || OPTIONS_DEFAULTS.supportLineWidth);
  viewerOptions.dispContourLineWidth = clampViewerOption(
    "dispContourLineWidth", parseFloat(el.optDispContourLineWidth.value) || OPTIONS_DEFAULTS.dispContourLineWidth);
  viewerOptions.elementLineWidth = clampViewerOption(
    "elementLineWidth", parseFloat(el.optElementLineWidth.value) || OPTIONS_DEFAULTS.elementLineWidth);
  viewerOptions.loadLineWidth = clampViewerOption(
    "loadLineWidth", parseFloat(el.optLoadLineWidth.value) || OPTIONS_DEFAULTS.loadLineWidth);
  viewerOptions.reactionLineWidth = clampViewerOption(
    "reactionLineWidth", parseFloat(el.optReactionLineWidth.value) || OPTIONS_DEFAULTS.reactionLineWidth);
  viewerOptions.forceLineWidth = clampViewerOption(
    "forceLineWidth", parseFloat(el.optForceLineWidth.value) || OPTIONS_DEFAULTS.forceLineWidth);
  viewerOptions.nodeLabelSize = clampViewerOption(
    "nodeLabelSize", parseFloat(el.optNodeLabel.value) || OPTIONS_DEFAULTS.nodeLabelSize);
  viewerOptions.elemLabelSize = clampViewerOption(
    "elemLabelSize", parseFloat(el.optElemLabel.value) || OPTIONS_DEFAULTS.elemLabelSize);
  viewerOptions.materialLabelSize = clampViewerOption(
    "materialLabelSize", parseFloat(el.optMaterialLabel.value) || OPTIONS_DEFAULTS.materialLabelSize);
  viewerOptions.sectionLabelSize = clampViewerOption(
    "sectionLabelSize", parseFloat(el.optSectionLabel.value) || OPTIONS_DEFAULTS.sectionLabelSize);
  viewerOptions.loadLabelSize = clampViewerOption(
    "loadLabelSize", parseFloat(el.optLoadLabel.value) || OPTIONS_DEFAULTS.loadLabelSize);
  viewerOptions.reactionLabelSize = clampViewerOption(
    "reactionLabelSize", parseFloat(el.optReactionLabel.value) || OPTIONS_DEFAULTS.reactionLabelSize);
  viewerOptions.forceLabelSize = clampViewerOption(
    "forceLabelSize", parseFloat(el.optForceLabel.value) || OPTIONS_DEFAULTS.forceLabelSize);
  if (el.optSectionSolidOpacity) {
    viewerOptions.sectionSolidOpacity = clampViewerOption(
      "sectionSolidOpacity",
      parseFloat(el.optSectionSolidOpacity.value) || OPTIONS_DEFAULTS.sectionSolidOpacity
    );
  }
  if (el.optSectionSolidColor) {
    viewerOptions.sectionSolidColor = sanitizeHexColor(
      el.optSectionSolidColor.value,
      OPTIONS_DEFAULTS.sectionSolidColor
    );
  }
  if (el.loadTypeFilter) {
    viewerOptions.inputLoadType = el.loadTypeFilter.value || OPTIONS_DEFAULTS.inputLoadType;
  }
}

function applyOptionsToUi() {
  el.optLoadArrow.value = String(viewerOptions.loadArrowSize);
  el.optLoadArrowVal.textContent = Number(viewerOptions.loadArrowSize).toFixed(1);
  if (el.optReactionArrow) {
    el.optReactionArrow.value = String(viewerOptions.reactionArrowSize);
    el.optReactionArrowVal.textContent = Number(viewerOptions.reactionArrowSize).toFixed(1);
  }
  el.optSupportGizmo.value = String(viewerOptions.supportGizmoSize);
  el.optSupportGizmoVal.textContent = String(viewerOptions.supportGizmoSize);
  if (el.optAxesSize) {
    el.optAxesSize.value = String(viewerOptions.axesSize);
    el.optAxesSizeVal.textContent = String(viewerOptions.axesSize);
  }
  el.optSupportLineWidth.value = String(viewerOptions.supportLineWidth);
  el.optDispContourLineWidth.value = String(viewerOptions.dispContourLineWidth);
  if (el.optElementLineWidth) el.optElementLineWidth.value = String(viewerOptions.elementLineWidth);
  if (el.optLoadLineWidth) el.optLoadLineWidth.value = String(viewerOptions.loadLineWidth);
  if (el.optReactionLineWidth) el.optReactionLineWidth.value = String(viewerOptions.reactionLineWidth);
  if (el.optForceLineWidth) el.optForceLineWidth.value = String(viewerOptions.forceLineWidth);
  el.optNodeLabel.value = String(viewerOptions.nodeLabelSize);
  el.optNodeLabelVal.textContent = String(viewerOptions.nodeLabelSize);
  el.optElemLabel.value = String(viewerOptions.elemLabelSize);
  el.optElemLabelVal.textContent = String(viewerOptions.elemLabelSize);
  el.optMaterialLabel.value = String(viewerOptions.materialLabelSize);
  el.optMaterialLabelVal.textContent = String(viewerOptions.materialLabelSize);
  el.optSectionLabel.value = String(viewerOptions.sectionLabelSize);
  el.optSectionLabelVal.textContent = String(viewerOptions.sectionLabelSize);
  el.optLoadLabel.value = String(viewerOptions.loadLabelSize);
  el.optLoadLabelVal.textContent = String(viewerOptions.loadLabelSize);
  el.optReactionLabel.value = String(viewerOptions.reactionLabelSize);
  el.optReactionLabelVal.textContent = String(viewerOptions.reactionLabelSize);
  el.optForceLabel.value = String(viewerOptions.forceLabelSize);
  el.optForceLabelVal.textContent = String(viewerOptions.forceLabelSize);
  if (el.optSectionSolidOpacity) {
    el.optSectionSolidOpacity.value = String(viewerOptions.sectionSolidOpacity);
    if (el.optSectionSolidOpacityVal) {
      el.optSectionSolidOpacityVal.textContent = Number(viewerOptions.sectionSolidOpacity).toFixed(2);
    }
  }
  if (el.optSectionSolidColor) {
    el.optSectionSolidColor.value = sanitizeHexColor(
      viewerOptions.sectionSolidColor,
      OPTIONS_DEFAULTS.sectionSolidColor
    );
  }
  if (el.loadTypeFilter) {
    el.loadTypeFilter.value = loadTypeFilterValue();
  }
}

function saveViewerOptions() {
  try {
    localStorage.setItem(OPTIONS_STORAGE_KEY, JSON.stringify(viewerOptions));
  } catch (e) { /* ignore */ }
}

function normalizeUiTheme(theme) {
  return theme === "light" ? "light" : "dark";
}

function uiThemeMetaColor(theme) {
  return theme === "light" ? "#f4f5f7" : "#1a1a22";
}

function applyRenderTheme(theme) {
  const palette = THEME_RENDER_COLORS[theme] || THEME_RENDER_COLORS.dark;
  COLORS.background = palette.background;
  COLORS.element = palette.element;
  COLORS.node = palette.node;
  COLORS.membraneEdge = palette.membraneEdge;
  COLORS.woodWallEdge = palette.woodWallEdge;
  COLORS.nodeLabel = palette.nodeLabel;
  if (scene) {
    scene.background = new THREE.Color(COLORS.background);
  }
  if (_nodeLabelLeaderMat) {
    _nodeLabelLeaderMat.color.setHex(COLORS.nodeLabel);
    _nodeLabelLeaderMat.needsUpdate = true;
  }
  clearSupportDiscTextureCache();
}

function preferredUiTheme() {
  if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
    return "light";
  }
  return "dark";
}

function loadUiTheme() {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY);
    if (!raw) return preferredUiTheme();
    return normalizeUiTheme(raw);
  } catch (e) {
    return preferredUiTheme();
  }
}

function saveUiTheme() {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, uiTheme);
  } catch (e) { /* ignore */ }
}

function applyUiTheme(theme) {
  uiTheme = normalizeUiTheme(theme);
  document.documentElement.setAttribute("data-theme", uiTheme);
  applyRenderTheme(uiTheme);
  const meta = document.querySelector("meta[name=\"theme-color\"]");
  if (meta) {
    meta.setAttribute("content", uiThemeMetaColor(uiTheme));
  }
  if (el.optTheme && el.optTheme.value !== uiTheme) {
    el.optTheme.value = uiTheme;
  }
  if (currentModel) {
    rebuildScene();
  }
}

function initUiTheme() {
  applyUiTheme(loadUiTheme());
}

function loadGuiMode() {
  try {
    return localStorage.getItem(GUI_MODE_STORAGE_KEY) === "advanced" ? "advanced" : "simple";
  } catch (e) {
    return "simple";
  }
}

function applyGuiMode(mode) {
  guiMode = mode === "advanced" ? "advanced" : "simple";
  document.documentElement.setAttribute("data-gui-mode", guiMode);
  if (el.btnGuiMode) {
    const advanced = guiMode === "advanced";
    el.btnGuiMode.textContent = advanced ? "Advanced GUI (WIP)" : "Simple GUI";
    el.btnGuiMode.classList.toggle("advanced", advanced);
    el.btnGuiMode.title = advanced
      ? "Switch to Simple GUI (hides Project / Loads / Practice)"
      : "Switch to Advanced GUI (WIP): adds Project / Loads / Practice";
  }
  if (el.loadTypeFilter) el.loadTypeFilter.value = loadTypeFilterValue();
  updatePickModeUI();
  updateWindLegendOverlay();
  if (currentModel) rebuildScene();
}

function isAdvancedGui() {
  return guiMode === "advanced";
}

function windLoadsShown() {
  return isAdvancedGui() && !!(el.chkWindLoads && el.chkWindLoads.checked);
}

function practiceCentersShown() {
  return isAdvancedGui() && !!(el.chkPracticeCenters && el.chkPracticeCenters.checked);
}

function membraneShown() {
  return isAdvancedGui() && !!(el.chkMembrane && el.chkMembrane.checked);
}

function woodWallShown() {
  return isAdvancedGui() && !!(el.chkWoodWall && el.chkWoodWall.checked);
}

function loadViewerOptions() {
  try {
    const raw = localStorage.getItem(OPTIONS_STORAGE_KEY);
    if (!raw) return;
    const st = JSON.parse(raw);
    if (typeof st.loadArrowSize === "number") viewerOptions.loadArrowSize = st.loadArrowSize;
    if (typeof st.reactionArrowSize === "number") viewerOptions.reactionArrowSize = st.reactionArrowSize;
    if (typeof st.supportGizmoSize === "number") viewerOptions.supportGizmoSize = st.supportGizmoSize;
    if (typeof st.axesSize === "number") viewerOptions.axesSize = st.axesSize;
    if (typeof st.supportLineWidth === "number") viewerOptions.supportLineWidth = st.supportLineWidth;
    if (typeof st.dispContourLineWidth === "number") viewerOptions.dispContourLineWidth = st.dispContourLineWidth;
    if (typeof st.elementLineWidth === "number") viewerOptions.elementLineWidth = st.elementLineWidth;
    if (typeof st.loadLineWidth === "number") viewerOptions.loadLineWidth = st.loadLineWidth;
    if (typeof st.reactionLineWidth === "number") viewerOptions.reactionLineWidth = st.reactionLineWidth;
    if (typeof st.forceLineWidth === "number") viewerOptions.forceLineWidth = st.forceLineWidth;
    if (typeof st.nodeLabelSize === "number") viewerOptions.nodeLabelSize = st.nodeLabelSize;
    if (typeof st.elemLabelSize === "number") viewerOptions.elemLabelSize = st.elemLabelSize;
    if (typeof st.materialLabelSize === "number") viewerOptions.materialLabelSize = st.materialLabelSize;
    if (typeof st.sectionLabelSize === "number") viewerOptions.sectionLabelSize = st.sectionLabelSize;
    if (typeof st.loadLabelSize === "number") viewerOptions.loadLabelSize = st.loadLabelSize;
    if (typeof st.reactionLabelSize === "number") viewerOptions.reactionLabelSize = st.reactionLabelSize;
    if (typeof st.forceLabelSize === "number") viewerOptions.forceLabelSize = st.forceLabelSize;
    if (typeof st.sectionSolidOpacity === "number") {
      viewerOptions.sectionSolidOpacity = st.sectionSolidOpacity;
    }
    if (typeof st.sectionSolidColor === "string") {
      viewerOptions.sectionSolidColor = sanitizeHexColor(st.sectionSolidColor, OPTIONS_DEFAULTS.sectionSolidColor);
    }
    if (typeof st.inputLoadType === "string") viewerOptions.inputLoadType = st.inputLoadType;
    clampAllViewerOptions();
  } catch (e) { /* ignore */ }
}

function onOptionsChanged() {
  readOptionsFromUi();
  saveViewerOptions();
  if (currentModel) rebuildScene();
}

function initViewerOptions() {
  loadViewerOptions();
  applyOptionsToUi();
  el.optLoadArrow.addEventListener("input", () => {
    el.optLoadArrowVal.textContent = Number(el.optLoadArrow.value).toFixed(1);
    onOptionsChanged();
  });
  if (el.optReactionArrow) {
    el.optReactionArrow.addEventListener("input", () => {
      el.optReactionArrowVal.textContent = Number(el.optReactionArrow.value).toFixed(1);
      onOptionsChanged();
    });
  }
  el.optSupportGizmo.addEventListener("input", () => {
    el.optSupportGizmoVal.textContent = el.optSupportGizmo.value;
    onOptionsChanged();
  });
  if (el.optAxesSize) {
    el.optAxesSize.addEventListener("input", () => {
      el.optAxesSizeVal.textContent = el.optAxesSize.value;
      onOptionsChanged();
    });
  }
  el.optSupportLineWidth.addEventListener("input", onOptionsChanged);
  el.optSupportLineWidth.addEventListener("change", onOptionsChanged);
  el.optDispContourLineWidth.addEventListener("input", onOptionsChanged);
  el.optDispContourLineWidth.addEventListener("change", onOptionsChanged);
  if (el.optElementLineWidth) {
    el.optElementLineWidth.addEventListener("input", onOptionsChanged);
    el.optElementLineWidth.addEventListener("change", onOptionsChanged);
  }
  if (el.optLoadLineWidth) {
    el.optLoadLineWidth.addEventListener("input", onOptionsChanged);
    el.optLoadLineWidth.addEventListener("change", onOptionsChanged);
  }
  if (el.optReactionLineWidth) {
    el.optReactionLineWidth.addEventListener("input", onOptionsChanged);
    el.optReactionLineWidth.addEventListener("change", onOptionsChanged);
  }
  if (el.optForceLineWidth) {
    el.optForceLineWidth.addEventListener("input", onOptionsChanged);
    el.optForceLineWidth.addEventListener("change", onOptionsChanged);
  }
  el.optNodeLabel.addEventListener("input", () => {
    el.optNodeLabelVal.textContent = el.optNodeLabel.value;
    onOptionsChanged();
  });
  el.optElemLabel.addEventListener("input", () => {
    el.optElemLabelVal.textContent = el.optElemLabel.value;
    onOptionsChanged();
  });
  el.optMaterialLabel.addEventListener("input", () => {
    el.optMaterialLabelVal.textContent = el.optMaterialLabel.value;
    onOptionsChanged();
  });
  el.optSectionLabel.addEventListener("input", () => {
    el.optSectionLabelVal.textContent = el.optSectionLabel.value;
    onOptionsChanged();
  });
  el.optLoadLabel.addEventListener("input", () => {
    el.optLoadLabelVal.textContent = el.optLoadLabel.value;
    onOptionsChanged();
  });
  el.optReactionLabel.addEventListener("input", () => {
    el.optReactionLabelVal.textContent = el.optReactionLabel.value;
    onOptionsChanged();
  });
  el.optForceLabel.addEventListener("input", () => {
    el.optForceLabelVal.textContent = el.optForceLabel.value;
    onOptionsChanged();
  });
  if (el.optSectionSolidOpacity) {
    el.optSectionSolidOpacity.addEventListener("input", () => {
      if (el.optSectionSolidOpacityVal) {
        el.optSectionSolidOpacityVal.textContent = Number(el.optSectionSolidOpacity.value).toFixed(2);
      }
      onOptionsChanged();
    });
  }
  if (el.optSectionSolidColor) {
    el.optSectionSolidColor.addEventListener("input", onOptionsChanged);
    el.optSectionSolidColor.addEventListener("change", onOptionsChanged);
  }
  if (el.loadTypeFilter) {
    el.loadTypeFilter.addEventListener("change", onOptionsChanged);
  }
}

function initDraggablePanel(cfg) {
  const panel = cfg.panel;
  const header = cfg.header;
  const collapseBtn = cfg.collapseBtn;

  function savePanelState() {
    try {
      const rect = panel.getBoundingClientRect();
      localStorage.setItem(cfg.storageKey, JSON.stringify({
        left: rect.left,
        top: rect.top,
        collapsed: panel.classList.contains("collapsed"),
        hidden: panel.classList.contains("hidden"),
      }));
    } catch (e) { /* ignore */ }
  }

  function loadPanelState() {
    try {
      const raw = localStorage.getItem(cfg.storageKey);
      if (!raw) {
        if (cfg.defaultHidden) panel.classList.add("hidden");
        return;
      }
      const st = JSON.parse(raw);
      if (st.hidden) panel.classList.add("hidden");
      else panel.classList.remove("hidden");
      if (st.collapsed) {
        panel.classList.add("collapsed");
        collapseBtn.textContent = "+";
      }
      if (typeof st.left === "number" && typeof st.top === "number") {
        panel.style.left = st.left + "px";
        panel.style.top = st.top + "px";
        panel.style.right = "auto";
      }
    } catch (e) {
      if (cfg.defaultHidden) panel.classList.add("hidden");
    }
  }

  function clampPanelPosition() {
    const rect = panel.getBoundingClientRect();
    const margin = 8;
    let left = rect.left;
    let top = rect.top;
    const maxLeft = window.innerWidth - rect.width - margin;
    const maxTop = window.innerHeight - rect.height - margin;
    left = Math.max(margin, Math.min(left, maxLeft));
    top = Math.max(margin, Math.min(top, maxTop));
    panel.style.left = left + "px";
    panel.style.top = top + "px";
    panel.style.right = "auto";
  }

  loadPanelState();
  if (cfg.autoVisibility) {
    panel.classList.add("hidden");
  }

  if (cfg.toggleBtn) {
    cfg.toggleBtn.addEventListener("click", () => {
      panel.classList.toggle("hidden");
      savePanelState();
    });
  }

  collapseBtn.addEventListener("click", (ev) => {
    ev.stopPropagation();
    panel.classList.toggle("collapsed");
    collapseBtn.textContent = panel.classList.contains("collapsed") ? "+" : "−";
    savePanelState();
  });

  let drag = null;
  header.addEventListener("mousedown", (ev) => {
    if (ev.target === collapseBtn) return;
    const rect = panel.getBoundingClientRect();
    drag = {
      startX: ev.clientX,
      startY: ev.clientY,
      left: rect.left,
      top: rect.top,
    };
    ev.preventDefault();
  });

  document.addEventListener("mousemove", (ev) => {
    if (!drag) return;
    if (panel.classList.contains("hidden")) return;
    const dx = ev.clientX - drag.startX;
    const dy = ev.clientY - drag.startY;
    panel.style.left = drag.left + dx + "px";
    panel.style.top = drag.top + dy + "px";
    panel.style.right = "auto";
  });

  document.addEventListener("mouseup", () => {
    if (!drag) return;
    drag = null;
    clampPanelPosition();
    savePanelState();
  });

  window.addEventListener("resize", () => {
    if (!panel.classList.contains("hidden")) clampPanelPosition();
  });
}

bootstrap();
