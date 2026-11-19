"use strict";

const token = document.querySelector('meta[name="local-token"]').content;
const $ = id => document.getElementById(id);
let state = null;
let videoId = "";
let clipId = "";
let projectId = "";
let editingProjectId = "";
let noticeTimer;
let pendingSeek = null;

async function api(path, data) {
  const options = {headers: {"X-Local-Token": token}};
  if (data !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(data);
  }
  const response = await fetch("/api/" + path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Não foi possível concluir a ação.");
  return body;
}

function notify(message, error = false) {
  const box = $("notice");
  box.textContent = message;
  box.classList.toggle("error", error);
  box.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => box.hidden = true, 5000);
}

async function act(path, data = {}) {
  try {
    const result = await api(path, data);
    await refresh();
    return result;
  } catch (error) {
    notify(error.message, true);
    return null;
  }
}

function navigate(next) {
  const target = document.getElementById("page-" + next);
  if (!target) return;
  document.querySelectorAll(".page").forEach(el => el.classList.toggle("active", el === target));
  document.querySelectorAll(".nav-item[data-page]").forEach(el => {
    const active = el.dataset.page === next;
    el.classList.toggle("active", active);
    if (active) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  const nav = document.querySelector('.nav-item[data-page="' + next + '"]');
  const more = document.querySelector(".nav-more");
  if (more) more.open = Boolean(nav && more.contains(nav));
  $("breadcrumb").textContent = nav ? nav.lastChild.textContent.trim() : target.querySelector("h1").textContent;
  window.scrollTo(0, 0);
  if (next === "project-detail") renderProjectDetail();
}

function text(tag, value, className) {
  const el = document.createElement(tag);
  el.textContent = value == null ? "" : String(value);
  if (className) el.className = className;
  return el;
}

function rowCopy(title, detail) {
  const copy = text("span", "", "row-copy");
  copy.append(text("strong", title), text("small", detail));
  return copy;
}

function makeRow(title, detail, action) {
  const row = document.createElement(action ? "button" : "div");
  row.className = "list-row" + (action ? " selectable" : "");
  if (action) row.type = "button";
  row.append(rowCopy(title, detail));
  if (action) row.addEventListener("click", action);
  return row;
}

const bytes = value => ((Number(value) || 0) / 1048576).toFixed(1) + " MB";
const seconds = value => Number(value || 0).toFixed(1) + " s";
const clipCount = () => Object.values(state.clips).reduce((count, clips) => count + clips.length, 0);

function renderDownload() {
  const job = state.download;
  const labels = {idle: "Aguardando", running: "Baixando", paused: "Pausado", done: "Concluído", error: "Interrompido"};
  $("download-status").textContent = labels[job.status] || job.status;
  $("download-message").textContent = job.message || "Nenhum download em andamento.";
  $("download-progress").value = job.total ? job.received / job.total * 100 : 0;
  $("download-meta").textContent = bytes(job.received) + (job.total ? " / " + bytes(job.total) : "") + (job.speed ? " · " + bytes(job.speed) + "/s" : "");
  $("start-download").disabled = ["running", "paused"].includes(job.status);
  $("pause-download").disabled = job.status !== "running" || !job.resumable;
  $("resume-download").disabled = job.status !== "paused";
  $("cancel-download").disabled = !["running", "paused"].includes(job.status);
}

function openContainingFolder(path) {
  const folder = path.replace(/[\\/][^\\/]+$/, "");
  act("open-folder", {path: folder});
}

function renderDownloads() {
  const list = $("history-list");
  list.replaceChildren();
  $("history-count").textContent = state.downloads.length + " arquivo(s)";
  for (const item of state.downloads) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.append(rowCopy(item.name, bytes(item.size) + " · " + item.date));
    const action = text("button", "Abrir pasta", "button secondary small");
    action.type = "button";
    action.addEventListener("click", () => openContainingFolder(item.path));
    row.append(action);
    list.append(row);
  }
}

function selectedVideo() {
  return state.videos.find(video => String(video.id) === videoId);
}

function selectedClip() {
  return (state.clips[videoId] || []).find(clip => String(clip.id) === clipId);
}

function selectClip(clip) {
  clipId = String(clip.id);
  $("clip-start").value = clip.start;
  $("clip-end").value = clip.end;
  $("clip-title").value = clip.title;
  pendingSeek = clip.start;
  const player = $("media-player");
  if (player.readyState >= 1) player.currentTime = clip.start;
  renderStudio();
}

function renderTimelineTracks(video, clips) {
  for (const id of ["video-track", "audio-track"]) {
    const rail = $(id);
    rail.replaceChildren();
    if (!video) continue;
    for (const clip of clips) {
      const segment = text("button", clip.title, "track-segment");
      segment.type = "button";
      segment.style.left = (clip.start / video.duration * 100) + "%";
      segment.style.width = Math.max(1.5, (clip.end - clip.start) / video.duration * 100) + "%";
      segment.title = clip.title + " · " + seconds(clip.start) + " → " + seconds(clip.end);
      segment.setAttribute("aria-label", "Selecionar " + clip.title + " na faixa " + (id === "video-track" ? "de vídeo" : "de áudio"));
      segment.addEventListener("click", () => selectClip(clip));
      rail.append(segment);
    }
  }
}

function renderStudio() {
  const select = $("video-select");
  select.replaceChildren(new Option("Selecione um vídeo", ""));
  for (const video of state.videos) select.add(new Option(video.name + " · " + seconds(video.duration), String(video.id)));
  if (!state.videos.some(video => String(video.id) === videoId)) videoId = state.videos.length ? String(state.videos[0].id) : "";
  select.value = videoId;
  const video = selectedVideo();
  $("video-empty").hidden = !!video;
  $("editor-controls").hidden = !video;
  $("video-info").textContent = video ? video.width + " × " + video.height + " · " + bytes(video.size) : "";
  const player = $("media-player");
  const sourceId = video ? String(video.id) : "";
  if (player.dataset.videoId !== sourceId) {
    player.pause();
    player.removeAttribute("src");
    player.dataset.videoId = sourceId;
    if (video) player.src = "/media/" + encodeURIComponent(sourceId) + "?token=" + encodeURIComponent(token);
    player.load();
    pendingSeek = 0;
  }
  $("timeline").disabled = !video;
  $("timeline").max = video ? video.duration : 1;
  $("add-clip").disabled = !video;
  if (!selectedClip()) clipId = "";
  $("update-clip").disabled = !clipId;
  $("delete-clip").disabled = !clipId;
  $("enqueue").disabled = !clipId;
  const clips = state.clips[videoId] || [];
  $("clips-count").textContent = clips.length + " intervalo(s)";
  const list = $("clips-list");
  list.replaceChildren();
  for (const clip of clips) {
    const row = makeRow(clip.title, seconds(clip.start) + " → " + seconds(clip.end), () => selectClip(clip));
    row.classList.toggle("selected", clipId === String(clip.id));
    list.append(row);
  }
  renderTimelineTracks(video, clips);
  renderExports();
}

function renderExports() {
  const list = $("exports-list");
  list.replaceChildren();
  const labels = {pending: "Na fila", running: "Exportando", done: "Concluído", cancelled: "Cancelado", error: "Falhou", interrupted: "Interrompido"};
  for (const item of state.exports) {
    list.append(makeRow(item.title, (labels[item.status] || item.status) + (item.result ? " · " + item.result : "")));
  }
  $("export-progress").value = state.export.progress || 0;
  $("cancel-export").disabled = state.export.id === null;
}

function renderProjects() {
  const list = $("projects-list");
  list.replaceChildren();
  for (const project of state.projects) {
    const row = document.createElement("div");
    row.className = "list-row";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "project-open";
    open.append(rowCopy(project.name, project.video_count + " vídeo(s)" + (project.description ? " · " + project.description : "")));
    open.addEventListener("click", () => {
      projectId = String(project.id);
      navigate("project-detail");
    });
    const actions = text("span", "", "row-actions");
    const detail = text("button", "Abrir", "button secondary small");
    detail.type = "button";
    detail.addEventListener("click", () => {
      projectId = String(project.id);
      navigate("project-detail");
    });
    actions.append(detail);
    row.append(open, actions);
    list.append(row);
  }

  const assigned = new Set(state.projects.flatMap(project => project.videos.map(video => String(video.id))));
  const unassigned = $("unassigned-list");
  unassigned.replaceChildren();
  for (const video of state.videos.filter(item => !assigned.has(String(item.id)))) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.append(rowCopy(video.name, seconds(video.duration) + " · " + video.width + " × " + video.height + " · " + bytes(video.size)));
    const open = text("button", "Abrir no editor", "button secondary small");
    open.type = "button";
    open.addEventListener("click", () => {
      videoId = String(video.id);
      clipId = "";
      navigate("editor");
      renderStudio();
    });
    row.append(open);
    unassigned.append(row);
  }
}

