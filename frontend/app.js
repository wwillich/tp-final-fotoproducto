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

const state = {
  source: null,  // foto cargada: { name, url, width, height }
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

/** Llama a la API y devuelve el JSON; ante un error lanza ApiError con textos en español. */
async function api(method, path, { formData } = {}) {
  let response;
  try {
    response = await fetch(API_BASE + path, { method, body: formData });
  } catch {
    const msg = `No se pudo conectar con ${API_BASE || location.origin}. ¿Está encendido el servidor?`;
    throw new ApiError(0, null, errorTitle(0), msg);
  }

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
  setSource({ name: file.name, url: URL.createObjectURL(file) });
  renderPhoto();
  measureSource();
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
  };
  img.src = source.url;
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
}

function init() {
  $("#link-docs").href = (API_BASE || "") + "/docs";
  renderPhoto();
  bindEvents();
  checkServer();
}

init();
