#!/usr/bin/env python3
"""bento: build and render announcement bento grids. Standard library only.

    uv run python ~/.agents/skills/bento/scripts/bento.py make  spec.json [-o OUTDIR] [--scale 2]
    uv run python ~/.agents/skills/bento/scripts/bento.py build spec.json [-o OUTDIR]
    uv run python ~/.agents/skills/bento/scripts/bento.py render page.html [--scale 2] [-o out.png]
    uv run python ~/.agents/skills/bento/scripts/bento.py slots [canonical]

`make` builds a self-contained HTML page, checks every tile for overflow in
headless Chrome, then screenshots it. A tile that overflows fails the run
(exit 2) unless --allow-overflow is passed. See ../SKILL.md for the spec format.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

SKILL = pathlib.Path(__file__).resolve().parent.parent
ICON_CACHE = pathlib.Path(os.environ.get("BENTO_ICON_CACHE", "~/.cache/bento/lucide")).expanduser()
LUCIDE_URL = "https://unpkg.com/lucide-static@latest/icons/{name}.svg"
SI_CACHE = ICON_CACHE.parent / "simple-icons"
SI_URL = "https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{name}.svg"

TYPE_DEFAULT_TONE = {"stat": "light", "icon": "light", "logo": "light", "list": "dark",
                     "image": "none", "html": "light", "feature": "light", "statement": "light"}
ARRANGEMENTS = ("top", "bottom", "left", "right", "over")
BLEEDS = ("bottom", "right", "left", "edges")
DEVICES = ("phone", "tablet", "laptop")
TONES = {"light", "dark", "accent", "none"}


class BentoError(Exception):
    pass


# ----------------------------------------------------------------- loading

def load_json(path: pathlib.Path) -> dict:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise BentoError(f"{path}: invalid JSON, {e}") from e


def resolve_named(value, folder: str, base: pathlib.Path) -> tuple[dict, pathlib.Path]:
    """A theme or layout given inline, as a path relative to the spec, or by
    name from the skill's own folder. Returns the object and its directory."""
    if isinstance(value, dict):
        return value, base
    p = (base / value)
    if p.suffix != ".json" and not p.exists():
        p = p.with_suffix(".json")
    if not p.exists():
        p = SKILL / folder / f"{value}.json"
    if not p.exists():
        names = ", ".join(sorted(x.stem for x in (SKILL / folder).glob("*.json")))
        raise BentoError(f"no {folder[:-1]} named {value!r} (have: {names})")
    return load_json(p), p.parent


def data_uri(path: pathlib.Path) -> str:
    if not path.exists():
        raise BentoError(f"file not found: {path}")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if path.suffix == ".woff2":
        mime = "font/woff2"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def find_file(name: str, *dirs: pathlib.Path) -> pathlib.Path:
    p = pathlib.Path(name).expanduser()
    if p.is_absolute():
        return p
    for d in dirs:
        if (d / name).exists():
            return d / name
    return dirs[0] / name


# ----------------------------------------------------------------- icons

def fetch_icon(name: str, url: str, cache: pathlib.Path, source: str, hint: str, refresh: bool) -> str:
    """The inner SVG of an icon, fetched once and cached."""
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise BentoError(f"bad icon name {name!r}")
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / f"{name}.svg"
    if refresh or not cached.exists():
        req = urllib.request.Request(url.format(name=name), headers={"User-Agent": "bento-skill"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                cached.write_bytes(r.read())
        except Exception as e:  # noqa: BLE001
            raise BentoError(f"icon {name!r}: could not fetch from {source} ({e}); {hint}") from e
    svg = cached.read_text()
    m = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S)
    if not m:
        raise BentoError(f"icon {name!r}: unexpected SVG")
    return re.sub(r"<title>.*?</title>", "", m.group(1), flags=re.S).strip()


def lucide(name: str, refresh: bool = False) -> str:
    """A Lucide icon from lucide-static@latest, cached under ~/.cache/bento/lucide."""
    return fetch_icon(name, LUCIDE_URL, ICON_CACHE, "lucide-static",
                      "check the name at https://lucide.dev/icons or pass icon_svg", refresh)


def glyph(name: str, size: int, stroke: float = 1.5, refresh: bool = False) -> str:
    """An icon as SVG: a Lucide name (stroked) or "si:<slug>", a Simple Icons
    brand mark (filled, one colour). Both draw in currentColor."""
    if name.startswith("si:"):
        inner = fetch_icon(name[3:], SI_URL, SI_CACHE, "simple-icons",
                           "check the slug at https://simpleicons.org", refresh)
        return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="currentColor" '
                f'aria-hidden="true">{inner}</svg>')
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{lucide(name, refresh)}</svg>')


