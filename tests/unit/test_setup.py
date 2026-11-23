"""T-SETUP-01: the package installs into the uv environment and imports (D-007, D-081)."""

import importlib
import importlib.metadata
import sys


def test_package_is_installed_and_importable():
    package = importlib.import_module("tir_asr")

    assert package.__name__ == "tir_asr"
    assert importlib.metadata.version("tir-asr") == "0.1.0"
    assert sys.version_info[:2] == (3, 11), sys.version
