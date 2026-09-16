#!/usr/bin/env python3
"""Long-format YouTube edit pipeline, driven by one project JSON.

  python3 build.py PROJECT.json --preview --detach   # fast 1080p review cut (no AI), in background
  python3 build.py PROJECT.json --detach             # AI 1440p master, in background
  python3 build.py PROJECT.json video mux qc         # re-run selected stages only
  python3 build.py PROJECT.json --check              # validate the project, render nothing

Stages: cards, clean, audio, segments, video, mux, qc. Segments, cleaned audio and card clips are
cached by a hash of their inputs, so a re-run after a crash or an edit only redoes what changed.
"""
import argparse, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

from common import (BT709, TAG, TO709, ROOT, TOOLS, Brand, crop_16x9, fit_filter, fmt_time, probe, run)

DEFAULTS = {
    "resolution": [2560, 1440],
    "fps": 30,
    "upscale": "ai",
    "ai_denoise": 0.5,
    "denoise_filter": "hqdn3d=1.5:1.2:6:4",
    "grade": ("eq=contrast=1.06:brightness=0.01:saturation=1.12:gamma=0.98,"
              "colorbalance=rs=0.025:bs=-0.025:rm=0.015:bm=-0.015:rh=0.015:bh=-0.02,vignette=PI/8"),
    "transitions": {"cut": 0.1, "jump": 0.5, "section": 0.8, "card_in": 1.0, "card_out": 1.2, "cold_to_intro": 0.8},
    "encode": {"preset": "medium", "crf": 15},
    "logo": "assets/logo_clean_circle.png",
    "masthead": {"date": None, "time": None, "scale": 1.05, "scrim": 0.62, "on_cards": True},
    "audio": {"real_lufs": -18.0, "real_max_gain_db": 10.0, "real_gain": 0.85, "master_lufs": -14.0, "true_peak": -1.0},
    "music": None,
    "cards": {"intro": {"dur": 5.0},
              "outro": {"dur": 7.0, "title": "ಧನ್ಯವಾದಗಳು",
                        "lines": [f"Subscribe · {Brand.name} · {Brand.handle}", Brand.tagline]}},
    "cold_open": [],
    "lower_thirds": [],
    "sections": {},
}
CLEAN = ("adeclip=w=55:o=75:a=8,highpass=f=90,lowpass=f=15000,afftdn=nf=-28:tn=1,"
         "acompressor=threshold=-18dB:ratio=2.5:attack=15:release=220:makeup=1")
STAGES = ["cards", "clean", "audio", "segments", "video", "mux", "qc"]


def has_videotoolbox():
    """Is Apple's hardware H.264 encoder available on this machine?"""
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                             capture_output=True, text=True, timeout=15).stdout
        return "h264_videotoolbox" in out
    except Exception:
        return False


def video_codec(enc):
    """The encoder arguments for this stage.

    Hardware (`h264_videotoolbox`) for previews: it runs on Apple's media
    engine rather than the CPU, leaving the unified memory to the renderer,
    and a preview's job is to be watched once and thrown away.

    Software (`libx264`) for masters: at CRF 14-15 it still carries more
    detail per bit than the hardware encoder, and gradients in a temple
    interior at night are exactly where that difference is visible. A master
    is encoded once and watched for years; the extra minutes are cheap.

    VideoToolbox takes a bitrate, not a CRF, so the CRF is mapped to one
    rather than silently dropped.
    """
    if enc.get("hw") and has_videotoolbox():
        crf = int(enc.get("crf", 18))
        # CRF 18 -> ~14 Mbps at 1080p30; each CRF step is roughly 12%.
        mbps = max(6, min(40, round(14 * (1.12 ** (18 - crf)))))
        return ["-c:v", "h264_videotoolbox", "-b:v", f"{mbps}M",
                "-profile:v", "high", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", enc["preset"], "-crf", enc["crf"],
            "-profile:v", "high"]