def icon_svg(tile: dict, size: int, refresh: bool) -> str:
    if tile.get("icon_svg"):
        return tile["icon_svg"]
    return glyph(tile["icon"], size, tile.get("icon_stroke", 1.5), refresh)


def app_icon(spec, size: int, refresh: bool) -> str:
    """An app icon: a glyph on a rounded square. `spec` is an icon name or
    {icon, color or colors (two or more make a vertical gradient), glyph
    (glyph colour), glyph_scale, stroke}."""
    spec = {"icon": spec} if isinstance(spec, str) else spec
    colors = spec.get("colors") or [spec.get("color", "var(--dark)")]
    bg = colors[0] if len(colors) == 1 else f"linear-gradient(180deg,{','.join(colors)})"
    g = glyph(spec["icon"], round(size * spec.get("glyph_scale", 0.56)), spec.get("stroke", 1.75), refresh)
    return (f'<span class="appicon" style="width:{size}px;height:{size}px;background:{bg};'
            f'color:{spec.get("glyph", "var(--on-dark)")}">{g}</span>')


# ----------------------------------------------------------------- layout

def tile_rect(tile: dict, slots: dict) -> list[int]:
    if "rect" in tile:
        r = tile["rect"]
        if not (isinstance(r, list) and len(r) == 4):
            raise BentoError(f"tile rect must be [x, y, w, h]: {r}")
        return [int(v) for v in r]
    slot = tile.get("slot")
    if slot not in slots:
        raise BentoError(f"unknown slot {slot!r}; layout has {', '.join(slots)}")
    return slots[slot]["rect"]


def validate(tiles: list[dict], rects: list[list[int]], canvas: tuple[int, int], slots: dict) -> list[str]:
    W, H = canvas
    warnings = []
    used = [t.get("slot") for t in tiles if "slot" in t]
    dupes = {s for s in used if used.count(s) > 1}
    if dupes:
        raise BentoError(f"slot used twice: {', '.join(sorted(dupes))}")
    for t, (x, y, w, h) in zip(tiles, rects):
        label = t.get("slot") or t.get("rect")
        if x < 0 or y < 0 or x + w > W or y + h > H:
            raise BentoError(f"tile {label} runs off the {W}x{H} canvas")
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, b = rects[i], rects[j]
            if a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]:
                raise BentoError(f"tiles {tiles[i].get('slot') or a} and {tiles[j].get('slot') or b} overlap")
    empty = [s for s in slots if s not in used]
    if empty:
        warnings.append(f"empty slots (left as canvas): {', '.join(empty)}")
    accents = sum(1 for t in tiles if t.get("tone", TYPE_DEFAULT_TONE.get(t.get("type"), "light")) == "accent")
    if accents > 1:
        warnings.append(f"{accents} accent tiles; one is the rule")
    return warnings


# ----------------------------------------------------------------- tiles

def esc(s) -> str:
    return html.escape(str(s), quote=False)


def rich(s) -> str:
    """Plain text, except **bold** and line breaks (\\n)."""
    out = esc(s)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    return out.replace("\n", "<br>")


def auto_figure_size(text: str, w: int, h: int, char_w: float, scale: float) -> int:
    longest = max((len(part) for part in str(text).split("\n")), default=1)
    by_width = (w - 56 * scale) / max(longest, 1) / char_w
    by_height = h * 0.42
    return int(max(36 * scale, min(by_width, by_height, 132 * scale)))


def fit_text_size(text: str, w: float, h: float, char_w: float, line_h: float, cap: float) -> int:
    """The largest font size at which every line of `text` fits w x h."""
    lines = str(text).split("\n")
    longest = max((len(x) for x in lines), default=1)
    return int(max(12, min(w / max(longest, 1) / char_w, h / (len(lines) * line_h), cap)))


