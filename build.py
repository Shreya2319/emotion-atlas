#!/usr/bin/env python3
"""
Emotion Atlas — static site generator.

Single source of truth for the whole site. Reads data.csv + the images/ and
guide/ folders, then renders fully pre-rendered, SEO-ready HTML:

  /                         -> index.html (static homepage grid + guides)
  /emotion/<slug>/          -> one real HTML page per emotion (clean URL)
  /404.html, /500.html      -> error pages
  /sitemap.xml, /robots.txt -> crawl + indexing
  /site.webmanifest         -> PWA / icons
  /manifest.json            -> build-time data (kept for future search / tools)
  favicons + default OG image (generated from brand/logo-globe.png)

No framework, no runtime data fetching. Design, fonts, colours and copy are
untouched — pages are simply rendered at build time instead of in the browser.

Run:  python build.py
"""

import os
import re
import csv
import json
import html
import datetime
from PIL import Image

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(BASE, "images")
GUIDE = os.path.join(BASE, "guide")
BRAND_DIR = os.path.join(BASE, "brand")

SITE_URL = "https://www.theemotionatlas.com"          # canonical origin (no trailing slash)
SITE_NAME = "Emotion Atlas"
SITE_TAGLINE = "A visual map of human emotion"
DEFAULT_DESC = ("Emotion Atlas is a visual encyclopaedia of human emotion — "
                "each feeling given a name, a place, and a set of connections.")
TWITTER_HANDLE = ""            # set to "@handle" when you have one
BG_COLOR = (250, 247, 242)     # --bg  #faf7f2
INK = (44, 46, 51)             # --ink

BUILD_DATE = datetime.date.today().isoformat()

# Google Fonts URL (same fonts already in use — just loaded more efficiently)
FONTS_HREF = ("https://fonts.googleapis.com/css2?"
              "family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600"
              "&family=Inter:wght@400;500;600&display=swap")

EXCLUDE = {"ea globe last post.png"}
DEMOTE = {"AMBITIOUS": "ambition.png", "INTERESTING": "interest.png"}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def natkey(s):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", s.lower())]


def slugify(name):
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def title_case(s):
    return re.sub(r"\b\w", lambda m: m.group(0).upper(), s.lower())


def esc(s):
    """Escape for HTML text/attribute context."""
    return html.escape(str(s), quote=True)


_DIM_CACHE = {}


def img_dims(path):
    if path in _DIM_CACHE:
        return _DIM_CACHE[path]
    try:
        with Image.open(path) as im:
            _DIM_CACHE[path] = im.size
    except Exception:
        _DIM_CACHE[path] = (None, None)
    return _DIM_CACHE[path]


def url_path(*segments):
    """Root-relative URL from path segments (each individually encoded)."""
    from urllib.parse import quote
    return "/" + "/".join(quote(seg) for seg in segments)


