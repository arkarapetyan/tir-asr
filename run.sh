#!/usr/bin/env bash
# Start tir-asr (ARCHITECTURE.md section 2.7, D-045). The arguments go to the program, for
# example: ./run.sh --help
#
# - The script goes to the project folder first, because the MT model folder is relative to it
#   (section 2.4). Thus it works from any folder.
# - HF_HUB_OFFLINE=1: the program uses only the local Hugging Face cache, and nothing downloads
#   (K2, sections 2.3 and 2.4). A missing model file gives an error, not a download.
# - exec: the shell becomes the program, so that Ctrl+C goes straight to it (L-02, D-044).
set -euo pipefail

cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
if [[ ! -x .venv/bin/tir-asr ]]; then
    echo "run.sh: .venv/bin/tir-asr not found. Run 'uv sync' in $(pwd) first." >&2
    exit 1
fi
export HF_HUB_OFFLINE=1
exec .venv/bin/tir-asr "$@"