def feature_visual(t: dict, scale: float, spec_dir: pathlib.Path, refresh: bool) -> str:
    """The visual half of a feature tile: one app icon, a row of them, a bare
    icon, an image or custom HTML."""
    if t.get("app"):
        return app_icon(t["app"], t.get("app_size", round(116 * scale)), refresh)
    if t.get("apps"):
        size = t.get("app_size", round(96 * scale))
        icons = "".join(app_icon(a, size, refresh) for a in t["apps"])
        return (f'<span class="apps" style="flex-direction:{t.get("apps_direction", "row")};'
                f'gap:{t.get("apps_gap", round(18 * scale))}px">{icons}</span>')
    if t.get("icon") or t.get("icon_svg"):
        color = f' style="color:{t["icon_color"]}"' if t.get("icon_color") else ""
        return f'<span class="ic"{color}>{icon_svg(t, t.get("icon_size", round(104 * scale)), refresh)}</span>'
    if t.get("src"):
        src = data_uri(find_file(t["src"], spec_dir))
        return (f'<img class="fimg" alt="{esc(t.get("alt", ""))}" src="{src}" '
                f'style="object-fit:{t.get("fit", "cover")};object-position:{t.get("position", "center")}">')
    if t.get("html_file"):
        return find_file(t["html_file"], spec_dir).read_text()
    if t.get("html"):
        return t["html"]
    raise BentoError(f"tile {t.get('slot')}: a feature needs a visual (app, apps, icon, src, html or html_file); "
                     f"use a statement tile for text alone")


