#!/usr/bin/env python3
"""Instagram Reel / YouTube Short (1080x1920) from real clips, driven by one reel.json.

  python3 reel_build.py reel.json --check              # validate the project
  python3 reel_build.py reel.json --dry-run            # validate every ffmpeg graph on null inputs; writes nothing
  python3 reel_build.py reel.json overlays             # masthead/credit, captions and outro as PNGs to look at
  python3 reel_build.py reel.json copy                 # caption + Shorts copy file only
  python3 reel_build.py reel.json --preview --detach   # fast review cut (no AI)
  python3 reel_build.py reel.json --detach             # AI master
  python3 reel_build.py reel.json --monitor [--preview] [--restart N]

Stages: overlays, clean, audio, segments, video, mux, qc, copy. Uses the long-format engine's tools
(AI upscaler, audio clean-up, loudness mastering, fonts) from ../../youtube-longform-edit/tools.
"""
import argparse, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

LONG = Path(__file__).resolve().parents[2] / "youtube-longform-edit" / "tools"
sys.path.insert(0, str(LONG))

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import build as lf  # noqa: E402
import make_cards as mc  # noqa: E402
from common import BT709, TAG, TO709, ROOT, C, Brand, FONT_BODY, FONT_TITLE, even, fmt_time, probe, run  # noqa: E402
from brand.tokens import fmt as brand_format  # noqa: E402

DEFAULTS = {
    "resolution": [1080, 1920],
    "fps": 30,
    "upscale": "ai",
    "ai_denoise": 0.5,
    "denoise_filter": "hqdn3d=1.2:1.0:6:4",
    "grade": ("eq=contrast=1.10:brightness=0.02:saturation=1.18:gamma=0.97,"
              "colorbalance=rs=0.03:gs=0.0:bs=-0.03:rm=0.02:gm=0.0:bm=-0.02:rh=0.02:gh=0.0:bh=-0.03"),
    "cut": 0.12,
    "hero_zoom": 0.055,
    "vignette": 0.3,
    "encode": {"preset": "medium", "crf": 17, "maxrate": 25},
    "logo": "assets/logo_clean_circle.png",
    "masthead": {"date": None, "time": None, "scale": 0.92, "rule": True, "on_outro": False},
    "credit_lines": [],
    "captions": [],
    "outro": {"dur": 2.2, "bg": None, "title": Brand.name, "line": f"Follow {Brand.handle}"},
    "audio": {"real_lufs": -18.0, "real_max_gain_db": 10.0, "real_gain": 1.0, "master_lufs": -13.0, "true_peak": -1.5},
    "music": None,
    "copy": {},
}
STAGES = ["overlays", "clean", "audio", "segments", "video", "mux", "qc", "copy"]
ENGAGEMENT_YT = "ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ."


# ---------------------------------------------------------------- config & timeline

def load_config(path, preview=False):
    path = Path(path) if Path(path).is_absolute() else (Path.cwd() / path).resolve()
    raw = json.loads(path.read_text())
    cfg = json.loads(json.dumps(DEFAULTS))
    for k, v in raw.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    cfg["project_file"] = path
    cfg["footage"] = ROOT / cfg["footage_dir"]
    cfg["work"] = ROOT / cfg.get("work_dir", f"{cfg['footage_dir']}/_work/reel")
    cfg["output"] = ROOT / cfg.get("output_dir", f"{cfg['footage_dir']}/output")
    cfg["suffix"] = ""
    if preview:
        cfg.update(upscale="grade", suffix="_preview")
        # Hardware encode for the preview only — see video_codec(). The reel
        # master stays on libx264 because Instagram re-encodes what we upload,
        # and handing a transcoder an already-soft hardware encode compounds.
        cfg["encode"] = {"preset": "veryfast", "crf": 20, "maxrate": 25, "hw": True}
        cfg["work"] = cfg["work"] / "preview"
    return cfg


def has_videotoolbox():
    """Is Apple's hardware H.264 encoder available on this machine?"""
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                             capture_output=True, text=True, timeout=15).stdout
        return "h264_videotoolbox" in out
    except Exception:
        return False


def video_codec(enc):
    """Hardware for previews, software for the file that gets uploaded.

    VideoToolbox runs on Apple's media engine instead of the CPU, so it does
    not fight the renderer for unified memory — on 8 GB that is what keeps a
    preview from becoming a swap storm. The master stays on libx264: Instagram
    transcodes every upload, and stacking a hardware encode under a platform
    re-encode shows up as mush in exactly the dark, detailed frames a temple
    or a night harbour is made of.
    """
    if enc.get("hw") and has_videotoolbox():
        crf = int(enc.get("crf", 20))
        mbps = max(6, min(40, round(12 * (1.12 ** (20 - crf)))))
        return ["-c:v", "h264_videotoolbox", "-b:v", f"{mbps}M",
                "-profile:v", "high", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", enc["preset"], "-crf", enc["crf"],
            "-maxrate", f"{enc['maxrate']}M", "-bufsize", f"{enc['maxrate'] * 2}M",
            "-profile:v", "high"]


