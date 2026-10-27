"""D145 — the reel standard exists, and everything it tells an AI to run exists."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TheStandardIsReal(unittest.TestCase):
    def test_every_command_and_file_it_names_exists(self):
        text = (ROOT / 'docs' / 'REEL_STANDARD.md').read_text(encoding='utf-8')
        for rel in set(re.findall(r'(?:scripts|brand|docs|assets)/[\w./-]+\.(?:py|md|json)', text)):
            self.assertTrue((ROOT / rel).exists(), f'{rel} is named in docs/REEL_STANDARD.md and does not exist')

    def test_both_ai_folders_point_at_it_and_the_skill_copies_match(self):
        self.assertIn('REEL_STANDARD.md', (ROOT / '.agents/rules/reel-quality-standard.md').read_text(encoding='utf-8'))
        self.assertIn('REEL_STANDARD.md', (ROOT / 'AGENTS.md').read_text(encoding='utf-8'))
        self.assertEqual((ROOT / '.claude/skills/daily-saara/SKILL.md').read_bytes(),
                         (ROOT / '.agents/skills/daily-saara/SKILL.md').read_bytes())

    def test_the_numbers_it_quotes_are_the_code_s(self):
        from brand.tokens import Limits
        text = (ROOT / 'docs' / 'REEL_STANDARD.md').read_text(encoding='utf-8')
        self.assertIn(f'{int(Limits.saara_reel_max_seconds)} s', text)
        self.assertIn(f'{Limits.saara_reel_town_pause}', text)


if __name__ == '__main__':
    unittest.main()
