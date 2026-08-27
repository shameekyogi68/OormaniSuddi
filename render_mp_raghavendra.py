"""
ಊರ್ಮನಿ ಸುದ್ದಿ — MP B. Y. Raghavendra Endorsement Bit
===================================================
Broadcast-grade 1080x1920 9:16 Full HD video bit.
Trims the raw interview cleanly, applies house color grading,
layers broadcast masthead + lower thirds + soundbite cards,
masters dialogue with EQ/compression, mixes news BGM ducking,
and concludes with the grand branded channel outro.
"""
from __future__ import annotations

import os
import sys
import shutil
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from brand import typo, surface as sfx, components as cp
from brand.tokens import (C, Role, T, Grid, fmt, category, alpha, Grade, Motion,
                         Ease, clamp01, phase, Brand)

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

INPUT_VIDEO = os.path.join(BASE, "WhatsApp Video 2026-08-23 at 17.54.36.mp4")
OUTPUT_VIDEO = os.path.join(BASE, "out", "oormani_suddi_mp_raghavendra_1080p.mp4")
BUILD_DIR = os.path.join(BASE, "build", "mp_bit")
os.makedirs(BUILD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)

# Precision Cut Timestamps
T_START = 7.7       # Skip camera shake & cue; speech begins at 8.0s cleanly
T_END = 58.8         # End after speech concludes & folded hands
SPEECH_DUR = T_END - T_START  # 51.1s
OUTRO_DUR = 3.5     # Branded outro
TOTAL_DUR = SPEECH_DUR + OUTRO_DUR  # 54.6s

W, H = 1080, 1920
FPS = 30
SS = 2


# ─────────────────────────────────────────────────────────────────────────────
#  GRAPHIC OVERLAYS (Supersampled @ 2x)
# ─────────────────────────────────────────────────────────────────────────────

def render_top_masthead(ss: int = SS) -> Image.Image:
    """Branded top masthead bar with live pulse badge."""
    sf = sfx.Surface(W, 220, ss=ss, bg=(0, 0, 0, 0))
    
    # Top gradient scrim for readability over clouds
    sfx.vgradient(sf, 0, 200, C.ink_950, C.ink_950, a_top=0.90, a_bot=0.0, ease=Ease.in_out_sine)
    
    # Paste logo mark
    logo_size = 76
    lx, ly = 48, 54
    logo_path = os.path.join(BASE, 'assets', 'logo_clean_circle.png')
    if os.path.exists(logo_path):
        lg = Image.open(logo_path).convert('RGBA').resize((int(logo_size * ss), int(logo_size * ss)), Image.Resampling.LANCZOS)
        sf.img.alpha_composite(lg, (int(lx * ss), int(ly * ss)))
    
    # Channel name & tagline
    tx = lx + logo_size + 20
    f_name = typo.font('kn', int(sf.s(38)))
    f_tag = typo.font('kn_var', int(sf.s(22)), weight=650)
    
    typo.draw_text(sf.img, Brand.name, sf.s(tx), sf.s(ly + 32), f_name, Role.text_hi,
                   shadow=(0, sf.s(2), sf.s(8), (0, 0, 0, 200)))
    typo.draw_text(sf.img, Brand.tagline, sf.s(tx), sf.s(ly + 64), f_tag, C.gold_500,
                   shadow=(0, sf.s(2), sf.s(8), (0, 0, 0, 200)))
    
    # Right badge: "ಶುಭ ಹಾರೈಕೆ" (Special Greetings)
    badge_w = 180
    badge_h = 44
    bx = W - 48 - badge_w
    by = ly + (logo_size - badge_h) / 2
    
    # Badge background
    sf.draw.rectangle([sf.s(bx), sf.s(by), sf.s(bx + badge_w) - 1, sf.s(by + badge_h) - 1],
                      fill=(*C.ink_900, 230), outline=(*C.gold_500, 160), width=max(1, int(1.5 * ss)))
    
    # Red dot indicator
    dot_r = 5.5
    dot_x = bx + 18
    dot_y = by + badge_h / 2
    sf.draw.ellipse([sf.s(dot_x - dot_r), sf.s(dot_y - dot_r), sf.s(dot_x + dot_r), sf.s(dot_y + dot_r)],
                    fill=C.red_500)
    
    # Badge text
    f_badge = typo.font('kn_var', int(sf.s(21)), weight=750)
    typo.draw_text(sf.img, 'ಶುಭ ಹಾರೈಕೆ', sf.s(dot_x + 14), sf.s(by + 30), f_badge, Role.text_hi)
    
    return sf.img.resize((W, 220), Image.Resampling.LANCZOS)


