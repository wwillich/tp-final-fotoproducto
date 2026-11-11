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
const PESOS = {
  liviano: "Pesa poco y carga más rápido. Puede perder un poco de detalle.",
  normal: "Un buen equilibrio entre calidad y peso.",
  maxima: "La mejor calidad posible. El archivo pesa más.",
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
  options: { plataforma: null, adaptacion: "bordes", posicion_x: 0.5, posicion_y: 0.5, peso: "normal", quitar_fondo: false, centrar: false, espacio: "normal",
    brillo: 0, contraste: 0, aclarar_oscuras: 0, colores_naturales: false, nitidez: "nada" },
  contorno: [],       // línea dibujada alrededor del producto: [[x, y], …] en píxeles de la foto (vacío = automático)
  preview: null,      // { url, ancho, alto, peso, calidad, avisos } de la última vista previa
  previewError: null, // ApiError de la última vista previa fallida
  busy: false,        // hay una vista previa en camino
  saving: false,      // se está guardando el trabajo
  trabajos: [],       // GET /api/trabajos
  galleryError: null, // ApiError si falló el listado
  viewing: null,      // trabajo guardado que se está mirando en el centro (solo lectura)
};

const COLOR_CONTORNO = "#00c878";
const CONTORNO_LADO_MAX = 1600;  // el contorno se manda reducido: el servidor lo reescala a la foto
const CONTORNO_SUAVIZADO = 0.03; // ventana del alisado del trazo, fracción de sus puntos a cada lado
const CONTORNO_PUNTOS = 18;      // puntos de control que se pueden mover
const CONTORNO_PUNTOS_MIN = 4;   // con menos puntos no se puede sacar ninguno más
const CONTORNO_TOQUE = 14;       // distancia (px de pantalla) a la que un toque agarra un punto o la línea
const CONTORNO_MIN = 0.03;       // una raya más corta que esto (fracción del lado mayor) no cuenta como contorno

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
  if (code === "CONTORNO_INVALIDO") return "Contorno inválido";
  if (code === "PRODUCTO_NO_ENCONTRADO") return "No pudimos separar el producto";
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
  state.viewing = null;
  state.contorno = [];
  setPreview(null, null);
  renderGallery();
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
  if (state.viewing) {  // cambiar una opción es volver a editar la foto propia
    state.viewing = null;
    renderPhoto();
    renderResult();
    renderGallery();
  }
}

/** Formulario que entienden /api/vista-previa y /api/trabajos: la foto, las opciones y (si hay) el contorno. */
async function buildForm(source, o) {
  const fd = new FormData();
  fd.append("archivo", source.file, source.name);
  for (const campo of ["plataforma", "adaptacion", "posicion_x", "posicion_y", "peso", "quitar_fondo", "espacio",
    "centrar", "brillo", "contraste", "aclarar_oscuras", "colores_naturales", "nitidez"]) fd.append(campo, o[campo]);
  if (contornoListo() && source.width) fd.append("contorno", await exportarContorno(source), "contorno.png");
  return fd;
}