# --------------------------------------------------------------------------
# Load data
# --------------------------------------------------------------------------
def load_emotions():
    emotions = []
    with open(os.path.join(BASE, "data.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            folder = row["image_folder"].strip()
            fp = os.path.join(IMAGES, folder)
            imgs = ([fn for fn in os.listdir(fp)
                     if os.path.isfile(os.path.join(fp, fn))
                     and fn.lower().endswith(".png")
                     and fn.lower() not in EXCLUDE]
                    if os.path.isdir(fp) else [])
            imgs.sort(key=natkey)
            card = DEMOTE.get(folder.upper())
            if card:
                moved = [fn for fn in imgs if fn.lower() == card]
                imgs = [fn for fn in imgs if fn.lower() != card] + moved
            emotions.append({
                "name": row["emotion_name"].strip(),
                "folder": folder,
                "slug": slugify(row["emotion_name"].strip()),
                "description": row["short_description"].strip(),
                "connected": [c.strip() for c in row["connected_emotions"].split(";") if c.strip()],
                "cover": imgs[0] if imgs else None,
                "images": imgs,
            })

    valid = {e["folder"].upper(): e for e in emotions}
    valid_names = {e["name"].upper(): e for e in emotions}
    for e in emotions:
        resolved = []
        for c in e["connected"]:
            match = valid.get(c.upper()) or valid_names.get(c.upper())
            resolved.append({
                "label": c,
                "folder": match["folder"] if match else None,
                "slug": match["slug"] if match else None,
            })
        e["connectedResolved"] = resolved
    return emotions


def load_guides():
    if not os.path.isdir(GUIDE):
        return []
    return [{"file": fn, "title": os.path.splitext(fn)[0]}
            for fn in sorted(os.listdir(GUIDE)) if fn.lower().endswith(".pdf")]


# --------------------------------------------------------------------------
# <head> builder — metadata, canonical, OG, Twitter, JSON-LD, icons, fonts
# --------------------------------------------------------------------------
def head(title, description, canonical, og_image, og_type="website",
         keywords=None, jsonld=None, og_image_alt=None):
    canonical_abs = SITE_URL + canonical
    og_image_abs = og_image if og_image.startswith("http") else SITE_URL + og_image
    parts = [
        "<meta charset=\"UTF-8\" />",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />",
        f"<title>{esc(title)}</title>",
        f"<meta name=\"description\" content=\"{esc(description)}\" />",
    ]
    if keywords:
        parts.append(f"<meta name=\"keywords\" content=\"{esc(', '.join(keywords))}\" />")
    parts += [
        "<meta name=\"robots\" content=\"index, follow, max-image-preview:large\" />",
        f"<link rel=\"canonical\" href=\"{esc(canonical_abs)}\" />",
        "<meta name=\"theme-color\" content=\"#faf7f2\" />",
        f"<meta name=\"author\" content=\"{esc(SITE_NAME)}\" />",
        # Open Graph
        f"<meta property=\"og:type\" content=\"{esc(og_type)}\" />",
        f"<meta property=\"og:site_name\" content=\"{esc(SITE_NAME)}\" />",
        f"<meta property=\"og:title\" content=\"{esc(title)}\" />",
        f"<meta property=\"og:description\" content=\"{esc(description)}\" />",
        f"<meta property=\"og:url\" content=\"{esc(canonical_abs)}\" />",
        f"<meta property=\"og:image\" content=\"{esc(og_image_abs)}\" />",
        f"<meta property=\"og:image:alt\" content=\"{esc(og_image_alt or title)}\" />",
        "<meta property=\"og:locale\" content=\"en_US\" />",
        # Twitter
        "<meta name=\"twitter:card\" content=\"summary_large_image\" />",
        f"<meta name=\"twitter:title\" content=\"{esc(title)}\" />",
        f"<meta name=\"twitter:description\" content=\"{esc(description)}\" />",
        f"<meta name=\"twitter:image\" content=\"{esc(og_image_abs)}\" />",
    ]
    if TWITTER_HANDLE:
        parts.append(f"<meta name=\"twitter:site\" content=\"{esc(TWITTER_HANDLE)}\" />")
    # Icons / manifest
    parts += [
        "<link rel=\"icon\" href=\"/favicon.ico\" sizes=\"any\" />",
        "<link rel=\"icon\" type=\"image/png\" sizes=\"32x32\" href=\"/favicon-32x32.png\" />",
        "<link rel=\"apple-touch-icon\" sizes=\"180x180\" href=\"/apple-touch-icon.png\" />",
        "<link rel=\"manifest\" href=\"/site.webmanifest\" />",
        # Fonts — preconnect + preload + stylesheet (same fonts, display=swap).
        # No inline onload handler, so a strict CSP (no 'unsafe-inline' scripts) works.
        "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />",
        "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />",
        f"<link rel=\"preload\" as=\"style\" href=\"{esc(FONTS_HREF)}\" />",
        f"<link rel=\"stylesheet\" href=\"{esc(FONTS_HREF)}\" />",
        # Site CSS
        "<link rel=\"stylesheet\" href=\"/assets/style.css\" />",
    ]
    for block in (jsonld or []):
        parts.append("<script type=\"application/ld+json\">"
                     + json.dumps(block, ensure_ascii=False) + "</script>")
    return "\n  ".join(parts)


def organization_ld():
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": SITE_NAME,
        "url": SITE_URL + "/",
        "logo": SITE_URL + "/brand/logo-globe.png",
        "description": DEFAULT_DESC,
    }


def website_ld():
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": SITE_URL + "/",
        "description": DEFAULT_DESC,
    }


