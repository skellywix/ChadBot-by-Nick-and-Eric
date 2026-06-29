const state = {
  scripts: [],
  files: [],
  selectedScript: null,
  selectedFile: null,
  fileContent: "",
  savedContent: "",
  logCursor: 0,
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
  logsView: document.querySelector("#logsView"),
  validationView: document.querySelector("#validationView"),
  fileSearch: document.querySelector("#fileSearch"),
  fileList: document.querySelector("#fileList"),
  refreshFiles: document.querySelector("#refreshFiles"),
  editorPath: document.querySelector("#editorPath"),
  editor: document.querySelector("#editor"),
  dirtyState: document.querySelector("#dirtyState"),
  toast: document.querySelector("#toast"),
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
  const payload = await response.json();
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
        renderScripts();
        renderRunState();
      });
      el.scriptList.append(row);
    }
  }
}

function renderFiles() {
  const query = el.fileSearch.value.trim().toLowerCase();
  const files = state.files.filter((file) => file.path.toLowerCase().includes(query));
  el.fileList.innerHTML = "";

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
  el.processState.textContent = status.running ? "Running" : "Ready";
  el.runStatus.textContent = status.running ? `Running ${status.script}` : "Ready";
  el.uptime.textContent = formatDuration(status.uptime || 0);
  el.serverDot.classList.toggle("running", Boolean(status.running));
  state.running = Boolean(status.running);
}

function renderDirtyState() {
  const dirty = state.fileContent !== state.savedContent;
  el.dirtyState.textContent = dirty ? "Unsaved changes" : "Saved";
  el.dirtyState.classList.toggle("changed", dirty);
}

async function refreshHealth() {
  try {
    const health = await api("/api/health");
    el.serverStatus.textContent = health.local ? "Local" : health.status;
    el.serverDot.classList.remove("error");
  } catch (error) {
    el.serverStatus.textContent = "Disconnected";
    el.serverDot.classList.add("error");
  }
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

async function pollLogs() {
  const payload = await api(`/api/process/logs?after=${state.logCursor}`);
  state.logCursor = payload.latest;
  for (const entry of payload.logs) {
    el.logsView.textContent += `[${new Date(entry.time * 1000).toLocaleTimeString()}] ${entry.text}\n`;
  }
  if (payload.logs.length) {
    el.logsView.scrollTop = el.logsView.scrollHeight;
  }
}

async function startScript() {
  if (!state.selectedScript) {
    showToast("Select a script first.");
    return;
  }
  el.logsView.textContent = "";
  state.logCursor = 0;
  const status = await api("/api/process/start", {
    method: "POST",
    body: JSON.stringify({ path: state.selectedScript.path }),
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

function activateTab(view) {
  for (const tab of document.querySelectorAll(".tab")) {
    tab.classList.toggle("active", tab.dataset.view === view);
  }
  el.logsView.classList.toggle("hidden", view !== "logs");
  el.validationView.classList.toggle("hidden", view !== "validation");
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
  document.querySelector("#refreshScripts").addEventListener("click", () => refreshScripts().catch((error) => showToast(error.message)));
  document.querySelector("#refreshFiles").addEventListener("click", () => refreshFiles().catch((error) => showToast(error.message)));
  el.scriptSearch.addEventListener("input", renderScripts);
  el.fileSearch.addEventListener("input", renderFiles);
  el.editor.addEventListener("input", () => {
    state.fileContent = el.editor.value;
    renderDirtyState();
  });
  for (const tab of document.querySelectorAll(".tab")) {
    tab.addEventListener("click", () => activateTab(tab.dataset.view));
  }
}

async function init() {
  bindEvents();
  await refreshHealth();
  await Promise.all([refreshScripts(), refreshFiles()]);
  setInterval(() => refreshStatus().catch(() => {}), 1000);
  setInterval(() => pollLogs().catch(() => {}), 900);
  if (state.files.length) {
    const readme = state.files.find((file) => file.path === "README.md") || state.files[0];
    await loadFile(readme.path);
  }
}

init().catch((error) => showToast(error.message));