def render_mp_lower_third(ss: int = SS) -> Image.Image:
    """Authoritative, respectful Lower-Third super for MP B. Y. Raghavendra."""
    card_h = 250
    sf = sfx.Surface(W, card_h, ss=ss, bg=(0, 0, 0, 0))
    
    x = 48
    w = W - 96
    y = 12
    h = 226
    
    # Dark ink panel with luxury glassmorphism
    panel_img = Image.new('RGBA', (int(w * ss), int(h * ss)), (*C.ink_950, 238))
    sf.img.alpha_composite(panel_img, (int(x * ss), int(y * ss)))
    
    # Gold accent top rule
    sf.draw.line([sf.s(x), sf.s(y), sf.s(x + w) - 1, sf.s(y)], fill=(*C.gold_500, 255), width=max(1, int(4 * ss)))
    
    # Gold vertical accent bar on the left
    sf.draw.rectangle([sf.s(x), sf.s(y), sf.s(x + 8) - 1, sf.s(y + h) - 1], fill=C.gold_500)
    
    # Subtitle eyebrow / Context pill
    f_eyebrow = typo.font('kn_var', int(sf.s(22)), weight=700)
    # Draw small gold chip
    sf.draw.rectangle([sf.s(x + 28), sf.s(y + 20), sf.s(x + 36), sf.s(y + 40)], fill=C.gold_500)
    typo.draw_text(sf.img, 'ಬೈಂದೂರು ಭೇಟಿ  •  ವಿಶೇಷ ಸಂದರ್ಶನ', sf.s(x + 46), sf.s(y + 36), f_eyebrow, C.gold_400)
    
    # Main Name: ಬಿ. ವೈ. ರಾಘವೇಂದ್ರ
    f_name = typo.font('kn', int(sf.s(54)))
    typo.draw_text(sf.img, 'ಬಿ. ವೈ. ರಾಘವೇಂದ್ರ', sf.s(x + 28), sf.s(y + 104), f_name, Role.text_hi)
    
    # Designation: ಸಂಸದರು, ಶಿವಮೊಗ್ಗ ಲೋಕಸಭಾ ಕ್ಷೇತ್ರ
    f_desig = typo.font('kn_var', int(sf.s(29)), weight=600)
    typo.draw_text(sf.img, 'ಸಂಸದರು, ಶಿವಮೊಗ್ಗ ಲೋಕಸಭಾ ಕ್ಷೇತ್ರ (ಬೈಂದೂರು)', sf.s(x + 28), sf.s(y + 154), f_desig, Role.text)
    
    # Channel note
    f_sub = typo.font('kn_var', int(sf.s(23)), weight=550)
    typo.draw_text(sf.img, '‘ಊರ್ಮನಿ ಸುದ್ದಿ’ ಡಿಜಿಟಲ್ ವಾಹಿನಿಗೆ ಹೃತ್ಪೂರ್ವಕ ಶುಭಾಶಯ', sf.s(x + 28), sf.s(y + 196), f_sub, C.gold_500)
    
    return sf.img.resize((W, card_h), Image.Resampling.LANCZOS)


def render_quote_card(header: str, quote: str, ss: int = SS) -> Image.Image:
    """Soundbite quote card highlighting key statements."""
    card_h = 230
    sf = sfx.Surface(W, card_h, ss=ss, bg=(0, 0, 0, 0))
    
    x = 48
    w = W - 96
    y = 16
    h = 200
    
    # Dark panel
    panel_img = Image.new('RGBA', (int(w * ss), int(h * ss)), (*C.ink_950, 238))
    sf.img.alpha_composite(panel_img, (int(x * ss), int(y * ss)))
    
    # Hairline outline with gold
    sf.draw.rectangle([sf.s(x), sf.s(y), sf.s(x + w) - 1, sf.s(y + h) - 1],
                      outline=(*C.gold_500, 180), width=max(1, int(1.5 * ss)))
    
    # Gold top pill tag
    f_tag = typo.font('kn_var', int(sf.s(22)), weight=750)
    tag_w = typo.text_width(header, f_tag) / ss + 40
    sf.draw.rectangle([sf.s(x + 24), sf.s(y - 14), sf.s(x + 24 + tag_w), sf.s(y + 20)],
                      fill=C.gold_500)
    typo.draw_text(sf.img, header, sf.s(x + 44), sf.s(y + 12), f_tag, C.ink_950)
    
    # Quote text wrapped
    f_quote = typo.font('kn_var', int(sf.s(32)), weight=650)
    lines = typo.wrap(quote, f_quote, sf.s(w - 60))
    
    cur_y = y + 70
    for line in lines[:3]:
        typo.draw_text(sf.img, line, sf.s(x + 30), sf.s(cur_y), f_quote, Role.text_hi)
        cur_y += 44
        
    return sf.img.resize((W, card_h), Image.Resampling.LANCZOS)


