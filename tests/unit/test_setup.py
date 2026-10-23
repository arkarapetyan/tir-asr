"""T-SETUP-01: the package installs into the uv environment and imports (D-007)."""

import importlib
import importlib.metadata


def test_package_is_installed_and_importable():
    package = importlib.import_module("tir_asr")

    assert package.__name__ == "tir_asr"
    assert importlib.metadata.version("tir-asr") == "0.1.0"
