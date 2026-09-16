#!/usr/bin/env python3
"""Step A: log every clip before any edit decision.

Writes <work>/intake/intake.md + intake.json and one 4x3 contact sheet per clip.
Look at EVERY sheet before writing the cut list.
"""
import argparse, json, re
from pathlib import Path

from common import ROOT, VIDEO_EXT, natural_key, probe, run, crop_16x9


def loudness(path):
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true",
               "-f", "null", "-"], capture=True, log=False).stderr
    i = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", err)
    tp = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", err)
    return (float(i[-1]) if i and i[-1] != "-inf" else None, float(tp[-1]) if tp and tp[-1] != "-inf" else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("footage", help="footage folder, relative to project root or absolute")
    ap.add_argument("--work", help="work folder (default <footage>/_work)")
    args = ap.parse_args()
    footage = (ROOT / args.footage).resolve()
    work = (ROOT / args.work).resolve() if args.work else footage / "_work"
    sheets = work / "intake"
    sheets.mkdir(parents=True, exist_ok=True)

    clips = sorted((p for p in footage.iterdir() if p.suffix.lower() in VIDEO_EXT), key=natural_key)
    rows, total, low_res, portrait = [], 0.0, 0, 0
    for c in clips:
        info = probe(c)
        i_lufs, tp = loudness(c) if info["has_audio"] else (None, None)
        info.update(name=c.name, lufs=i_lufs, true_peak=tp)
        short = min(info["w"], info["h"])
        flags = []
        if short < 720:
            flags.append("LOW-RES (likely WhatsApp/forwarded - ask for originals)")
            low_res += 1
        if info["h"] > info["w"]:
            flags.append("portrait - pillarbox")
            portrait += 1
        if info["w"] * 9 != info["h"] * 16 and info["h"] <= info["w"]:
            flags.append(f"non-16:9 -> crop {crop_16x9(info['w'], info['h'])[0]}x{crop_16x9(info['w'], info['h'])[1]}")
        if tp is not None and tp > -0.5:
            flags.append("audio clips (declip)")
        if not info["has_audio"]:
            flags.append("NO AUDIO")
        info["flags"] = flags
        rows.append(info)
        total += info["duration"]
        n = 12
        run(["ffmpeg", "-y", "-v", "error", "-i", c, "-vf",
             f"fps={n}/{max(info['duration'], 0.5):.3f},scale=320:-2,tile=4x3", "-frames:v", "1",
             sheets / f"{c.stem}.jpg"], log=False)
        print(f"{c.name}: {info['w']}x{info['h']} {info['duration']:.1f}s {' | '.join(flags)}", flush=True)

    (sheets / "intake.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    lines = [f"# Intake: {footage.name}", "",
             f"{len(rows)} clips, {total / 60:.1f} min raw. Order = natural filename order.", ""]
    if low_res:
        lines += [f"**{low_res} clip(s) are below 720p.** Before editing, ask once for the original phone files "
                  "(AirDrop / Google Drive 'original quality' / cable) - not WhatsApp. Source quality is the hard "
                  "ceiling on the final result.", ""]
    lines += ["| # | clip | size | fps | dur | kbps | LUFS | TP | flags | sheet |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in enumerate(rows, 1):
        lines.append(f"| {k} | {r['name']} | {r['w']}x{r['h']} | {r['fps']} | {r['duration']:.1f}s | "
                     f"{r['bitrate_kbps']} | {r['lufs']} | {r['true_peak']} | {'; '.join(r['flags'])} | "
                     f"{r['name'].rsplit('.', 1)[0]}.jpg |")
    (sheets / "intake.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {sheets / 'intake.md'} and {len(rows)} contact sheets")


if __name__ == "__main__":
    main()
