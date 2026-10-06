"""
A moment's network trouble does not change the voice.
=====================================================
Every narration beat goes over the network. Before this, one dropped request
on one chunk failed the whole beat over to the next engine in
voice.FALLBACK_ORDER — the neural voice the native ear rejected. A transient
failure is now retried; a refusal of the input is not, because it would fail
the same way again. D110.
"""
from __future__ import annotations

import io
import unittest
import urllib.error
import urllib.request
from unittest import mock

from brand import voice


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError('https://x', code, 'x', {}, None)


class TransientFailuresAreRetried(unittest.TestCase):

    def setUp(self):
        p = mock.patch.object(voice, 'NET_BACKOFF', 0)
        p.start()
        self.addCleanup(p.stop)
        self.req = urllib.request.Request('https://example.invalid/tts')

    def _fetch_with(self, *outcomes):
        calls = []

        def fake(req, timeout):
            calls.append(req)
            out = outcomes[len(calls) - 1]
            if isinstance(out, Exception):
                raise out
            return _Resp(out)
        with mock.patch.object(urllib.request, 'urlopen', fake):
            try:
                return voice._fetch(self.req, timeout=1), len(calls)
            except Exception as e:      # noqa: BLE001
                return e, len(calls)

    def test_a_dropped_connection_is_retried_and_succeeds(self):
        got, n = self._fetch_with(urllib.error.URLError('reset'),
                                  TimeoutError(), b'audio')
        self.assertEqual(got, b'audio')
        self.assertEqual(n, 3)

    def test_rate_limits_and_server_errors_are_retried(self):
        for code in (429, 500, 503):
            got, n = self._fetch_with(_http(code), b'audio')
            self.assertEqual(got, b'audio', code)
            self.assertEqual(n, 2)

    def test_a_refused_input_is_not_retried(self):
        got, n = self._fetch_with(_http(400), b'never reached')
        self.assertIsInstance(got, urllib.error.HTTPError)
        self.assertEqual(n, 1)

    def test_it_gives_up_after_the_last_attempt(self):
        fails = [urllib.error.URLError('down')] * voice.NET_ATTEMPTS
        got, n = self._fetch_with(*fails)
        self.assertIsInstance(got, urllib.error.URLError)
        self.assertEqual(n, voice.NET_ATTEMPTS)


if __name__ == '__main__':
    unittest.main()