def ensure(p):
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe(cfg):
    W = cfg["resolution"][0]
    return [v * W / 1080 for v in brand_format("reel").safe]


def items_of(cfg):
    items = [dict(s, kind="seg") for s in cfg["segments"]]
    items.append({"kind": "card", "name": "outro", "dur": float(cfg["outro"]["dur"])})
    for it in items:
        if it["kind"] == "seg":
            it["dur"] = round(float(it["out"]) - float(it["in"]), 3)
    return items


def timeline(cfg):
    items = items_of(cfg)
    juncs = [None] + [tuple(items[j].get("transition_in") or ("fade", cfg["cut"])) for j in range(1, len(items))]
    starts, running = [0.0], items[0]["dur"]
    for j in range(1, len(items)):
        t = float(juncs[j][1])
        if t >= min(items[j - 1]["dur"], items[j]["dur"]):
            raise SystemExit(f"transition {t}s into item {j} is longer than a neighbouring shot")
        starts.append(running - t)
        running += items[j]["dur"] - t
    return items, juncs, starts, running


def framing(info, it, W, H):
    """(crop_w, crop_h, x, y, blur_fill) for a 9:16 canvas."""
    w, h = info["w"], info["h"]
    if it.get("fill") == "blur":
        return even(w), even(h), 0, 0, True
    if w * H >= h * W:
        cw, ch = even(h * W / H), even(h)
    else:
        cw, ch = even(w), even(w * H / W)
    x = even((w - cw) * float(it.get("frame_x", 0.5)))
    y = even((h - ch) * float(it.get("frame_y", 0.5)))
    return cw, ch, x, y, False


def blur_fill(W, H):
    return (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"gblur=sigma={W / 27:.0f},eq=brightness=-0.12:saturation=0.9[bg];"
            f"[b]scale={W}:-2:flags=lanczos[fg];[bg][fg]overlay=0:(H-h)/2")


def push_in(cfg, it, W, H):
    n = max(round(it["dur"] * cfg["fps"]) - 1, 1)
    return (f"zoompan=z='1+{cfg['hero_zoom']}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d=1:s={W}x{H}:fps={cfg['fps']}")


def seg_plan(cfg, it, info):
    """Everything needed to render one shot: crop, AI sizes, the post filter and the grade-mode filter."""
    W, H = cfg["resolution"]
    cw, ch, x, y, blur = framing(info, it, W, H)
    hero = bool(it.get("hero")) and not blur
    geo = blur_fill(W, H) if blur else (push_in(cfg, it, W, H) if hero else "")
    grade = f"{cfg['grade']},format=yuv420p"
    size = None if blur else ((W * 2, H * 2) if hero else (W, H))
    post = ",".join(p for p in (geo, grade) if p)
    scale = f"scale={size[0]}:{size[1]}:flags=lanczos+accurate_rnd+full_chroma_int" if size else ""
    grade_vf = ",".join(p for p in (f"fps={cfg['fps']}", cfg["denoise_filter"], f"crop={cw}:{ch}:{x}:{y}", scale,
                                    geo, "cas=strength=0.5", grade, "setsar=1", TAG) if p)
    return {"crop": (cw, ch, x, y), "size": size, "post": post, "grade_vf": grade_vf, "blur": blur, "hero": hero}


def seg_path(cfg, it):
    W, H = cfg["resolution"]
    k = lf._h(it["clip"], it["in"], it["out"], cfg["upscale"], cfg["ai_denoise"], W, H, cfg["fps"], cfg["grade"],
              cfg["denoise_filter"], bool(it.get("hero")), it.get("frame_x"), it.get("frame_y"), it.get("fill"),
              cfg["hero_zoom"])
    return cfg["work"] / "segs" / f"{Path(it['clip']).stem}_{float(it['in']):g}-{float(it['out']):g}_{k}.mp4"


def outro_png(cfg):
    return cfg["work"] / "cards" / "outro.png"


def outro_clip(cfg):
    png = outro_png(cfg)
    digest = hashlib.sha1(png.read_bytes()).hexdigest()[:10] if png.exists() else "none"
    return cfg["work"] / "cards" / f"outro_{lf._h(digest, cfg['resolution'], cfg['fps'], cfg['outro']['dur'])}.mp4"


def final_path(cfg):
    W, H = cfg["resolution"]
    return cfg["output"] / f"{cfg['title_slug']}_{W}x{H}{cfg['suffix']}.mp4"


def set_stage(cfg, stage, **kw):
    ensure(cfg["work"])
    lf.set_stage(cfg, stage, **kw)


