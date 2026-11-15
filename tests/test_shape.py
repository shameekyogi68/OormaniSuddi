"""A wrong-shaped edition is refused in words, never with a traceback (D150).

The JSON is written by whichever AI tool the editor is using that day. Before
D150 a number where a sentence goes, one string where a list goes, or a file
cut off half-way surfaced as a Python traceback from deep inside a renderer —
which tells the tool nothing it can act on, and on a deadline reads as "the
system is broken". Every case below was measured crashing at least one daily
command on 2026-11-15; each must now be a ContentError that names the field.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

from brand.content import ContentError, Edition, read_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GOOD = {
    'schema_version': 4, 'date': '2026-11-14',
    'stories': [
        {'segment': 'saara', 'headline': 'ಉಡುಪಿ: ರಸ್ತೆ ದುರಸ್ತಿ ಆರಂಭ', 'category': 'civic',
         'deck': 'ನಗರಸಭೆ ಕಾಮಗಾರಿ ಆರಂಭಿಸಿದೆ.', 'points': ['ಒಂದು', 'ಎರಡು'],
         'sources': ['ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ'], 'status': 'confirmed',
         'published_at': '2026-11-14T08:00:00+05:30', 'location': 'ಉಡುಪಿ'},
        {'segment': 'saara', 'headline': 'ಕುಂದಾಪುರ: ಶಾಲೆಗೆ ಹೊಸ ಕಟ್ಟಡ', 'category': 'education',
         'deck': 'ಕಟ್ಟಡ ಉದ್ಘಾಟನೆಯಾಗಿದೆ.', 'points': ['ಒಂದು'],
         'sources': ['ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ'], 'status': 'confirmed',
         'published_at': '2026-11-14T08:00:00+05:30', 'location': 'ಕುಂದಾಪುರ'},
    ],
}


def _story(key, value, n=0):
    def f(d):
        d['stories'][n][key] = value
    return f


def _top(key, value):
    def f(d):
        d[key] = value
    return f


# name → (mutation, a word the message must contain)
BROKEN = {
    'stories is null':        (_top('stories', None), 'stories'),
    'stories is an object':   (_top('stories', {'a': 1}), 'stories'),
    'a story is a string':    (_top('stories', ['x']), 'story 1'),
    'no stories':             (_top('stories', []), 'at least one story'),
    'date is not a date':     (_top('date', 'tomorrow'), 'not a date'),
    'schema is a string':     (_top('schema_version', '4'), 'schema_version'),
    'edition_no is a word':   (_top('edition_no', 'one'), 'edition_no'),
    'strapline is a number':  (_top('strapline', 3), 'strapline'),
    'headline missing':       (lambda d: d['stories'][0].pop('headline'), 'headline'),
    'headline null':          (_story('headline', None), 'headline'),
    'headline a number':      (_story('headline', 5), 'headline'),
    'headline a list':        (_story('headline', ['a']), 'headline'),
    'deck null':              (_story('deck', None), 'deck'),
    'points one string':      (_story('points', 'abc'), 'points'),
    'points of numbers':      (_story('points', [1, 2]), 'points[1]'),
    'sources one string':     (_story('sources', 'x'), 'sources'),
    'source_urls null':       (_story('source_urls', None), 'source_urls'),
    'reel_line a number':     (_story('reel_line', 7), 'reel_line'),
    'segment null':           (_story('segment', None), 'segment'),
    'category null':          (_story('category', None), 'category'),
    'minor flag a word':      (_story('involves_minor', 'yes'), 'involves_minor'),
    'published_at nonsense':  (_story('published_at', 'now'), 'not a date'),
    'verified_at a number':   (_story('verified_at', 5), 'not a date'),
    'photo a file name':      (_story('photo', 'a.jpg'), 'photo'),
    'photo path a number':    (_story('photo', {'path': 5}), 'path'),
    'photo focal a word':     (_story('photo', {'path': 'a.jpg', 'focal': 'mid'}), 'focal'),
    'gallery one string':     (_story('gallery', 'a'), 'gallery'),
    'numbers not pairs':      (_story('numbers', [1]), 'numbers'),
    'quote one string':       (_story('quote', 'hi'), 'quote'),
    'unknown field':          (_story('zzz', 1), 'zzz'),
}


def _broken(name):
    d = copy.deepcopy(GOOD)
    BROKEN[name][0](d)
    return d


class TheShapeIsCheckedAtTheDoor(unittest.TestCase):

    def test_the_good_edition_loads(self):
        self.assertEqual(len(Edition.from_dict(copy.deepcopy(GOOD)).stories), 2)

    def test_every_wrong_shape_is_a_content_error_that_names_the_field(self):
        for name, (_, word) in BROKEN.items():
            with self.subTest(name):
                with self.assertRaises(ContentError) as cm:
                    Edition.from_dict(_broken(name))
                self.assertIn(word, str(cm.exception))

    def test_the_message_says_which_story(self):
        d = copy.deepcopy(GOOD)
        d['stories'][1]['points'] = 'abc'
        with self.assertRaises(ContentError) as cm:
            Edition.from_dict(d)
        self.assertTrue(str(cm.exception).startswith('story 2:'), cm.exception)

    def test_the_top_level_must_be_an_object(self):
        for raw in (5, 'x', None):
            with self.subTest(raw=raw), self.assertRaises(ContentError):
                Edition.from_dict(raw)


class TheFileItself(unittest.TestCase):

    def _file(self, text):
        fd, p = tempfile.mkstemp(suffix='.json')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
        self.addCleanup(os.remove, p)
        return p

    def test_a_missing_file(self):
        with self.assertRaises(ContentError) as cm:
            read_json(os.path.join(tempfile.gettempdir(), 'no-such-edition.json'))
        self.assertIn('no such file', str(cm.exception))

    def test_an_empty_file(self):
        with self.assertRaises(ContentError) as cm:
            read_json(self._file('  \n'))
        self.assertIn('empty', str(cm.exception))

    def test_a_file_cut_off_half_way_says_where(self):
        with self.assertRaises(ContentError) as cm:
            read_json(self._file('{"stories": [\n  {"headline": "x",'))
        self.assertIn('line 2', str(cm.exception))


class NoDailyCommandShowsATraceback(unittest.TestCase):
    """The commands the editor's AI runs every morning, fed each broken file."""

    COMMANDS = (
        ['render.py', '--check'],
        [os.path.join('scripts', 'fact_check.py')],
        [os.path.join('scripts', 'intake.py'), 'seen'],
        [os.path.join('scripts', 'reel_check.py')],
        [os.path.join('scripts', 'regate.py')],
        [os.path.join('scripts', 'pick_formats.py')],
    )
    # One of each kind of fault; the unit test above covers every field.
    SAMPLE = ('stories is null', 'a story is a string', 'headline a number',
              'points one string', 'date is not a date', 'photo a file name')

    def _run(self, cmd, path):
        return subprocess.run([sys.executable, *cmd, path], cwd=ROOT,
                              capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=120)

    def test_broken_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = {}
            for name in self.SAMPLE:
                files[name] = os.path.join(tmp, name.replace(' ', '_') + '.json')
                with open(files[name], 'w', encoding='utf-8') as f:
                    json.dump(_broken(name), f, ensure_ascii=False)
            files['cut off'] = os.path.join(tmp, 'cut.json')
            with open(files['cut off'], 'w', encoding='utf-8') as f:
                f.write('{"stories": [')
            files['missing'] = os.path.join(tmp, 'nope.json')
            # side by side: forty short processes, not forty in a queue
            from concurrent.futures import ThreadPoolExecutor
            jobs = [(cmd, name, path) for cmd in self.COMMANDS for name, path in files.items()]
            with ThreadPoolExecutor(max_workers=8) as pool:
                done = list(pool.map(lambda j: self._run(j[0], j[2]), jobs))
            for (cmd, name, _), r in zip(jobs, done):
                with self.subTest(cmd=cmd[0], file=name):
                    self.assertNotIn('Traceback', r.stderr + r.stdout)


if __name__ == '__main__':
    unittest.main()