# ---------------------------------------------------------------- config & timeline

def load_config(path, preview=False):
    path = Path(path) if Path(path).is_absolute() else (Path.cwd() / path).resolve()
    if not path.exists():
        path = (ROOT / path.name).resolve()
    raw = json.loads(path.read_text())
    cfg = json.loads(json.dumps(DEFAULTS))
    for k, v in raw.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict) and k != "cards":
            cfg[k].update(v)
        elif k == "cards":
            for name, card in v.items():
                cfg["cards"].setdefault(name, {}).update(card)
        else:
            cfg[k] = v
    cfg["project_file"] = path
    cfg["footage"] = ROOT / cfg["footage_dir"]
    cfg["work"] = ROOT / cfg.get("work_dir", f"{cfg['footage_dir']}/_work")
    cfg["output"] = ROOT / cfg.get("output_dir", f"{cfg['footage_dir']}/output")
    cfg["suffix"] = ""
    if preview:
        cfg.update(upscale="grade", resolution=[1920, 1080], suffix="_preview")
        # A preview is thrown away the moment the client says yes or no, so it
        # is the one encode where speed is worth more than bits. VideoToolbox
        # is Apple's dedicated media engine: it does not compete with the
        # renderer for unified memory, and on this 8 GB M1 that is the
        # difference between a preview and a swap storm. The MASTER stays on
        # libx264 — at CRF 15 software x264 still beats hardware per bit, and
        # the master is the thing a viewer actually watches.
        cfg["encode"] = {"preset": "veryfast", "crf": 18, "hw": True}
        cfg["work"] = cfg["work"] / "preview"
    cfg["work"].mkdir(parents=True, exist_ok=True)
    cfg["output"].mkdir(parents=True, exist_ok=True)
    return cfg


def items_of(cfg):
    items = [dict(s, kind="seg", role="cold") for s in cfg["cold_open"]]
    items.append({"kind": "card", "name": "intro", "dur": float(cfg["cards"]["intro"]["dur"])})
    items += [dict(s, kind="seg", role="main") for s in cfg["segments"]]
    items.append({"kind": "card", "name": "outro", "dur": float(cfg["cards"]["outro"]["dur"])})
    for it in items:
        if it["kind"] == "seg":
            it["dur"] = round(float(it["out"]) - float(it["in"]), 3)
    return items


def junction(cfg, a, b):
    T = cfg["transitions"]
    if b.get("transition_in"):
        return tuple(b["transition_in"])
    if b["kind"] == "card":
        return ("fadeblack", T["card_out"] if b["name"] == "outro" else T["cold_to_intro"])
    if a["kind"] == "card":
        return ("fadeblack", T["card_in"])
    if a["clip"] == b["clip"]:
        return ("fade", T["jump"])
    if a.get("section") != b.get("section"):
        return ("fade", T["section"])
    return ("fade", T["cut"])


def timeline(cfg):
    items = items_of(cfg)
    juncs = [None] + [junction(cfg, items[j - 1], items[j]) for j in range(1, len(items))]
    starts, running = [0.0], items[0]["dur"]
    for j in range(1, len(items)):
        t = float(juncs[j][1])
        if t >= min(items[j - 1]["dur"], items[j]["dur"]):
            raise SystemExit(f"transition {t}s into item {j} is longer than a neighbouring shot")
        starts.append(running - t)
        running += items[j]["dur"] - t
    return items, juncs, starts, running


def _h(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:10]


def seg_path(cfg, it):
    W, H = cfg["resolution"]
    k = _h(it["clip"], it["in"], it["out"], cfg["upscale"], cfg["ai_denoise"], W, H, cfg["fps"], cfg["grade"],
           cfg["denoise_filter"])
    return cfg["work"] / "segs" / f"{Path(it['clip']).stem}_{float(it['in']):g}-{float(it['out']):g}_{k}.mp4"


