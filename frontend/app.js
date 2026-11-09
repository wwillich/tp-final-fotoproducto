/*
 * Foto de producto (frontend)
 *
 * Dónde busca la API:
 *   - servido por el backend (http://localhost:8765) → mismo origen;
 *   - abierto como archivo (file://) → http://localhost:8765;
 *   - en cualquier otro caso, agregar ?api=http://host:puerto a la URL (se recuerda).
 */

"use strict";

const API_BASE = (() => {
  try {
    const param = new URLSearchParams(location.search).get("api");
    if (param) localStorage.setItem("apiBase", param);
    const saved = param || localStorage.getItem("apiBase");
    if (saved) return saved.replace(/\/$/, "");
  } catch { /* almacenamiento bloqueado */ }
  return location.protocol.startsWith("http") ? "" : "http://localhost:8765";
})();

/* ------------------------------------------------------------------------ */
/* Estado                                                                    */
/* ------------------------------------------------------------------------ */

const ADAPTACIONES = {
  bordes: "Completa con blanco para que no se corte nada.",
  recortar: "Corta lo que sobra para llenar todo el formato.",
};
// Qué decir debajo de "¿Qué parte mostrar?" según de qué lado sobra foto.
const AYUDA_POSICION = {
  horizontal: "Con esta foto y este formato solo se puede mover de izquierda a derecha.",
  vertical: "Con esta foto y este formato solo se puede mover de arriba a abajo.",
  ninguno: "Tu foto ya tiene la proporción de este formato: no hay nada para mover.",
};

const state = {
  source: null,       // foto cargada: { name, url, file, width, height }
  plataformas: [],    // GET /api/plataformas
  options: { plataforma: null, adaptacion: "bordes", posicion_x: 0.5, posicion_y: 0.5 },
  preview: null,      // { url, ancho, alto, peso, avisos } de la última vista previa
  previewError: null, // ApiError de la última vista previa fallida
  busy: false,
};

const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "style") node.style.cssText = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v === true) node.setAttribute(k, "");
    else if (v !== false && v != null) node.setAttribute(k, v);
  }
  for (const c of children.flat()) if (c != null) node.append(c);
  return node;
};

/* ------------------------------------------------------------------------ */
/* Cliente HTTP                                                              */
/* ------------------------------------------------------------------------ */

class ApiError extends Error {
  constructor(status, code, title, message) {
    super(message);
    this.status = status;
    this.code = code;
    this.title = title;
  }
}

function errorMessage(status, body) {
  const detail = body && body.detail !== undefined ? body.detail : body;
  if (detail && typeof detail === "object" && !Array.isArray(detail) && detail.message) return detail.message;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) {
    // Errores de validación de FastAPI (422)
    return detail.map((e) => `${(e.loc || []).filter((p) => p !== "body").join(".") || "pedido"}: ${e.msg}`).join(" · ");
  }
  return `El servidor respondió ${status}.`;
}

function errorTitle(status, code) {
  if (code === "UNSUPPORTED_FORMAT") return "Formato no soportado";
  if (code === "INVALID_FILE") return "Archivo inválido";
  if (status === 0) return "Sin conexión con el servidor";
  if (status === 404) return "No encontrado";
  if (status === 400 || status === 422) return "Pedido inválido";
  if (status === 413) return "Archivo demasiado grande";
  if (status >= 500) return "Error del servidor";
  return `Error ${status}`;
}

/** Llama a la API y devuelve el JSON (o la respuesta entera con `raw`); ante un error lanza ApiError en español. */
async function api(method, path, { formData, raw } = {}) {
  let response;
  try {
    response = await fetch(API_BASE + path, { method, body: formData });
  } catch {
    const msg = `No se pudo conectar con ${API_BASE || location.origin}. ¿Está encendido el servidor?`;
    throw new ApiError(0, null, errorTitle(0), msg);
  }

  if (response.ok && raw) return response;

  const text = await response.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }

  if (!response.ok) {
    const code = body?.detail?.code ?? null;
    throw new ApiError(response.status, code, errorTitle(response.status, code), errorMessage(response.status, body));
  }
  return body;
}

/* ------------------------------------------------------------------------ */
/* Avisos                                                                    */
/* ------------------------------------------------------------------------ */

function toast(kind, title, message) {
  const node = el("div", { class: `toast ${kind}`, role: "status" },
    el("div", {}, el("strong", {}, title), message ? el("p", {}, message) : null));
  const container = $("#toasts");
  container.append(node);
  while (container.children.length > 3) container.firstElementChild.remove();
  setTimeout(() => {
    node.classList.add("leaving");
    setTimeout(() => node.remove(), 250);
  }, kind === "ok" ? 3000 : 6000);
}