def render_tile(t: dict, rect, theme: dict, scale: float, spec_dir: pathlib.Path, refresh: bool) -> str:
    x, y, w, h = rect
    kind = t.get("type")
    if kind not in TYPE_DEFAULT_TONE:
        raise BentoError(f"tile {t.get('slot')}: unknown type {kind!r} (use {', '.join(TYPE_DEFAULT_TONE)})")
    tone = t.get("tone", TYPE_DEFAULT_TONE[kind])
    if tone not in TONES:
        raise BentoError(f"tile {t.get('slot')}: unknown tone {tone!r}")
    align = t.get("align", "left" if kind in ("list", "html") else "center")
    if kind == "feature":
        arrange = t.get("arrange", "top")
        if arrange not in ARRANGEMENTS:
            raise BentoError(f"tile {t.get('slot')}: arrange must be one of {', '.join(ARRANGEMENTS)}")
        t = {**t, "class": f'{t.get("class", "")} arr-{arrange} place-{t.get("place", "top")}'}
    char_w = theme.get("display", {}).get("char_width", 0.5)
    cap_size = t.get("caption_size", round(28 * scale))
    classes = ["tile", f"tone-{tone}", f"type-{kind}", f"align-{align}"] + str(t.get("class", "")).split()
    style = f"left:{x}px;top:{y}px;width:{w}px;height:{h}px;"
    if t.get("background"):
        style += f"background:{t['background']};"
    style += t.get("style", "")
    name = esc(t.get("slot") or f"{x},{y}")
    body = []

    if kind == "stat":
        if t.get("label"):
            body.append(f'<p class="lab" style="font-size:{t.get("label_size", cap_size)}px">{rich(t["label"])}</p>')
        fs = t.get("figure_size") or auto_figure_size(t.get("figure", ""), w, h, char_w, scale)
        body.append(f'<p class="fig" style="font-size:{fs}px">{rich(t.get("figure", ""))}</p>')
        if t.get("caption"):
            body.append(f'<p class="cap" style="font-size:{cap_size}px">{rich(t["caption"])}</p>')
    elif kind == "icon":
        size = t.get("icon_size", round(88 * scale))
        body.append(f'<span class="ic">{icon_svg(t, size, refresh)}</span>')
        if t.get("figure"):
            fs = t.get("figure_size") or auto_figure_size(t["figure"], w, h * 0.6, char_w, scale)
            body.append(f'<p class="fig" style="font-size:{fs}px">{rich(t["figure"])}</p>')
        if t.get("caption"):
            body.append(f'<p class="cap" style="font-size:{cap_size}px">{rich(t["caption"])}</p>')
    elif kind == "logo":
        if t.get("src"):
            src = data_uri(find_file(t["src"], spec_dir))
            mw = t.get("max_width", w - 64 * scale)
            body.append(f'<img class="logo-img" alt="{esc(t.get("alt", ""))}" src="{src}" style="max-width:{mw}px">')
        else:
            fs = t.get("figure_size") or auto_figure_size(t.get("text", ""), w, h, char_w, scale)
            body.append(f'<p class="fig" style="font-size:{fs}px">{rich(t.get("text", ""))}</p>')
        if t.get("caption"):
            body.append(f'<p class="cap" style="font-size:{cap_size}px">{rich(t["caption"])}</p>')
    elif kind == "list":
        if t.get("eyebrow"):
            body.append(f'<p class="eyebrow">{rich(t["eyebrow"])}</p>')
        if t.get("title"):
            body.append(f'<p class="title" style="font-size:{t.get("title_size", round(64 * scale))}px">{rich(t["title"])}</p>')
        if t.get("subtitle"):
            body.append(f'<p class="subtitle">{rich(t["subtitle"])}</p>')
        if t.get("lines"):
            items = []
            for line in t["lines"]:
                line = {"text": line} if isinstance(line, str) else line
                st = f' style="color:{line["color"]}"' if line.get("color") else ""
                items.append(f"<li{st}>{rich(line['text'])}</li>")
            body.append(f'<ul class="lines" style="font-size:{t.get("line_size", round(28 * scale))}px">{"".join(items)}</ul>')
        if t.get("note"):
            body.append(f'<p class="note">{rich(t["note"])}</p>')
    elif kind == "image":
        src = data_uri(find_file(t["src"], spec_dir))
        pos = t.get("position", "center")
        body.append(f'<img class="fill" alt="{esc(t.get("alt", ""))}" src="{src}" style="object-position:{pos}">')
        if t.get("scrim"):
            body.append(f'<div class="scrim" style="background:rgba(0,0,0,{float(t["scrim"]):g})"></div>')
        ov = t.get("overlay")
        if ov:
            parts = []
            if ov.get("figure"):
                fs = ov.get("figure_size") or auto_figure_size(ov["figure"], w, h, char_w, scale)
                parts.append(f'<p class="fig" style="font-size:{fs}px">{rich(ov["figure"])}</p>')
            if ov.get("caption"):
                parts.append(f'<p class="cap" style="font-size:{ov.get("caption_size", cap_size)}px">{rich(ov["caption"])}</p>')
            where = ov.get("place", "center")
            body.append(f'<div class="overlay at-{where}" style="color:{ov.get("color", "#fff")}">{"".join(parts)}</div>')
    elif kind == "feature":
        text = ""
        if t.get("label"):
            text += f'<p class="flab" style="font-size:{t.get("label_size", round(28 * scale))}px">{rich(t["label"])}</p>'
        if t.get("sub"):
            text += f'<p class="fsub" style="font-size:{t.get("sub_size", round(22 * scale))}px">{rich(t["sub"])}</p>'
        bleed = t.get("bleed")
        if bleed is True:
            bleed = "bottom" if t.get("arrange", "top") == "top" else "edges"
        if bleed and bleed not in BLEEDS:
            raise BentoError(f"tile {t.get('slot')}: bleed must be true or one of {', '.join(BLEEDS)}")
        vcls = "fvis" + (f" bleed bleed-{bleed}" if bleed else "")
        if t.get("arrange") == "over" and not bleed:
            vcls += " bleed"  # an "over" visual fills the tile by design
        vstyle = f' style="{t["visual_style"]}"' if t.get("visual_style") else ""
        visual = feature_visual(t, scale, spec_dir, refresh)
        device = t.get("device")
        if device:
            if device not in DEVICES:
                raise BentoError(f"tile {t.get('slot')}: device must be one of {', '.join(DEVICES)}")
            dw = f' style="--dw:{t["device_width"]}"' if t.get("device_width") else ""
            visual = f'<div class="device device-{device}"{dw}><div class="screen">{visual}</div></div>'
        if text:
            body.append(f'<div class="ftext">{text}</div>')
        body.append(f'<div class="{vcls}"{vstyle}>{visual}</div>')
    elif kind == "statement":
        pad = 28 * scale
        font = t.get("font", "sans")
        cw = char_w if font == "display" else t.get("char_width", theme.get("statement", {}).get("char_width", 0.56))
        lh = 0.92 if font == "display" else 1.04
        sub_h = sum((t.get(k + "_size", cap_size) * 1.3 + 12 * scale) for k in ("sub", "eyebrow") if t.get(k))
        fs = t.get("size") or fit_text_size(t.get("text", ""), w - 2 * pad, (h - 2 * pad - sub_h) * 0.9,
                                            cw, lh, t.get("max_size", 140 * scale))
        # The tile's own colour wins; otherwise a theme may set a default for its
        # tone, e.g. Apple's blue gradient on light tiles.
        house = theme.get("statement", {}).get(tone, {}) if not (t.get("gradient") or t.get("color")) else {}
        gradient, color = t.get("gradient") or house.get("gradient"), t.get("color") or house.get("color")
        paint = ""
        if gradient:
            paint = (f"background:linear-gradient({t.get('angle', house.get('angle', '90deg'))},{','.join(gradient)});"
                     "-webkit-background-clip:text;background-clip:text;color:transparent;")
        elif color:
            paint = f"color:{color};"
        glow = t.get("glow", house.get("glow"))
        if glow:
            paint += f"filter:drop-shadow({glow});"
        if t.get("eyebrow"):
            body.append(f'<p class="cap eyb" style="font-size:{t.get("eyebrow_size", cap_size)}px">{rich(t["eyebrow"])}</p>')
        body.append(f'<p class="stm font-{font}" style="font-size:{fs}px;{paint}">{rich(t.get("text", ""))}</p>')
        if t.get("sub"):
            body.append(f'<p class="cap" style="font-size:{t.get("sub_size", cap_size)}px">{rich(t["sub"])}</p>')
    elif kind == "html":
        if t.get("html_file"):
            body.append(find_file(t["html_file"], spec_dir).read_text())
        else:
            body.append(t.get("html", ""))

    return f'<div class="{" ".join(classes)}" data-tile="{name}" style="{style}">{"".join(body)}</div>'


