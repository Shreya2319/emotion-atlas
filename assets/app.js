/* Emotion Atlas — shared front-end logic */

const MANIFEST_URL = "manifest.json";

/* Encode a path made of segments that may contain spaces / special chars */
function encPath(...segments) {
  return segments.map(encodeURIComponent).join("/");
}

function imgSrc(folder, filename) {
  return encPath("images", folder, filename);
}

function guideSrc(dir, file) {
  return encPath(dir, file);
}

async function loadManifest() {
  // Primary: embedded data (assets/data.js) — works with no server, even file://
  if (window.EMOTION_DATA) return window.EMOTION_DATA;
  // Fallback: fetch the JSON (only works over http/https)
  const res = await fetch(MANIFEST_URL, { cache: "no-cache" });
  if (!res.ok) throw new Error("Could not load manifest.json (" + res.status + ")");
  return res.json();
}

/* Prettify an ALLCAPS folder/name into Title Case for display */
function titleCase(str) {
  return str
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

/* ---------------- Homepage ---------------- */
async function initHome() {
  let data;
  try {
    data = await loadManifest();
  } catch (e) {
    document.getElementById("emotion-grid").innerHTML =
      `<p class="notice">Couldn't load data. If you opened this file directly, please run it through a local server (see README).</p>`;
    console.error(e);
    return;
  }

  // Emotion grid
  const grid = document.getElementById("emotion-grid");
  grid.innerHTML = data.emotions
    .map((e) => {
      const cover = e.cover
        ? `<img class="card-img" src="${imgSrc(e.folder, e.cover)}" alt="${titleCase(e.name)}" loading="lazy">`
        : `<div class="card-img card-img--empty"></div>`;
      return `
        <a class="emotion-card" href="emotion.html?e=${encodeURIComponent(e.folder)}">
          <div class="card-img-wrap">${cover}</div>
          <span class="card-name">${titleCase(e.name)}</span>
        </a>`;
    })
    .join("");
  document.getElementById("emotion-count").textContent = data.emotions.length;

  // Guides
  const guidesEl = document.getElementById("guides");
  if (data.guides && data.guides.length) {
    guidesEl.innerHTML = data.guides
      .map((g) => {
        const href = guideSrc(data.guideDir || "guide", g.file);
        return `
          <a class="guide-card" href="${href}" download>
            <span class="guide-icon" aria-hidden="true">↓</span>
            <span class="guide-text">
              <span class="guide-title">${g.title}</span>
              <span class="guide-meta">PDF · Free download</span>
            </span>
          </a>`;
      })
      .join("");
  } else {
    guidesEl.innerHTML = `<p class="notice">No guides available yet.</p>`;
  }
}

/* ---------------- Detail page ---------------- */
async function initDetail() {
  let data;
  try {
    data = await loadManifest();
  } catch (e) {
    document.getElementById("detail-root").innerHTML =
      `<p class="notice">Couldn't load data. If you opened this file directly, please run it through a local server (see README).</p>`;
    console.error(e);
    return;
  }

  const folder = getParam("e");
  const emotion = data.emotions.find((x) => x.folder === folder);

  const root = document.getElementById("detail-root");
  if (!emotion) {
    root.innerHTML = `
      <div class="detail-head">
        <h1>Emotion not found</h1>
        <p class="lede">We couldn't find that emotion. <a href="index.html">Return to the atlas</a>.</p>
      </div>`;
    return;
  }

  document.title = `${titleCase(emotion.name)} — Emotion Atlas`;

  // Connected chips
  const chips = emotion.connectedResolved
    .map((c) => {
      if (c.folder) {
        return `<a class="chip" href="emotion.html?e=${encodeURIComponent(c.folder)}">${titleCase(c.label)}</a>`;
      }
      return `<span class="chip chip--disabled" title="No page yet">${titleCase(c.label)}</span>`;
    })
    .join("");

  // Gallery
  const slides = emotion.images
    .map(
      (fn, i) =>
        `<button class="frame" data-index="${i}" aria-label="Open image ${i + 1}">
           <img src="${imgSrc(emotion.folder, fn)}" alt="${titleCase(emotion.name)} ${i + 1}" loading="lazy">
         </button>`
    )
    .join("");

  root.innerHTML = `
    <a class="back-link" href="index.html">← All emotions</a>
    <header class="detail-head">
      <p class="eyebrow">Emotion</p>
      <h1>${titleCase(emotion.name)}</h1>
      <p class="lede">${emotion.description}</p>
    </header>

    <section class="gallery" aria-label="${titleCase(emotion.name)} gallery">
      <button class="scroll-btn scroll-btn--prev" aria-label="Scroll left">‹</button>
      <div class="filmstrip" id="filmstrip">${slides}</div>
      <button class="scroll-btn scroll-btn--next" aria-label="Scroll right">›</button>
    </section>

    <section class="detail-block">
      <h2>Connected emotions</h2>
      <div class="chips">${chips}</div>
    </section>

    <section class="detail-block">
      <h2>Go deeper</h2>
      <button class="btn btn--disabled" disabled>Related Workbook — Coming Soon</button>
    </section>
  `;

  wireGallery(emotion);
}

function wireGallery(emotion) {
  const strip = document.getElementById("filmstrip");
  const prev = document.querySelector(".scroll-btn--prev");
  const next = document.querySelector(".scroll-btn--next");
  const step = () => Math.max(strip.clientWidth * 0.8, 240);
  prev.addEventListener("click", () => strip.scrollBy({ left: -step(), behavior: "smooth" }));
  next.addEventListener("click", () => strip.scrollBy({ left: step(), behavior: "smooth" }));

  // Lightbox
  const frames = [...strip.querySelectorAll(".frame")];
  let current = 0;
  const lb = document.getElementById("lightbox");
  const lbImg = document.getElementById("lightbox-img");
  const show = (i) => {
    current = (i + emotion.images.length) % emotion.images.length;
    lbImg.src = imgSrc(emotion.folder, emotion.images[current]);
    lbImg.alt = titleCase(emotion.name) + " " + (current + 1);
    lb.classList.add("open");
    lb.setAttribute("aria-hidden", "false");
  };
  const close = () => {
    lb.classList.remove("open");
    lb.setAttribute("aria-hidden", "true");
    lbImg.src = "";
  };
  frames.forEach((f) =>
    f.addEventListener("click", () => show(parseInt(f.dataset.index, 10)))
  );
  lb.querySelector(".lb-close").addEventListener("click", close);
  lb.querySelector(".lb-prev").addEventListener("click", () => show(current - 1));
  lb.querySelector(".lb-next").addEventListener("click", () => show(current + 1));
  lb.addEventListener("click", (e) => {
    if (e.target === lb) close();
  });
  document.addEventListener("keydown", (e) => {
    if (!lb.classList.contains("open")) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowRight") show(current + 1);
    if (e.key === "ArrowLeft") show(current - 1);
  });
}
