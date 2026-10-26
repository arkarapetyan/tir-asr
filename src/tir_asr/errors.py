"""The base class of the module errors (ARCHITECTURE.md section 2, D-042).

Each module has its own error class, with the message `<module>: <cause>` (D-036). Each error
class inherits from `TirError`, so that the pipeline can tell our errors from other exceptions:
a `TirError` gives `tir-asr: <message>`, and any other exception also gives its traceback.
This module imports nothing (D-021).
"""


class TirError(Exception):
    """An error of a tir-asr module. The message is `<module>: <cause>`."""
