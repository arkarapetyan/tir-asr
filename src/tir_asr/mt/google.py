"""Google Translate adapter: the Translator over the network (ARCHITECTURE.md section 2.4).

`googletrans` 4.0.2 is an unofficial client of the Google Translate website (D-079). It sends
each Armenian text to Google over the network. The program uses it only with the consent of the
other people (D-079). Moved from `eval/google_mt.py` in C10 (D-081 point 3).

- Source `SOURCE`, target `TARGET`, and the default service URL of googletrans 4.0.2.
- R10: `RAISE` is True. With the googletrans default (False), a failed call gives the input
  text as the "translation" (`client.py`, `DUMMY_DATA`). There are no retries, and no fallback
  to another translator: a failed call stops the program with an `mt` error.
- `TIMEOUT_S`: 10 s (D-082; the httpx default of 5 s in D-079). A call with no answer in that
  time raises. [RUN, C10] One call took 4.75 s.
- googletrans 4 is async only. One event loop runs all calls, because the httpx client keeps
  its connections on one loop. The warm-up (main thread) and the worker thread use the loop one
  after the other, never at the same time.

This module imports `googletrans`. Only `app.py`, `scripts/c9_run.py`, and the model tests import
it. The core modules do not (D-021, T-IMPORT-01).
"""

import asyncio

import googletrans

from tir_asr.errors import TirError

SOURCE = "hy"
TARGET = "en"
# D-079 and D-082, approved by Aren on 2026-11-23.
RAISE = True
TIMEOUT_S = 10.0
PARAMS = {"source": SOURCE, "target": TARGET, "raise_exception": RAISE, "timeout_s": TIMEOUT_S}


class MtError(TirError):
    """An error of the MT adapter. The message is `mt: <cause>`."""


class GoogleTranslator:
    """`translate(text)` gives the English text of a non-empty Armenian text."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._translator = googletrans.Translator(raise_exception=RAISE, timeout=TIMEOUT_S)
        self.service_urls = list(self._translator.service_urls)

    def translate(self, text: str) -> str:
        if not text:
            raise MtError("mt: empty input text")
        call = self._translator.translate(text, src=SOURCE, dest=TARGET)
        try:
            result = self._loop.run_until_complete(call)
        except Exception as error:
            raise MtError(
                f"mt: Google Translate failed: {type(error).__name__}: {error}"
            ) from error
        return result.text