def render_outro_bed(ss: int = SS) -> Image.Image:
    """Create the rich outro bed with sunset glow and horizon."""
    sf = sfx.Surface(W, H, ss=ss)
    cp.page_base(sf, 0.95)
    sfx.radial_glow(sf, W * 0.5, H * 0.40, W * 1.30, C.gold_700, 0.40)
    sfx.radial_glow(sf, W * 0.5, H * 0.40, W * 0.65, C.gold_600, 0.35)
    sfx.radial_glow(sf, W * 0.5, H * 0.40, W * 0.32, C.gold_500, 0.25)
    cp.horizon(sf, H * 0.615, 1.0)
    sfx.grain(sf, Grade.grain, Grade.grain_shadow_bias)
    return sf.finish()


def render_outro_frame(t_in_outro: float, bed: Image.Image, ss: int = SS) -> Image.Image:
    """Render animated outro frame with easing."""
    f = bed.copy().convert('RGBA')
    
    # Logo animation
    p_logo = phase(t_in_outro, 0.0, 0.8, Ease.out_back)
    size = int(240 * (0.80 + 0.20 * p_logo))
    logo_path = os.path.join(BASE, 'assets', 'logo_clean_circle.png')
    if os.path.exists(logo_path):
        lg = Image.open(logo_path).convert('RGBA').resize((size, size), Image.Resampling.LANCZOS)
        if p_logo < 1.0:
            lg.putalpha(lg.getchannel('A').point(lambda v: int(v * clamp01(p_logo * 1.5))))
        f.alpha_composite(lg, ((W - size) // 2, int(H * 0.30) - size // 2))
    
    # Typography overlay
    sf_txt = sfx.Surface(W, H, ss=ss, bg=(0, 0, 0, 0))
    
    # Channel Name
    p_name = phase(t_in_outro, 0.25, 0.55, Ease.out_quint)
    if p_name > 0:
        dy = int(25 * (1.0 - p_name))
        f_title = typo.font('kn', int(sf_txt.s(82)))
        typo.draw_text(sf_txt.img, Brand.name, sf_txt.s(W / 2), sf_txt.s(H * 0.48 + dy), f_title, Role.text_hi, anchor_x='c')
    
    # Tagline
    p_tag = phase(t_in_outro, 0.40, 0.55, Ease.out_quint)
    if p_tag > 0:
        dy = int(20 * (1.0 - p_tag))
        f_tag = typo.font('kn_var', int(sf_txt.s(36)), weight=650)
        typo.draw_text(sf_txt.img, Brand.tagline, sf_txt.s(W / 2), sf_txt.s(H * 0.54 + dy), f_tag, C.gold_500, anchor_x='c')
    
    # CTA: ಲೈಕ್ ಮಾಡಿ • ಶೇರ್ ಮಾಡಿ • ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ
    p_cta = phase(t_in_outro, 0.55, 0.55, Ease.out_quint)
    if p_cta > 0:
        dy = int(18 * (1.0 - p_cta))
        f_cta = typo.font('kn_var', int(sf_txt.s(32)), weight=600)
        typo.draw_text(sf_txt.img, 'ಲೈಕ್ ಮಾಡಿ  •  ಶೇರ್ ಮಾಡಿ  •  ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ', sf_txt.s(W / 2), sf_txt.s(H * 0.62 + dy), f_cta, Role.text, anchor_x='c')
    
    # Social Handle: @OormaniSuddi
    p_handle = phase(t_in_outro, 0.70, 0.55, Ease.out_quint)
    if p_handle > 0:
        dy = int(22 * (1.0 - p_handle))
        f_handle = typo.font('latin', int(sf_txt.s(68)), weight=780)
        typo.draw_text(sf_txt.img, Brand.handle, sf_txt.s(W / 2), sf_txt.s(H * 0.70 + dy), f_handle, C.gold_500, anchor_x='c', tracking=0.01)
    
    # Coverage: ಕರಾವಳಿ
    p_where = phase(t_in_outro, 0.85, 0.50, Ease.out_quint)
    if p_where > 0:
        dy = int(15 * (1.0 - p_where))
        f_where = typo.font('kn_var', int(sf_txt.s(28)), weight=500)
        typo.draw_text(sf_txt.img, 'ನಮ್ಮ ಕರಾವಳಿಯ ವಿಶ್ವಾಸಾರ್ಹ ಡಿಜಿಟಲ್ ಸುದ್ದಿ ವಾಹಿನಿ', sf_txt.s(W / 2), sf_txt.s(H * 0.76 + dy), f_where, Role.text_dim, anchor_x='c')
    
    txt_layer = sf_txt.img.resize((W, H), Image.Resampling.LANCZOS)
    f.alpha_composite(txt_layer)
    return f.convert('RGB')


# ─────────────────────────────────────────────────────────────────────────────
#  COLOR GRADING & COMPOSITING
# ─────────────────────────────────────────────────────────────────────────────

def color_grade_frame(frame: Image.Image) -> Image.Image:
    """House Broadcast Color Grade.
    Lifts contrast, balances coastal sunset warmth, and restores sharpness.
    """
    # 1. Contrast enhancement (S-curve feel)
    enh_c = ImageEnhance.Contrast(frame).enhance(1.09)
    # 2. Brightness balance
    enh_b = ImageEnhance.Brightness(enh_c).enhance(1.02)
    # 3. Rich skin tone & warm vibrancy
    enh_s = ImageEnhance.Color(enh_b).enhance(1.14)
    # 4. Broadcast detail sharpening
    sharp = enh_s.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=2))
    return sharp


