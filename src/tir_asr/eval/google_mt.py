"""Eval candidate: Google Translate through `googletrans` (unofficial, D-079).

Adapter: it imports googletrans, which sends each text to Google over the network.

- Source `SOURCE`, target `TARGET`, and the default service URL of googletrans 4.0.2
  (`translate.googleapis.com`).
- R10: `RAISE` is True. With the googletrans default (False), a failed call gives the input
  text as the "translation" (`client.py`, `DUMMY_DATA`). There are no retries.
- `TIMEOUT_S`: the httpx default (5 s), now explicit. A call with no answer in that time raises.
- googletrans 4 is async only. One event loop runs all calls, because the httpx client keeps
  its connections on one loop.

The program does not import this module.
"""

import asyncio

import googletrans

from tir_asr.errors import TirError

SOURCE = "hy"
TARGET = "en"
# D-079, approved by Aren on 2026-11-23. The run file keeps them.
RAISE = True
TIMEOUT_S = 5.0
PARAMS = {"source": SOURCE, "target": TARGET, "raise_exception": RAISE, "timeout_s": TIMEOUT_S}


class GoogleMtError(TirError):
    """An error of the Google eval adapter. The message is `mt: <cause>`."""


class GoogleTranslator:
    """`translate(hy)` gives the English text from Google Translate."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._translator = googletrans.Translator(raise_exception=RAISE, timeout=TIMEOUT_S)
        self.service_urls = list(self._translator.service_urls)

    def translate(self, hy: str) -> str:
        call = self._translator.translate(hy, src=SOURCE, dest=TARGET)
        try:
            result = self._loop.run_until_complete(call)
        except Exception as error:
            raise GoogleMtError(
                f"mt: Google Translate failed: {type(error).__name__}: {error}"
            ) from error
        return result.text