def validate(cfg):
    problems, notes = [], []
    for key in ("title_slug", "footage_dir", "segments"):
        if not cfg.get(key):
            problems.append(f"missing '{key}'")
    m = cfg["masthead"]
    if m.get("date"):
        try:
            time.strptime(m["date"], "%Y-%m-%d")
        except ValueError:
            problems.append("masthead.date must be YYYY-MM-DD")
    else:
        notes.append("masthead.date is empty - top-right date will be blank")
    if m.get("time") and not re.fullmatch(r"\d{1,2}:\d{2}", m["time"]):
        problems.append("masthead.time must be HH:MM")
    W, H = cfg["resolution"]
    for n, it in enumerate(cfg["segments"]):
        clip = cfg["footage"] / it["clip"]
        if not clip.exists():
            problems.append(f"clip not found: {clip}")
            continue
        info = probe(clip)
        if not 0 <= float(it["in"]) < float(it["out"]) <= info["duration"] + 0.05:
            problems.append(f"{it['clip']}: in/out {it['in']}-{it['out']} outside 0-{info['duration']:.2f}s")
        cw, ch, _, _, blur = framing(info, it, W, H)
        if not blur and cw * ch < 0.4 * info["w"] * info["h"]:
            notes.append(f"segment {n} ({it['clip']}): 9:16 crop keeps only {100 * cw * ch / (info['w'] * info['h']):.0f}% "
                         f"of the frame - set frame_x or use \"fill\": \"blur\"")
        if float(it["out"]) - float(it["in"]) > 7:
            notes.append(f"segment {n}: {float(it['out']) - float(it['in']):.1f}s shot - reels rarely hold over 7 s")
    if cfg["segments"] and float(cfg["segments"][0]["out"]) - float(cfg["segments"][0]["in"]) > 2.5:
        notes.append("first shot is longer than 2.5 s - the hook should land in 1.5 s")
    if cfg.get("music") and not (ROOT / cfg["music"]["file"]).exists():
        problems.append(f"music file not found: {cfg['music']['file']}")
    if cfg.get("music") and not cfg["music"].get("license"):
        problems.append("music.license is empty - record source and licence first")
    if not (ROOT / cfg["logo"]).exists():
        problems.append(f"logo not found: {cfg['logo']}")
    if len(cfg["credit_lines"]) > 2:
        problems.append("credit_lines takes at most 2 lines")
    for cap in cfg["captions"]:
        if not 0 <= cap["segment"] < len(cfg["segments"]):
            problems.append(f"caption points at segment {cap['segment']} which does not exist")
        if len(cap["text"]) > 40:
            notes.append(f"caption '{cap['text'][:20]}...' is long for a reel (>40 characters)")
    title = cfg["copy"].get("shorts_title") or cfg["copy"].get("headline", "")
    if cfg["copy"] and len(title) > 60:
        notes.append(f"Shorts title is {len(title)} characters - keep it under 60")
    if cfg["copy"] and not cfg["copy"].get("headline"):
        problems.append("copy.headline is required when a copy block is given")
    if problems:
        raise SystemExit("project invalid:\n  - " + "\n  - ".join(problems))
    items, _, _, total = timeline(cfg)
    if total > 90:
        raise SystemExit(f"runtime {total:.1f}s is over 90 s - cut it down for a reel")
    if total > 60 or total < 10:
        notes.append(f"runtime {total:.1f}s - aim for 30-45 s")
    frames = sum(round(it["dur"] * cfg["fps"]) for it in items if it["kind"] == "seg")
    for n in notes:
        print("NOTE:", n, flush=True)
    print(f"reel ok: {len(cfg['segments'])} shots, runtime {total:.1f}s, {frames} frames, "
          f"mode={cfg['upscale']} {W}x{H}", flush=True)


# ---------------------------------------------------------------- overlays (PNG)

def shadow_text(img, text, font, cx, y_top, fill):
    d = ImageDraw.Draw(img)
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    x, y = cx - (r - l) / 2 - l, y_top - t
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((x + 3, y + 5), text, font=font, fill=(0, 0, 0, 200))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(img).text((x, y), text, font=font, fill=fill)
    return b - t


def text_height(text, font):
    l, t, r, b = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=font)
    return b - t


