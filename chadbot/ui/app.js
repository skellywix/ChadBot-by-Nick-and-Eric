const state = {
  scripts: [],
  files: [],
  selectedScript: null,
  selectedFile: null,
  fileContent: "",
  savedContent: "",
  health: null,
  settings: null,
  portability: null,
  diagnostics: null,
  scriptAnalysis: null,
  settingsDirty: false,
  logCursor: 0,
  logLines: [],
  setupCursor: 0,
  setupLines: [],
  setupRunning: false,
  running: false,
};

const el = {
  serverDot: document.querySelector("#serverDot"),
  serverStatus: document.querySelector("#serverStatus"),
  runStatus: document.querySelector("#runStatus"),
  scriptSearch: document.querySelector("#scriptSearch"),
  scriptList: document.querySelector("#scriptList"),
  refreshScripts: document.querySelector("#refreshScripts"),
  selectedScriptName: document.querySelector("#selectedScriptName"),
  activeScriptLabel: document.querySelector("#activeScriptLabel"),
  processState: document.querySelector("#processState"),
  uptime: document.querySelector("#uptime"),
  baselineValue: document.querySelector("#baselineValue"),
  scalingValue: document.querySelector("#scalingValue"),
  templateScaleValue: document.querySelector("#templateScaleValue"),
  scriptDirValue: document.querySelector("#scriptDirValue"),
  scriptArgs: document.querySelector("#scriptArgs"),
  baseWidthInput: document.querySelector("#baseWidthInput"),
  baseHeightInput: document.querySelector("#baseHeightInput"),
  templateScalesInput: document.querySelector("#templateScalesInput"),
  disableScalingInput: document.querySelector("#disableScalingInput"),
  saveSettings: document.querySelector("#saveSettings"),
  resetSettings: document.querySelector("#resetSettings"),
  diagnosticsPanel: document.querySelector("#diagnosticsPanel"),
  diagnosticsStatus: document.querySelector("#diagnosticsStatus"),
  diagnosticsSummary: document.querySelector("#diagnosticsSummary"),
  diagnosticsChecks: document.querySelector("#diagnosticsChecks"),
  refreshDiagnostics: document.querySelector("#refreshDiagnostics"),
  installRequirements: document.querySelector("#installRequirements"),
  scriptAnalysisPanel: document.querySelector("#scriptAnalysisPanel"),
  scriptAnalysisStatus: document.querySelector("#scriptAnalysisStatus"),
  scriptAnalysisSummary: document.querySelector("#scriptAnalysisSummary"),
  scriptAnalysisAssets: document.querySelector("#scriptAnalysisAssets"),
  refreshScriptAnalysis: document.querySelector("#refreshScriptAnalysis"),
  logsView: document.querySelector("#logsView"),
  validationView: document.querySelector("#validationView"),
  setupView: document.querySelector("#setupView"),
  fileSearch: document.querySelector("#fileSearch"),
  fileList: document.querySelector("#fileList"),
  refreshFiles: document.querySelector("#refreshFiles"),
  editorPath: document.querySelector("#editorPath"),
  editor: document.querySelector("#editor"),
  dirtyState: document.querySelector("#dirtyState"),
  toast: document.querySelector("#toast"),
  startButtons: [document.querySelector("#startTop"), document.querySelector("#startMain")],
  stopButtons: [document.querySelector("#stopTop"), document.querySelector("#stopMain")],
};