async function runPreview() {
  const source = state.source;
  if (!source || !state.options.plataforma) return;

  const seq = ++previewSeq;
  state.busy = true;
  renderResult();
  try {
    const r = await api("POST", "/api/vista-previa", { formData: await buildForm(source, state.options), raw: true });
    const blob = await r.blob();
    if (seq !== previewSeq) return;
    setPreview({
      url: URL.createObjectURL(blob),
      ancho: Number(r.headers.get("X-Ancho")),
      alto: Number(r.headers.get("X-Alto")),
      peso: Number(r.headers.get("X-Peso-Bytes")),
      calidad: decodeURIComponent(r.headers.get("X-Calidad") || ""),
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

const absoluteUrl = (url) => (/^(https?:|blob:|data:)/.test(url) ? url : API_BASE + url);
const formatBytes = (b) => (b >= 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);
const resultLine = (peso, calidad, ancho, alto) => `Pesa ${formatBytes(peso)} · Calidad: ${calidad} · ${ancho} × ${alto}`;
const avisosNodes = (avisos) => avisos.map((texto) => el("div", { class: "notice notice-warn" }, texto));

function renderPhoto() {
  const frame = $("#photo-frame");
  const v = state.viewing;
  const source = state.source;
  if (v) {
    $("#photo-meta").textContent = v.nombre_original;
    frame.replaceChildren(el("img", { src: absoluteUrl(v.url_original), alt: v.nombre_original }));
    return;
  }
  $("#photo-meta").textContent = source
    ? [source.width ? `${source.width} × ${source.height}` : null, source.name].filter(Boolean).join(" · ")
    : "";
  if (!source) {
    frame.replaceChildren(el("div", { class: "empty" }, "Subí una foto para empezar"));
  } else if (!source.width) {  // todavía no se midió: sin capa de dibujo
    frame.replaceChildren(el("img", { src: source.url, alt: source.name }));
  } else {
    frame.replaceChildren(el("div", { class: "stage", style: `--ar: ${source.width} / ${source.height}` },
      el("img", { src: source.url, alt: source.name, draggable: "false" }), crearCanvasContorno(source)));
  }
}

/* ------------------------------------------------------------------------ */
/* Quitar el fondo: automático, o con un contorno dibujado                   */
/* ------------------------------------------------------------------------ */

// El contorno ayuda a ubicar el producto: sirve tanto para quitar el fondo como para centrarlo.
const usaProducto = () => state.options.quitar_fondo || state.options.centrar;
const contornoListo = () => usaProducto() && state.contorno.length > 2;

const anchoLinea = (w, h) => Math.max(2, Math.max(w, h) / 300);

/** Alisa el pulso de la mano: promedia cada punto con sus vecinos (el trazo se trata como cerrado). */
function suavizarTrazo(puntos) {
  const n = puntos.length;
  const radio = Math.max(2, Math.round(n * CONTORNO_SUAVIZADO));
  return puntos.map((_, i) => {
    let x = 0, y = 0;
    for (let k = -radio; k <= radio; k++) {
      const p = puntos[(i + k + n) % n];
      x += p[0];
      y += p[1];
    }
    return [x / (2 * radio + 1), y / (2 * radio + 1)];
  });
}

/** Deja el trazo en CONTORNO_PUNTOS puntos de control repartidos por igual a lo largo de la línea cerrada. */
function puntosDeControl(trazo) {
  const n = trazo.length;
  const largo = trazo.map((p, i) => Math.hypot(trazo[(i + 1) % n][0] - p[0], trazo[(i + 1) % n][1] - p[1]));
  const total = largo.reduce((a, b) => a + b, 0);
  const paso = total / CONTORNO_PUNTOS;
  const control = [];
  let i = 0, acumulado = 0;
  for (let k = 0; k < CONTORNO_PUNTOS; k++) {
    while (i < n - 1 && acumulado + largo[i] < k * paso) acumulado += largo[i++];
    const a = trazo[i], b = trazo[(i + 1) % n];
    const t = largo[i] ? (k * paso - acumulado) / largo[i] : 0;
    control.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
  }
  return control;
}

/** Curva suave que pasa cerca de los puntos de control (corte de esquinas de Chaikin, línea cerrada). */
function curvaSuave(control) {
  let puntos = control;
  for (let vuelta = 0; vuelta < 3; vuelta++) {
    puntos = puntos.flatMap((p, i) => {
      const q = puntos[(i + 1) % puntos.length];
      return [[.75 * p[0] + .25 * q[0], .75 * p[1] + .25 * q[1]], [.25 * p[0] + .75 * q[0], .25 * p[1] + .75 * q[1]]];
    });
  }
  return puntos;
}

function trazarCamino(ctx, puntos) {
  ctx.beginPath();
  ctx.moveTo(...puntos[0]);
  for (const p of puntos.slice(1)) ctx.lineTo(...p);
}

/** Trazo en curso, todavía abierto: solo una línea. */
function dibujarTrazo(ctx, puntos, ancho) {
  if (puntos.length < 2) return;
  trazarCamino(ctx, puntos);
  ctx.strokeStyle = COLOR_CONTORNO;
  ctx.lineWidth = ancho;
  ctx.lineJoin = ctx.lineCap = "round";
  ctx.stroke();
}

/** Contorno terminado: línea, relleno suave y un punto en cada punto de control. */
function dibujarContorno(canvas) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (state.contorno.length < 3) return;
  const ancho = anchoLinea(canvas.width, canvas.height);
  trazarCamino(ctx, curvaSuave(state.contorno));
  ctx.closePath();
  ctx.fillStyle = "rgba(0, 200, 120, .18)";
  ctx.fill();
  ctx.strokeStyle = COLOR_CONTORNO;
  ctx.lineWidth = ancho;
  ctx.lineJoin = "round";
  ctx.stroke();
  ctx.fillStyle = "#fff";
  ctx.lineWidth = ancho * .8;
  for (const [x, y] of state.contorno) {
    ctx.beginPath();
    ctx.arc(x, y, ancho * 2.6, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
  }
}

/** Distancia de un punto a un segmento, y el punto más cercano del segmento. */
function acercarASegmento(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const t = dx || dy ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy))) : 0;
  const q = [a[0] + dx * t, a[1] + dy * t];
  return { distancia: Math.hypot(p[0] - q[0], p[1] - q[1]), punto: q };
}

/**
 * Capa transparente del mismo tamaño en píxeles que la foto, para dibujar encima con el mouse o el dedo.
 * - Arrastrar en un lugar libre dibuja un contorno nuevo.
 * - Arrastrar un punto lo mueve; arrastrar sobre la línea agrega un punto ahí; doble clic en un punto lo saca.
 */
function crearCanvasContorno(source) {
  const canvas = el("canvas", {
    id: "contorno-canvas", width: source.width, height: source.height, hidden: !usaProducto(),
    "aria-label": "Zona para dibujar una línea alrededor del producto",
  });
  dibujarContorno(canvas);

  let trazo = null;     // trazo libre en curso
  let previo = [];      // el contorno que había antes de empezar a dibujar
  let movido = null;    // índice del punto de control que se está arrastrando
  let cambio = false;   // el arrastre de un punto cambió algo
  const punto = (e) => {  // de la pantalla a píxeles de la foto (el canvas se muestra escalado por CSS)
    const r = canvas.getBoundingClientRect();
    return [(e.clientX - r.left) * canvas.width / r.width, (e.clientY - r.top) * canvas.height / r.height];
  };
  const tolerancia = () => CONTORNO_TOQUE * canvas.width / canvas.getBoundingClientRect().width;
  const puntoCerca = (p) => state.contorno.findIndex((c) => Math.hypot(c[0] - p[0], c[1] - p[1]) < tolerancia());
  const lineaCerca = (p) => {  // índice del tramo de control más cercano, si p está sobre la línea
    const c = state.contorno;
    let mejor = null;
    c.forEach((a, i) => {
      const r = acercarASegmento(p, a, c[(i + 1) % c.length]);
      if (r.distancia < tolerancia() && (!mejor || r.distancia < mejor.distancia)) mejor = { ...r, i };
    });
    return mejor;
  };

  canvas.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    canvas.setPointerCapture(e.pointerId);
    const p = punto(e);
    cambio = false;
    if (state.contorno.length > 2) {
      movido = puntoCerca(p);
      if (movido < 0) {
        const cerca = lineaCerca(p);
        if (cerca) {
          state.contorno = state.contorno.toSpliced(cerca.i + 1, 0, cerca.punto);
          movido = cerca.i + 1;
          cambio = true;
        } else {
          movido = null;
        }
      }
      if (movido !== null) {
        dibujarContorno(canvas);
        return;
      }
    }
    movido = null;
    previo = state.contorno;
    trazo = [p];
  });
  canvas.addEventListener("pointermove", (e) => {
    if (movido !== null) {
      state.contorno = state.contorno.with(movido, punto(e));
      cambio = true;
      dibujarContorno(canvas);
    } else if (trazo) {
      trazo.push(punto(e));
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      dibujarTrazo(ctx, trazo, anchoLinea(canvas.width, canvas.height));
    }
  });
  const soltar = () => {
    if (movido !== null) {
      movido = null;
      if (cambio) schedulePreview();
      return;
    }
    if (!trazo) return;
    const xs = trazo.map((p) => p[0]), ys = trazo.map((p) => p[1]);
    const lado = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
    // Un toque o una raya mínima no es un contorno: se conserva el anterior.
    const valido = lado > Math.max(source.width, source.height) * CONTORNO_MIN;
    state.contorno = valido ? puntosDeControl(suavizarTrazo(trazo)) : previo;
    trazo = null;
    dibujarContorno(canvas);
    renderFondo();
    if (state.contorno !== previo) schedulePreview();
  };
  canvas.addEventListener("pointerup", soltar);
  canvas.addEventListener("pointercancel", soltar);
  canvas.addEventListener("dblclick", (e) => {
    const i = state.contorno.length > CONTORNO_PUNTOS_MIN ? puntoCerca(punto(e)) : -1;
    if (i < 0) return;
    state.contorno = state.contorno.toSpliced(i, 1);
    dibujarContorno(canvas);
    schedulePreview();
  });
  return canvas;
}