function currentProject() {
  return state.projects.find(project => String(project.id) === projectId);
}

function renderProjectDetail() {
  const project = currentProject();
  $("project-detail-title").textContent = project ? project.name : "Detalhes do projeto";
  $("project-detail-description").textContent = project ? (project.description || "Sem descrição.") : "Selecione um projeto na biblioteca.";
  $("project-created").textContent = project ? "Criado em " + project.created_at : "";
  $("project-video-count").textContent = project ? project.video_count + " vídeo(s)" : "";
  $("edit-project").disabled = !project;
  $("delete-project").disabled = !project;
  $("import-project-video").disabled = !project;
  const list = $("project-videos-list");
  list.replaceChildren();
  if (project) for (const video of project.videos) {
    const row = document.createElement("div");
    row.className = "list-row";
    row.append(rowCopy(video.name, seconds(video.duration) + " · " + video.width + " × " + video.height + " · " + bytes(video.size)));
    const open = text("button", "Abrir no editor", "button secondary small");
    open.type = "button";
    open.addEventListener("click", () => {
      videoId = String(video.id);
      clipId = "";
      navigate("editor");
      renderStudio();
    });
    row.append(open);
    list.append(row);
  }
}

function renderHistoryAndMetrics() {
  const logsDownloads = $("logs-downloads");
  logsDownloads.replaceChildren();
  $("history-count-full").textContent = state.downloads.length + " arquivo(s)";
  for (const item of state.downloads) logsDownloads.append(makeRow(item.name, bytes(item.size) + " · " + item.date + " · " + item.path));
  const logsExports = $("logs-exports");
  logsExports.replaceChildren();
  const labels = {pending: "Na fila", running: "Exportando", done: "Concluído", cancelled: "Cancelado", error: "Falhou", interrupted: "Interrompido"};
  for (const item of state.exports) logsExports.append(makeRow(item.title, (labels[item.status] || item.status) + (item.result ? " · " + item.result : "")));

  const totalDownloadBytes = state.downloads.reduce((sum, item) => sum + Number(item.size || 0), 0);
  const totalVideoBytes = state.videos.reduce((sum, item) => sum + Number(item.size || 0), 0);
  $("metric-downloads").textContent = state.downloads.length;
  $("metric-videos").textContent = state.videos.length;
  $("metric-clips").textContent = clipCount();
  $("metric-exports").textContent = state.exports.length;
  $("metric-download-size").textContent = bytes(totalDownloadBytes);
  $("metric-video-size").textContent = bytes(totalVideoBytes);
}