def stage_overlays(cfg):
    from brand.components import masthead
    from brand.surface import Surface, scrim
    set_stage(cfg, "overlays")
    cards = ensure(cfg["work"] / "cards")
    W, H = cfg["resolution"]
    fs = W / 1080
    sl, st, sr, sb = safe(cfg)
    m = cfg["masthead"]

    sf = Surface(W, H, 2, bg=(0, 0, 0, 0))
    scrim(sf, 0, st + 30 * fs, C.ink_950, 0.62, 0.0, curve=1.5)
    if cfg["credit_lines"]:
        scrim(sf, H - sb - 420 * fs, H, C.ink_950, 0.0, 0.62, curve=1.4)
    top, bot = mc._date_lines(m)
    masthead(sf, sl, st - 118 * fs, W - 2 * sl, right_top=m.get("right_top", top), right_bot=m.get("right_bot", bot),
             scale=m["scale"] * fs, on_photo=True, rule_below=m["rule"])
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if cfg["vignette"]:
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).ellipse([-W * 0.2, -H * 0.08, W * 1.2, H * 1.08], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(W * 0.12))
        layer = Image.new("RGBA", (W, H), C.ink_950 + (255,))
        layer.putalpha(mask.point(lambda v: int((255 - v) * cfg["vignette"])))
    layer.alpha_composite(sf.img.resize((W, H), Image.LANCZOS))

    # Centred on the frame like the posted reel; the width cap keeps the right edge clear of the button column.
    cx, max_w = W / 2, W - 2 * 112 * fs
    lines = cfg["credit_lines"]
    if lines:
        fonts = [mc.fitted(lines[0], FONT_TITLE, 48 * fs, max_w)]
        if len(lines) > 1:
            fonts.append(mc.fitted(lines[1], FONT_BODY, 44 * fs, max_w, weight=500))
        heights = [text_height(t, f) for t, f in zip(lines, fonts)]
        y = H - sb - 30 * fs - sum(heights) - 18 * fs * (len(lines) - 1)
        for k, (t, f) in enumerate(zip(lines, fonts)):
            y += shadow_text(layer, t, f, cx, y, (C.gold_400 if k == 0 else C.paper_50) + (255,)) + 18 * fs
    layer.save(cards / "overlay.png")

    for k, cap in enumerate(cfg["captions"]):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        f = mc.fitted(cap["text"], FONT_TITLE, 62 * fs, max_w)
        if f.size < 44 * fs:
            print(f"NOTE: caption {k} shrank to {f.size:.0f}px to fit - shorten it", flush=True)
        shadow_text(img, cap["text"], f, cx, H * 0.60 - text_height(cap["text"], f) / 2, C.paper_50 + (255,))
        img.save(cards / f"caption_{k}.png")

    o = cfg["outro"]
    seg = cfg["segments"][-1]
    clip, t = o.get("bg") or [seg["clip"], (float(seg["in"]) + float(seg["out"])) / 2]
    info = probe(cfg["footage"] / clip)
    cw, ch, x, y, _ = framing(info, {}, W, H)
    t = min(max(float(t), 0.0), max(info["duration"] - 0.1, 0.0))
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", cfg["footage"] / clip, "-frames:v", "1",
         "-vf", f"crop={cw}:{ch}:{x}:{y},scale={W}:{H}:flags=lanczos", cards / "outro_bg.png"], log=False)
    img = mc.backdrop(cards / "outro_bg.png", W, H)
    d = int(400 * fs)
    mc.paste_logo(img, ROOT / cfg["logo"], d, W // 2, int(560 * fs))
    draw = ImageDraw.Draw(img)
    y = int(560 * fs) + d + int(50 * fs)
    y = mc.centred(draw, o["title"], mc.fitted(o["title"], FONT_TITLE, 64 * fs, max_w), y, W, C.gold_400) + int(40 * fs)
    mc.centred(draw, o["line"], mc.fitted(o["line"], FONT_BODY, 46 * fs, max_w, weight=500), y, W, C.paper_50)
    img.convert("RGB").save(outro_png(cfg))
    for p in [cards / "overlay.png", *(cards / f"caption_{k}.png" for k in range(len(cfg["captions"]))), outro_png(cfg)]:
        print("overlay:", p, flush=True)


def outro_clip_render(cfg):
    W, H = cfg["resolution"]
    fps, dur = cfg["fps"], cfg["outro"]["dur"]
    out = outro_clip(cfg)
    if out.exists():
        return
    frames = round(dur * fps)
    vf = (f"scale={W * 2}:{H * 2}:flags=lanczos,"
          f"zoompan=z='1+0.04*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={fps},"
          f"{TO709},format=yuv420p,{TAG}")
    run(["ffmpeg", "-y", "-v", "error", "-i", outro_png(cfg), "-vf", vf, "-frames:v", frames,
         "-c:v", "libx264", "-preset", "medium", "-crf", "15", *BT709, out])


# ---------------------------------------------------------------- graphs (shared by the render and --dry-run)

def audio_graph(cfg, dry=False):
    items, juncs, starts, total = timeline(cfg)
    A, M = cfg["audio"], cfg.get("music")
    segs = [(j, it) for j, it in enumerate(items) if it["kind"] == "seg"]
    inputs, filt, labels = [], [], []
    for n, (j, it) in enumerate(segs):
        inputs += (["-f", "lavfi", "-t", str(it["dur"]), "-i", "anullsrc=r=48000:cl=stereo"] if dry
                   else ["-i", lf.aud_path(cfg, it)])
        fin = juncs[j][1] if j > 0 else 0.01
        fout = juncs[j + 1][1]
        filt.append(f"[{n}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,asetpts=N/SR/TB,"
                    f"afade=t=in:st=0:d={fin},afade=t=out:st={it['dur'] - fout:.3f}:d={fout},"
                    f"adelay={round(starts[j] * 1000)}:all=1,apad=whole_dur={total:.3f}[r{n}]")
        labels.append(f"[r{n}]")
    head = (f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,"
            if len(labels) > 1 else f"{labels[0]}anull,")
    filt.append(f"{head}atrim=0:{total:.3f},asetpts=N/SR/TB,"
                f"acompressor=threshold=-22dB:ratio=3:attack=5:release=200:makeup=1,"
                f"volume={A['real_gain']},alimiter=limit=0.95:level=false,asplit=2[key][real]")
    if M:
        offset = float(M.get("offset", 0))
        if dry:
            inputs += ["-f", "lavfi", "-t", str(offset + total + 1), "-i", "anullsrc=r=44100:cl=stereo"]
        else:
            mfile = ROOT / M["file"]
            if lf.media_duration(mfile) < offset + total:
                print("WARNING: music shorter than offset+runtime; it will loop with a seam", flush=True)
                inputs += ["-stream_loop", "-1"]
            inputs += ["-i", mfile]
        filt.append(f"[{len(segs)}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                    f"atrim=start={offset}:duration={total:.3f},asetpts=N/SR/TB,volume={M.get('level', 0.8)},"
                    f"afade=t=in:st=0:d=0.4,afade=t=out:st={total - 1.0:.3f}:d=1.0[mus]")
        if M.get("duck", True):
            filt.append("[mus][key]sidechaincompress=threshold=0.15:ratio=6:attack=5:release=180:makeup=1[bed]")
        else:
            filt.append("[key]anullsink;[mus]anull[bed]")
        filt.append("[bed][real]amix=inputs=2:duration=first:normalize=0[aout]")
    else:
        filt.append("[key]anullsink;[real]anull[aout]")
    return inputs, ";".join(filt), total


def video_graph(cfg, dry=False):
    items, juncs, starts, total = timeline(cfg)
    W, H = cfg["resolution"]
    fps, cards = cfg["fps"], cfg["work"] / "cards"
    null_rgba = ["-f", "lavfi", "-i", f"color=c=black@0.0:s={W}x{H}:r={fps}:d={total:.3f},format=rgba"]
    inputs = []
    for it in items:
        if dry:
            inputs += ["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps}:d={it['dur']},format=yuv420p"]
            continue
        p = outro_clip(cfg) if it["kind"] == "card" else seg_path(cfg, it)
        if not p.exists():
            raise SystemExit(f"missing {p.name} - run the overlays and segments stages first")
        inputs += ["-i", p]
    filt, prev, running = [], "0:v", items[0]["dur"]
    for j in range(1, len(items)):
        tr, t = juncs[j]
        filt.append(f"[{prev}][{j}:v]xfade=transition={tr}:duration={t}:offset={running - t:.4f}[x{j}]")
        running += items[j]["dur"] - t
        prev = f"x{j}"
    n = len(items)
    for k, cap in enumerate(cfg["captions"]):
        j = cap["segment"]
        st = starts[j] + (juncs[j][1] if j > 0 else 0) + cap.get("delay", 0.15)
        dur = cap.get("dur", 2.2)
        inputs += null_rgba if dry else ["-loop", "1", "-framerate", fps, "-t", f"{total:.3f}",
                                         "-i", cards / f"caption_{k}.png"]
        filt.append(f"[{n}:v]format=rgba,fade=t=in:st={st:.3f}:d=0.18:alpha=1,"
                    f"fade=t=out:st={st + dur - 0.18:.3f}:d=0.18:alpha=1,{TO709},format=yuva420p[c{k}]")
        filt.append(f"[{prev}][c{k}]overlay=0:0:eof_action=pass[o{k}]")
        prev, n = f"o{k}", n + 1
    inputs += null_rgba if dry else ["-i", cards / "overlay.png"]
    enable = "" if cfg["masthead"]["on_outro"] else f":enable='lt(t,{starts[-1]:.3f})'"
    filt.append(f"[{n}:v]format=rgba,{TO709},format=yuva420p[ov]")
    filt.append(f"[{prev}][ov]overlay=0:0{enable},format=yuv420p,{TAG}[vout]")
    return inputs, ";".join(filt), total


# ---------------------------------------------------------------- stages

def stage_clean(cfg):
    ensure(cfg["work"])
    lf.stage_clean(cfg, [it for it in items_of(cfg) if it["kind"] == "seg"])


def stage_audio(cfg):
    set_stage(cfg, "audio")
    work = cfg["work"]
    inputs, graph, total = audio_graph(cfg)
    premix, master = work / "premix.wav", work / "master_audio.wav"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[aout]",
         "-t", f"{total:.3f}", "-c:a", "pcm_s24le", "-ar", "48000", premix])
    report = lf.master_loudness(premix, master, cfg["audio"], lra=9)
    (work / "audio_report.json").write_text(json.dumps(report, indent=2))