# ----------------------------------------------------------------- page

def font_faces(theme: dict, theme_dir: pathlib.Path) -> str:
    out = []
    for f in theme.get("fonts", {}).get("faces", []):
        path = find_file(f["file"], theme_dir, SKILL / "assets" / "fonts")
        uri = data_uri(path)
        fmt = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}.get(path.suffix, "woff2")
        decl = [f'font-family:"{f["family"]}"', f"src:url({uri}) format(\"{fmt}\")", "font-display:block"]
        if f.get("weight"):
            decl.append(f"font-weight:{f['weight']}")
        if f.get("stretch"):
            decl.append(f"font-stretch:{f['stretch']}")
        if f.get("style"):
            decl.append(f"font-style:{f['style']}")
        out.append("@font-face{" + ";".join(decl) + "}")
    return "\n".join(out)


BASE_CSS = """
*{box-sizing:border-box}
html,body{margin:0;width:var(--W);height:var(--H);background:var(--canvas)}
.canvas{position:relative;width:var(--W);height:var(--H);overflow:hidden;background:var(--canvas);color:var(--ink);
  font:400 calc(28px * var(--s))/1.2 var(--sans);font-synthesis:none;font-optical-sizing:auto;font-variant-numeric:tabular-nums;
  -webkit-font-smoothing:antialiased}
:where(.canvas) p{margin:0}
:where(.canvas) ul{margin:0;padding:0;list-style:none}
.tile{position:absolute;overflow:hidden;border-radius:var(--radius);padding:calc(24px * var(--s))}
.tone-light{background:var(--tile);color:var(--ink)}
.tone-dark{background:var(--dark);color:var(--on-dark)}
.tone-accent{background:var(--accent);color:var(--on-accent)}
.tone-none{background:none;border-radius:0;padding:0;overflow:visible}
.type-stat,.type-icon,.type-logo{display:flex;flex-direction:column;justify-content:center}
.align-center{align-items:center;text-align:center}
.align-left{align-items:flex-start;text-align:left}
.fig{font-family:var(--display-family);font-weight:var(--display-weight);font-stretch:var(--display-stretch);
  letter-spacing:var(--display-tracking);line-height:.92;font-variant-numeric:tabular-nums}
.fig b{font-weight:inherit}
.cap,.lab{line-height:1.2;text-wrap:balance}
.lab+.fig{margin-top:calc(6px * var(--s))}
.fig+.cap{margin-top:calc(10px * var(--s))}
.ic{display:block;line-height:0}
.ic+.cap,.ic+.fig{margin-top:calc(14px * var(--s))}
.tone-light .cap,.tone-light .lab{color:var(--ink)}
.tone-dark .cap,.tone-dark .lab{color:var(--on-dark-mute)}
.tone-accent .cap{font-weight:600}
.type-list{padding:calc(40px * var(--s))}
.type-list .eyebrow{font-weight:600;font-size:calc(30px * var(--s));margin-bottom:calc(18px * var(--s))}
.type-list .title{font-family:var(--display-family);font-weight:var(--display-weight);font-stretch:var(--display-stretch);
  letter-spacing:var(--display-tracking);line-height:.98}
.type-list .subtitle{margin-top:calc(10px * var(--s));font-weight:600;font-size:calc(28px * var(--s))}
.type-list .lines{margin-top:calc(22px * var(--s));line-height:1.32}
.type-list .note{margin-top:calc(22px * var(--s));font-size:calc(25px * var(--s));line-height:1.28;color:var(--on-dark-mute)}
.tone-light.type-list .note{color:var(--mute)}
.type-image{padding:0}
.type-image .fill{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.type-image .scrim{position:absolute;inset:0}
.overlay{position:absolute;left:0;right:0;padding:calc(32px * var(--s));display:flex;flex-direction:column;align-items:center;text-align:center}
.overlay.at-center{top:50%;transform:translateY(-50%)}
.overlay.at-bottom{bottom:0}
.overlay.at-top{top:0}
.logo-img{display:block;height:auto}
.type-html{padding:calc(40px * var(--s))}
.appicon{display:inline-flex;align-items:center;justify-content:center;flex:none;border-radius:22.5%;line-height:0}
.apps{display:flex;align-items:center;justify-content:center}
.type-feature{--pad:calc(28px * var(--s));display:flex;gap:calc(16px * var(--s));padding:var(--pad)}
.type-feature .ftext{flex:none;text-align:center}
.flab{margin:0;font-weight:600;line-height:1.14;letter-spacing:-.005em;text-wrap:balance}
.fsub{margin:calc(6px * var(--s)) 0 0;line-height:1.22;text-wrap:balance}
.tone-light .fsub{color:var(--mute)}
.tone-dark .fsub{color:var(--on-dark-mute)}
.fvis{position:relative;display:flex;align-items:center;justify-content:center;min-width:0;min-height:0;text-align:left}
.arr-top,.arr-bottom{flex-direction:column}
.arr-bottom{flex-direction:column-reverse}
.arr-top .fvis,.arr-bottom .fvis{flex:1;width:100%}
.arr-left{flex-direction:row;align-items:center}
.arr-right{flex-direction:row-reverse;align-items:center}
.arr-left .ftext,.arr-right .ftext{flex:1}
.arr-left .fvis,.arr-right .fvis{flex:none}
.arr-over{padding:0}
.arr-over .fvis{position:absolute;inset:0}
.arr-over .ftext{position:absolute;left:var(--pad);right:var(--pad);top:var(--pad);z-index:1}
.arr-over.place-bottom .ftext{top:auto;bottom:var(--pad)}
.fvis.bleed-bottom{margin-bottom:calc(-1 * var(--pad))}
.fvis.bleed-right{margin-right:calc(-1 * var(--pad))}
.fvis.bleed-left{margin-left:calc(-1 * var(--pad))}
.arr-top .fvis.bleed-edges{width:auto;align-self:stretch;margin:0 calc(-1 * var(--pad)) calc(-1 * var(--pad))}
.arr-bottom .fvis.bleed-edges{width:auto;align-self:stretch;margin:calc(-1 * var(--pad)) calc(-1 * var(--pad)) 0}
.arr-left .fvis.bleed-edges{align-self:stretch;margin:calc(-1 * var(--pad)) calc(-1 * var(--pad)) calc(-1 * var(--pad)) 0}
.arr-right .fvis.bleed-edges{align-self:stretch;margin:calc(-1 * var(--pad)) 0 calc(-1 * var(--pad)) calc(-1 * var(--pad))}
.fimg{display:block;width:100%;height:100%}
.type-statement{display:flex;flex-direction:column;justify-content:center;padding:calc(28px * var(--s))}
.stm{margin:0;font-weight:700;line-height:1.04;letter-spacing:-.02em;text-wrap:balance}
.stm.font-display{font-family:var(--display-family);font-weight:var(--display-weight);font-stretch:var(--display-stretch);
  letter-spacing:var(--display-tracking);line-height:.92}
.stm+.cap{margin-top:calc(12px * var(--s))}
.eyb{margin:0 0 calc(8px * var(--s))}
.tone-dark .eyb,.tone-dark .stm+.cap{color:var(--on-dark)}
.fvis.bleed-bottom{align-items:flex-start}
.device{position:relative;flex:none;background:#1d1d1f;padding:calc(9px * var(--s))}
.device .screen{width:100%;height:100%;overflow:hidden;background:var(--tile);color:var(--ink)}
.device-phone{width:var(--dw,46%);aspect-ratio:9/19.5;border-radius:calc(56px * var(--s))}
.device-phone .screen{border-radius:calc(47px * var(--s))}
.device-tablet{width:var(--dw,84%);aspect-ratio:4/3;border-radius:calc(30px * var(--s))}
.device-tablet .screen{border-radius:calc(21px * var(--s))}
.device-laptop{width:var(--dw,88%);aspect-ratio:16/10;border-radius:calc(18px * var(--s)) calc(18px * var(--s)) 0 0}
.device-laptop .screen{border-radius:calc(9px * var(--s)) calc(9px * var(--s)) 0 0}
"""