def aud_path(cfg, it):
    A = cfg["audio"]
    k = _h(it["clip"], it["in"], it["out"], CLEAN, A["real_lufs"], A["real_max_gain_db"])
    return cfg["work"] / "audio" / f"{Path(it['clip']).stem}_{float(it['in']):g}-{float(it['out']):g}_{k}.wav"


def card_png(cfg, name):
    return cfg["work"] / "cards" / f"{name}.png"


def card_clip(cfg, name, dur):
    png = card_png(cfg, name)
    digest = hashlib.sha1(png.read_bytes()).hexdigest()[:10] if png.exists() else "none"
    return cfg["work"] / "cards" / f"{name}_{_h(digest, cfg['resolution'], cfg['fps'], dur)}.mp4"


def final_path(cfg):
    return cfg["output"] / f"{cfg['title_slug']}_{cfg['resolution'][1]}p{cfg['suffix']}.mp4"


def set_stage(cfg, stage, **kw):
    (cfg["work"] / "stage.json").write_text(json.dumps({"stage": stage, "time": time.time(), **kw},
                                                       ensure_ascii=False, default=str))


def media_duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                     capture=True, log=False).stdout.strip())


def validate(cfg):
    problems = []
    for key in ("title_slug", "footage_dir", "segments"):
        if not cfg.get(key):
            problems.append(f"missing '{key}'")
    if not cfg["cards"]["intro"].get("title"):
        problems.append("cards.intro.title is required (use the names exactly as the client wrote them)")
    for it in cfg["cold_open"] + cfg["segments"]:
        clip = cfg["footage"] / it["clip"]
        if not clip.exists():
            problems.append(f"clip not found: {clip}")
            continue
        d = probe(clip)["duration"]
        if not 0 <= float(it["in"]) < float(it["out"]) <= d + 0.05:
            problems.append(f"{it['clip']}: in/out {it['in']}-{it['out']} outside 0-{d:.2f}s")
    if cfg.get("music") and not (ROOT / cfg["music"]["file"]).exists():
        problems.append(f"music file not found: {cfg['music']['file']}")
    if cfg.get("music") and not cfg["music"].get("license"):
        problems.append("music.license is empty - record the source and licence before using a track")
    if not (ROOT / cfg["logo"]).exists():
        problems.append(f"logo not found: {cfg['logo']}")
    if cfg["masthead"].get("date"):
        try:
            time.strptime(cfg["masthead"]["date"], "%Y-%m-%d")
        except ValueError:
            problems.append("masthead.date must be YYYY-MM-DD (the event date)")
    else:
        print("NOTE: masthead.date is empty - the top-right date will be blank", flush=True)
    for lt in cfg["lower_thirds"]:
        if not 0 <= lt["segment"] < len(cfg["segments"]):
            problems.append(f"lower third points at segment {lt['segment']} which does not exist")
    if problems:
        raise SystemExit("project invalid:\n  - " + "\n  - ".join(problems))
    items, _, _, total = timeline(cfg)
    frames = sum(round(it["dur"] * cfg["fps"]) for it in items if it["kind"] == "seg")
    print(f"project ok: {len(cfg['segments'])} segments (+{len(cfg['cold_open'])} cold open), runtime "
          f"{fmt_time(total)}, {frames} frames, mode={cfg['upscale']} {cfg['resolution'][0]}x{cfg['resolution'][1]}")


# ---------------------------------------------------------------- stages

def stage_cards(cfg):
    import make_cards
    set_stage(cfg, "cards")
    W, H = cfg["resolution"]
    fps = cfg["fps"]
    make_cards.render_all(cfg)
    for it in items_of(cfg):
        if it["kind"] != "card":
            continue
        out = card_clip(cfg, it["name"], it["dur"])
        if out.exists():
            continue
        frames = round(it["dur"] * fps)
        vf = (f"scale={W * 2}:{H * 2}:flags=lanczos,"
              f"zoompan=z='1+0.04*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={fps},"
              f"{TO709},format=yuv420p,{TAG}")
        run(["ffmpeg", "-y", "-v", "error", "-i", card_png(cfg, it["name"]), "-vf", vf, "-frames:v", frames,
             "-c:v", "libx264", "-preset", "medium", "-crf", "14", *BT709, out])