def build_bottom_scrim() -> Image.Image:
    """Bottom gradient scrim to protect lower thirds against bright clothing/ground."""
    scrim = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(scrim)
    for y in range(1250, 1920):
        t = (y - 1250) / 670.0
        # Smoothstep curve
        s = t * t * (3.0 - 2.0 * t)
        alpha_val = int(225 * s)
        d.line([(0, y), (W, y)], fill=(*C.ink_950, alpha_val))
    return scrim


def progress_bar(frame: Image.Image, p: float):
    """Sleek top gold progress bar."""
    h = 4
    d = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    d.paste((*C.paper_50, 40), (0, 0, W, h))
    d.paste((*C.gold_500, 255), (0, 0, max(1, int(W * clamp01(p))), h))
    frame.alpha_composite(d, (0, 0))


# ─────────────────────────────────────────────────────────────────────────────
#  AUDIO PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def master_audio(output_audio_path: str) -> str:
    """Master dialogue with highpass, vocal EQ, compression, ducked BGM, and new studio SFX."""
    print("  Mastering broadcast audio with new studio SFX & score ducking...")
    
    # 1. Extract and enhance speech from source
    raw_speech = os.path.join(BUILD_DIR, "raw_speech.wav")
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-ss', str(T_START), '-to', str(T_END),
        '-i', INPUT_VIDEO,
        # Highpass wind filter + vocal presence EQ + compression + leveling
        '-af', 'highpass=f=90,lowpass=f=12000,equalizer=f=3000:t=q:w=1.2:g=3.5,equalizer=f=320:t=q:w=1.5:g=-2.5,acompressor=threshold=-18dB:ratio=3.2:attack=15:release=120,volume=2.2',
        '-ar', '48000', '-ac', '2', raw_speech
    ], check=True)
    
    # 2. Studio Sound Effects
    bgm_file = os.path.join(BASE, 'assets', 'news_bgm.mp3')
    pro_impact = os.path.join(BASE, 'sfx', 'pro_impact.wav')
    pro_whoosh = os.path.join(BASE, 'sfx', 'pro_whoosh.wav')
    pro_card_swipe = os.path.join(BASE, 'sfx', 'pro_card_swipe.wav')
    pro_outro_hit = os.path.join(BASE, 'sfx', 'pro_outro_hit.wav')
    
    filter_complex = (
        # Dialogue: delay 0, hold for SPEECH_DUR, smooth fade out at end
        f"[0:a]atrim=0:{SPEECH_DUR:.2f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.25,afade=t=out:st={SPEECH_DUR-0.35:.2f}:d=0.35[vox];"
        # BGM: ducked during speech (-23dB / vol=0.075), swells during outro to vol=0.55
        f"[1:a]atrim=0:{TOTAL_DUR:.2f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.8,afade=t=out:st={TOTAL_DUR-1.5:.2f}:d=1.5,"
        f"volume=enable='between(t,0,{SPEECH_DUR-0.5:.2f})':volume=0.075,"
        f"volume=enable='between(t,{SPEECH_DUR-0.5:.2f},{TOTAL_DUR:.2f})':volume=0.55[bgm];"
        # SFX 1: Lower third entrance (Impact + whoosh layered at t=0.5s)
        f"[2:a]adelay=500|500,volume=0.35[sfx_lt_impact];"
        f"[3:a]adelay=450|450,volume=0.25[sfx_lt_whoosh];"
        # SFX 2: Outro entrance (Outro hit + whoosh at t=51.1s)
        f"[4:a]adelay={int(SPEECH_DUR*1000)}|{int(SPEECH_DUR*1000)},volume=0.55[sfx_outro_hit];"
        f"[3:a]adelay={int((SPEECH_DUR-0.1)*1000)}|{int((SPEECH_DUR-0.1)*1000)},volume=0.35[sfx_outro_whoosh];"
        # SFX 3: Clean card transitions at soundbites
        f"[5:a]adelay=12000|12000,volume=0.22[sw1];"
        f"[5:a]adelay=23500|23500,volume=0.22[sw2];"
        f"[5:a]adelay=35000|35000,volume=0.22[sw3];"
        f"[5:a]adelay=44500|44500,volume=0.22[sw4];"
        # Mix all tracks together and apply broadcast loudnorm (-14 LUFS / -1.5 dBTP)
        f"[vox][bgm][sfx_lt_impact][sfx_lt_whoosh][sfx_outro_hit][sfx_outro_whoosh][sw1][sw2][sw3][sw4]amix=inputs=10:duration=first:dropout_transition=2,"
        f"loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
    )
    
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-i', raw_speech,
        '-i', bgm_file,
        '-i', pro_impact,
        '-i', pro_whoosh,
        '-i', pro_outro_hit,
        '-i', pro_card_swipe,
        '-filter_complex', filter_complex,
        '-map', '[aout]',
        '-c:a', 'pcm_s16le',
        output_audio_path
    ], check=True)
    
    print("  ✓ New studio audio & SFX mastered (-14 LUFS / -1.5 dBTP)")
    return output_audio_path


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN RENDERING PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def render_full_video():
    print(f"🎬 Starting Oormani Suddi MP Bit Render...")
    print(f"   Resolution: {W}x{H} (9:16 Full HD 1080p)")
    print(f"   Speech Duration: {SPEECH_DUR:.1f}s | Outro: {OUTRO_DUR:.1f}s | Total: {TOTAL_DUR:.1f}s")
    
    # 1. Pre-render static layers
    print("  Pre-rendering broadcast graphic sprites...")
    masthead_img = render_top_masthead()
    lt_mp = render_mp_lower_third()
    bottom_scrim = build_bottom_scrim()
    
    qc1 = render_quote_card('ವಿಶೇಷ ಮೆಚ್ಚುಗೆ', '"AI ತಂತ್ರಜ್ಞಾನ ಬಳಸಿ ಕರಾವಳಿಯ ಪರಂಪರೆ ಉಳಿಸುವ ಉತ್ತಮ ಕಾರ್ಯ"')
    qc2 = render_quote_card('ಸಂಪರ್ಕ ಸೇತುವೆ', '"ಮುಂದಿನ ಪೀಳಿಗೆಗೆ ಮತ್ತು ಯುವಜನತೆಗೆ ಕರಾವಳಿ ಸಂಸ್ಕೃತಿ ತಲುಪಿಸುವ ಸೇತುವೆ"')
    qc3 = render_quote_card('ಯಶಸ್ವಿ ಹೆಜ್ಜೆ', '"‘ಊರ್ಮನಿ ಸುದ್ದಿ’ ತಂಡಕ್ಕೆ ನನ್ನ ಹೃತ್ಪೂರ್ವಕ ಅಭಿನಂದನೆಗಳು ಹಾಗೂ ಶುಭ ಹಾರೈಕೆ"')
    qc4 = render_quote_card('ನಾಡಿನ ಕರೆ', '"ಹೊರಗಿರುವ ಯುವಜನತೆಯನ್ನು ನಮ್ಮ ನಾಡಿನ ಕಡೆಗೆ ಸೆಳೆಯುವ ಮಹತ್ತರ ಕಾರ್ಯ"')
    
    outro_bed = render_outro_bed()
    
    # 2. Extract video frames from source
    video_frames_dir = os.path.join(BUILD_DIR, "source_frames")
    os.makedirs(video_frames_dir, exist_ok=True)
    
    print("  Extracting source video frames at 30 fps...")
    # Clear old frames
    for f in os.listdir(video_frames_dir):
        if f.endswith('.jpg') or f.endswith('.png'):
            os.remove(os.path.join(video_frames_dir, f))
            
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-ss', str(T_START), '-to', str(T_END),
        '-i', INPUT_VIDEO,
        '-vf', f'fps={FPS},scale={W}:{H}:flags=lanczos',
        '-q:v', '2',
        os.path.join(video_frames_dir, 'f_%05d.jpg')
    ], check=True)
    
    extracted_frames = sorted([f for f in os.listdir(video_frames_dir) if f.startswith('f_') and f.endswith('.jpg')])
    n_speech_frames = len(extracted_frames)
    n_outro_frames = int(round(OUTRO_DUR * FPS))
    total_frames = n_speech_frames + n_outro_frames
    
    print(f"  Extracted {n_speech_frames} video frames + {n_outro_frames} outro frames = {total_frames} total frames")
    
    # 3. Setup FFmpeg video encoder pipe
    temp_video_path = os.path.join(BUILD_DIR, "temp_graded_video.mp4")
    enc = subprocess.Popen([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
        '-r', str(FPS), '-i', 'pipe:0',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
        '-maxrate', '14M', '-bufsize', '28M',
        '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.2',
        '-x264-params', 'ref=4:bframes=3',
        '-movflags', '+faststart', temp_video_path
    ], stdin=subprocess.PIPE)
    
    print("  Rendering and compositing video frames...")
    
    # Process speech frames
    for i, fname in enumerate(extracted_frames):
        t = i / float(FPS)
        frame_path = os.path.join(video_frames_dir, fname)
        raw_f = Image.open(frame_path).convert('RGB')
        
        # House color grade
        graded_f = color_grade_frame(raw_f).convert('RGBA')
        
        # Composite bottom scrim
        graded_f.alpha_composite(bottom_scrim)
        
        # Masthead entrance (slide down 0.0s -> 0.6s)
        p_mast = phase(t, 0.0, 0.6, Ease.out_quint)
        if p_mast > 0:
            dy_mast = int(30 * (1.0 - p_mast))
            graded_f.alpha_composite(masthead_img, (0, -dy_mast))
            
        # Lower-third timeline
        # 0.5s -> 11.5s: MP Raghavendra identification super
        if t < 12.0:
            # Entry at 0.5s (dur 0.6s), exit at 11.2s (dur 0.5s)
            p_in = phase(t, 0.5, 0.6, Ease.out_quint)
            p_out = phase(t, 11.2, 0.5, Ease.out_quint)
            if p_in > 0 and p_out < 1.0:
                dy = int(35 * (1.0 - p_in)) + int(35 * p_out)
                alpha_mult = p_in * (1.0 - p_out)
                lt_copy = lt_mp.copy()
                if alpha_mult < 1.0:
                    lt_copy.putalpha(lt_copy.getchannel('A').point(lambda v: int(v * alpha_mult)))
                graded_f.alpha_composite(lt_copy, (0, 1570 + dy))
        
        # 12.0s -> 23.5s: Quote Card 1 (AI Tech & Heritage)
        elif 12.0 <= t < 23.5:
            p_in = phase(t, 12.0, 0.5, Ease.out_quint)
            p_out = phase(t, 22.8, 0.4, Ease.out_quint)
            if p_in > 0 and p_out < 1.0:
                dy = int(30 * (1.0 - p_in)) + int(30 * p_out)
                alpha_mult = p_in * (1.0 - p_out)
                qc = qc1.copy()
                if alpha_mult < 1.0:
                    qc.putalpha(qc.getchannel('A').point(lambda v: int(v * alpha_mult)))
                graded_f.alpha_composite(qc, (0, 1590 + dy))
                
        # 23.5s -> 35.0s: Quote Card 2 (Generational Bridge)
        elif 23.5 <= t < 35.0:
            p_in = phase(t, 23.5, 0.5, Ease.out_quint)
            p_out = phase(t, 34.3, 0.4, Ease.out_quint)
            if p_in > 0 and p_out < 1.0:
                dy = int(30 * (1.0 - p_in)) + int(30 * p_out)
                alpha_mult = p_in * (1.0 - p_out)
                qc = qc2.copy()
                if alpha_mult < 1.0:
                    qc.putalpha(qc.getchannel('A').point(lambda v: int(v * alpha_mult)))
                graded_f.alpha_composite(qc, (0, 1590 + dy))
                
        # 35.0s -> 44.5s: Quote Card 3 (Appreciation & Best Wishes)
        elif 35.0 <= t < 44.5:
            p_in = phase(t, 35.0, 0.5, Ease.out_quint)
            p_out = phase(t, 43.8, 0.4, Ease.out_quint)
            if p_in > 0 and p_out < 1.0:
                dy = int(30 * (1.0 - p_in)) + int(30 * p_out)
                alpha_mult = p_in * (1.0 - p_out)
                qc = qc3.copy()
                if alpha_mult < 1.0:
                    qc.putalpha(qc.getchannel('A').point(lambda v: int(v * alpha_mult)))
                graded_f.alpha_composite(qc, (0, 1590 + dy))
                
        # 44.5s -> 51.1s: Quote Card 4 (Call to Youth)
        elif 44.5 <= t:
            p_in = phase(t, 44.5, 0.5, Ease.out_quint)
            p_out = phase(t, 50.4, 0.4, Ease.out_quint)
            if p_in > 0 and p_out < 1.0:
                dy = int(30 * (1.0 - p_in)) + int(30 * p_out)
                alpha_mult = p_in * (1.0 - p_out)
                qc = qc4.copy()
                if alpha_mult < 1.0:
                    qc.putalpha(qc.getchannel('A').point(lambda v: int(v * alpha_mult)))
                graded_f.alpha_composite(qc, (0, 1590 + dy))
        
        # Top gold progress bar
        progress_bar(graded_f, t / TOTAL_DUR)
        
        enc.stdin.write(graded_f.convert('RGB').tobytes())
        if i % 90 == 0 or i == n_speech_frames - 1:
            print(f"    Speech frame {i+1}/{n_speech_frames} ({t:4.1f}s / {SPEECH_DUR:4.1f}s)", end='\r')
            
    # Process outro frames (with smooth crossfade transition)
    print("\n  Rendering outro scene...")
    last_speech_frame = graded_f.convert('RGB')
    
    for j in range(n_outro_frames):
        t_outro = j / float(FPS)
        t_global = SPEECH_DUR + t_outro
        
        outro_f = render_outro_frame(t_outro, outro_bed)
        
        # Smooth 0.5s crossfade from video to outro
        if t_outro < 0.5:
            p_fade = Ease.in_out_cubic(t_outro / 0.5)
            f_final = Image.blend(last_speech_frame, outro_f, p_fade).convert('RGBA')
        else:
            f_final = outro_f.convert('RGBA')
            
        progress_bar(f_final, t_global / TOTAL_DUR)
        enc.stdin.write(f_final.convert('RGB').tobytes())
        
    enc.stdin.close()
    enc.wait()
    print("  ✓ Picture locked and encoded")
    
    # 4. Master and mix audio
    mastered_audio_path = os.path.join(BUILD_DIR, "mastered_audio.wav")
    master_audio(mastered_audio_path)
    
    # 5. Mux video and audio together
    print(f"  Muxing final deliverable -> {OUTPUT_VIDEO}")
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-i', temp_video_path,
        '-i', mastered_audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '256k',
        '-movflags', '+faststart',
        OUTPUT_VIDEO
    ], check=True)
    
    print(f"\n🎉 Finished successfully! Deliverable saved at:\n   {OUTPUT_VIDEO}")
    return OUTPUT_VIDEO


if __name__ == '__main__':
    render_full_video()
