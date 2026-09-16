#!/usr/bin/env python3
"""Real-ESRGAN general-x4v3 video upscaler for Apple Silicon (MPS) or CPU.

Decodes a clip window with ffmpeg, upscales every frame 4x on the GPU, optionally
resizes to the delivery size on the GPU, and pipes to an ffmpeg encoder whose
-vf carries the grade. Colour is handled explicitly as BT.709 limited range.
"""
import argparse, subprocess, sys, time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

MODELS = Path(__file__).resolve().parent.parent / "models"
BT709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
TAG = "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv"
SCALE = 4


class SRVGGNetCompact(nn.Module):
    # Real-ESRGAN realesrgan/archs/srvgg_arch.py, reimplemented to avoid installing basicsr
    def __init__(self, num_feat=64, num_conv=32, upscale=4):
        super().__init__()
        self.upscale = upscale
        body = [nn.Conv2d(3, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        for _ in range(num_conv):
            body += [nn.Conv2d(num_feat, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        body.append(nn.Conv2d(num_feat, 3 * upscale * upscale, 3, 1, 1))
        self.body = nn.ModuleList(body)
        self.upsampler = nn.PixelShuffle(upscale)

    def forward(self, x):
        out = x
        for layer in self.body:
            out = layer(out)
        return self.upsampler(out) + F.interpolate(x, scale_factor=self.upscale, mode="nearest")


def load_model(denoise, device):
    paths = [MODELS / "realesr-general-x4v3.pth", MODELS / "realesr-general-wdn-x4v3.pth"]
    if not all(p.exists() for p in paths):
        raise SystemExit(f"model weights missing in {MODELS} - run tools/fetch_models.sh")
    a = torch.load(paths[0], map_location="cpu", weights_only=True)["params"]
    b = torch.load(paths[1], map_location="cpu", weights_only=True)["params"]
    net = SRVGGNetCompact()
    # DNI blend as in Real-ESRGAN inference: 1.0 = full denoise model, 0.0 = weak-denoise model
    net.load_state_dict({k: denoise * a[k] + (1 - denoise) * b[k] for k in a})
    return net.eval().to(device).half()


def make_resizer(device, out_size):
    if out_size is None:
        return lambda x: x
    w, h = out_size
    probe = torch.rand(1, 3, 64, 64, device=device)
    for mode in ("bicubic", "bilinear"):
        try:
            F.interpolate(probe, size=(48, 48), mode=mode, antialias=True, align_corners=False)
            return lambda x, m=mode: F.interpolate(x, size=(h, w), mode=m, antialias=True, align_corners=False)
        except (NotImplementedError, RuntimeError):
            continue
    return lambda x: F.interpolate(x.cpu(), size=(h, w), mode="bicubic", antialias=True, align_corners=False)


@torch.inference_mode()
def upscale(net, resize, rgb, device):
    t = torch.from_numpy(rgb).to(device).permute(2, 0, 1).unsqueeze(0).half().div_(255.0)
    out = resize(net(t).float()).clamp_(0, 1).mul_(255.0).round_().byte()
    return out.squeeze(0).permute(1, 2, 0).contiguous().cpu().numpy()


def upscale_tiled(net, resize, rgb, device, tile=256, overlap=16):
    """Tile the frame so an 8 GB M1 does not swap-death on a full 4× buffer."""
    h, w, _ = rgb.shape
    if tile <= 0 or max(h, w) <= tile:
        return upscale(net, resize, rgb, device)
    acc = np.zeros((h * SCALE, w * SCALE, 3), dtype=np.float32)
    wgt = np.zeros((h * SCALE, w * SCALE, 1), dtype=np.float32)
    ys = list(range(0, h, tile - overlap)) or [0]
    xs = list(range(0, w, tile - overlap)) or [0]
    for y0 in ys:
        for x0 in xs:
            y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
            patch = rgb[y0:y1, x0:x1]
            out = upscale(net, lambda x: x, patch, device).astype(np.float32)
            Y0, X0 = y0 * SCALE, x0 * SCALE
            acc[Y0:Y0 + out.shape[0], X0:X0 + out.shape[1]] += out
            wgt[Y0:Y0 + out.shape[0], X0:X0 + out.shape[1]] += 1.0
    acc /= np.maximum(wgt, 1.0)
    full = acc.clip(0, 255).astype(np.uint8)
    if resize is None:
        return full
    dummy = torch.from_numpy(full).to(device).permute(2, 0, 1).unsqueeze(0).float()
    out = resize(dummy / 255.0).clamp_(0, 1).mul_(255.0).round_().byte()
    return out.squeeze(0).permute(1, 2, 0).contiguous().cpu().numpy()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--crop", required=True, help="W:H crop applied before upscaling (even numbers)")
    p.add_argument("--crop-xy", help="X:Y top-left of the crop (default: centred)")
    p.add_argument("--start", type=float, default=0)
    p.add_argument("--duration", type=float, required=True)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--denoise", type=float, default=0.5)
    p.add_argument("--out-size", type=int, nargs=2, metavar=("W", "H"))
    p.add_argument("--post-vf", default="format=yuv420p")
    p.add_argument("--preset", default="veryfast")
    p.add_argument("--crf", type=int, default=12)
    p.add_argument("--tile", type=int, default=256,
                   help="tile size in source pixels; 0 disables tiling")
    args = p.parse_args()

    in_w, in_h = (int(v) for v in args.crop.split(":"))
    crop = f"crop={in_w}:{in_h}" + (f":{args.crop_xy}" if args.crop_xy else "")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    net = load_model(args.denoise, device)
    resize = make_resizer(device, args.out_size)
    ow, oh = args.out_size or (in_w * SCALE, in_h * SCALE)

    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-ss", str(args.start), "-i", args.input, "-t", str(args.duration),
         "-vf", f"{crop},fps={args.fps},scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ow}x{oh}", "-r", str(args.fps),
         "-i", "-", "-vf", f"scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv444p,{args.post_vf},{TAG}",
         "-an", "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf), "-pix_fmt", "yuv420p",
         *BT709, args.output],
        stdin=subprocess.PIPE)
    n, frame_bytes, t0 = 0, in_w * in_h * 3, time.time()
    while True:
        buf = dec.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        rgb = np.frombuffer(bytearray(buf), np.uint8).reshape(in_h, in_w, 3)
        enc.stdin.write(upscale_tiled(net, resize, rgb, device, tile=args.tile).tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print(f"{args.output}: {n} frames, {(time.time() - t0) / max(n, 1):.3f} sec/frame", flush=True)
    if enc.returncode != 0 or n == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