def lufs(path):
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
              capture=True, log=False).stderr
    m = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", err)
    return None if not m or m[-1] == "-inf" else float(m[-1])


def stage_clean(cfg, segs=None):
    A = cfg["audio"]
    segs = segs if segs is not None else [it for it in items_of(cfg) if it["kind"] == "seg"]
    (cfg["work"] / "audio").mkdir(parents=True, exist_ok=True)
    for n, it in enumerate(segs):
        out = aud_path(cfg, it)
        if out.exists():
            continue
        set_stage(cfg, "clean", done=n, total=len(segs))
        clip = cfg["footage"] / it["clip"]
        if not probe(clip)["has_audio"]:
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", it["dur"],
                 "-c:a", "pcm_s24le", out])
            continue
        tmp = out.with_suffix(".stage1.wav")
        run(["ffmpeg", "-y", "-v", "error", "-ss", it["in"], "-i", clip, "-t", it["dur"], "-vn", "-af", CLEAN,
             "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", tmp])
        level = lufs(tmp)
        gain = 0.0 if level is None else max(-20.0, min(A["real_max_gain_db"], A["real_lufs"] - level))
        run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=false",
             "-c:a", "pcm_s24le", out])
        tmp.unlink()


def piecewise(points):
    expr = f"{points[-1][1]}"
    for (t0, v0), (t1, v1) in reversed(list(zip(points, points[1:]))):
        expr = f"if(lt(t,{t1:.3f}),{v0}+({v1}-{v0})*(t-{t0:.3f})/{max(t1 - t0, 1e-3):.3f},{expr})"
    return expr


def stage_audio(cfg):
    set_stage(cfg, "audio")
    items, juncs, starts, total = timeline(cfg)
    A, M, work = cfg["audio"], cfg.get("music"), cfg["work"]
    segs = [(j, it) for j, it in enumerate(items) if it["kind"] == "seg"]
    inputs, filt, labels = [], [], []
    # Each shot's real sound is faded over its own transitions and placed at its timeline start.
    # Summing (normalize=0) gives equal-gain crossfades and keeps timestamps continuous, which
    # sidechaincompress needs (an acrossfade chain leaves gaps it stops at).
    for n, (j, it) in enumerate(segs):
        inputs += ["-i", aud_path(cfg, it)]
        fin = juncs[j][1] if j > 0 else 0.02
        fout = juncs[j + 1][1] if j + 1 < len(items) else 0.02
        filt.append(f"[{n}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,asetpts=N/SR/TB,"
                    f"afade=t=in:st=0:d={fin},afade=t=out:st={it['dur'] - fout:.3f}:d={fout},"
                    f"adelay={round(starts[j] * 1000)}:all=1,apad=whole_dur={total:.3f}[r{n}]")
        labels.append(f"[r{n}]")
    head = (f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,"
            if len(labels) > 1 else f"{labels[0]}anull,")
    filt.append(f"{head}atrim=0:{total:.3f},asetpts=N/SR/TB,"
                f"acompressor=threshold=-24dB:ratio=3:attack=10:release=250:makeup=1,"
                f"volume={A['real_gain']},alimiter=limit=0.95:level=false,asplit=2[key][real]")

    if M:
        mfile = ROOT / M["file"]
        offset = float(M.get("offset", 0))
        if media_duration(mfile) < offset + total:
            print(f"WARNING: music is shorter than offset+runtime; it will loop with an audible seam", flush=True)
            inputs += ["-stream_loop", "-1"]
        inputs += ["-i", mfile]
        L = M.get("levels", {})
        card, default = L.get("card", 0.8), L.get("default", 0.62)
        cold, by_section = L.get("cold_open", default), L.get("sections", {})

        def level(it):
            if it["kind"] == "card":
                return card
            return cold if it["role"] == "cold" else by_section.get(it.get("section"), default)

        pts = [(0.0, level(items[0]))]
        for j in range(1, len(items)):
            a, b = level(items[j - 1]), level(items[j])
            if a != b:
                t0 = max(starts[j], pts[-1][0])
                pts += [(t0, a), (t0 + min(2.0, items[j]["dur"] / 2), b)]
        pts.append((total, pts[-1][1]))
        filt.append(f"[{len(segs)}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                    f"atrim=start={offset}:duration={total:.3f},asetpts=N/SR/TB,"
                    f"volume=eval=frame:volume='{piecewise(pts)}',"
                    f"afade=t=in:st=0:d=1.0,afade=t=out:st={total - 3:.3f}:d=3[mus]")
        if M.get("duck"):
            filt.append("[mus][key]sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400:makeup=1[bed]")
        else:
            filt.append("[key]anullsink;[mus]anull[bed]")
        filt.append("[bed][real]amix=inputs=2:duration=first:normalize=0[aout]")
    else:
        filt.append("[key]anullsink;[real]anull[aout]")

    premix, master = work / "premix.wav", work / "master_audio.wav"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "[aout]",
         "-t", f"{total:.3f}", "-c:a", "pcm_s24le", "-ar", "48000", premix])

    report = master_loudness(premix, master, A)
    report["music_points"] = pts if M else None
    (work / "audio_report.json").write_text(json.dumps(report, indent=2))