/** Imagen PNG del contorno (la zona encerrada en blanco, el resto negro), reducida a CONTORNO_LADO_MAX. */
function exportarContorno(source) {
  const escala = Math.min(1, CONTORNO_LADO_MAX / Math.max(source.width, source.height));
  const canvas = el("canvas", { width: Math.round(source.width * escala), height: Math.round(source.height * escala) });
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.scale(escala, escala);
  trazarCamino(ctx, curvaSuave(state.contorno));
  ctx.closePath();
  ctx.fillStyle = "#fff";
  ctx.fill();
  return new Promise((ok) => canvas.toBlob(ok, "image/png"));
}

function renderFondo() {
  const activo = usaProducto();
  $("#quitar-fondo").checked = state.options.quitar_fondo;
  $("#centrar").checked = state.options.centrar;
  $("#contorno-controles").hidden = !activo;
  $("#btn-borrar-contorno").disabled = !state.contorno.length;
  $("#contorno-aviso").textContent = state.contorno.length
    ? "Usamos tu contorno. Arrastrá un punto para corregirlo, tocá la línea para agregar uno o hacé doble clic en un punto para sacarlo."
    : "Encontramos tu producto automáticamente. Si no quedó bien, dibujá una línea alrededor de tu producto, sobre la foto.";
  const canvas = $("#contorno-canvas");
  if (canvas) canvas.hidden = !activo;

  $("#field-espacio").hidden = !state.options.centrar;
  for (const b of document.querySelectorAll("#espacio button")) {
    b.setAttribute("aria-pressed", String(b.dataset.value === state.options.espacio));
  }
}