function renderOverview() {
  $("count-downloads").textContent = state.downloads.length;
  $("count-projects").textContent = state.projects.length;
  $("count-videos").textContent = state.videos.length;
  $("count-clips").textContent = clipCount();
  const recent = $("recent-list");
  recent.replaceChildren();
  for (const item of state.downloads.slice(0, 3)) recent.append(makeRow(item.name, bytes(item.size) + " · " + item.date));
  if (!state.downloads.length) recent.append(text("p", "Nenhum download concluído.", "muted"));
}

function render() {
  renderOverview();
  renderDownload();
  renderDownloads();
  renderStudio();
  renderProjects();
  renderProjectDetail();
  renderHistoryAndMetrics();
}

async function refresh() {
  try {
    state = await api("state");
    render();
  } catch (error) {
    notify("Conexão local perdida: " + error.message, true);
  }
}

async function choose(kind) {
  const response = await act("choose", {kind});
  return response && response.result;
}

async function importVideos(targetProjectId) {
  const paths = await choose("videos");
  if (!paths || !paths.length) return;
  notify("Lendo metadados dos vídeos…");
  const payload = {paths};
  if (targetProjectId) payload.project_id = Number(targetProjectId);
  const response = await act("import", payload);
  const result = response && response.result;
  if (!result) return;
  if (result.errors.length) notify("Importados: " + result.imported.length + ". " + result.errors.join(" · "), true);
  else if (targetProjectId) notify(result.imported.length + " vídeo(s) adicionado(s) ao projeto.");
  else notify(result.imported.length + " vídeo(s) importado(s).");
  if (!targetProjectId && result.imported.length) {
    videoId = String(result.imported[0]);
    clipId = "";
    renderStudio();
    navigate("editor");
  }
}

