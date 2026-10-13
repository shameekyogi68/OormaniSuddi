"""
The company's books and the firewall between money and news (D118).

The firewall is the part that matters: a rule here that quietly weakens is
a newsroom that can be bought. Each refusal is pinned by its code.
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import business as B          # noqa: E402
from brand import dispatch as D          # noqa: E402


class Books(unittest.TestCase):
    """Every test runs against a throwaway business/ folder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        biz = os.path.join(self.tmp.name, 'business')
        paths = {'BIZ': biz,
                 'LEDGER': os.path.join(biz, 'ledger.csv'),
                 'AUDIENCE': os.path.join(biz, 'audience.csv'),
                 'DEALS': os.path.join(biz, 'deals.json'),
                 'GOALS': os.path.join(biz, 'goals.json'),
                 'RATE_CARD': os.path.join(biz, 'rate_card.json'),
                 'NOTES': os.path.join(biz, 'notes.md'),
                 'REPORTS': os.path.join(biz, 'reports'),
                 'DRAFTS': os.path.join(biz, 'drafts')}
        for k, v in paths.items():
            p = mock.patch.object(B, k, v)
            p.start()
            self.addCleanup(p.stop)
        B.init()

    def deal(self, **kw):
        d = {'client': 'Sri Durga Jewellers', 'product': 'greeting_sponsor',
             'category': 'jewellery', 'price_inr': 1500,
             'names': ['ಶ್ರೀ ದುರ್ಗಾ ಜ್ಯುವೆಲ್ಲರ್ಸ್', 'Sri Durga Jewellers']}
        d.update(kw)
        return B.add_deal(d, today=date(2026, 10, 12))

    def codes(self, fn, *a, **kw):
        with self.assertRaises(B.BizError) as cm:
            fn(*a, **kw)
        return str(cm.exception)


class TheFirewall(Books):

    def test_money_buys_only_a_listed_product(self):
        self.assertIn('AD-01', self.codes(self.deal, product='news_story'))
        self.assertIn('AD-01', self.codes(self.deal, product='mukhya'))

    def test_a_deal_that_asks_for_news_or_a_removal_is_refused(self):
        for ask in ('please run it as a news story', 'put us in ಮುಖ್ಯ ಸುದ್ದಿ',
                    'remove the post about our shop', 'ಹಳೆಯ ಪೋಸ್ಟ್ ತೆಗೆದುಹಾಕಿ',
                    'ಸುದ್ದಿಯಾಗಿ ಹಾಕಿ',
                    # the research report's ideas, refused (D119)
                    'sponsor line on the morning WhatsApp bulletin',
                    '5-second bumper in the daily digest',
                    'logo footer on breaking alert cards',
                    'ವಿಶೇಷ ವರದಿ — 6 min video', 'label it ಪ್ರಾಯೋಜಿತ ಸುದ್ದಿ'):
            self.assertIn('AD-02', self.codes(self.deal, deliverable=ask), ask)

    def test_our_own_name_and_ordinary_words_are_not_a_news_request(self):
        d = self.deal(deliverable='ಊರ್ಮನಿ ಸುದ್ದಿ Instagram story ಮತ್ತು ಮುಖ್ಯ ಅತಿಥಿ '
                                  'ಸಾರಿಗೆ ಮಾಹಿತಿ')
        self.assertEqual(d['stage'], 'lead')

    def test_prohibited_advertisers_are_refused_at_the_door(self):
        for cat in B.PROHIBITED:
            self.assertIn('AD-04', self.codes(self.deal, category=cat), cat)

    def test_the_label_is_the_products_own(self):
        self.assertEqual(self.deal()['label'], 'ಪ್ರಾಯೋಜಿತ')
        self.assertIn('AD-06', self.codes(self.deal, label='Special offer'))
        self.assertEqual(self.deal(product='production')['label'], '')

    def test_names_are_required_so_conflicts_can_be_caught(self):
        self.assertIn('AD-07', self.codes(self.deal, names=[]))

    def test_nothing_goes_live_until_a_person_clears_it(self):
        d = self.deal()
        B.move_deal(d['id'], 'agreed')
        self.assertIn('AD-08', self.codes(B.move_deal, d['id'], 'live'))
        self.assertIn('AD-08', self.codes(B.clear_deal, d['id'], ''))
        B.clear_deal(d['id'], 'Gautam Paduvari')
        self.assertEqual(B.move_deal(d['id'], 'live')['stage'], 'live')

    def test_a_sensitive_deal_needs_the_ad_desk_before_a_person_can_clear(self):
        d = self.deal(category='hospital', product='ad_post')
        self.assertIn('AD-09', self.codes(B.clear_deal, d['id'], 'Gautam'))
        with open(B.ad_report_path(d['id']), 'w') as fh:
            fh.write('PASS')
        B.clear_deal(d['id'], 'Gautam')

    def test_a_political_ad_needs_its_mcmc_certificate(self):
        d = self.deal(category='political', product='ad_post')
        self.assertIn('AD-05', self.codes(B.move_deal, d['id'], 'agreed'))
        B.move_deal(d['id'], 'agreed', mcmc_ref='MCMC/UDP/2026/14')

    def test_there_is_no_override(self):
        """D29's reason: a flag gets used on a deadline."""
        import inspect
        for fn in (B.check_deal, B.add_deal, B.move_deal, B.clear_deal):
            params = set(inspect.signature(fn).parameters)
            self.assertFalse(params & {'force', 'override', 'skip', 'waive'}, fn)

    def test_a_story_naming_a_sponsor_is_flagged(self):
        d = self.deal()
        B.move_deal(d['id'], 'agreed', today=date(2026, 10, 12))
        ed = {'stories': [{'headline': 'ಕುಂದಾಪುರ: ಶ್ರೀ ದುರ್ಗಾ ಜ್ಯುವೆಲ್ಲರ್ಸ್ ಬಳಿ ರಸ್ತೆ ಕಾಮಗಾರಿ'},
                          {'headline': 'ಬೈಂದೂರು: ಮಳೆ'}]}
        found = B.conflicts(ed, today=date(2026, 10, 12))
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith('story 1'))

    def test_a_lost_deal_is_not_a_conflict(self):
        d = self.deal()
        B.move_deal(d['id'], 'lost')
        ed = {'stories': [{'headline': 'Sri Durga Jewellers'}]}
        self.assertEqual(B.conflicts(ed), [])