# Marks overflowing tiles on <html data-overflow="...">; `render` reads it back.
CHECK_JS = """
(function(){
  // A tile overflows when any of its content comes within 8 px (at the
  // 2000 px canvas) of the tile's edge, or past it: reaching into the
  // padding is fine, being clipped or touching the edge is not. Content
  // inside a .bleed visual is exempt: it is cropped by the tile on purpose.
  function check(){
    var s=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--s'))||1, inset=8*s, bad=[];
    document.querySelectorAll('[data-tile]').forEach(function(t){
      if(t.classList.contains('tone-none')) return;
      var r=t.getBoundingClientRect(), over=false;
      t.querySelectorAll('*').forEach(function(e){
        if(e.closest('.bleed')) return; // bleeding visuals run past the edge on purpose
        var q=e.getBoundingClientRect(); if(!q.width||!q.height) return;
        if(q.left<r.left+inset-.5||q.top<r.top+inset-.5||q.right>r.right-inset+.5||q.bottom>r.bottom-inset+.5) over=true;
      });
      if(over) bad.push(t.dataset.tile);
    });
    document.documentElement.setAttribute('data-overflow',bad.join(','));
    document.documentElement.setAttribute('data-checked','1');
  }
  // Timers, not requestAnimationFrame: headless --dump-dom advances virtual time but paints no frames.
  (document.fonts&&document.fonts.ready?document.fonts.ready:Promise.resolve()).then(function(){setTimeout(check,50)});
})();
"""