/* Luz y color: los tres deslizadores y la casilla. El de "aclarar" se muestra de 0 a 100 y se manda de 0 a 1. */
const LUZ_NEUTRA = { brillo: 0, contraste: 0, aclarar_oscuras: 0, colores_naturales: false };

function renderLuz() {
  const o = state.options;
  $("#brillo").value = o.brillo;
  $("#contraste").value = o.contraste;
  $("#aclarar-oscuras").value = Math.round(o.aclarar_oscuras * 100);
  $("#colores-naturales").checked = o.colores_naturales;
  $("#btn-restablecer-luz").disabled = Object.keys(LUZ_NEUTRA).every((k) => o[k] === LUZ_NEUTRA[k]);
}

function cambiarLuz(cambio) {
  cambio();
  renderLuz();
  schedulePreview();
}

function cambiarFondo(cambio) {
  cambio();
  const canvas = $("#contorno-canvas");
  if (canvas) dibujarContorno(canvas);
  renderFondo();
  schedulePreview();
}

function renderSaveButton() {
  const button = $("#btn-guardar");
  button.disabled = !state.preview || state.busy || state.saving || Boolean(state.viewing);
  button.textContent = state.saving ? "Guardando…" : "Guardar y descargar";
}

function renderResult() {
  const frame = $("#result-frame");
  const { preview, previewError: error, viewing: v } = state;
  renderSaveButton();

  if (v) {  // mirando un trabajo guardado: solo lectura
    frame.classList.remove("loading");
    $("#result-meta").textContent = resultLine(v.peso_bytes, v.calidad, v.ancho, v.alto);
    $("#result-avisos").replaceChildren(
      el("div", { class: "notice" }, "Estás viendo una foto guardada. ",
        el("button", { type: "button", class: "btn btn-ghost btn-sm", onclick: closeView },
          state.source ? "Volver a mi foto" : "Cerrar")),
      ...avisosNodes(v.avisos));
    frame.replaceChildren(el("img", { src: absoluteUrl(v.url), alt: `Foto guardada: ${v.nombre_original}` }));
    return;
  }

  frame.classList.toggle("loading", state.busy);
  $("#result-meta").textContent = preview ? resultLine(preview.peso, preview.calidad, preview.ancho, preview.alto) : "";
  $("#result-avisos").replaceChildren(...avisosNodes(preview?.avisos ?? []));

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
  for (const b of document.querySelectorAll("#peso button")) {
    b.setAttribute("aria-pressed", String(b.dataset.value === o.peso));
  }
  for (const b of document.querySelectorAll("#nitidez button")) {
    b.setAttribute("aria-pressed", String(b.dataset.value === o.nitidez));
  }
  $("#peso-help").textContent = PESOS[o.peso];

  const eje = ejeRecorte();
  $("#field-posicion").hidden = o.adaptacion !== "recortar";
  // Siempre se muestran los dos, pero solo tiene efecto el del eje donde sobra foto.
  $("#posicion-x").disabled = eje !== "horizontal";
  $("#posicion-y").disabled = eje !== "vertical";
  $("#posicion-x").value = Math.round(o.posicion_x * 100);
  $("#posicion-y").value = Math.round(o.posicion_y * 100);
  $("#posicion-help").textContent = AYUDA_POSICION[eje ?? "ninguno"];
  renderFondo();
  renderLuz();
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
/* Guardado y galería                                                        */
/* ------------------------------------------------------------------------ */

const formatDate = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString([], { dateStyle: "short", timeStyle: "short" });
};