class SponsoredGreeting(Books):
    """A paid wish renders only for a deal a person cleared (D118, D119)."""

    def greeting(self, **kw):
        from templates.greeting import Greeting
        g = dict(occasion='ದೀಪಾವಳಿ ಹಬ್ಬದ', sponsor='Sri Durga Jewellers')
        g.update(kw)
        return Greeting(**g)

    def test_it_needs_a_cleared_greeting_deal(self):
        from brand.content import ContentError
        with self.assertRaisesRegex(ContentError, 'deal'):
            self.greeting().validate()
        d = self.deal()
        with self.assertRaisesRegex(ContentError, 'AD-10'):
            self.greeting(deal=d['id']).validate()          # still a lead
        B.move_deal(d['id'], 'agreed')
        with self.assertRaisesRegex(ContentError, 'AD-08'):
            self.greeting(deal=d['id']).validate()          # nobody cleared it
        B.clear_deal(d['id'], 'Gautam Paduvari')
        self.greeting(deal=d['id']).validate()
        with self.assertRaisesRegex(ContentError, 'AD-10'):
            self.greeting(deal=d['id'], sponsor='Someone Else').validate()

    def test_another_product_cannot_become_a_greeting(self):
        from brand.content import ContentError
        d = self.deal(product='ad_post')
        B.move_deal(d['id'], 'agreed')
        B.clear_deal(d['id'], 'Gautam')
        with self.assertRaisesRegex(ContentError, 'AD-10'):
            self.greeting(deal=d['id']).validate()

    def test_the_poster_and_the_caption_say_so(self):
        from templates import greeting as G
        d = self.deal()
        B.move_deal(d['id'], 'agreed')
        B.clear_deal(d['id'], 'Gautam')
        g = self.greeting(deal=d['id'])
        self.assertTrue(g.sign_text.startswith(G.SPONSORED))
        c = G.greeting_copy(g)
        self.assertTrue(c['instagram'].startswith(G.SPONSORED))
        self.assertTrue(c['alt_text'].startswith(G.SPONSORED))
        self.assertIn('Paid partnership', c['paid_partnership'])
        self.assertFalse([t for t in c['hashtags']
                          if 'ಸುದ್ದಿ' in t or 'news' in t.lower()])
        out = os.path.join(self.tmp.name, 'out')
        made = G.package(g, out, formats=['post'])
        self.assertTrue(os.path.exists(made[0][0]))

    def test_an_unsponsored_greeting_is_unchanged(self):
        from templates import greeting as G
        g = G.Greeting(occasion='ದೀಪಾವಳಿ ಹಬ್ಬದ')
        g.validate()                     # no books needed, no deal asked for
        self.assertEqual(g.sign_text, 'ಶುಭ ಕೋರುವವರು')
        self.assertEqual(G.greeting_copy(g)['paid_partnership'], '')