function formatDuration(seconds) {
  const value = Math.max(0, Math.floor(seconds || 0));
  const minutes = String(Math.floor(value / 60)).padStart(2, "0");
  const secs = String(value % 60).padStart(2, "0");
  return `${minutes}:${secs}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { error: text || response.statusText };
  }
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function showToast(message) {
  el.toast.textContent = message;
  el.toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => el.toast.classList.remove("show"), 2600);
}

function groupBy(items, key) {
  return items.reduce((groups, item) => {
    const group = item[key] || "Root";
    groups[group] = groups[group] || [];
    groups[group].push(item);
    return groups;
  }, {});
}

function renderScripts() {
  const query = el.scriptSearch.value.trim().toLowerCase();
  const scripts = state.scripts.filter((script) => {
    const haystack = `${script.name} ${script.path} ${script.group}`.toLowerCase();
    return haystack.includes(query);
  });
  const groups = groupBy(scripts, "group");
  el.scriptList.innerHTML = "";
  if (!scripts.length) {
    el.scriptList.innerHTML = '<div class="empty-state">No scripts found.</div>';
    return;
  }

  for (const group of Object.keys(groups).sort()) {
    const label = document.createElement("div");
    label.className = "group-label";
    label.textContent = group;
    el.scriptList.append(label);

    for (const script of groups[group]) {
      const row = document.createElement("button");
      row.className = `script-row${state.selectedScript?.path === script.path ? " active" : ""}`;
      row.innerHTML = `
        <span>
          <strong>${escapeHtml(script.name)}</strong>
          <span>${escapeHtml(script.path)}</span>
        </span>
        ${script.running ? '<span class="running-badge">RUN</span>' : ""}
      `;
      row.addEventListener("click", () => {
        state.selectedScript = script;
        state.scriptAnalysis = null;
        renderScripts();
        renderRunState();
        renderScriptAnalysis();
        refreshScriptAnalysis().catch((error) => showToast(error.message));
      });
      el.scriptList.append(row);
    }
  }
}

function renderFiles() {
  const query = el.fileSearch.value.trim().toLowerCase();
  const files = state.files.filter((file) => file.path.toLowerCase().includes(query));
  el.fileList.innerHTML = "";
  if (!files.length) {
    el.fileList.innerHTML = '<div class="empty-state">No files found.</div>';
    return;
  }

  for (const file of files) {
    const row = document.createElement("button");
    row.className = `file-row${state.selectedFile === file.path ? " active" : ""}`;
    row.innerHTML = `
      <strong>${escapeHtml(file.name)}</strong>
      <span>${escapeHtml(file.folder || "root")}</span>
    `;
    row.addEventListener("click", () => loadFile(file.path));
    el.fileList.append(row);
  }
}

function renderRunState(status = {}) {
  const selected = state.selectedScript;
  el.selectedScriptName.textContent = selected?.name || "None";
  el.activeScriptLabel.textContent = selected?.path || "No script selected";
  el.scriptDirValue.textContent = selected?.path?.includes("/") ? selected.path.split("/").slice(0, -1).join("/") : "Repo root";
  el.processState.textContent = status.running ? "Running" : "Ready";
  el.runStatus.textContent = status.running ? `Running ${status.script}` : "Ready";
  el.uptime.textContent = formatDuration(status.uptime || 0);
  el.serverDot.classList.toggle("running", Boolean(status.running));
  state.running = Boolean(status.running);
  for (const button of el.startButtons) {
    button.disabled = !selected || state.running;
  }
  for (const button of el.stopButtons) {
    button.disabled = !state.running;
  }
}

function renderPortability() {
  const portability = state.portability || state.health?.portability;
  if (!portability) {
    return;
  }
  el.baselineValue.textContent = `${portability.baseWidth} x ${portability.baseHeight}`;
  el.scalingValue.textContent = portability.scalingDisabled ? "Off" : "Auto";
  el.templateScaleValue.textContent = portability.templateScales === "auto" ? "Auto" : portability.templateScales;
}

function renderSettings() {
  if (!state.settings || state.settingsDirty) {
    return;
  }
  el.baseWidthInput.value = state.settings.baseWidth;
  el.baseHeightInput.value = state.settings.baseHeight;
  el.templateScalesInput.value = state.settings.templateScales || "";
  el.disableScalingInput.checked = Boolean(state.settings.disableScaling);
}

function statusLabel(status) {
  if (status === "error") return "Needs Fix";
  if (status === "warn") return "Review";
  return "Ready";
}

function renderDiagnostics() {
  const diagnostics = state.diagnostics;
  if (!diagnostics) {
    return;
  }

  const missingDependencies = diagnostics.dependencies.filter((dependency) => dependency.status === "error").length;
  const screenLabel = diagnostics.screen.available
    ? `${diagnostics.screen.width} x ${diagnostics.screen.height}`
    : "Unavailable";
  const summary = [
    ["Python", diagnostics.environment.python],
    ["Screen", screenLabel],
    ["Packages", missingDependencies ? `${missingDependencies} missing` : "All found"],
    ["Assets", `${diagnostics.assets.scripts} scripts / ${diagnostics.assets.imageFiles} images`],
  ];

  el.diagnosticsPanel.dataset.status = diagnostics.status;
  el.diagnosticsStatus.className = `readiness-badge ${diagnostics.status}`;
  el.diagnosticsStatus.textContent = statusLabel(diagnostics.status);
  el.diagnosticsSummary.innerHTML = summary.map(([label, value]) => `
    <div class="diagnostic-pill">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join("");
  el.diagnosticsChecks.innerHTML = diagnostics.checks.map((check) => `
    <div class="diagnostic-row ${escapeHtml(check.status)}">
      <span class="diagnostic-dot"></span>
      <span>
        <strong>${escapeHtml(check.label)}</strong>
        <small>${escapeHtml(check.detail)}</small>
      </span>
    </div>
  `).join("");
}