def master_loudness(premix, master, A, lra=11):
    """Two-pass linear loudnorm to A['master_lufs'] / A['true_peak'] (also used by the reels tool)."""
    target = f"I={A['master_lufs']}:TP={A['true_peak']}:LRA={lra}"

    def measure(pre):
        err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", premix, "-af", f"{pre}loudnorm={target}:print_format=json",
                   "-f", "null", "-"], capture=True, log=False).stderr
        return json.loads(re.findall(r"\{[^{}]+\}", err)[-1])

    # Limit transients first, just enough that loudnorm can apply one linear gain (no pumping).
    m0 = measure("")
    ceiling_db = A["true_peak"] - (A["master_lufs"] - float(m0["input_i"])) - 0.5
    pre = (f"alimiter=limit={max(0.0625, 10 ** (ceiling_db / 20)):.4f}:attack=5:release=60:level=false,"
           if ceiling_db < 0 else "")
    m = measure(pre) if pre else m0
    err = run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", premix, "-af",
               f"{pre}loudnorm={target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
               f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
               f"linear=true:print_format=json,aresample=48000", "-c:a", "pcm_s24le", master],
              capture=True, log=False).stderr
    o = json.loads(re.findall(r"\{[^{}]+\}", err)[-1])
    print(f"audio: premix {m0['input_i']} LUFS/{m0['input_tp']} dBTP -> master {o['output_i']} LUFS/"
          f"{o['output_tp']} dBTP ({o['normalization_type']})", flush=True)
    return {"premix_lufs": m0["input_i"], "premix_tp": m0["input_tp"], "master_lufs": o["output_i"],
            "master_tp": o["output_tp"], "mode": o["normalization_type"]}