/** Descarga el resultado de un trabajo guardado. */
function download(trabajo) {
  const base = trabajo.nombre_original.replace(/\.[^.]+$/, "") || "foto";
  const ext = trabajo.url.split(".").pop();
  const a = el("a", { href: absoluteUrl(trabajo.url), download: `${base}-${trabajo.plataforma}.${ext}` });
  document.body.append(a);
  a.click();
  a.remove();
}

async function save() {
  const source = state.source;
  if (!source || state.saving) return;
  state.saving = true;
  renderSaveButton();
  try {
    const trabajo = await api("POST", "/api/trabajos", { formData: await buildForm(source, state.options) });
    download(trabajo);
    toast("ok", "Foto guardada", "Quedó en tu galería y se descargó.");
    await loadGallery();
  } catch (err) {
    toastError(err);
  } finally {
    state.saving = false;
    renderSaveButton();
  }
}

async function loadGallery() {
  try {
    state.trabajos = await api("GET", "/api/trabajos");
    state.galleryError = null;
  } catch (err) {
    state.trabajos = [];
    state.galleryError = err;
  }
  renderGallery();
}

function renderGallery() {
  const gallery = $("#gallery");
  if (state.galleryError) {
    gallery.replaceChildren(el("div", { class: "notice notice-err" },
      el("strong", {}, state.galleryError.title + ". "), state.galleryError.message));
    return;
  }
  if (!state.trabajos.length) {
    gallery.replaceChildren(el("div", { class: "notice" }, "Todavía no guardaste ninguna foto."));
    return;
  }
  gallery.replaceChildren(...state.trabajos.map((t) => {
    const plataforma = state.plataformas.find((p) => p.clave === t.plataforma)?.nombre ?? t.plataforma;
    return el("div", {
      class: `item${state.viewing?.id === t.id ? " active" : ""}`, role: "button", tabindex: "0",
      title: `${t.nombre_original} · ${formatDate(t.creado)}`,
      onclick: () => view(t),
      onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); view(t); } },
    },
      el("img", { class: "item-thumb", src: absoluteUrl(t.url), alt: "", loading: "lazy" }),
      el("div", { class: "item-info" },
        el("div", { class: "item-name" }, t.nombre_original),
        el("div", { class: "item-detail" }, `${plataforma} · ${formatBytes(t.peso_bytes)}`)),
      el("div", { class: "item-actions" },
        el("button", {
          type: "button", class: "item-btn", title: "Descargar", "aria-label": `Descargar ${t.nombre_original}`,
          onclick: (e) => { e.stopPropagation(); download(t); },
        }, "↓"),
        el("button", {
          type: "button", class: "item-btn item-delete", title: "Borrar", "aria-label": `Borrar ${t.nombre_original}`,
          onclick: (e) => { e.stopPropagation(); remove(t); },
        }, "×")),
    );
  }));
}