def build(spec_path: pathlib.Path, outdir: pathlib.Path | None, refresh_icons: bool = False) -> pathlib.Path:
    spec = load_json(spec_path)
    spec_dir = spec_path.parent
    theme, theme_dir = resolve_named(spec.get("theme", "neutral"), "themes", spec_dir)
    layout, _ = resolve_named(spec.get("layout", "canonical"), "layouts", spec_dir)
    W, H = layout["canvas"]
    slots = layout.get("slots", {})
    scale = W / 2000
    tiles = spec.get("tiles", [])
    if not tiles:
        raise BentoError("spec has no tiles")
    rects = [tile_rect(t, slots) for t in tiles]
    for w in validate(tiles, rects, (W, H), slots):
        print(f"warning: {w}", file=sys.stderr)

    c = theme["colors"]
    d = theme.get("display", {})
    fonts = theme.get("fonts", {})
    variables = {
        "--W": f"{W}px", "--H": f"{H}px", "--s": f"{scale:g}",
        "--canvas": c["canvas"], "--tile": c["tile"], "--ink": c["ink"], "--mute": c.get("mute", c["ink"]),
        "--dark": c["dark"], "--on-dark": c["on_dark"], "--on-dark-mute": c.get("on_dark_mute", c["on_dark"]),
        "--accent": c["accent"], "--on-accent": c["on_accent"],
        "--radius": f"{theme.get('radius', 32) * scale:g}px",
        "--sans": fonts.get("sans", "system-ui,sans-serif"),
        "--mono": fonts.get("mono", "ui-monospace,monospace"),
        "--display-family": d.get("family", fonts.get("sans", "system-ui,sans-serif")),
        "--display-weight": str(d.get("weight", 700)),
        "--display-stretch": d.get("stretch", "100%"),
        "--display-tracking": d.get("tracking", "-.01em"),
    }
    root = ":root{" + ";".join(f"{k}:{v}" for k, v in variables.items()) + "}"

    extra_css = ""
    for css in ([spec["css"]] if isinstance(spec.get("css"), str) else spec.get("css", [])):
        extra_css += "\n" + find_file(css, spec_dir).read_text()

    body = "\n".join(render_tile(t, r, theme, scale, spec_dir, refresh_icons) for t, r in zip(tiles, rects))
    title = esc(spec.get("title", spec.get("name", "Bento")))
    page = f"""<!doctype html>
<html lang="{esc(spec.get('lang', 'en'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={W}">
<meta name="bento:size" content="{W}x{H}">
<title>{title}</title>
<style>
{font_faces(theme, theme_dir)}
{root}
{BASE_CSS}
{theme.get('css', '')}
{extra_css}
</style>
</head>
<body>
<main class="canvas" role="img" aria-label="{esc(spec.get('alt', title))}">
{body}
</main>
<script>{CHECK_JS}</script>
</body>
</html>
"""
    outdir = outdir or spec_dir / "out"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{spec.get('name', spec_path.stem)}.html"
    out.write_text(page)
    print(f"built {out} ({len(page) // 1024} KiB, {W}x{H}, {len(tiles)} tiles)")
    return out


