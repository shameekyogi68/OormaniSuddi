#!/usr/bin/env python3
"""Build the branded Ganeshotsava procession documentary.

Generates intro/outro cards, trims black bookends, overlays masthead,
assembles with transitions, masters audio, and outputs the final MP4.
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "youtube-longform-edit" / "tools"))

from common import BT709, TAG, TO709, C, Brand, probe, run, fit_filter

# ── Config ──────────────────────────────────────────────────────────
SRC         = ROOT / "Ganeshotsava_procession_Documentary_v2_4K.mp4"
WORK        = ROOT / "_work" / "ganeshotsava_branded"
OUTPUT      = ROOT / "Ganeshotsava_procession_Documentary_v2_4K_branded.mp4"
LOGO        = ROOT / "assets" / "logo_clean_circle.png"

TRIM_IN     = 2.7      # start after head black
TRIM_OUT    = 175.5    # end before tail black
CONTENT_DUR = round(TRIM_OUT - TRIM_IN, 3)  # 172.8s

INTRO_DUR   = 5.0
OUTRO_DUR   = 7.0
XFADE_IN    = 1.0      # intro -> content dip to black
XFADE_OUT   = 1.2      # content -> outro dip to black

TITLE       = "ಗಣೇಶೋತ್ಸವ ಮೆರವಣಿಗೆ"
PLACE       = "ಬೈಂದೂರು"
DATE_STR    = "18 ಸೆಪ್ಟೆಂಬರ್ 2026"
DAY_STR     = "ಶುಕ್ರವಾರ"
MASTHEAD_SPEC = {"date": "2026-09-18", "scale": 1.05, "scrim": 0.62}

HERO_T      = 90.0     # illuminated chariot frame
OUTRO_T     = 170.0    # procession tail frame

W, H, FPS   = 3840, 2160, 30
BITRATE     = "55M"
MASTER_LUFS = -14.0
TRUE_PEAK   = -1.0


def ensure_dirs():
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "cards").mkdir(exist_ok=True)


def step1_cards():
    import make_cards
    cards_dir = WORK / "cards"

    print("\n[1/6] Generating brand cards...", flush=True)
    bg_intro = make_cards.grab_frame(str(SRC), HERO_T, W, H, str(cards_dir / "bg_intro.png"))
    make_cards.title_card(
        bg_intro, str(cards_dir / "intro.png"), W, H, str(LOGO),
        TITLE, [f"{PLACE} • {DATE_STR}", f"{DAY_STR} • {Brand.tagline}"], kind="intro"
    )
    print(f"  ✓ intro card: {cards_dir / 'intro.png'}", flush=True)

    bg_outro = make_cards.grab_frame(str(SRC), OUTRO_T, W, H, str(cards_dir / "bg_outro.png"))
    make_cards.title_card(
        bg_outro, str(cards_dir / "outro.png"), W, H, str(LOGO),
        "ಧನ್ಯವಾದಗಳು", [f"Subscribe · {Brand.name} · {Brand.handle}", Brand.tagline], kind="outro"
    )
    print(f"  ✓ outro card: {cards_dir / 'outro.png'}", flush=True)

    make_cards.masthead_overlay(str(cards_dir / "masthead.png"), W, H, MASTHEAD_SPEC)
    print(f"  ✓ masthead: {cards_dir / 'masthead.png'}", flush=True)


def step2_card_clips():
    print("\n[2/6] Rendering card motion clips (Ken Burns zoompan)...", flush=True)
    for name, dur in [("intro", INTRO_DUR), ("outro", OUTRO_DUR)]:
        png = WORK / "cards" / f"{name}.png"
        out = WORK / "cards" / f"{name}_clip.mp4"
        frames = round(dur * FPS)
        # Slow 4% zoom-in for dynamic broadcast motion
        vf = (f"scale={W * 2}:{H * 2}:flags=lanczos,"
              f"zoompan=z='1+0.04*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={W}x{H}:fps={FPS},"
              f"{TO709},format=yuv420p,{TAG}")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(png), "-vf", vf, "-frames:v", str(frames),
             "-c:v", "h264_videotoolbox", "-b:v", BITRATE, "-profile:v", "high", "-pix_fmt", "yuv420p",
             *BT709, str(out)])
        print(f"  ✓ {name} clip: {out} ({dur}s)", flush=True)


def step3_trimmed_content():
    print("\n[3/6] Trimming source & applying masthead overlay...", flush=True)
    trimmed = WORK / "trimmed_content.mp4"
    masthead = WORK / "cards" / "masthead.png"

    info = probe(str(SRC))
    vf_fit = fit_filter(info, W, H)

    # Trim, scale to 4K, overlay top masthead veil
    vf = (f"[0:v]{vf_fit},fps={FPS},{TO709},format=yuv420p[base];"
          f"[1:v]format=yuva420p,{TO709}[mh];"
          f"[base][mh]overlay=0:0,fade=t=in:st=0:d=0.8,fade=t=out:st={CONTENT_DUR - 0.8:.3f}:d=0.8,format=yuv420p,{TAG}")

    run(["ffmpeg", "-y", "-v", "error",
         "-ss", str(TRIM_IN), "-i", str(SRC), "-t", str(CONTENT_DUR),
         "-i", str(masthead),
         "-filter_complex", vf,
         "-an",
         "-c:v", "h264_videotoolbox", "-b:v", BITRATE, "-profile:v", "high",
         "-pix_fmt", "yuv420p", *BT709,
         "-movflags", "+faststart",
         str(trimmed)])
    print(f"  ✓ trimmed content: {trimmed} ({CONTENT_DUR}s)", flush=True)
    return trimmed


def step4_assemble_video():
    print("\n[4/6] Assembling intro + content + outro with dip-to-black...", flush=True)
    intro_clip = WORK / "cards" / "intro_clip.mp4"
    trimmed    = WORK / "trimmed_content.mp4"
    outro_clip = WORK / "cards" / "outro_clip.mp4"
    master_v   = WORK / "master_video.mp4"

    offset1 = INTRO_DUR - XFADE_IN               # 4.0s
    offset2 = offset1 + CONTENT_DUR - XFADE_OUT   # 4.0 + 172.8 - 1.2 = 175.6s
    total   = INTRO_DUR + CONTENT_DUR + OUTRO_DUR - XFADE_IN - XFADE_OUT  # 182.6s

    filt = (f"[0:v][1:v]xfade=transition=fadeblack:duration={XFADE_IN}:offset={offset1:.4f}[x1];"
            f"[x1][2:v]xfade=transition=fadeblack:duration={XFADE_OUT}:offset={offset2:.4f},"
            f"fade=t=in:st=0:d=0.5,fade=t=out:st={total - 1.0:.3f}:d=1.0,"
            f"format=yuv420p,{TAG}[vout]")

    run(["ffmpeg", "-y", "-v", "error",
         "-i", str(intro_clip), "-i", str(trimmed), "-i", str(outro_clip),
         "-filter_complex", filt, "-map", "[vout]",
         "-t", f"{total:.3f}", "-r", str(FPS), "-an",
         "-c:v", "h264_videotoolbox", "-b:v", BITRATE, "-profile:v", "high",
         "-pix_fmt", "yuv420p", "-g", str(FPS * 2), *BT709,
         "-movflags", "+faststart",
         str(master_v)])
    print(f"  ✓ assembled video: {master_v} ({total:.1f}s)", flush=True)
    return master_v, total


def step5_audio(total_dur):
    print("\n[5/6] Building synchronized audio & mastering to EBU R128 (-14 LUFS)...", flush=True)
    premix   = WORK / "premix.wav"
    master_a = WORK / "master_audio.wav"

    # Content video starts at timeline t = offset1 = 4.0s.
    # Source audio corresponds to trimmed range [TRIM_IN, TRIM_OUT].
    # We delay source audio by 4.0s (4000ms), pad silence to total_dur, and apply smooth fades.
    delay_ms = round((INTRO_DUR - XFADE_IN) * 1000)  # 4000ms

    af = (f"adelay={delay_ms}:all=1,"
          f"apad=whole_dur={total_dur:.3f},"
          f"atrim=0:{total_dur:.3f},asetpts=N/SR/TB,"
          f"afade=t=in:st={INTRO_DUR - XFADE_IN:.3f}:d=1.0,"
          f"afade=t=out:st={total_dur - OUTRO_DUR + XFADE_OUT / 2:.3f}:d=1.5")

    run(["ffmpeg", "-y", "-v", "error",
         "-ss", str(TRIM_IN), "-i", str(SRC), "-t", str(CONTENT_DUR),
         "-vn", "-af", af,
         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le",
         str(premix)])

    # Two-pass loudnorm
    target = f"I={MASTER_LUFS}:TP={TRUE_PEAK}:LRA=11"
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(premix),
               "-af", f"loudnorm={target}:print_format=json",
               "-f", "null", "-"], capture=True, log=False).stderr
    m = json.loads(re.findall(r"\{[^{}]+\}", err)[-1])

    err = run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", str(premix), "-af",
               f"loudnorm={target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
               f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
               f"offset={m['target_offset']}:linear=true:print_format=json,aresample=48000",
               "-c:a", "pcm_s24le", str(master_a)], capture=True, log=False).stderr
    o = json.loads(re.findall(r"\{[^{}]+\}", err)[-1])
    print(f"  ✓ audio mastered: {m['input_i']} -> {o['output_i']} LUFS, peak {o['output_tp']} dBTP", flush=True)
    return master_a


def step6_mux(master_v, master_a):
    print("\n[6/6] Muxing final video and audio...", flush=True)
    run(["ffmpeg", "-y", "-v", "error",
         "-i", str(master_v), "-i", str(master_a),
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart",
         str(OUTPUT)])
    print(f"  ✓ FINAL FILE WRITTEN: {OUTPUT}", flush=True)


def step7_qc(total_dur):
    print("\n" + "=" * 60, flush=True)
    print("QUALITY CONTROL VERIFICATION", flush=True)
    print("=" * 60, flush=True)
    info = probe(str(OUTPUT))
    rows = []

    def check(ok, name, detail):
        rows.append(("PASS" if ok else "FAIL", name, str(detail)))

    check(info["w"] == W and info["h"] == H, "Resolution", f"{info['w']}x{info['h']} (Expected {W}x{H})")
    check(abs(info["fps"] - FPS) < 0.05, "Frame Rate", f"{info['fps']} fps")
    check(abs(info["duration"] - total_dur) < 0.5, "Duration", f"{info['duration']:.2f}s (Expected {total_dur:.2f}s)")
    check(info["has_audio"], "Audio Stream", f"{info['audio']}")
    check(info["color"][0] == "bt709", "Colour Space", f"{info['color']}")

    # Loudness verification
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(OUTPUT),
               "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
              capture=True, log=False).stderr
    i_lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)[-1])
    check(abs(i_lufs - MASTER_LUFS) <= 1.5, "Loudness", f"{i_lufs} LUFS (Target {MASTER_LUFS})")
    check(tp <= TRUE_PEAK + 0.5, "True Peak", f"{tp} dBTP (Limit {TRUE_PEAK})")

    # Extract sample verification frames
    qc_dir = WORK / "qc"
    qc_dir.mkdir(exist_ok=True)
    sample_points = [
        ("01_intro_card", 2.5),
        ("02_transition_to_content", 4.5),
        ("03_content_start", 6.0),
        ("04_content_mid", total_dur / 2),
        ("05_content_near_end", total_dur - 8.0),
        ("06_outro_card", total_dur - 3.5),
    ]
    for label, t in sample_points:
        frame_out = qc_dir / f"{label}.jpg"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(OUTPUT),
             "-frames:v", "1", "-vf", "scale=960:-2,format=yuvj420p", "-q:v", "2", str(frame_out)], log=False)

    for r, n, d in rows:
        mark = "✓" if r == "PASS" else "✗"
        print(f"  {mark} {r:4s}  {n:15s}: {d}", flush=True)
    print("=" * 60, flush=True)

    # Clean intermediate files to conserve disk space
    print("\nCleaning intermediate render files...", flush=True)
    for f in [WORK / "trimmed_content.mp4", WORK / "master_video.mp4",
              WORK / "premix.wav", WORK / "master_audio.wav"]:
        if f.exists():
            sz = f.stat().st_size / (1024 * 1024)
            f.unlink()
            print(f"  deleted temporary {f.name} ({sz:.1f} MB)", flush=True)

    return qc_dir


def main():
    start_time = time.time()
    ensure_dirs()
    step1_cards()
    step2_card_clips()
    step3_trimmed_content()
    master_v, total_dur = step4_assemble_video()
    master_a = step5_audio(total_dur)
    step6_mux(master_v, master_a)
    qc_dir = step7_qc(total_dur)
    elapsed = time.time() - start_time
    print(f"\n🎉 Pipeline completed in {elapsed:.1f} seconds!", flush=True)
    print(f"Output file: {OUTPUT}", flush=True)
    print(f"File size: {OUTPUT.stat().st_size / (1024 * 1024):.1f} MB", flush=True)


if __name__ == "__main__":
    main()