def stage_segments(cfg):
    W, H = cfg["resolution"]
    fps = cfg["fps"]
    grade = f"{cfg['grade']},format=yuv420p"
    segs = [it for it in items_of(cfg) if it["kind"] == "seg"]
    (cfg["work"] / "segs").mkdir(exist_ok=True)
    for n, it in enumerate(segs):
        out = seg_path(cfg, it)
        if out.exists():
            continue
        set_stage(cfg, "segments", done=n, total=len(segs), current=it["clip"])
        clip = cfg["footage"] / it["clip"]
        info = probe(clip)
        part = out.with_suffix(".part.mp4")
        if cfg["upscale"] == "ai":
            if info["h"] > info["w"]:
                crop, size, post = f"{info['w'] // 2 * 2}:{info['h'] // 2 * 2}", [], f"{fit_filter(info, W, H)},{grade}"
            else:
                cw, ch = crop_16x9(info["w"], info["h"])
                crop, size, post = f"{cw}:{ch}", ["--out-size", W, H], grade
            run([sys.executable, TOOLS / "sr_upscale.py", clip, part, "--crop", crop, "--start", it["in"],
                 "--duration", it["dur"], "--fps", fps, "--denoise", cfg["ai_denoise"], *size, "--post-vf", post])
        else:
            vf = (f"fps={fps},{cfg['denoise_filter']},{fit_filter(info, W, H)},cas=strength=0.5,deband,{grade},"
                  f"setsar=1,{TAG}")
            run(["ffmpeg", "-y", "-v", "error", "-ss", it["in"], "-i", clip, "-t", it["dur"], "-vf", vf, "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "13", "-pix_fmt", "yuv420p", *BT709, part])
        frames = int(run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", part], capture=True, log=False).stdout.strip())
        expected = round(it["dur"] * fps)
        if abs(frames - expected) > 1:
            raise SystemExit(f"{it['clip']} {it['in']}-{it['out']}: {frames} frames, expected {expected}")
        os.replace(part, out)


def stage_video(cfg):
    items, juncs, starts, total = timeline(cfg)
    W, H = cfg["resolution"]
    fps, E, work = cfg["fps"], cfg["encode"], cfg["work"]
    set_stage(cfg, "video", total=total)
    inputs = []
    for it in items:
        p = card_clip(cfg, it["name"], it["dur"]) if it["kind"] == "card" else seg_path(cfg, it)
        if not p.exists():
            raise SystemExit(f"missing {p.name} - run the cards and segments stages first")
        inputs += ["-i", p]
    filt, prev, running = [], "0:v", items[0]["dur"]
    for j in range(1, len(items)):
        tr, t = juncs[j]
        filt.append(f"[{prev}][{j}:v]xfade=transition={tr}:duration={t}:offset={running - t:.4f}[x{j}]")
        running += items[j]["dur"] - t
        prev = f"x{j}"
    n = len(items)
    main = [j for j, it in enumerate(items) if it.get("role") == "main"]
    for k, lt in enumerate(cfg["lower_thirds"]):
        j = main[lt["segment"]]
        st, dur = starts[j] + juncs[j][1] + lt.get("delay", 0.6), lt.get("dur", 4.6)
        inputs += ["-loop", "1", "-framerate", fps, "-t", f"{total:.3f}", "-i", work / "cards" / f"lt_{k}.png"]
        filt.append(f"[{n}:v]format=rgba,fade=t=in:st={st:.3f}:d=0.5:alpha=1,"
                    f"fade=t=out:st={st + dur - 0.5:.3f}:d=0.5:alpha=1,{TO709},format=yuva420p[l{k}]")
        filt.append(f"[{prev}][l{k}]overlay=0:0:eof_action=pass[o{k}]")
        prev, n = f"o{k}", n + 1
    masthead = work / "cards" / "masthead.png"
    if not masthead.exists():
        raise SystemExit("missing masthead.png - run the cards stage first")
    inputs += ["-i", masthead]
    enable = ""
    if not cfg["masthead"]["on_cards"]:
        enable = f":enable='between(t,{starts[main[0]]:.3f},{starts[-1] + juncs[-1][1]:.3f})'"
    filt.append(f"[{n}:v]format=rgba,{TO709},format=yuva420p[mh]")
    filt.append(f"[{prev}][mh]overlay=0:0{enable},fade=t=in:st=0:d=0.6,"
                f"fade=t=out:st={total - 1.0:.3f}:d=1.0,format=yuv420p,{TAG}[vout]")
    progress = work / "progress_video.txt"
    progress.unlink(missing_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-nostats", "-progress", progress, *inputs,
         "-filter_complex", ";".join(filt), "-map", "[vout]", "-t", f"{total:.3f}", "-r", fps, "-an",
         *video_codec(E), "-g", fps * 2,
         *BT709, "-movflags", "+faststart", work / "master_video.mp4"])


def chapters(cfg):
    items, _, starts, total = timeline(cfg)
    labels, out, last = cfg["sections"], [], object()
    for j, it in enumerate(items):
        sec = it.get("section")
        if it.get("role") != "main" or sec == last:
            continue
        last = sec
        if not labels.get(sec):
            continue
        t = 0.0 if not out else starts[j]
        if out and t - out[-1][0] < 10:
            continue
        out.append((t, labels[sec]))
    if out and total - out[-1][0] < 10:
        out.pop()
    return out


def stage_mux(cfg):
    set_stage(cfg, "mux")
    work, final = cfg["work"], final_path(cfg)
    run(["ffmpeg", "-y", "-v", "error", "-i", work / "master_video.mp4", "-i", work / "master_audio.wav",
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final])
    ch = chapters(cfg)
    if ch:
        txt = "\n".join(f"{fmt_time(t)} {name}" for t, name in ch)
        (cfg["output"] / f"{cfg['title_slug']}_chapters.txt").write_text(txt + "\n")
        if len(ch) < 3:
            print("NOTE: YouTube shows chapters only with 3+ entries of 10 s+; add section labels", flush=True)
    print("final:", final, flush=True)


def stage_qc(cfg):
    from PIL import Image, ImageDraw
    set_stage(cfg, "qc")
    items, juncs, starts, total = timeline(cfg)
    W, H = cfg["resolution"]
    A, final, qc = cfg["audio"], final_path(cfg), cfg["work"] / "qc"
    qc.mkdir(exist_ok=True)
    rows = []

    def check(ok, name, detail):
        rows.append(("PASS" if ok is True else "WARN" if ok is None else "FAIL", name, str(detail)))

    info = probe(final)
    check(info["w"] == W and info["h"] == H, "resolution", f"{info['w']}x{info['h']}")
    check(abs(info["fps"] - cfg["fps"]) < 0.05, "frame rate", info["fps"])
    check(abs(info["duration"] - total) < 0.25, "duration", f"{info['duration']:.2f}s (timeline {total:.2f}s)")
    check(info["has_audio"], "audio stream", info["audio"])
    check(info["color"][0] == "bt709", "colour tags", info["color"])

    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", final, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
              capture=True, log=False).stderr
    i_lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)[-1])
    check(abs(i_lufs - A["master_lufs"]) <= 1.0, "loudness", f"{i_lufs} LUFS (target {A['master_lufs']})")
    check(tp <= A["true_peak"] + 0.5, "true peak", f"{tp} dBTP (limit {A['true_peak']})")

    allowed = [(0, 1.5), (total - 2.0, total)]
    allowed += [(starts[j] - 0.3, starts[j] + it["dur"] + 0.3) for j, it in enumerate(items) if it["kind"] == "card"]
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", final, "-an", "-vf",
               "scale=480:-2,blackdetect=d=0.6:pix_th=0.08", "-f", "null", "-"], capture=True, log=False).stderr
    bad = [(float(s), float(e)) for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)
           if not any(a <= float(s) and float(e) <= b for a, b in allowed)]
    check(not bad, "no unexpected black", bad or "none")

    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", final, "-vn", "-af", "silencedetect=noise=-50dB:d=2.5",
               "-f", "null", "-"], capture=True, log=False).stderr
    silences = re.findall(r"silence_start: ([\d.]+)", err)
    check(True if not silences else None, "no long silences", silences or "none")

    main = [j for j, it in enumerate(items) if it.get("role") == "main"]
    times = {"intro": starts[main[0] - 1] + items[main[0] - 1]["dur"] / 2,
             "outro": starts[-1] + items[-1]["dur"] / 2}
    for k, lt in enumerate(cfg["lower_thirds"]):
        j = main[lt["segment"]]
        times[f"lower third {k}"] = starts[j] + juncs[j][1] + lt.get("delay", 0.6) + lt.get("dur", 4.6) / 2
    last = None
    for j in main:
        if items[j].get("section") != last:
            last = items[j].get("section")
            times[f"section {last}"] = starts[j] + juncs[j][1] + 1.0
    for q in range(1, 7):
        times[f"content {q}"] = starts[main[0]] + (starts[main[-1]] + items[main[-1]]["dur"] - starts[main[0]]) * q / 7
    tiles = []
    for label, t in sorted(times.items(), key=lambda kv: kv[1]):
        p = qc / f"{t:07.2f}.jpg"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", final, "-frames:v", "1", "-vf", "scale=640:-2", p],
            log=False)
        tiles.append((label, t, p))
    cols, tw, th = 3, 640, 360
    sheet = Image.new("RGB", (cols * tw, ((len(tiles) + cols - 1) // cols) * (th + 30)), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    for k, (label, t, p) in enumerate(tiles):
        x, y = (k % cols) * tw, (k // cols) * (th + 30)
        sheet.paste(Image.open(p).resize((tw, th)), (x, y + 30))
        d.text((x + 8, y + 8), f"{fmt_time(t)}  {label}", fill=(255, 201, 60))
    sheet.save(qc / "qc_sheet.jpg", quality=90)

    report = [f"# QC: {final.name}", "", "| result | check | detail |", "|---|---|---|"]
    report += [f"| {r} | {n} | {dtl} |" for r, n, dtl in rows]
    report += ["", f"Frame sheet: {qc / 'qc_sheet.jpg'} - LOOK at it: grade consistency, logo, Kannada text, "
                   "no frozen/black frames, faces not smeared."]
    (qc / "qc_report.md").write_text("\n".join(report) + "\n")
    print("\n".join(f"{r:4s}  {n}: {dtl}" for r, n, dtl in rows), flush=True)
    print(f"qc report: {qc / 'qc_report.md'}", flush=True)
    if any(r == "FAIL" for r, _, _ in rows):
        raise SystemExit("QC FAILED - see qc_report.md")


FUNCS = {"cards": stage_cards, "clean": stage_clean, "audio": stage_audio, "segments": stage_segments,
         "video": stage_video, "mux": stage_mux, "qc": stage_qc}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("stages", nargs="*", choices=STAGES + [[]], metavar="stage")
    ap.add_argument("--preview", action="store_true", help="1080p, no AI, fast encode - for review")
    ap.add_argument("--detach", action="store_true", help="run in the background, immune to session exit")
    ap.add_argument("--check", action="store_true", help="validate only")
    a = ap.parse_args()
    cfg = load_config(a.project, a.preview)
    if a.detach:
        log = cfg["work"] / "build.log"
        cmd = [sys.executable, str(Path(__file__).resolve()), str(cfg["project_file"]), *a.stages]
        cmd += ["--preview"] if a.preview else []
        with open(log, "a") as fh:
            fh.write(f"\n=== start {time.ctime()} {' '.join(cmd)} ===\n")
            fh.flush()
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    start_new_session=True)
        print(f"detached pid {proc.pid}; log {log}")
        print(f"watch: python3 {TOOLS / 'monitor.py'} {cfg['project_file']}{' --preview' if a.preview else ''}")
        return
    validate(cfg)
    if a.check:
        return
    try:
        for s in a.stages or STAGES:
            FUNCS[s](cfg)
        set_stage(cfg, "done", final=final_path(cfg))
    except SystemExit as e:
        if e.code not in (0, None):
            set_stage(cfg, "failed", error=str(e.code))
        raise


if __name__ == "__main__":
    main()