# --------------------------------------------------------------------------
# Shared chrome (header / footer)
# --------------------------------------------------------------------------
def site_header():
    return """  <header class="site-header">
    <div class="wrap">
      <a class="brand" href="/"><img class="brand-logo" src="/brand/logo-globe.png" alt="" width="888" height="619" /> Emotion Atlas</a>
      <nav class="nav-links" aria-label="Primary">
        <a href="/#journey">Journey</a>
        <a href="/#emotions">Emotions</a>
        <a href="/#guides">Free Guides</a>
        <a href="/#workbooks">Workbooks</a>
      </nav>
    </div>
  </header>"""


def site_footer():
    year = datetime.date.today().year
    return f"""  <footer class="site-footer">
    <div class="wrap">
      <span>&copy; {year} Emotion Atlas</span>
      <span>Every feeling has a place.</span>
    </div>
  </footer>"""


def page(head_html, body_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  {head_html}
</head>
<body>
{body_html}
</body>
</html>
"""


# --------------------------------------------------------------------------
# Homepage
# --------------------------------------------------------------------------
def render_home(emotions, guides):
    # Emotion grid (static)
    cards = []
    for e in emotions:
        if e["cover"]:
            w, h = img_dims(os.path.join(IMAGES, e["folder"], e["cover"]))
            dim = f' width="{w}" height="{h}"' if w else ""
            cover = (f'<img class="card-img" src="{esc(url_path("images", e["folder"], e["cover"]))}" '
                     f'alt="{esc(title_case(e["name"]))} — Emotion Atlas" loading="lazy" decoding="async"{dim}>')
        else:
            cover = '<div class="card-img card-img--empty"></div>'
        cards.append(
            f'<a class="emotion-card" href="/emotion/{e["slug"]}">'
            f'<div class="card-img-wrap">{cover}</div>'
            f'<span class="card-name">{esc(title_case(e["name"]))}</span></a>')
    grid_html = "\n          ".join(cards)

    # Guides (static)
    if guides:
        gcards = []
        for g in guides:
            href = esc(url_path("guide", g["file"]))
            gcards.append(
                f'<a class="guide-card" href="{href}" download>'
                f'<span class="guide-icon" aria-hidden="true">&darr;</span>'
                f'<span class="guide-text">'
                f'<span class="guide-title">{esc(g["title"])}</span>'
                f'<span class="guide-meta">PDF &middot; Free download</span></span></a>')
        guides_html = "\n          ".join(gcards)
    else:
        guides_html = '<p class="notice">No guides available yet.</p>'

    keywords = ["emotion atlas", "human emotions", "map of emotions", "feelings",
                "emotional intelligence", "emotional awareness", "list of emotions",
                "understanding emotions"]

    head_html = head(
        title=f"{SITE_NAME} — {SITE_TAGLINE}",
        description=DEFAULT_DESC,
        canonical="/",
        og_image="/og-default.png",
        og_type="website",
        keywords=keywords,
        og_image_alt="Emotion Atlas — a visual map of human emotion",
        jsonld=[organization_ld(), website_ld()],
    )

    body = f"""{site_header()}
  <main>
    <section class="hero">
      <div class="wrap">
        <img class="hero-globe" src="/brand/logo-globe.png" alt="Atlas of Emotions — every feeling has a place" width="888" height="619" fetchpriority="high" decoding="async" />
        <p class="eyebrow">A visual encyclopaedia of feeling</p>
        <h1>Every emotion has a name and a place.</h1>
        <p class="lede">
          Emotion Atlas maps human emotion the way a field guide maps the natural world &mdash;
          with precision, depth, and calm. Explore each feeling, see how it connects to others,
          and learn to experience it without being consumed by it.
        </p>
        <div class="hero-cta">
          <a class="btn btn--primary" href="#emotions">Explore the atlas</a>
          <a class="btn btn--ghost" href="#journey">The journey within</a>
        </div>
      </div>
    </section>

    <section class="section journey" id="journey">
      <div class="wrap">
        <div class="section-head section-head--center">
          <p class="eyebrow">From reaction to enlightenment</p>
          <h2>The Journey Within</h2>
          <p>Every feeling moves through five stages. You don't suppress emotions &mdash; you outgrow their control.</p>
        </div>

        <ol class="steps">
          <li class="step-card">
            <span class="step-num">1</span>
            <img src="/brand/feel.png" alt="Feel — allow yourself to experience what's within" loading="lazy" decoding="async" />
            <div class="step-body">
              <h3>Feel</h3>
              <p>Allow yourself to experience what's within. Every emotion is a message, not a mistake.</p>
            </div>
          </li>
          <li class="step-card">
            <span class="step-num">2</span>
            <img src="/brand/observe.png" alt="Observe — watch your thoughts without judgment" loading="lazy" decoding="async" />
            <div class="step-body">
              <h3>Observe</h3>
              <p>Step back. Watch your thoughts and emotions without judgment. Observation creates space between you and the storm.</p>
            </div>
          </li>
          <li class="step-card">
            <span class="step-num">3</span>
            <img src="/brand/understand.png" alt="Understand — seek the why behind what you feel" loading="lazy" decoding="async" />
            <div class="step-body">
              <h3>Understand</h3>
              <p>Seek the why behind what you feel. Understanding brings clarity, and clarity creates choice.</p>
            </div>
          </li>
          <li class="step-card">
            <span class="step-num">4</span>
            <img src="/brand/grow.png" alt="Grow — use what you've learned to evolve" loading="lazy" decoding="async" />
            <div class="step-body">
              <h3>Grow</h3>
              <p>Use what you've learned to evolve. Growth happens when you choose healing over habit.</p>
            </div>
          </li>
          <li class="step-card">
            <span class="step-num">5</span>
            <img src="/brand/detach.png" alt="Detach — release what no longer serves you" loading="lazy" decoding="async" />
            <div class="step-body">
              <h3>Detach</h3>
              <p>Release what no longer serves you. Detachment isn't coldness, it's freedom. You can feel, without losing yourself.</p>
            </div>
          </li>
        </ol>

        <figure class="journey-full">
          <img src="/brand/journey.png" alt="The Journey Within — from reaction to enlightenment: Feel, Observe, Understand, Grow, Detach" loading="lazy" decoding="async" />
          <figcaption>Emotions are temporary. Awareness is power. Detachment is freedom.</figcaption>
        </figure>
      </div>
    </section>

    <section class="section" id="emotions">
      <div class="wrap">
        <div class="section-head">
          <h2>The Atlas</h2>
          <p><span id="emotion-count">{len(emotions)}</span> emotions mapped, and growing. Tap any feeling to explore it.</p>
        </div>
        <div class="emotion-grid" id="emotion-grid">
          {grid_html}
        </div>
      </div>
    </section>

    <section class="section" id="guides" style="background: var(--surface-2);">
      <div class="wrap">
        <div class="section-head">
          <h2>Free Guides</h2>
          <p>Starter resources for mapping your own emotional landscape. Free to download.</p>
        </div>
        <div class="guides" id="guides">
          {guides_html}
        </div>
      </div>
    </section>

    <section class="section" id="workbooks">
      <div class="wrap">
        <div class="section-head">
          <h2>Workbooks &mdash; Coming Soon</h2>
          <p>Guided workbooks to move through each emotion: experience it, acknowledge it, and gently detach.</p>
        </div>
        <div class="workbooks">
          <div class="workbook-card">
            <span class="ph-tag">Coming Soon</span>
            <span class="ph-title">Workbook One</span>
            <div><div class="ph-line"></div><div class="ph-line short" style="margin-top:10px;"></div></div>
          </div>
          <div class="workbook-card">
            <span class="ph-tag">Coming Soon</span>
            <span class="ph-title">Workbook Two</span>
            <div><div class="ph-line"></div><div class="ph-line short" style="margin-top:10px;"></div></div>
          </div>
          <div class="workbook-card">
            <span class="ph-tag">Coming Soon</span>
            <span class="ph-title">Workbook Three</span>
            <div><div class="ph-line"></div><div class="ph-line short" style="margin-top:10px;"></div></div>
          </div>
        </div>
      </div>
    </section>
  </main>

{site_footer()}"""
    return page(head_html, body)


# --------------------------------------------------------------------------
# Emotion detail page
# --------------------------------------------------------------------------
def render_emotion(e, index):
    name = title_case(e["name"])
    cover_url = url_path("images", e["folder"], e["cover"]) if e["cover"] else "/og-default.png"

    # Gallery
    frames = []
    for i, fn in enumerate(e["images"]):
        w, h = img_dims(os.path.join(IMAGES, e["folder"], fn))
        dim = f' width="{w}" height="{h}"' if w else ""
        # First image is the LCP candidate on this page — load it eagerly.
        loading = 'loading="eager" fetchpriority="high"' if i == 0 else 'loading="lazy"'
        frames.append(
            f'<button class="frame" data-index="{i}" aria-label="Open image {i + 1} of {len(e["images"])}" type="button">'
            f'<img src="{esc(url_path("images", e["folder"], fn))}" alt="{esc(name)} — image {i + 1}" '
            f'{loading} decoding="async"{dim}></button>')
    gallery_html = "\n        ".join(frames)

    # Connected chips (internal links to related emotions)
    chips = []
    for c in e["connectedResolved"]:
        if c["slug"]:
            chips.append(f'<a class="chip" href="/emotion/{c["slug"]}">{esc(title_case(c["label"]))}</a>')
        else:
            chips.append(f'<span class="chip chip--disabled" title="No page yet">{esc(title_case(c["label"]))}</span>')
    chips_html = "\n        ".join(chips)

    # Keywords + meta description
    connected_names = [title_case(c["label"]) for c in e["connectedResolved"]]
    keywords = [name.lower(), f"{name.lower()} emotion", f"meaning of {name.lower()}",
                f"what is {name.lower()}", "emotion atlas"] + [c.lower() for c in connected_names]
    meta_desc = (f"{name}: {e['description']} Explore {name.lower()} in the Emotion Atlas — "
                 f"imagery, meaning, and its connections to {', '.join(connected_names) or 'other feelings'}.")
    meta_desc = meta_desc[:300]

    canonical = f"/emotion/{e['slug']}"

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "The Atlas", "item": SITE_URL + "/#emotions"},
            {"@type": "ListItem", "position": 3, "name": name, "item": SITE_URL + canonical},
        ],
    }
    article_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{name} — Emotion Atlas",
        "description": e["description"],
        "image": SITE_URL + cover_url,
        "about": {"@type": "Thing", "name": name},
        "author": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/"},
        "publisher": {
            "@type": "Organization",
            "name": SITE_NAME,
            "logo": {"@type": "ImageObject", "url": SITE_URL + "/brand/logo-globe.png"},
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": SITE_URL + canonical},
        "datePublished": BUILD_DATE,
        "dateModified": BUILD_DATE,
        "inLanguage": "en",
    }

    head_html = head(
        title=f"{name} — Emotion Atlas",
        description=meta_desc,
        canonical=canonical,
        og_image=cover_url,
        og_type="article",
        keywords=keywords,
        og_image_alt=f"{name} — Emotion Atlas",
        jsonld=[breadcrumb_ld, article_ld],
    )

    body = f"""{site_header()}
  <main>
    <div class="wrap detail-root" id="detail-root">
      <a class="back-link" href="/">&larr; All emotions</a>
      <header class="detail-head">
        <p class="eyebrow">Emotion</p>
        <h1>{esc(name)}</h1>
        <p class="lede">{esc(e['description'])}</p>
      </header>

      <section class="gallery" aria-label="{esc(name)} gallery">
        <button class="scroll-btn scroll-btn--prev" aria-label="Scroll left" type="button">&lsaquo;</button>
        <div class="filmstrip" id="filmstrip">
        {gallery_html}
        </div>
        <button class="scroll-btn scroll-btn--next" aria-label="Scroll right" type="button">&rsaquo;</button>
      </section>

      <section class="detail-block">
        <h2>Connected emotions</h2>
        <div class="chips">
        {chips_html}
        </div>
      </section>

      <section class="detail-block">
        <h2>Go deeper</h2>
        <button class="btn btn--disabled" disabled>Related Workbook &mdash; Coming Soon</button>
      </section>
    </div>
  </main>

  <div class="lightbox" id="lightbox" aria-hidden="true" role="dialog" aria-label="Image viewer" aria-modal="true">
    <button class="lb-btn lb-close" aria-label="Close image viewer" type="button">&#10005;</button>
    <button class="lb-btn lb-prev" aria-label="Previous image" type="button">&lsaquo;</button>
    <img id="lightbox-img" src="" alt="" />
    <button class="lb-btn lb-next" aria-label="Next image" type="button">&rsaquo;</button>
  </div>

{site_footer()}

  <script src="/assets/app.js" defer></script>"""
    return page(head_html, body)


# --------------------------------------------------------------------------
# Error pages
# --------------------------------------------------------------------------
def render_error(code, heading, message):
    head_html = head(
        title=f"{heading} — Emotion Atlas",
        description=message,
        canonical="/",
        og_image="/og-default.png",
        keywords=None,
        jsonld=None,
    )
    # noindex the error pages
    head_html = head_html.replace(
        '<meta name="robots" content="index, follow, max-image-preview:large" />',
        '<meta name="robots" content="noindex, follow" />')
    body = f"""{site_header()}
  <main>
    <section class="section">
      <div class="wrap" style="text-align:center; padding: 80px 24px;">
        <p class="eyebrow">Error {code}</p>
        <h1>{esc(heading)}</h1>
        <p class="lede" style="margin: 0 auto 28px;">{esc(message)}</p>
        <a class="btn btn--primary" href="/">Return to the atlas</a>
      </div>
    </section>
  </main>

{site_footer()}"""
    return page(head_html, body)


# --------------------------------------------------------------------------
# sitemap.xml + robots.txt
# --------------------------------------------------------------------------
def render_sitemap(emotions):
    urls = [{"loc": SITE_URL + "/", "priority": "1.0", "changefreq": "weekly"}]
    for e in emotions:
        urls.append({"loc": SITE_URL + f"/emotion/{e['slug']}",
                     "priority": "0.8", "changefreq": "monthly"})
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{u['loc']}</loc>")
        lines.append(f"    <lastmod>{BUILD_DATE}</lastmod>")
        lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        lines.append(f"    <priority>{u['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def render_robots():
    return (
        "User-agent: *\n"
        "Allow: /\n\n"
        "# Block the legacy client-rendered template (superseded by /emotion/<slug>)\n"
        "Disallow: /emotion.html\n\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )


def render_legacy_redirect(emotions):
    """Keep old ?e=FOLDER links working: client-side 301-style redirect to the
    new clean URL. Marked noindex so search engines only index /emotion/<slug>."""
    mapping = {e["folder"]: e["slug"] for e in emotions}
    mapping_json = json.dumps(mapping, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="robots" content="noindex, follow" />
  <title>Redirecting… — Emotion Atlas</title>
  <link rel="canonical" href="{SITE_URL}/" />
  <script>
    (function () {{
      var MAP = {mapping_json};
      var e = new URLSearchParams(location.search).get("e");
      var slug = e && MAP[e] ? MAP[e] : null;
      location.replace(slug ? "/emotion/" + slug : "/");
    }})();
  </script>
</head>
<body>
  <p>Redirecting to the Emotion Atlas… <a href="/">Continue</a>.</p>
</body>
</html>
"""


def render_webmanifest():
    return json.dumps({
        "name": SITE_NAME,
        "short_name": SITE_NAME,
        "description": DEFAULT_DESC,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#faf7f2",
        "theme_color": "#faf7f2",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# Icons + default OG image (generated from brand/logo-globe.png)
# --------------------------------------------------------------------------
def make_icons():
    logo_path = os.path.join(BRAND_DIR, "logo-globe.png")
    if not os.path.exists(logo_path):
        print("!! brand/logo-globe.png missing — skipping icon generation")
        return
    logo = Image.open(logo_path).convert("RGBA")

    def square(size, bg):
        canvas = Image.new("RGBA", (size, size), bg)
        pad = int(size * 0.12)
        target = size - 2 * pad
        lw, lh = logo.size
        scale = min(target / lw, target / lh)
        nw, nh = int(lw * scale), int(lh * scale)
        resized = logo.resize((nw, nh), Image.LANCZOS)
        canvas.paste(resized, ((size - nw) // 2, (size - nh) // 2), resized)
        return canvas

    bg = BG_COLOR + (255,)
    square(32, bg).convert("RGB").save(os.path.join(BASE, "favicon-32x32.png"))
    square(180, bg).convert("RGB").save(os.path.join(BASE, "apple-touch-icon.png"))
    square(192, bg).convert("RGB").save(os.path.join(BASE, "icon-192.png"))
    square(512, bg).convert("RGB").save(os.path.join(BASE, "icon-512.png"))
    # Multi-resolution .ico
    ico = square(64, bg).convert("RGBA")
    ico.save(os.path.join(BASE, "favicon.ico"),
             sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    # Default 1200x630 Open Graph image: logo centred on brand background.
    og = Image.new("RGB", (1200, 630), BG_COLOR)
    target = 380
    lw, lh = logo.size
    scale = min(target / lw, target / lh)
    nw, nh = int(lw * scale), int(lh * scale)
    resized = logo.resize((nw, nh), Image.LANCZOS)
    og.paste(resized, ((1200 - nw) // 2, (630 - nh) // 2 - 40),
             resized if resized.mode == "RGBA" else None)
    og.save(os.path.join(BASE, "og-default.png"))
    print("Generated favicons, apple-touch-icon, icon-192/512, favicon.ico, og-default.png")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def write(path, content):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True) if os.path.dirname(full) else None
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    emotions = load_emotions()
    guides = load_guides()

    # Build-time data (kept for future search / tooling; not fetched at runtime)
    data = {"emotions": [{k: v for k, v in e.items()} for e in emotions],
            "guides": guides, "guideDir": "guide"}
    write("manifest.json", json.dumps(data, ensure_ascii=False, indent=2))

    # Icons + OG
    make_icons()

    # Homepage
    write("index.html", render_home(emotions, guides))

    # Emotion pages at clean URLs
    for i, e in enumerate(emotions):
        write(os.path.join("emotion", e["slug"], "index.html"), render_emotion(e, i))

    # Error pages
    write("404.html", render_error(404, "Page not found",
          "We couldn't find that page. It may have moved, or the link may be incomplete."))
    write("500.html", render_error(500, "Something went wrong",
          "An unexpected error occurred on our end. Please try again in a moment."))

    # Legacy ?e= redirect stub (backwards compatibility)
    write("emotion.html", render_legacy_redirect(emotions))

    # Crawl / indexing / PWA
    write("sitemap.xml", render_sitemap(emotions))
    write("robots.txt", render_robots())
    write("site.webmanifest", render_webmanifest())

    print(f"Built {len(emotions)} emotion pages + homepage, "
          f"{len(guides)} guides, sitemap ({len(emotions)+1} urls), robots, error pages.")


if __name__ == "__main__":
    main()