function toastError(err) {
  if (err instanceof ApiError) {
    toast("err", err.title, err.message);
  } else {
    console.error(err);
    toast("err", "Error inesperado", String(err.message || err));
  }
}

/* ------------------------------------------------------------------------ */
/* Servidor                                                                  */
/* ------------------------------------------------------------------------ */

async function checkServer() {
  const pill = $("#server-status");
  try {
    await api("GET", "/api/health");
    pill.dataset.status = "ok";
    pill.querySelector(".status-text").textContent = "Servidor conectado";
  } catch {
    pill.dataset.status = "error";
    pill.querySelector(".status-text").textContent = "Servidor desconectado";
  }
}

/* ------------------------------------------------------------------------ */
/* Carga de la foto                                                          */
/* ------------------------------------------------------------------------ */

const FORMATS = ["image/png", "image/jpeg", "image/webp", "image/bmp"];
const MAX_BYTES = 10 * 1024 * 1024;

function setSource(source) {
  if (state.source) URL.revokeObjectURL(state.source.url);
  state.source = source;
}

function uploadFile(file) {
  if (!file) return;
  if (!FORMATS.includes(file.type)) {
    toast("err", "Formato no soportado", `${file.name} (${file.type || "desconocido"}). Usá PNG, JPG, WEBP o BMP.`);
    return;
  }
  if (file.size > MAX_BYTES) {
    toast("err", "Archivo demasiado grande", "El máximo es 10 MB.");
    return;
  }
  setSource({ name: file.name, url: URL.createObjectURL(file), file });
  previewSeq++;  // la respuesta pendiente (si la hay) era de la foto anterior
  state.busy = false;
  setPreview(null, null);
  renderPhoto();
  renderOptions();
  renderResult();
  measureSource();
  schedulePreview(0);
}

/** Mide la foto cargada; el navegador ya aplica la orientación EXIF al mostrarla. */
function measureSource() {
  const source = state.source;
  const img = new Image();
  img.onload = () => {
    if (state.source !== source) return;
    source.width = img.naturalWidth;
    source.height = img.naturalHeight;
    renderPhoto();
    renderOptions();  // el eje de recorte depende de las medidas de la foto
  };
  img.src = source.url;
}

/* ------------------------------------------------------------------------ */
/* Vista previa                                                              */
/* ------------------------------------------------------------------------ */

let previewTimer = null;
let previewSeq = 0;  // descarta respuestas viejas si el usuario cambió algo mientras esperaba

function setPreview(preview, error) {
  if (state.preview) URL.revokeObjectURL(state.preview.url);
  state.preview = preview;
  state.previewError = error;
}

/** Pide la vista previa con un pequeño retardo, para no saturar al servidor mientras se cambian opciones. */
function schedulePreview(delay = 300) {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(runPreview, delay);
}

async function runPreview() {
  const source = state.source;
  const o = state.options;
  if (!source || !o.plataforma) return;

  const seq = ++previewSeq;
  const fd = new FormData();
  fd.append("archivo", source.file, source.name);
  fd.append("plataforma", o.plataforma);
  fd.append("adaptacion", o.adaptacion);
  fd.append("posicion_x", o.posicion_x);
  fd.append("posicion_y", o.posicion_y);

  state.busy = true;
  renderResult();
  try {
    const r = await api("POST", "/api/vista-previa", { formData: fd, raw: true });
    const blob = await r.blob();
    if (seq !== previewSeq) return;
    setPreview({
      url: URL.createObjectURL(blob),
      ancho: Number(r.headers.get("X-Ancho")),
      alto: Number(r.headers.get("X-Alto")),
      peso: Number(r.headers.get("X-Peso-Bytes")),
      avisos: JSON.parse(decodeURIComponent(r.headers.get("X-Avisos") || "[]")),
    }, null);
  } catch (err) {
    if (seq !== previewSeq) return;
    setPreview(null, err);
  } finally {
    if (seq === previewSeq) {
      state.busy = false;
      renderResult();
    }
  }
}

/* ------------------------------------------------------------------------ */
/* Vista                                                                     */
/* ------------------------------------------------------------------------ */

function renderPhoto() {
  const frame = $("#photo-frame");
  const source = state.source;
  $("#photo-meta").textContent = source
    ? [source.width ? `${source.width} × ${source.height}` : null, source.name].filter(Boolean).join(" · ")
    : "";
  frame.replaceChildren(source
    ? el("img", { src: source.url, alt: source.name })
    : el("div", { class: "empty" }, "Subí una foto para empezar"));
}

