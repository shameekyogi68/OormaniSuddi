"""
A missing system face never stops a render.
===========================================
D115. The Latin faces are macOS system fonts — not the channel's to ship, and
Apple has renamed SF's file between releases. A missing file used to stop
every render with "cannot open resource" (it is why CI could not run the
contract on Linux). Now Latin falls back to the house Kannada faces, which
carry full Latin, and health.py says the design is off-spec.
"""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from unittest import mock

from brand import tokens, typo


class AMissingSystemFaceFallsBack(unittest.TestCase):

    def setUp(self):
        typo.font.cache_clear()
        typo._missing_face.cache_clear()
        self.addCleanup(typo.font.cache_clear)
        self.addCleanup(typo._missing_face.cache_clear)

    def test_latin_falls_back_to_a_house_face_and_says_so(self):
        err = io.StringIO()
        with mock.patch.dict(tokens.FONTS, {'latin': '/nowhere/SFNS.ttf'}), \
                redirect_stderr(err):
            f = typo.font('latin', 40, weight=760)
            self.assertEqual(f.path, typo.font('kn_var', 40, weight=760).path)
        self.assertIn('D115', err.getvalue())

    def test_the_house_faces_set_every_latin_character_the_copy_uses(self):
        from fontTools.ttLib import TTFont
        need = set(range(0x20, 0x7f)) | {ord(c) for c in '₹•·—–’'}
        for fam in set(typo._LATIN_FALLBACK.values()):
            cmap = TTFont(typo.os.path.join(typo.BASE_DIR, tokens.FONTS[fam])).getBestCmap()
            self.assertFalse([chr(c) for c in need if c not in cmap], fam)

    def test_a_kannada_face_is_never_silently_replaced(self):
        with mock.patch.dict(tokens.FONTS, {'kn': '/nowhere/kn.ttf'}):
            typo.font.cache_clear()
            with self.assertRaises(OSError):
                typo.font('kn', 40)


if __name__ == '__main__':
    unittest.main()
