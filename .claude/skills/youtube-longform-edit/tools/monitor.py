#!/usr/bin/env python3
"""Live status for a build started with --detach.

Prints one line whenever something changes (stage, a segment finishes) and a heartbeat every
10 min. ETAs come from measured speed only: segment finish times and ffmpeg -progress, never guesses.
Exits when the build finishes, fails, or its process disappears (use --restart N to relaunch).
"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path

from build import final_path, items_of, load_config, seg_path, timeline
from common import TOOLS, fmt_time

HEARTBEAT = 600


def alive():
    return subprocess.run(["pgrep", "-f", "youtube-longform-edit/tools/build.py"], capture_output=True).returncode == 0


def say(msg):
    print(f"[{time.strftime('%H:%M')}] {msg}", flush=True)


def segment_status(cfg):
    fps = cfg["fps"]
    segs = [it for it in items_of(cfg) if it["kind"] == "seg"]
    done, left = [], 0
    for it in segs:
        p, frames = seg_path(cfg, it), round(it["dur"] * fps)
        if p.exists():
            done.append((p.stat().st_mtime, frames))
        else:
            left += frames
    done.sort()
    gaps = [(b[0] - a[0], b[1]) for a, b in zip(done, done[1:]) if 0 < b[0] - a[0] < 900][-5:]
    spf = sum(g for g, _ in gaps) / sum(f for _, f in gaps) if gaps else None
    return len(done), len(segs), left, spf


def video_status(cfg, total):
    p = cfg["work"] / "progress_video.txt"
    if not p.exists():
        return None, None
    txt = p.read_text()
    t = re.findall(r"out_time_us=(\d+)", txt)
    sp = re.findall(r"speed=\s*([\d.]+)x", txt)
    pos = int(t[-1]) / 1e6 if t else 0.0
    speed = float(sp[-1]) if sp else None
    return pos, ((total - pos) / speed if speed else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--restart", type=int, default=0, help="relaunch the build up to N times if it is killed")
    a = ap.parse_args()
    cfg = load_config(a.project, a.preview)
    _, _, _, total = timeline(cfg)
    stage_file = cfg["work"] / "stage.json"
    last_key, last_emit, restarts, gone_since = None, 0.0, 0, None

    while True:
        st = json.loads(stage_file.read_text()) if stage_file.exists() else {"stage": "not started"}
        stage = st["stage"]
        if stage == "done":
            say(f"DONE: {final_path(cfg)} - now open qc/qc_sheet.jpg and qc_report.md before telling anyone it is ready")
            return
        if stage == "failed":
            log = cfg["work"] / "build.log"
            tail = log.read_text().strip().splitlines()[-6:] if log.exists() else []
            say(f"FAILED in build: {st.get('error')} | log tail: {' / '.join(tail)}")
            sys.exit(1)

        n_done, n_total, frames_left, spf = segment_status(cfg)
        if stage == "segments":
            eta = f"~{fmt_time(frames_left * spf)}" if spf else "measuring speed after 2 finished segments"
            line = (f"segments {n_done}/{n_total}, {frames_left} frames left, "
                    f"{f'{spf:.2f} s/frame, ' if spf else ''}ETA {eta}; then video assembly")
            key = (stage, n_done)
        elif stage == "video":
            pos, eta = video_status(cfg, total)
            pct = f"{100 * pos / total:.0f}% ({fmt_time(pos)}/{fmt_time(total)})" if pos is not None else "starting"
            line = f"video assembly {pct}, ETA {fmt_time(eta) if eta else 'measuring'}; then mux + QC (~3 min)"
            key = (stage, int((pos or 0) // (total / 10)))
        else:
            line = f"{stage} (started {fmt_time(time.time() - st.get('time', time.time()))} ago)"
            key = (stage, st.get("done"))

        running = alive()
        if not running:
            gone_since = gone_since or time.time()
            if time.time() - gone_since > 45:
                if restarts < a.restart:
                    restarts += 1
                    cmd = [sys.executable, str(TOOLS / "build.py"), str(cfg["project_file"]), "--detach"]
                    subprocess.run(cmd + (["--preview"] if a.preview else []), check=True)
                    say(f"build process was gone (usually killed for memory); relaunched {restarts}/{a.restart}, "
                        f"cached work is kept")
                    gone_since = None
                    time.sleep(20)
                    continue
                say(f"STOPPED: build process is gone at stage '{stage}'. Relaunch with build.py --detach; "
                    f"finished work is cached")
                sys.exit(2)
        else:
            gone_since = None

        if key != last_key or time.time() - last_emit >= HEARTBEAT:
            say(line)
            last_key, last_emit = key, time.time()
        time.sleep(20)


if __name__ == "__main__":
    main()