/** Muestra un trabajo guardado en el centro (original y resultado), sin tocar la foto que se está editando. */
function view(trabajo) {
  state.viewing = trabajo;
  renderPhoto();
  renderResult();
  renderGallery();
}

function closeView() {
  state.viewing = null;
  renderPhoto();
  renderResult();
  renderGallery();
}

async function remove(trabajo) {
  try {
    await api("DELETE", `/api/trabajos/${encodeURIComponent(trabajo.id)}`);
    toast("ok", "Foto borrada", trabajo.nombre_original);
    if (state.viewing?.id === trabajo.id) closeView();
    await loadGallery();
  } catch (err) {
    toastError(err);
  }
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
  for (const campo of ["adaptacion", "nitidez", "peso"]) {
    for (const b of document.querySelectorAll(`#${campo} button`)) {
      b.addEventListener("click", () => {
        state.options[campo] = b.dataset.value;
        renderOptions();
        schedulePreview();
      });
    }
  }
  $("#btn-guardar").addEventListener("click", save);

  $("#quitar-fondo").addEventListener("change", (e) => cambiarFondo(() => { state.options.quitar_fondo = e.target.checked; }));
  $("#centrar").addEventListener("change", (e) => cambiarFondo(() => { state.options.centrar = e.target.checked; }));
  for (const b of document.querySelectorAll("#espacio button")) {
    b.addEventListener("click", () => cambiarFondo(() => { state.options.espacio = b.dataset.value; }));
  }
  $("#brillo").addEventListener("input", (e) => cambiarLuz(() => { state.options.brillo = Number(e.target.value); }));
  $("#contraste").addEventListener("input", (e) => cambiarLuz(() => { state.options.contraste = Number(e.target.value); }));
  $("#aclarar-oscuras").addEventListener("input", (e) => cambiarLuz(() => { state.options.aclarar_oscuras = Number(e.target.value) / 100; }));
  $("#colores-naturales").addEventListener("change", (e) => cambiarLuz(() => { state.options.colores_naturales = e.target.checked; }));
  $("#btn-restablecer-luz").addEventListener("click", () => cambiarLuz(() => Object.assign(state.options, LUZ_NEUTRA)));
  $("#btn-borrar-contorno").addEventListener("click", () => cambiarFondo(() => { state.contorno = []; }));
}

function init() {
  $("#link-docs").href = (API_BASE || "") + "/docs";
  renderPhoto();
  renderOptions();
  bindEvents();
  checkServer();
  loadPlataformas().then(loadGallery);  // la galería usa los nombres de las plataformas
}

init();