function clipForm() {
  return {
    video_id: Number(videoId),
    start: Number($("clip-start").value),
    end: Number($("clip-end").value),
    title: $("clip-title").value.trim()
  };
}

function openProjectModal(project) {
  editingProjectId = project ? String(project.id) : "";
  $("project-modal-title").textContent = project ? "Editar projeto" : "Novo projeto";
  $("save-project").textContent = project ? "Salvar alterações" : "Criar projeto";
  $("project-name").value = project ? project.name : "";
  $("project-description").value = project ? project.description : "";
  $("project-modal").showModal();
  $("project-name").focus();
}

document.querySelectorAll(".nav-item[data-page]").forEach(el => el.addEventListener("click", () => navigate(el.dataset.page)));
document.querySelectorAll("[data-go]").forEach(el => el.addEventListener("click", event => {
  event.preventDefault();
  navigate(el.currentTarget.dataset.go);
}));

$("download-form").addEventListener("submit", async event => {
  event.preventDefault();
  await act("download", {
    url: $("download-url").value.trim(),
    folder: $("download-folder").value.trim(),
    limit: Number($("settings-limit").value)
  });
  navigate("manager");
});
$("pause-download").addEventListener("click", () => act("pause"));
$("resume-download").addEventListener("click", () => act("resume"));
$("cancel-download").addEventListener("click", () => act("cancel"));
$("choose-download-folder").addEventListener("click", async () => {
  const value = await choose("download_folder");
  if (value) $("download-folder").value = value;
});
$("choose-settings-folder").addEventListener("click", async () => {
  const value = await choose("download_folder");
  if (value) $("settings-folder").value = value;
});
$("choose-export-folder").addEventListener("click", async () => {
  const value = await choose("export_folder");
  if (value) $("export-folder").value = value;
});
$("import-videos").addEventListener("click", () => importVideos());
$("import-unassigned").addEventListener("click", () => importVideos());
$("new-project").addEventListener("click", () => openProjectModal(null));
$("close-project-modal").addEventListener("click", () => $("project-modal").close());
$("cancel-project-modal").addEventListener("click", () => $("project-modal").close());
$("project-form").addEventListener("submit", async event => {
  event.preventDefault();
  const data = {name: $("project-name").value.trim(), description: $("project-description").value.trim()};
  const editingId = editingProjectId;
  const response = await act(editingId ? "project/update" : "project/create", editingId ? {...data, id: Number(editingId)} : data);
  if (!response) return;
  projectId = String(response.result);
  $("project-modal").close();
  navigate("project-detail");
});
$("edit-project").addEventListener("click", () => {
  const project = currentProject();
  if (project) openProjectModal(project);
});
$("delete-project").addEventListener("click", async () => {
  const project = currentProject();
  if (!project || !confirm("Excluir o projeto? Os vídeos originais e os intervalos serão mantidos.")) return;
  const response = await act("project/delete", {id: Number(project.id)});
  if (response) {
    projectId = "";
    navigate("projects");
  }
});
$("import-project-video").addEventListener("click", () => {
  if (projectId) importVideos(projectId);
});
$("video-select").addEventListener("change", event => {
  videoId = event.target.value;
  clipId = "";
  const video = selectedVideo();
  if (video) {
    $("clip-start").value = 0;
    $("clip-end").value = Math.min(10, video.duration);
    $("clip-title").value = "Clipe 1";
    $("timeline").value = 0;
    $("position-label").textContent = seconds(0);
  }
  renderStudio();
});
$("timeline").addEventListener("input", event => {
  const position = Number(event.target.value);
  $("position-label").textContent = seconds(position);
  const player = $("media-player");
  if (player.readyState >= 1) player.currentTime = position;
  else pendingSeek = position;
});
$("media-player").addEventListener("loadedmetadata", () => {
  if (pendingSeek !== null) {
    $("media-player").currentTime = Math.min(pendingSeek, $("media-player").duration || pendingSeek);
    pendingSeek = null;
  }
});
$("media-player").addEventListener("timeupdate", () => {
  const player = $("media-player");
  if (!Number.isFinite(player.currentTime)) return;
  $("timeline").value = player.currentTime;
  $("position-label").textContent = seconds(player.currentTime);
});
$("mark-in").addEventListener("click", () => {
  const position = Number($("media-player").currentTime || 0);
  $("clip-start").value = position.toFixed(1);
  $("timeline").value = position;
});
$("mark-out").addEventListener("click", () => {
  const player = $("media-player");
  const position = Number(player.currentTime || 0);
  $("clip-end").value = position.toFixed(1);
  $("timeline").value = position;
});
$("add-clip").addEventListener("click", async () => {
  if (await act("clip/add", clipForm())) notify("Intervalo adicionado.");
});
$("update-clip").addEventListener("click", async () => {
  if (clipId && await act("clip/update", {...clipForm(), id: Number(clipId)})) notify("Intervalo atualizado.");
});
$("delete-clip").addEventListener("click", async () => {
  if (!clipId || !confirm("Excluir este intervalo e suas tarefas de exportação?")) return;
  if (await act("clip/delete", {id: Number(clipId)})) {
    clipId = "";
    renderStudio();
  }
});
$("enqueue").addEventListener("click", async () => {
  if (await act("enqueue", {
    clip_id: Number(clipId),
    folder: $("export-folder").value.trim(),
    preset: $("export-preset").value,
    quality: Number($("export-quality").value)
  })) notify("Clipe adicionado à fila.");
});
$("cancel-export").addEventListener("click", () => act("cancel-export"));
$("settings-form").addEventListener("submit", async event => {
  event.preventDefault();
  const response = await act("settings", {
    folder: $("settings-folder").value.trim(),
    limit_mb: Number($("settings-limit").value)
  });
  if (response) {
    $("download-limit-label").textContent = $("settings-limit").value;
    $("download-folder").value = $("settings-folder").value;
    $("export-folder").value = $("settings-folder").value;
    notify("Configurações salvas.");
  }
});

async function init() {
  await refresh();
  if (!state) return;
  const settings = state.settings;
  $("settings-folder").value = settings.folder || "";
  $("download-folder").value = settings.folder || "";
  $("export-folder").value = settings.folder || "";
  $("settings-limit").value = settings.limit_mb || 500;
  $("download-limit-label").textContent = $("settings-limit").value;
  for (const preset of state.presets) $("export-preset").add(new Option(preset, preset));
  setInterval(refresh, 1000);
}
$("shutdown-app").addEventListener("click", async () => {
  if (!confirm("Encerrar o Media Studio e cancelar tarefas em andamento?")) return;
  try {
    const response = await fetch("/api/shutdown", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-Local-Token": token},
      body: "{}"
    });
    if (!response.ok) throw new Error("Não foi possível encerrar o Media Studio.");
    $("shutdown-app").disabled = true;
    notify("Media Studio encerrado. Você pode fechar esta guia.");
  } catch (error) {
    notify(error.message, true);
  }
});

init();