const formatBytes = (b) => (b >= 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

function renderResult() {
  const frame = $("#result-frame");
  const { preview, previewError: error } = state;
  frame.classList.toggle("loading", state.busy);
  $("#result-meta").textContent = preview
    ? `${preview.ancho} × ${preview.alto} · ${formatBytes(preview.peso)}`
    : "";
  $("#result-avisos").replaceChildren(
    ...(preview?.avisos ?? []).map((texto) => el("div", { class: "notice notice-warn" }, texto)));

  if (error) {
    frame.replaceChildren(el("div", { class: "problem", role: "alert" },
      el("strong", {}, error.title), el("p", {}, error.message)));
  } else if (preview) {
    frame.replaceChildren(el("img", { src: preview.url, alt: "Cómo va a quedar tu foto" }));
  } else if (!state.busy) {
    frame.replaceChildren(el("div", { class: "empty" },
      state.source ? "Preparando la vista previa…" : "Acá vas a ver el resultado"));
  }
}

/* ------------------------------------------------------------------------ */
/* Opciones                                                                  */
/* ------------------------------------------------------------------------ */

/** Hacia dónde sobra foto respecto del formato elegido: "horizontal", "vertical" o null si ya coincide. */
function ejeRecorte() {
  const { source } = state;
  const p = state.plataformas.find((x) => x.clave === state.options.plataforma);
  if (!source?.width || !p) return null;
  const foto = source.width / source.height;
  const destino = p.ancho / p.alto;
  if (Math.abs(foto - destino) < 0.005) return null;
  return foto > destino ? "horizontal" : "vertical";
}

function renderOptions() {
  const o = state.options;
  if (o.plataforma) $("#plataforma").value = o.plataforma;
  for (const b of document.querySelectorAll("#adaptacion button")) {
    b.setAttribute("aria-pressed", String(b.dataset.value === o.adaptacion));
  }
  $("#adaptacion-help").textContent = ADAPTACIONES[o.adaptacion];

  const eje = ejeRecorte();
  $("#field-posicion").hidden = o.adaptacion !== "recortar";
  // Siempre se muestran los dos, pero solo tiene efecto el del eje donde sobra foto.
  $("#posicion-x").disabled = eje !== "horizontal";
  $("#posicion-y").disabled = eje !== "vertical";
  $("#posicion-x").value = Math.round(o.posicion_x * 100);
  $("#posicion-y").value = Math.round(o.posicion_y * 100);
  $("#posicion-help").textContent = AYUDA_POSICION[eje ?? "ninguno"];
}

async function loadPlataformas() {
  try {
    state.plataformas = await api("GET", "/api/plataformas");
  } catch (err) {
    toastError(err);
    return;
  }
  $("#plataforma").replaceChildren(...state.plataformas.map((p) => el("option", { value: p.clave }, p.nombre)));
  state.options.plataforma = state.plataformas[0]?.clave ?? null;
  renderOptions();
  schedulePreview(0);
}

/* ------------------------------------------------------------------------ */
/* Eventos                                                                   */
/* ------------------------------------------------------------------------ */

function bindEvents() {
  $("#file-input").addEventListener("change", (e) => {
    uploadFile(e.target.files[0]);
    e.target.value = "";
  });

  const zone = $("#dropzone");
  ["dragenter", "dragover"].forEach((t) => zone.addEventListener(t, (e) => { e.preventDefault(); zone.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach((t) => zone.addEventListener(t, () => zone.classList.remove("dragging")));
  zone.addEventListener("drop", (e) => { e.preventDefault(); uploadFile(e.dataTransfer.files[0]); });

  $("#plataforma").addEventListener("change", (e) => {
    state.options.plataforma = e.target.value;
    renderOptions();
    schedulePreview();
  });
  for (const eje of ["x", "y"]) {
    $(`#posicion-${eje}`).addEventListener("input", (e) => {
      state.options[`posicion_${eje}`] = Number(e.target.value) / 100;
      schedulePreview();
    });
  }
  for (const b of document.querySelectorAll("#adaptacion button")) {
    b.addEventListener("click", () => {
      state.options.adaptacion = b.dataset.value;
      renderOptions();
      schedulePreview();
    });
  }
}

function init() {
  $("#link-docs").href = (API_BASE || "") + "/docs";
  renderPhoto();
  renderOptions();
  bindEvents();
  checkServer();
  loadPlataformas();
}

init();