# ----------------------------------------------------------------- render

def find_chrome() -> str:
    env = os.environ.get("BENTO_CHROME")
    if env:
        return env
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    candidates += sorted(str(p) for p in pathlib.Path("~/Library/Caches/ms-playwright").expanduser()
                         .glob("chromium-*/chrome-mac*/*.app/Contents/MacOS/*"))
    candidates += [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    raise BentoError("no Chrome or Chromium found; set BENTO_CHROME to a browser binary")


def chrome(args: list[str], timeout: int = 90) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(prefix="bento-chrome-") as profile:
        cmd = [find_chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               "--no-default-browser-check", f"--user-data-dir={profile}", "--virtual-time-budget=6000"] + args
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:  # Chrome can linger after finishing; the caller checks output
            return subprocess.CompletedProcess(cmd, 124, e.stdout or "", e.stderr or "")


def page_size(page: pathlib.Path) -> tuple[int, int]:
    m = re.search(r'name="bento:size" content="(\d+)x(\d+)"', page.read_text())
    if not m:
        raise BentoError(f"{page} has no bento:size meta; build it with bento.py")
    return int(m.group(1)), int(m.group(2))


def check_overflow(page: pathlib.Path, W: int, H: int) -> list[str] | None:
    res = chrome([f"--window-size={W},{H}", "--dump-dom", page.resolve().as_uri()])
    m = re.search(r'<html[^>]*\bdata-overflow="([^"]*)"', res.stdout)
    if not m:
        return None
    return [s for s in m.group(1).split(",") if s]


def render(page: pathlib.Path, out: pathlib.Path | None, scale: float, allow_overflow: bool) -> pathlib.Path:
    W, H = page_size(page)
    bad = check_overflow(page, W, H)
    if bad is None:
        print("warning: overflow check did not run (no data-overflow on the page)", file=sys.stderr)
    elif bad:
        msg = f"overflowing tiles: {', '.join(bad)}"
        if not allow_overflow:
            raise BentoError(msg + " (shrink copy or sizes, or pass --allow-overflow)")
        print(f"warning: {msg}", file=sys.stderr)
    else:
        print("overflow check: clean")
    suffix = "" if scale == 1 else f"@{scale:g}x"
    out = out or page.with_name(f"{page.stem}{suffix}.png")
    if out.exists():
        out.unlink()
    chrome([f"--window-size={W},{H}", f"--force-device-scale-factor={scale:g}",
            f"--screenshot={out.resolve()}", page.resolve().as_uri()])
    if not out.exists() or out.stat().st_size == 0:
        raise BentoError(f"Chrome wrote no screenshot to {out}")
    print(f"rendered {out} ({int(W * scale)}x{int(H * scale)}, {out.stat().st_size // 1024} KiB)")
    return out


def slots(name: str) -> None:
    layout, _ = resolve_named(name, "layouts", SKILL / "layouts")
    W, H = layout["canvas"]
    print(f"{name}: {W}x{H}")
    for key, s in layout["slots"].items():
        x, y, w, h = s["rect"]
        print(f"  {key:5} {w:4}x{h:<4} at {x},{y}  {s.get('role', '')}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build and render announcement bento grids.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("make", "build"):
        p = sub.add_parser(cmd)
        p.add_argument("spec", type=pathlib.Path)
        p.add_argument("-o", "--outdir", type=pathlib.Path)
        p.add_argument("--refresh-icons", action="store_true", help="refetch cached Lucide and Simple Icons")
        if cmd == "make":
            p.add_argument("--scale", type=float, default=2)
            p.add_argument("--allow-overflow", action="store_true")
    p = sub.add_parser("render")
    p.add_argument("page", type=pathlib.Path)
    p.add_argument("-o", "--out", type=pathlib.Path)
    p.add_argument("--scale", type=float, default=2)
    p.add_argument("--allow-overflow", action="store_true")
    p = sub.add_parser("slots")
    p.add_argument("layout", nargs="?", default="canonical")
    a = ap.parse_args()
    try:
        if a.cmd == "build":
            build(a.spec, a.outdir, a.refresh_icons)
        elif a.cmd == "make":
            render(build(a.spec, a.outdir, a.refresh_icons), None, a.scale, a.allow_overflow)
        elif a.cmd == "render":
            render(a.page, a.out, a.scale, a.allow_overflow)
        else:
            slots(a.layout)
    except BentoError as e:
        print(f"bento: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
