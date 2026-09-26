"""
Fresh, ours, a real article, credited to its outlet. D88.
==========================================================
On 2026-09-24 six stories — some found by the intake, some the editor added —
all went out credited to ಉದಯವಾಣಿ with links a chatbot had produced; the
morning draft carried two stories from the 22nd and a section page as a
"source". Each of those is knowable before anybody reads a word.
"""
from __future__ import annotations

import unittest
from datetime import datetime

from brand import sourcing as S
from brand.copy import is_coastal, place_in
from brand.content import Story


def story(**kw):
    base = dict(headline='ಉಡುಪಿಯಲ್ಲಿ ಸಭೆ', category='civic',
                sources=['Daijiworld'],
                source_urls=['https://www.daijiworld.com/news/newsDisplay?newsID=1326570'])
    base.update(kw)
    return Story(**base)


class EachStoryCreditsItsOwnOutlet(unittest.TestCase):

    def test_the_right_outlet_passes(self):
        self.assertEqual(S.source_problems(story()), [])

    def test_a_link_credited_to_another_paper_is_caught(self):
        """The 24 Sept failure: everything filed under one paper's name."""
        codes = [c for c, _ in S.source_problems(story(sources=['ಉದಯವಾಣಿ']))]
        self.assertIn('FACT-06', codes)

    def test_two_outlets_need_two_credits(self):
        s = story(sources=['ದಿ ಹಿಂದೂಸ್ತಾನ್ ಗೆಜೆಟ್'], source_urls=[
            'https://kannada.thehindustangazette.com/udupi/appeal-to-vacate-rural-areas-155434',
            'https://kannada.newskarnataka.com/udupi/massive-farmers-protest-in-byndoor/07082026'])
        self.assertEqual([c for c, _ in S.source_problems(s)], ['FACT-06'])


class OnlyARealArticleIsASource(unittest.TestCase):

    def test_a_chatbot_link_is_not_a_source(self):
        u = ('https://udayavani.com/udupi-news/english-heading-bugurikadu-'
             'sugarcane-ready-for-ganesh-chaturthi-260135?lang=kn&utm_source=gemini')
        self.assertIn('chatbot', S.url_problem(u))

    def test_udayavanis_own_slug_is_not_a_placeholder(self):
        """`english-heading-…` is Udayavani's CMS slug; the article behind it
        is real. Only the chatbot tag on the end was wrong (2026-09-25)."""
        self.assertEqual(S.url_problem(
            'https://udayavani.com/udupi-news/english-heading-bugurikadu-'
            'sugarcane-ready-for-ganesh-chaturthi-260135?lang=kn'), '')

    def test_a_section_page_is_not_a_source(self):
        self.assertTrue(S.url_problem('https://www.varthabharati.in/karavali'))

    def test_a_real_article_passes(self):
        for u in ('https://www.daijiworld.com/news/newsDisplay?newsID=1326570',
                  'https://www.udayavani.com/karavali-udupi/karkala-man-of-fever',
                  'http://kannada.newskarnataka.com/mangaluru/special-gram-sabha/22092026'):
            self.assertEqual(S.url_problem(u), '', u)


class OnlyTodaysNews(unittest.TestCase):

    NOW = datetime(2026, 9, 24, 7, 0, tzinfo=S.IST)

    def test_a_dated_url_says_how_old_it_is(self):
        d = S.date_in_url('http://kannada.newskarnataka.com/x/y/22092026')
        self.assertEqual((d.year, d.month, d.day), (2026, 9, 22))

    def test_two_days_old_is_stale(self):
        d = S.date_in_url('http://kannada.newskarnataka.com/x/y/22092026')
        self.assertTrue(S.is_stale(d, self.NOW, date_only=True))

    def test_yesterday_is_still_news_this_morning(self):
        d = S.date_in_url('http://kannada.newskarnataka.com/x/y/23092026')
        self.assertFalse(S.is_stale(d, self.NOW, date_only=True))

    def test_no_date_is_not_called_stale(self):
        """Unknown is said as unknown on the tip sheet, not guessed."""
        self.assertFalse(S.is_stale(None, self.NOW))


class TheSameLetterMatchesHowever_ItIsEncoded(unittest.TestCase):

    def test_decomposed_vowel_signs_still_match(self):
        """Udayavani writes ೊ as ೆ + ೂ. It looks identical; unnormalised, ಕೊರತೆ
        read as 'not in the source' when it was."""
        import unicodedata
        from brand.factcheck import _unsupported
        src = unicodedata.normalize('NFD', 'ಮಳೆ ಕೊರತೆ ಇರುವುದರಿಂದ ಕೊಲ್ಲೂರು')
        self.assertEqual(_unsupported('ಮಳೆ ಕೊರತೆ ಕೊಲ್ಲೂರು', src), [])


class OnlyTheCoast(unittest.TestCase):

    def test_english_spellings_of_our_towns_count(self):
        for t in ('Kundapur: man ends life', 'Brahmavar: cattle theft',
                  'Mangalore airport flight resumes'):
            self.assertTrue(is_coastal(t), t)

    def test_somewhere_else_is_not_ours(self):
        self.assertFalse(is_coastal('Kasargod: boy drowns in river'))
        self.assertFalse(is_coastal('ಬೆಂಗಳೂರಿನಲ್ಲಿ ಮೆಟ್ರೋ ದರ ಏರಿಕೆ'))

    def test_the_town_is_found_for_the_hashtags(self):
        self.assertEqual(place_in('Shirva: ಅವ್ಯವಸ್ಥೆಯ ಆಗರ ಶಿರ್ವ ಆರೋಗ್ಯಕೇಂದ್ರ'), 'ಶಿರ್ವ')


if __name__ == '__main__':
    unittest.main()