def stage_segments(cfg):
    segs = [it for it in items_of(cfg) if it["kind"] == "seg"]
    ensure(cfg["work"] / "segs")
    for n, it in enumerate(segs):
        out = seg_path(cfg, it)
        if out.exists():
            continue
        set_stage(cfg, "segments", done=n, total=len(segs), current=it["clip"])
        clip = cfg["footage"] / it["clip"]
        plan = seg_plan(cfg, it, probe(clip))
        part = out.with_suffix(".part.mp4")
        cw, ch, x, y = plan["crop"]
        if cfg["upscale"] == "ai":
            size = ["--out-size", *plan["size"]] if plan["size"] else []
            run([sys.executable, LONG / "sr_upscale.py", clip, part, "--crop", f"{cw}:{ch}", "--crop-xy", f"{x}:{y}",
                 "--start", it["in"], "--duration", it["dur"], "--fps", cfg["fps"], "--denoise", cfg["ai_denoise"],
                 *size, "--post-vf", plan["post"]])
        else:
            run(["ffmpeg", "-y", "-v", "error", "-ss", it["in"], "-i", clip, "-t", it["dur"], "-vf", plan["grade_vf"],
                 "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "13", "-pix_fmt", "yuv420p", *BT709, part])
        frames = int(run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", part], capture=True, log=False).stdout.strip())
        expected = round(it["dur"] * cfg["fps"])
        if abs(frames - expected) > 1:
            raise SystemExit(f"{it['clip']} {it['in']}-{it['out']}: {frames} frames, expected {expected}")
        os.replace(part, out)


def stage_video(cfg):
    set_stage(cfg, "video", total=timeline(cfg)[3])
    outro_clip_render(cfg)
    inputs, graph, total = video_graph(cfg)
    E, fps, work = cfg["encode"], cfg["fps"], cfg["work"]
    progress = work / "progress_video.txt"
    progress.unlink(missing_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-nostats", "-progress", progress, *inputs, "-filter_complex", graph,
         "-map", "[vout]", "-t", f"{total:.3f}", "-r", fps, "-an", *video_codec(E),
         "-g", fps * 2, *BT709, "-movflags", "+faststart", work / "reel_video.mp4"])


def stage_mux(cfg):
    set_stage(cfg, "mux")
    ensure(cfg["output"])
    run(["ffmpeg", "-y", "-v", "error", "-i", cfg["work"] / "reel_video.mp4", "-i", cfg["work"] / "master_audio.wav",
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final_path(cfg)])
    print("final:", final_path(cfg), flush=True)


def stage_qc(cfg):
    set_stage(cfg, "qc")
    items, juncs, starts, total = timeline(cfg)
    W, H = cfg["resolution"]
    A, final, qc = cfg["audio"], final_path(cfg), ensure(cfg["work"] / "qc")
    rows = []

    def check(ok, name, detail):
        rows.append(("PASS" if ok is True else "WARN" if ok is None else "FAIL", name, str(detail)))

    info = probe(final)
    check(info["w"] == W and info["h"] == H, "resolution", f"{info['w']}x{info['h']}")
    check(abs(info["fps"] - cfg["fps"]) < 0.05, "frame rate", info["fps"])
    check(abs(info["duration"] - total) < 0.25, "duration", f"{info['duration']:.2f}s (timeline {total:.2f}s)")
    check(True if 10 <= info["duration"] <= 60 else (None if info["duration"] <= 90 else False),
          "reel length", f"{info['duration']:.1f}s (aim 30-45)")
    check(info["has_audio"], "audio stream", info["audio"])
    check(info["color"][0] == "bt709", "colour tags", info["color"])
    first = items[0]["dur"]
    check(True if first <= 2.5 else None, "hook shot", f"{first:.1f}s")
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", final, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
              capture=True, log=False).stderr
    i_lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)[-1])
    check(abs(i_lufs - A["master_lufs"]) <= 1.0, "loudness", f"{i_lufs} LUFS (target {A['master_lufs']})")
    check(tp <= -1.0, "true peak after AAC", f"{tp} dBTP (must be <= -1.0)")
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", final, "-an", "-vf",
               "scale=270:-2,blackdetect=d=0.4:pix_th=0.08", "-f", "null", "-"], capture=True, log=False).stderr
    bad = [(float(s), float(e)) for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)
           if float(s) < starts[-1] - 0.3]
    check(not bad, "no unexpected black", bad or "none")
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", final, "-vn", "-af", "silencedetect=noise=-50dB:d=1.5",
               "-f", "null", "-"], capture=True, log=False).stderr
    silences = re.findall(r"silence_start: ([\d.]+)", err)
    check(True if not silences else None, "no silences", silences or "none")

    times = {"hook": 0.3, "outro": starts[-1] + items[-1]["dur"] / 2}
    for k, cap in enumerate(cfg["captions"]):
        j = cap["segment"]
        times[f"caption {k}"] = starts[j] + (juncs[j][1] if j > 0 else 0) + cap.get("delay", 0.15) + cap.get("dur", 2.2) / 2
    for q in range(1, 6):
        times[f"content {q}"] = starts[-1] * q / 6
    tw, th = 270, 480
    sl, st, sr, sb = [v * tw / W for v in safe(cfg)]
    tiles = sorted(times.items(), key=lambda kv: kv[1])
    cols = 4
    sheet = Image.new("RGB", (cols * tw, ((len(tiles) + cols - 1) // cols) * (th + 24)), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    for k, (label, t) in enumerate(tiles):
        p = qc / f"{t:06.2f}.jpg"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", final, "-frames:v", "1", "-vf", f"scale={tw}:{th}", p],
            log=False)
        x0, y0 = (k % cols) * tw, (k // cols) * (th + 24) + 24
        tile = Image.open(p).convert("RGBA")
        guides = ImageDraw.Draw(tile)
        for line in ([(0, st), (tw, st)], [(0, th - sb), (tw, th - sb)], [(tw - sr, 0), (tw - sr, th)]):
            guides.line(line, fill=(255, 60, 60, 255), width=1)
        sheet.paste(tile.convert("RGB"), (x0, y0))
        d.text((x0 + 6, y0 - 18), f"{t:.1f}s {label}", fill=(255, 201, 60))
    sheet.save(qc / "qc_sheet.jpg", quality=90)
    report = [f"# Reel QC: {final.name}", "", "| result | check | detail |", "|---|---|---|"]
    report += [f"| {r} | {n} | {dtl} |" for r, n, dtl in rows]
    report += ["", f"Frame sheet: {qc / 'qc_sheet.jpg'} (red lines = Instagram safe zones: nothing important above "
                   "the top line, below the bottom line or right of the side line). Pick the cover frame here."]
    (qc / "qc_report.md").write_text("\n".join(report) + "\n")
    print("\n".join(f"{r:4s}  {n}: {dtl}" for r, n, dtl in rows), flush=True)
    if any(r == "FAIL" for r, _, _ in rows):
        raise SystemExit("QC FAILED - see qc_report.md")


def stage_copy(cfg):
    c = cfg["copy"]
    if not c:
        print("NOTE: no copy block - skipping copy file", flush=True)
        return
    ensure(cfg["output"])
    date_kn, day_line = mc._date_lines(cfg["masthead"])
    time_kn = day_line.split(" • ", 1)[1] if " • " in day_line else ""
    when = " · ".join(p for p in (date_kn, time_kn) if p)
    tags = c.get("hashtags", [])
    ig = [c["headline"], c.get("question", ""),
          "\n".join(p for p in (f"📍 {c.get('place', '')}  🕐 {when}".strip(),
                                f"ಸ್ಥಿತಿ: {c['status']}" if c.get("status") else "",
                                f"ಕೃಪೆ: {c['credit']}" if c.get("credit") else "",
                                f"📌 ಮೂಲ: {c['source']}" if c.get("source") else "") if p),
          Brand.grievance_line(), " ".join(tags)]
    title = c.get("shorts_title") or c["headline"]
    desc = [title, f"📍 {c.get('place', '')} · {date_kn}".strip(" ·"), f"{Brand.name} · {Brand.tagline}",
            c.get("music_credit", ""), " ".join(tags[:5] + ["#Shorts"]), ENGAGEMENT_YT]
    yt_tags = [t.lstrip("#") for t in tags] + [Brand.name, "Shorts"]

    def block(name, body):
        return f"═══ {name} {'═' * max(3, 64 - len(name))}\n\n{body}\n"

    text = "\n".join([
        block("INSTAGRAM REEL CAPTION", "\n\n".join(p for p in ig if p)),
        block("INSTAGRAM FIRST COMMENT (paste the moment you post)", c.get("first_comment", "")),
        block("YOUTUBE SHORTS TITLE", f"{title}\n({len(title)} characters)"),
        block("YOUTUBE SHORTS DESCRIPTION", "\n\n".join(p for p in desc if p)),
        block("YOUTUBE TAGS", ", ".join(yt_tags)),
    ])
    out = cfg["output"] / f"{cfg['title_slug']}_copy.txt"
    out.write_text(text)
    print("copy:", out, flush=True)


FUNCS = {"overlays": stage_overlays, "clean": stage_clean, "audio": stage_audio, "segments": stage_segments,
         "video": stage_video, "mux": stage_mux, "qc": stage_qc, "copy": stage_copy}


# ---------------------------------------------------------------- dry run & monitor

def dry_run(cfg):
    """Parse and link every filter graph against null inputs. Nothing is written."""
    W, H = cfg["resolution"]
    checked = set()
    for it in cfg["segments"]:
        info = probe(cfg["footage"] / it["clip"])
        p = seg_plan(cfg, dict(it, dur=round(float(it["out"]) - float(it["in"]), 3)), info)
        key = (info["w"], info["h"], p["hero"], p["blur"], p["size"], p["crop"])
        if key in checked:
            continue
        checked.add(key)
        cw, ch, _, _ = p["crop"]
        src = f"testsrc2=s={info['w']}x{info['h']}:r={cfg['fps']}:d=0.2"
        run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", src, "-vf", p["grade_vf"], "-f", "null", "-"], log=False)
        ai_in = f"{p['size'][0]}x{p['size'][1]}" if p["size"] else f"{cw * 4}x{ch * 4}"
        run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=s={ai_in}:r={cfg['fps']}:d=0.2", "-vf",
             f"format=yuv444p,{p['post']},{TAG}", "-f", "null", "-"], log=False)
    print(f"segment filters ok ({len(checked)} distinct shot setups, grade and AI paths)", flush=True)
    for name, fn, mp in (("video", video_graph, "[vout]"), ("audio", audio_graph, "[aout]")):
        inputs, graph, total = fn(cfg, dry=True)
        run(["ffmpeg", "-v", "error", *inputs, "-filter_complex", graph, "-map", mp, "-t", "0.5", "-f", "null", "-"],
            log=False)
        print(f"{name} graph ok ({total:.1f}s timeline)", flush=True)


def build_alive():
    out = subprocess.run(["ps", "-Ao", "pid,args"], capture_output=True, text=True).stdout
    return any("reels-shorts-edit/tools/reel_build.py" in line and "--monitor" not in line
               and int(line.split()[0]) != os.getpid() for line in out.splitlines()[1:])


def monitor(cfg, preview, restart):
    import monitor as lfm
    _, _, _, total = timeline(cfg)
    stage_file, fps = cfg["work"] / "stage.json", cfg["fps"]
    last_key, last_emit, restarts, gone = None, 0.0, 0, None
    while True:
        st = json.loads(stage_file.read_text()) if stage_file.exists() else {"stage": "not started"}
        stage = st["stage"]
        if stage == "done":
            lfm.say(f"DONE: {final_path(cfg)} - open qc/qc_sheet.jpg and qc_report.md before calling it ready")
            return
        if stage == "failed":
            log = cfg["work"] / "build.log"
            tail = log.read_text().strip().splitlines()[-6:] if log.exists() else []
            lfm.say(f"FAILED: {st.get('error')} | {' / '.join(tail)}")
            sys.exit(1)
        segs = [it for it in items_of(cfg) if it["kind"] == "seg"]
        done = sorted((seg_path(cfg, it).stat().st_mtime, round(it["dur"] * fps)) for it in segs if seg_path(cfg, it).exists())
        left = sum(round(it["dur"] * fps) for it in segs if not seg_path(cfg, it).exists())
        gaps = [(b[0] - a[0], b[1]) for a, b in zip(done, done[1:]) if 0 < b[0] - a[0] < 900][-5:]
        spf = sum(g for g, _ in gaps) / sum(f for _, f in gaps) if gaps else None
        if stage == "segments":
            line = (f"shots {len(done)}/{len(segs)}, {left} frames left, "
                    + (f"{spf:.2f} s/frame, ETA ~{fmt_time(left * spf)}" if spf else "ETA after 2 shots")
                    + "; then assembly")
            key = (stage, len(done))
        elif stage == "video":
            pos, eta = lfm.video_status(cfg, total)
            line = (f"assembly {100 * (pos or 0) / total:.0f}%, ETA {fmt_time(eta) if eta else 'measuring'}; "
                    f"then mux + QC (~1 min)")
            key = (stage, int((pos or 0) // (total / 5)))
        else:
            line, key = stage, (stage, st.get("done"))
        if not build_alive():
            gone = gone or time.time()
            if time.time() - gone > 45:
                if restarts < restart:
                    restarts += 1
                    subprocess.run([sys.executable, __file__, str(cfg["project_file"]), "--detach"]
                                   + (["--preview"] if preview else []), check=True)
                    lfm.say(f"build was gone (usually killed for memory); relaunched {restarts}/{restart}, cache kept")
                    gone = None
                    time.sleep(20)
                    continue
                lfm.say(f"STOPPED at '{stage}': build process gone. Relaunch with --detach; finished work is cached")
                sys.exit(2)
        else:
            gone = None
        if key != last_key or time.time() - last_emit >= 600:
            lfm.say(line)
            last_key, last_emit = key, time.time()
        time.sleep(15)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("stages", nargs="*", metavar="stage")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--detach", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--monitor", action="store_true")
    ap.add_argument("--restart", type=int, default=0)
    a = ap.parse_args()
    bad = [s for s in a.stages if s not in STAGES]
    if bad:
        ap.error(f"unknown stage(s) {bad}; choose from {STAGES}")
    cfg = load_config(a.project, a.preview)
    if a.monitor:
        return monitor(cfg, a.preview, a.restart)
    if a.detach:
        ensure(cfg["work"])
        log = cfg["work"] / "build.log"
        cmd = [sys.executable, str(Path(__file__).resolve()), str(cfg["project_file"]), *a.stages]
        cmd += ["--preview"] if a.preview else []
        with open(log, "a") as fh:
            fh.write(f"\n=== start {time.ctime()} {' '.join(cmd)} ===\n")
            fh.flush()
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    start_new_session=True)
        print(f"detached pid {proc.pid}; log {log}")
        print(f"watch: python3 {Path(__file__).resolve()} {cfg['project_file']} --monitor"
              f"{' --preview' if a.preview else ''} --restart 2")
        return
    validate(cfg)
    if a.check:
        return
    if a.dry_run:
        return dry_run(cfg)
    try:
        for s in a.stages or STAGES:
            FUNCS[s](cfg)
        if not a.stages or "mux" in a.stages:
            set_stage(cfg, "done", final=final_path(cfg))
    except SystemExit as e:
        if e.code not in (0, None):
            set_stage(cfg, "failed", error=str(e.code))
        raise


if __name__ == "__main__":
    main()