class Money(Books):

    def test_rows_outside_the_streams_are_refused(self):
        bad = {'date': '2026-10-01', 'kind': 'income', 'amount_inr': '500',
               'stream': 'misc'}
        self.assertIn('BIZ-01', self.codes(B.add_money, bad))
        self.assertIn('BIZ-01', self.codes(
            B.add_money, {**bad, 'stream': 'ad_post', 'amount_inr': '-5'}))
        self.assertIn('BIZ-01', self.codes(
            B.add_money, {**bad, 'stream': 'ad_post', 'tds_inr': '900'}))

    def test_month_fy_and_tools_cover(self):
        B.add_money({'date': '2026-10-02', 'kind': 'income', 'amount_inr': '3000',
                     'stream': 'greeting_sponsor', 'tds_inr': '300'})
        B.add_money({'date': '2026-10-03', 'kind': 'expense', 'amount_inr': '2000',
                     'stream': 'ai_tools'})
        B.add_money({'date': '2026-03-30', 'kind': 'income', 'amount_inr': '999',
                     'stream': 'ad_post'})                     # previous FY
        s = B.status(date(2026, 10, 12))
        self.assertEqual(s.month['net'], 1000)
        self.assertEqual(s.fy['income'], 3000)
        self.assertEqual(s.fy['tds'], 300)
        self.assertAlmostEqual(s.tools_cover, 1.5)
        self.assertEqual(B.fy_of(date(2027, 3, 31)), 2026)

    def test_gst_warns_before_the_line(self):
        B.add_money({'date': '2026-06-01', 'kind': 'income',
                     'amount_inr': str(int(B.GST_THRESHOLD_INR * 0.8)),
                     'stream': 'event_coverage'})
        g = B.gst_watch(B.ledger(), date(2026, 10, 12))
        self.assertTrue(g['warn'])
        self.assertFalse(g['over'])

    def test_init_never_overwrites(self):
        B.add_money({'date': '2026-10-02', 'kind': 'income', 'amount_inr': '1',
                     'stream': 'notice'})
        self.assertEqual(B.init(), [])
        self.assertEqual(len(B.ledger()), 1)

    def test_the_books_validate_clean(self):
        self.deal()
        self.assertEqual(B.validate_books(), [])


class Audience(Books):

    def test_progress_toward_each_programme(self):
        B.add_audience({'date': '2026-10-05', 'platform': 'youtube',
                        'followers': '500', 'uploads_90d': '10',
                        'watch_hours_12m': '1500', 'shorts_views_90d': '100000'})
        prog = {p['programme']: p for p in B.monetisation()}
        fans = prog['youtube_fans']
        self.assertFalse(fans['eligible'])
        self.assertEqual(fans['missing'], ['watch_hours_12m 1,500/3,000'])
        self.assertAlmostEqual(fans['progress'], (1 + 1 + 0.5) / 3)
        self.assertFalse(prog['facebook_ads']['known'])

    def test_newest_figure_wins_per_metric(self):
        B.add_audience({'date': '2026-10-01', 'platform': 'youtube',
                        'followers': '400', 'watch_hours_12m': '3100',
                        'uploads_90d': '4'})
        B.add_audience({'date': '2026-10-08', 'platform': 'youtube',
                        'followers': '520'})
        prog = {p['programme']: p for p in B.monetisation()}
        self.assertTrue(prog['youtube_fans']['eligible'])

    def test_platform_rules_say_when_they_were_checked(self):
        for k, r in B.PLATFORM_RULES.items():
            date.fromisoformat(r['checked'])
            self.assertIn(r['platform'], B.PLATFORMS, k)
            self.assertTrue(r['where'], k)


class TheDispatcherSeesTheCompany(Books):

    def test_business_tasks_never_enter_the_production_waves(self):
        d = self.deal()
        B.move_deal(d['id'], 'pitched', next_action='call back',
                    next_date='2026-10-10')
        p = D.Plan('2026-10-12')
        D._business_tasks(p, date(2026, 10, 12), [])
        self.assertEqual(p.tasks, [])
        agents = {t.agent for t in p.business}
        self.assertIn('ad-standards', agents)
        self.assertIn('general-manager', agents)
        self.assertTrue(any('follow up' in x for x in p.person))
        self.assertTrue(any('audience' in x for x in p.person))

    def test_finance_closes_the_month_that_ended(self):
        f = D.business_report('finance-controller', date(2026, 1, 3))
        self.assertTrue(f.endswith('finance_2025-12.md'))
        f = D.business_report('general-manager', date(2026, 10, 12))
        self.assertTrue(f.endswith('gm_2026-W42.md'))


if __name__ == '__main__':
    unittest.main()
