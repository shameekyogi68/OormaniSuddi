#!/usr/bin/env python3
"""
Generate Broadcast SFX for Oormani Suddi Reel
- News Stinger / Impact
- Camera Shutter Click
- Fast Cinematic Whoosh Transition
- High-Tech Notification Ping
"""

import os
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal

SFX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sfx')
os.makedirs(SFX_DIR, exist_ok=True)
SR = 44100

def save_wav(filename, audio):
    audio = audio / (np.max(np.abs(audio)) + 1e-9) * 0.95
    audio_int16 = (audio * 32767).astype(np.int16)
    path = os.path.join(SFX_DIR, filename)
    wavfile.write(path, SR, audio_int16)
    print(f"Saved SFX: {path}")

# 1. Cinematic Whoosh
def make_whoosh():
    dur = 0.6
    t = np.linspace(0, dur, int(SR * dur))
    # Noise sweep
    noise = np.random.randn(len(t))
    # Frequency modulated filter
    cutoff = np.linspace(200, 3500, len(t))
    # Envelope
    env = np.sin(np.pi * t / dur) ** 2
    # Sine sub sweep
    sub = np.sin(2 * np.pi * np.linspace(60, 240, len(t)) * t) * 0.6
    audio = (noise * 0.5 + sub) * env
    # Apply soft clipping
    audio = np.tanh(audio * 2)
    save_wav('whoosh.wav', audio)

# 2. Camera Shutter Click
def make_shutter():
    dur = 0.25
    t = np.linspace(0, dur, int(SR * dur))
    audio = np.zeros(len(t))
    
    # Click 1 (mirror up)
    c1_idx = int(0.02 * SR)
    c1_len = int(0.04 * SR)
    audio[c1_idx:c1_idx+c1_len] += np.random.randn(c1_len) * np.exp(-np.linspace(0, 15, c1_len))
    
    # Click 2 (shutter open/close)
    c2_idx = int(0.08 * SR)
    c2_len = int(0.06 * SR)
    audio[c2_idx:c2_idx+c2_len] += np.random.randn(c2_len) * np.exp(-np.linspace(0, 20, c2_len)) * 1.5
    
    # Mechanical tone
    audio += np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 30) * 0.2
    save_wav('camera_shutter.wav', audio)

# 3. News Impact Stinger
def make_stinger():
    dur = 1.2
    t = np.linspace(0, dur, int(SR * dur))
    # Low boom 50Hz dropping to 30Hz
    freq = np.linspace(80, 35, len(t))
    boom = np.sin(2 * np.pi * freq * t) * np.exp(-t * 3.5)
    # Mid punch
    punch = np.sin(2 * np.pi * 150 * t) * np.exp(-t * 12) * 0.8
    # Noise transient
    transient = np.random.randn(len(t)) * np.exp(-t * 25) * 0.5
    audio = boom + punch + transient
    save_wav('news_impact.wav', audio)

# 4. Tech Ping / Bell
def make_ping():
    dur = 0.8
    t = np.linspace(0, dur, int(SR * dur))
    f1 = np.sin(2 * np.pi * 1760 * t) * np.exp(-t * 6)
    f2 = np.sin(2 * np.pi * 2640 * t) * np.exp(-t * 8) * 0.6
    audio = f1 + f2
    save_wav('tech_ping.wav', audio)

if __name__ == '__main__':
    make_whoosh()
    make_shutter()
    make_stinger()
    make_ping()
    print("All SFX generated successfully!")
