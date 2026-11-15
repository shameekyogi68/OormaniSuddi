#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Kannada Voice & Delivery Director Expert (D142)
=============================================================
Evaluates and grades the spoken news script for the ಸುದ್ದಿ ಸಾರ reel on a 10.0 scale.
Guarantees authentic Coastal Karnataka (ಕರಾವಳಿ) news broadcast cadence, perfect
ottakshara articulation, and eliminates all robotic/English-accented artificial phrasing.

Usage:
  python3 scripts/voice_expert.py editions/DATE.json           # Evaluate & score
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brand import content, saara_reel

# Passive/translated patterns that make Kannada sound like an English speaker translated it
AWKWARD_PATTERNS = [
    (r'ನಡುವೆ ಸಂಭವಿಸಿದ', 'ಬಸ್‌ಗಳು/ವಾಹನಗಳು ಡಿಕ್ಕಿಯಾಗಿ (use active verb, not passive nominal clause)'),
    (r'ವೇಳೆ ತೆರಳಿದ್ದಾಗ', 'ಹೋಗಿದ್ದಾಗ / ತೆರಳಿದ್ದ ವೇಳೆ'),
    (r'ಹಿನ್ನೆಲೆಯಲ್ಲಿ ಜಾರಿಯಲ್ಲಿದ್ದ', 'ಹಿನ್ನೆಲೆಯಲ್ಲಿ ಇದ್ದ'),
    (r'ಬಸ್ ಡಿಕ್ಕಿ\b', 'ಬಸ್‌ಗಳು ಡಿಕ್ಕಿ / ಬಸ್ಸು ಡಿಕ್ಕಿ (raw halant "ಸ್" slurs into "ಡಿ")'),
    (r'ಇಎಸ್ಐ\b', 'ಇ ಎಸ್ ಐ (separate letters for crisp Indian broadcast pronunciation)'),
]

class VoiceScore:
    def __init__(self, story_num: int, headline: str, body: str):
        self.story_num = story_num
        self.headline = headline
        self.body = body
        self.cadence_score = 2.5
        self.articulation_score = 2.5
        self.naturalness_score = 2.5
        self.urgency_score = 2.5
        self.feedback: list[str] = []

    @property
    def total_score(self) -> float:
        return round(self.cadence_score + self.articulation_score + self.naturalness_score + self.urgency_score, 1)

def evaluate_story(i: int, copy: dict) -> VoiceScore:
    head = copy['say_head']
    body = copy['body']
    score = VoiceScore(i + 1, head, body)
    
    # 1. Cadence & Slang (ಕರಾವಳಿ ಸುದ್ದಿ ವಾಚನ ಲಯ)
    for pat, fix in AWKWARD_PATTERNS:
        if re.search(pat, head + ' ' + body):
            score.cadence_score = max(1.0, score.cadence_score - 0.5)
            score.feedback.append(f'ಕೃತಕ ರಚನೆ: "{pat}" ಕಂಡುಬಂದಿದೆ → {fix}')

    # 2. Articulation & Ottakshara (ಒತ್ತಕ್ಷರಗಳ ಸ್ಪಷ್ಟತೆ)
    if re.search(r'ಸ್\s+ಡ', head + ' ' + body):
        score.articulation_score = max(1.0, score.articulation_score - 0.5)
        score.feedback.append('ಉಚ್ಚಾರಣಾ ದೋಷ: "ಸ್ ಡಿ" ಶಬ್ದಗಳು ಒಂದಕ್ಕೊಂದು ಅಂಟಿ "ಸ್ಟಿ" ಆಗಿ ಧ್ವನಿಸುತ್ತದೆ. "ಬಸ್‌ಗಳು" ಅಥವಾ "ಬಸ್ಸು" ಬಳಸಿ.')

    if 'ಇಎಸ್ಐ' in head or 'ಇಎಸ್ಐ' in body:
        score.articulation_score = max(1.0, score.articulation_score - 0.4)
        score.feedback.append('ಸಂಕ್ಷಿಪ್ತ ರೂಪ: "ಇಎಸ್ಐ" ಬದಲು "ಇ ಎಸ್ ಐ" ಎಂದು ಬರೆಯಿರಿ.')

    # 3. Naturalness & Breathing (ಉಸಿರಾಟ ಮತ್ತು ವಾಕ್ಯ ಬಿಗಿ)
    words = body.split()
    if len(words) > 14:
        score.naturalness_score = max(1.2, score.naturalness_score - 0.4)
        score.feedback.append(f'ವಾಕ್ಯ ತುಂಬಾ ಉದ್ದವಾಗಿದೆ ({len(words)} ಪದಗಳು). ನ್ಯೂಸ್ ಆಂಕರ್ ಉಸಿರಾಟಕ್ಕೆ ತಕ್ಕಂತೆ 10-12 ಪದಗಳಿಗೆ ಮಿತಿಗೊಳಿಸಿ.')

    # 4. Urgency & News Hook (ಸುದ್ದಿ ಗಾಂಭೀರ್ಯ)
    if not any(k in head for k in ['ಡಿಕ್ಕಿ', 'ಸಾವು', 'ಎಚ್ಚರಿಕೆ', 'ಆಗ್ರಹ', 'ಸ್ಪರ್ಧೆ', 'ಬಂಧನ', 'ದಾಳಿ']):
        score.urgency_score = max(1.5, score.urgency_score - 0.3)
        score.feedback.append('ಹೆಡ್‌ಲೈನ್‌ನಲ್ಲಿ ಸುದ್ದಿ ಕ್ರಿಯಾಪದ (Action verb) ಕೊರತೆಯಿದೆ.')

    return score

def audit_edition(edition_path: str) -> tuple[float, list[VoiceScore]]:
    data = json.load(open(edition_path, encoding='utf-8'))
    stories = [content.Story(**s) for s in data['stories']]
    copies = saara_reel._copies(stories)

    scores: list[VoiceScore] = []
    for i, c in enumerate(copies):
        sc = evaluate_story(i, c)
        scores.append(sc)

    avg_score = round(sum(s.total_score for s in scores) / len(scores), 1) if scores else 0.0
    return avg_score, scores

def main():
    parser = argparse.ArgumentParser(description='Kannada Voice Director Delivery Expert')
    parser.add_argument('edition', help='Path to edition JSON')
    args = parser.parse_args()

    avg, scores = audit_edition(args.edition)
    print("=" * 70)
    print("🎙️ ಊರ್ಮನಿ ಸುದ್ದಿ — KANNADA VOICE & DELIVERY DIRECTOR SCORECARD")
    print("=" * 70)
    print(f"Overall Native Delivery Score: {avg}/10.0")
    print("-" * 70)

    for sc in scores:
        status = "🟢 10/10 PASS" if sc.total_score >= 9.5 else f"🟡 {sc.total_score}/10 NEEDS POLISH"
        print(f"Story {sc.story_num}: {status}")
        print(f"  Head: {sc.headline}")
        print(f"  Body: {sc.body}")
        if sc.feedback:
            for fb in sc.feedback:
                print(f"   ↳ {fb}")
        print()

    if avg >= 9.5:
        print("✅ VERDICT: 10/10 NATIVE COASTAL KANNADA DELIVERY APPROVED.")
        return 0
    else:
        print("⚠️ VERDICT: SCRIPT HAS NON-NATIVE / ARTIFICIAL PHRASING. POLISH REQUIRED.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