function usageLabel(usage) {
  if (usage === "folder") return "folder";
  if (usage === "write") return "generated";
  if (usage === "read") return "required";
  return "reference";
}

function renderScriptAnalysis() {
  const selected = state.selectedScript;
  const analysis = state.scriptAnalysis;
  el.refreshScriptAnalysis.disabled = !selected;

  if (!selected) {
    el.scriptAnalysisPanel.dataset.status = "idle";
    el.scriptAnalysisStatus.className = "readiness-badge warn";
    el.scriptAnalysisStatus.textContent = "Select";
    el.scriptAnalysisSummary.innerHTML = "";
    el.scriptAnalysisAssets.innerHTML = '<div class="empty-state">No script selected.</div>';
    return;
  }

  if (!analysis || analysis.script.path !== selected.path) {
    el.scriptAnalysisPanel.dataset.status = "loading";
    el.scriptAnalysisStatus.className = "readiness-badge warn";
    el.scriptAnalysisStatus.textContent = "Checking";
    el.scriptAnalysisSummary.innerHTML = "";
    el.scriptAnalysisAssets.innerHTML = '<div class="empty-state">Checking selected script.</div>';
    return;
  }

  const summary = [
    ["Assets", String(analysis.summary.assets)],
    ["Missing", String(analysis.summary.missing)],
    ["Warnings", String(analysis.summary.warnings)],
    ["Helpers", analysis.importsFunctions ? "Enabled" : "Missing"],
  ];
  el.scriptAnalysisPanel.dataset.status = analysis.status;
  el.scriptAnalysisStatus.className = `readiness-badge ${analysis.status}`;
  el.scriptAnalysisStatus.textContent = statusLabel(analysis.status);
  el.scriptAnalysisSummary.innerHTML = summary.map(([label, value]) => `
    <div class="diagnostic-pill">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join("");

  const warnings = analysis.warnings.slice(0, 4).map((warning) => `
    <div class="analysis-row ${escapeHtml(warning.status)}">
      <span class="diagnostic-dot"></span>
      <span>
        <strong>${escapeHtml(warning.label)}</strong>
        <small>${escapeHtml(warning.detail)}${warning.line ? ` - line ${escapeHtml(warning.line)}` : ""}</small>
      </span>
    </div>
  `).join("");
  const assets = analysis.assetReferences.slice(0, 8).map((asset) => `
    <div class="analysis-row ${escapeHtml(asset.status === "missing" ? "error" : asset.status === "generated" ? "warn" : "ok")}">
      <span class="diagnostic-dot"></span>
      <span>
        <strong>${escapeHtml(asset.value)}</strong>
        <small>${escapeHtml(usageLabel(asset.usage))} - ${escapeHtml(asset.status)}${asset.line ? ` - line ${escapeHtml(asset.line)}` : ""}</small>
      </span>
    </div>
  `).join("");
  const overflow = analysis.assetReferences.length > 8
    ? `<div class="analysis-more">${analysis.assetReferences.length - 8} more references</div>`
    : "";
  el.scriptAnalysisAssets.innerHTML = warnings || assets
    ? `${warnings}${assets}${overflow}`
    : '<div class="empty-state">No local assets referenced.</div>';
}

function renderSetupStatus(status = {}) {
  state.setupRunning = Boolean(status.running);
  el.installRequirements.disabled = state.setupRunning;
}

function renderDirtyState() {
  const dirty = state.fileContent !== state.savedContent;
  el.dirtyState.textContent = dirty ? "Unsaved changes" : "Saved";
  el.dirtyState.classList.toggle("changed", dirty);
}

async function refreshHealth() {
  try {
    const health = await api("/api/health");
    state.health = health;
    state.portability = health.portability;
    el.serverStatus.textContent = health.local ? "Local" : health.status;
    el.serverDot.classList.remove("error");
    renderPortability();
  } catch (error) {
    el.serverStatus.textContent = "Disconnected";
    el.serverDot.classList.add("error");
  }
}

async function refreshSettings() {
  const payload = await api("/api/settings");
  state.settings = payload.settings;
  state.portability = payload.portability;
  state.settingsDirty = false;
  renderPortability();
  renderSettings();
}

async function refreshDiagnostics() {
  const payload = await api("/api/diagnostics");
  state.diagnostics = payload.diagnostics;
  renderDiagnostics();
}

async function refreshScriptAnalysis() {
  if (!state.selectedScript) {
    state.scriptAnalysis = null;
    renderScriptAnalysis();
    return;
  }
  const selectedPath = state.selectedScript.path;
  const payload = await api(`/api/scripts/analyze?path=${encodeURIComponent(selectedPath)}`);
  if (state.selectedScript?.path !== selectedPath) {
    return;
  }
  state.scriptAnalysis = payload.analysis;
  renderScriptAnalysis();
}

async function refreshScripts() {
  const payload = await api("/api/scripts");
  state.scripts = payload.scripts;
  if (!state.selectedScript && state.scripts.length) {
    state.selectedScript = state.scripts[0];
  } else if (state.selectedScript) {
    state.selectedScript = state.scripts.find((script) => script.path === state.selectedScript.path) || state.selectedScript;
  }
  renderScripts();
  renderRunState(payload.status);
  await refreshScriptAnalysis();
}

async function refreshFiles() {
  const payload = await api("/api/files/tree");
  state.files = payload.files;
  renderFiles();
}

async function refreshStatus() {
  const status = await api("/api/process/status");
  renderRunState(status);
}

async function refreshSetupStatus() {
  const wasRunning = state.setupRunning;
  const status = await api("/api/setup/status");
  renderSetupStatus(status);
  if (wasRunning && !status.running) {
    await refreshDiagnostics();
    showToast(status.returnCode === 0 ? "Setup completed." : "Setup failed.");
  }
}

async function pollLogs() {
  const payload = await api(`/api/process/logs?after=${state.logCursor}`);
  state.logCursor = payload.latest;
  for (const entry of payload.logs) {
    state.logLines.push(`[${new Date(entry.time * 1000).toLocaleTimeString()}] ${entry.text}`);
  }
  if (state.logLines.length > 1000) {
    state.logLines = state.logLines.slice(-1000);
  }
  if (payload.logs.length) {
    el.logsView.textContent = `${state.logLines.join("\n")}\n`;
    el.logsView.scrollTop = el.logsView.scrollHeight;
  }
}

async function pollSetupLogs() {
  const payload = await api(`/api/setup/logs?after=${state.setupCursor}`);
  state.setupCursor = payload.latest;
  for (const entry of payload.logs) {
    state.setupLines.push(`[${new Date(entry.time * 1000).toLocaleTimeString()}] ${entry.text}`);
  }
  if (state.setupLines.length > 1200) {
    state.setupLines = state.setupLines.slice(-1200);
  }
  if (payload.logs.length) {
    el.setupView.textContent = `${state.setupLines.join("\n")}\n`;
    el.setupView.scrollTop = el.setupView.scrollHeight;
  }
}

async function startScript() {
  if (!state.selectedScript) {
    showToast("Select a script first.");
    return;
  }
  el.logsView.textContent = "";
  state.logLines = [];
  state.logCursor = 0;
  let args = [];
  try {
    args = parseCommandArgs(el.scriptArgs.value);
  } catch (error) {
    showToast(error.message);
    return;
  }
  const status = await api("/api/process/start", {
    method: "POST",
    body: JSON.stringify({ path: state.selectedScript.path, args }),
  });
  renderRunState(status);
  await refreshScripts();
  showToast(`Started ${state.selectedScript.name}`);
}

async function stopScript() {
  const status = await api("/api/process/stop", { method: "POST", body: "{}" });
  renderRunState(status);
  await refreshScripts();
  showToast("Stop requested.");
}

async function loadFile(path) {
  const payload = await api(`/api/files/read?path=${encodeURIComponent(path)}`);
  state.selectedFile = payload.path;
  state.fileContent = payload.content;
  state.savedContent = payload.content;
  el.editorPath.textContent = payload.path;
  el.editor.value = payload.content;
  renderFiles();
  renderDirtyState();
}

async function saveFile() {
  if (!state.selectedFile) {
    showToast("Select a file first.");
    return;
  }
  const payload = await api("/api/files/write", {
    method: "POST",
    body: JSON.stringify({ path: state.selectedFile, content: state.fileContent }),
  });
  state.savedContent = state.fileContent;
  renderDirtyState();
  await refreshFiles();
  showToast(`Saved ${payload.path}`);
}

async function createFile() {
  const path = window.prompt("New file path inside the repo, for example scripts/my_bot/my_bot.py");
  if (!path) {
    return;
  }
  state.selectedFile = path;
  state.fileContent = "";
  state.savedContent = "";
  el.editorPath.textContent = path;
  el.editor.value = "";
  renderDirtyState();
  showToast("New file ready. Save when finished.");
}

async function runValidation(check) {
  activateTab("validation");
  el.validationView.textContent = `Running ${check}...\n`;
  const payload = await api("/api/checks/run", {
    method: "POST",
    body: JSON.stringify({ check }),
  });
  el.validationView.textContent =
    `${check} exited ${payload.returnCode} in ${payload.duration}s\n\n${payload.output}`;
  showToast(payload.returnCode === 0 ? `${check} passed.` : `${check} failed.`);
}

async function installRequirements() {
  activateTab("setup");
  state.setupCursor = 0;
  state.setupLines = [];
  el.setupView.textContent = "Starting setup...\n";
  const status = await api("/api/setup/install", {
    method: "POST",
    body: "{}",
  });
  renderSetupStatus(status);
  await pollSetupLogs();
  showToast("Installing requirements.");
}

function readSettingsForm() {
  const baseWidth = Number(el.baseWidthInput.value);
  const baseHeight = Number(el.baseHeightInput.value);
  if (!Number.isInteger(baseWidth) || baseWidth <= 0 || !Number.isInteger(baseHeight) || baseHeight <= 0) {
    throw new Error("Base size must use positive whole numbers.");
  }
  return {
    baseWidth,
    baseHeight,
    disableScaling: el.disableScalingInput.checked,
    templateScales: normalizeTemplateScales(el.templateScalesInput.value),
  };
}

function normalizeTemplateScales(value) {
  const text = value.trim();
  if (!text) {
    return "";
  }
  const normalized = [];
  for (const item of text.split(",")) {
    const token = item.trim().toLowerCase();
    if (!token) {
      continue;
    }
    if (token.includes("x")) {
      const parts = token.split("x");
      if (parts.length !== 2 || !parts[0] || !parts[1]) {
        throw new Error("Template scales must use values like 1,0.75,1.25 or 0.75x0.8.");
      }
      const sx = Number(parts[0]);
      const sy = Number(parts[1]);
      if (!Number.isFinite(sx) || !Number.isFinite(sy) || sx <= 0 || sy <= 0) {
        throw new Error("Template scales must use positive numbers.");
      }
      normalized.push(`${sx}x${sy}`);
    } else {
      const scale = Number(token);
      if (!Number.isFinite(scale) || scale <= 0) {
        throw new Error("Template scales must use positive numbers.");
      }
      normalized.push(String(scale));
    }
  }
  return normalized.join(",");
}

async function saveSettings() {
  const settings = readSettingsForm();
  const payload = await api("/api/settings", {
    method: "POST",
    body: JSON.stringify({ settings }),
  });
  state.settings = payload.settings;
  state.portability = payload.portability;
  state.settingsDirty = false;
  renderPortability();
  renderSettings();
  await refreshDiagnostics();
  showToast("Runtime settings applied.");
}

async function resetSettings() {
  const payload = await api("/api/settings", {
    method: "POST",
    body: JSON.stringify({ action: "reset" }),
  });
  state.settings = payload.settings;
  state.portability = payload.portability;
  state.settingsDirty = false;
  renderPortability();
  renderSettings();
  await refreshDiagnostics();
  showToast("Runtime settings reset.");
}

function activateTab(view) {
  for (const tab of document.querySelectorAll(".tab")) {
    tab.classList.toggle("active", tab.dataset.view === view);
  }
  el.logsView.classList.toggle("hidden", view !== "logs");
  el.validationView.classList.toggle("hidden", view !== "validation");
  el.setupView.classList.toggle("hidden", view !== "setup");
}

function parseCommandArgs(value) {
  const args = [];
  let current = "";
  let quote = null;
  let escaping = false;

  for (const char of value.trim()) {
    if (escaping) {
      current += char;
      escaping = false;
    } else if (char === "\\") {
      escaping = true;
    } else if (quote) {
      if (char === quote) {
        quote = null;
      } else {
        current += char;
      }
    } else if (char === '"' || char === "'") {
      quote = char;
    } else if (/\s/.test(char)) {
      if (current) {
        args.push(current);
        current = "";
      }
    } else {
      current += char;
    }
  }

  if (escaping) {
    current += "\\";
  }
  if (quote) {
    throw new Error("Close the quoted argument first.");
  }
  if (current) {
    args.push(current);
  }
  return args;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bindEvents() {
  document.querySelector("#startTop").addEventListener("click", () => startScript().catch((error) => showToast(error.message)));
  document.querySelector("#startMain").addEventListener("click", () => startScript().catch((error) => showToast(error.message)));
  document.querySelector("#stopTop").addEventListener("click", () => stopScript().catch((error) => showToast(error.message)));
  document.querySelector("#stopMain").addEventListener("click", () => stopScript().catch((error) => showToast(error.message)));
  document.querySelector("#saveFile").addEventListener("click", () => saveFile().catch((error) => showToast(error.message)));
  document.querySelector("#revertFile").addEventListener("click", () => {
    el.editor.value = state.savedContent;
    state.fileContent = state.savedContent;
    renderDirtyState();
  });
  document.querySelector("#reloadFile").addEventListener("click", () => {
    if (state.selectedFile) loadFile(state.selectedFile).catch((error) => showToast(error.message));
  });
  document.querySelector("#newFile").addEventListener("click", () => createFile());
  document.querySelector("#runPytest").addEventListener("click", () => runValidation("pytest").catch((error) => showToast(error.message)));
  document.querySelector("#runCompile").addEventListener("click", () => runValidation("compile").catch((error) => showToast(error.message)));
  el.saveSettings.addEventListener("click", () => saveSettings().catch((error) => showToast(error.message)));
  el.resetSettings.addEventListener("click", () => resetSettings().catch((error) => showToast(error.message)));
  el.refreshDiagnostics.addEventListener("click", () => refreshDiagnostics().catch((error) => showToast(error.message)));
  el.installRequirements.addEventListener("click", () => installRequirements().catch((error) => showToast(error.message)));
  el.refreshScriptAnalysis.addEventListener("click", () => refreshScriptAnalysis().catch((error) => showToast(error.message)));
  document.querySelector("#refreshScripts").addEventListener("click", () => refreshScripts().catch((error) => showToast(error.message)));
  document.querySelector("#refreshFiles").addEventListener("click", () => refreshFiles().catch((error) => showToast(error.message)));
  el.scriptSearch.addEventListener("input", renderScripts);
  el.fileSearch.addEventListener("input", renderFiles);
  el.editor.addEventListener("input", () => {
    state.fileContent = el.editor.value;
    renderDirtyState();
  });
  for (const input of [el.baseWidthInput, el.baseHeightInput, el.templateScalesInput, el.disableScalingInput]) {
    input.addEventListener("input", () => {
      state.settingsDirty = true;
    });
    input.addEventListener("change", () => {
      state.settingsDirty = true;
    });
  }
  for (const tab of document.querySelectorAll(".tab")) {
    tab.addEventListener("click", () => activateTab(tab.dataset.view));
  }
}

async function init() {
  bindEvents();
  await refreshHealth();
  await Promise.all([refreshSettings(), refreshDiagnostics(), refreshSetupStatus(), refreshScripts(), refreshFiles()]);
  setInterval(() => refreshStatus().catch(() => {}), 1000);
  setInterval(() => pollLogs().catch(() => {}), 900);
  setInterval(() => refreshSetupStatus().catch(() => {}), 1400);
  setInterval(() => pollSetupLogs().catch(() => {}), 1000);
  if (state.files.length) {
    const readme = state.files.find((file) => file.path === "README.md") || state.files[0];
    await loadFile(readme.path);
  }
}

init().catch((error) => showToast(error.message));
