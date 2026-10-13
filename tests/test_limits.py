"""
One home for a number, or the two homes drift. D56.
====================================================
`templates/registry.json` tells an outside caller what a format rejects and
how much of it the format takes; `tokens.Limits` is the machine home the
gates and skills read. The registry's `limits` dicts are built FROM
`tokens.Limits` (templates/__init__._limits) — this suite pins that they
stay built from it. If someone hand-edits a number back into the Spec, or
renames a Limits field, this fails before the two homes can silently
disagree.
"""

# Enforces D121 — see docs/DECISIONS.md.
from __future__ import annotations

import unittest

from brand.tokens import Limits
from templates import TEMPLATES


# Every numeric entry in TEMPLATES[k].limits, mapped to its namesake in
# tokens.Limits. 'target_seconds_max' is a whole-second cap; the registry
# says 45 and reel_target_max is 45.0 — assertEqual treats them as equal,
# and the Spec stores int() of it so the dumped JSON stays value-identical.
NAMESAKES = {
    'saara': {'stories_min': 'saara_min_stories',
              'stories_max': 'saara_max_stories',
              'points': 'points_max'},
    'mukhya': {'per_day': 'mukhya_max_per_day',
               'points': 'points_max'},
    'roundup': {'stories_min': 'roundup_min_stories',
                'reel_line_chars': 'reel_line_chars',
                'target_seconds_max': 'reel_target_max'},
}


class LimitsAreSingleSourced(unittest.TestCase):

    def test_every_news_format_limit_has_a_limits_namesake(self):
        for key, mapping in NAMESAKES.items():
            with self.subTest(format=key):
                limits = TEMPLATES[key].limits
                self.assertEqual(set(limits), set(mapping),
                                 f'{key}: a limit with no namesake (or a '
                                 f'namesake with no limit) was added by hand')

    def test_limits_values_equal_their_namesakes(self):
        for key, mapping in NAMESAKES.items():
            for limit_key, limits_attr in mapping.items():
                with self.subTest(format=key, limit=limit_key):
                    self.assertEqual(TEMPLATES[key].limits[limit_key],
                                     getattr(Limits, limits_attr))

    def test_greeting_limits_have_no_limits_namesake(self):
        # The greeting caps are a genre of their own (D54) and live only in
        # the Spec — pin that none of them quietly shadows a Limits field.
        limits_names = {n for n in dir(Limits)
                        if not n.startswith('_')}
        for k, v in TEMPLATES['greeting'].limits.items():
            with self.subTest(limit=k):
                self.assertNotIn(k, limits_names)
                self.assertIsInstance(v, (int, str))


if __name__ == '__main__':
    unittest.main()
