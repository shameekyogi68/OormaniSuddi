"""
The room the design is pinned in.
=================================
The golden test hashes decoded pixels, so it only holds when this
interpreter shapes Kannada the way the blessed machine did. That shaping
comes from libraqm inside Pillow: without it, conjuncts break apart and the
failure surfaces as a cryptic golden mismatch hours later, in a commit that
has nothing to do with fonts.

This suite fails HERE, named and actionable, the moment the environment can
no longer hold the design. health.py reports the same condition for the
daily sit-down check; this test makes it stop-the-line.
"""

# Enforces D123 — see docs/DECISIONS.md.
from __future__ import annotations

import unittest


class TheEnvironmentCanHoldTheDesign(unittest.TestCase):

    def test_pillow_shapes_with_raqm(self):
        try:
            from PIL import features
            raqm = features.check('raqm')
        except Exception as e:              # no Pillow at all — worse
            self.fail(f'Pillow cannot report its features ({e}); reinstall '
                      f'with: python3 -m pip install --break-system-packages '
                      f'--force-reinstall Pillow')
        if not raqm:
            self.fail(
                'Pillow has no raqm — Kannada conjunct shaping will differ '
                'from the blessed design and the golden test will fail in a '
                'confusing way. Fix the environment, not the hashes:\n'
                '    python3 -m pip install --break-system-packages '
                '--force-reinstall Pillow\n'
                '(the wheel bundles libraqm; a build from source does not '
                'unless raqm is installed first).')


if __name__ == '__main__':
    unittest.main()
