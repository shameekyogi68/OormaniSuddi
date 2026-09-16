import json, subprocess, sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SKILL = TOOLS.parent
ROOT = SKILL.parents[2]
MODELS = SKILL / "models"
FONT_TITLE = ROOT / "fonts" / "NotoSansKannada-Bold.ttf"
FONT_BODY = ROOT / "fonts" / "AnekKannada-Variable.ttf"

BT709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
TAG = "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv"
TO709 = "scale=out_color_matrix=bt709:out_range=tv"
VIDEO_EXT = {".mov", ".mp4", ".m4v", ".mts", ".mkv", ".avi", ".3gp"}

sys.path.insert(0, str(ROOT))
from brand.tokens import C, Brand  # noqa: E402  (brand colours/strings are the single source of truth)


def run(cmd, capture=False, log=True):
    if log:
        print("RUN:", " ".join(str(c) for c in cmd)[:240], flush=True)
    r = subprocess.run([str(c) for c in cmd], capture_output=capture, text=True)
    if r.returncode != 0:
        if capture:
            print(r.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"failed: {cmd[0]} (exit {r.returncode})")
    return r


def probe(path):
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
              capture=True, log=False).stdout
    d = json.loads(out)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        raise SystemExit(f"no video stream: {path}")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(round(float(sd["rotation"])))
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    return {
        "w": w, "h": h, "fps": round(fps, 3), "rotation": rot,
        "duration": float(d["format"].get("duration", 0)),
        "bitrate_kbps": round(int(d["format"].get("bit_rate", 0)) / 1000),
        "vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
        "color": [v.get("color_space"), v.get("color_primaries"), v.get("color_transfer"), v.get("color_range")],
        "has_audio": a is not None,
        "audio": {"sr": int(a["sample_rate"]), "ch": a.get("channels")} if a else None,
    }


def even(x):
    return int(x) // 2 * 2


def crop_16x9(w, h):
    if w * 9 >= h * 16:
        return even(h * 16 / 9), even(h)
    return even(w), even(w * 9 / 16)


def fit_filter(info, W, H):
    """16:9 centre crop + scale for landscape; blurred-fill pillarbox for portrait."""
    w, h = info["w"], info["h"]
    if h > w:
        return (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"gblur=sigma={H / 36:.0f},eq=brightness=-0.12:saturation=0.9[bg];"
                f"[b]scale=-2:{H}:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:0")
    cw, ch = crop_16x9(w, h)
    return f"crop={cw}:{ch},scale={W}:{H}:flags=lanczos+accurate_rnd+full_chroma_int"


def natural_key(p):
    import re
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", Path(p).name)]


def fmt_time(sec):
    sec = int(round(sec))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"
