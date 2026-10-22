#!/usr/bin/env bash
set -euo pipefail
# Tested with system Blender 4.3.2 (embedded CPython 3.13) and command-line Python 3.12.
# Keep TLS and normal package verification enabled.
python -m pip install --only-binary=:all: --target /workspace/cctv-blender-python --python-version 3.13 shapely==2.1.2 numpy==2.5.4
python -m pip install --only-binary=:all: --target /workspace/cctv-denoise oidn==0.2.1 numpy==2.5.4 pillow==13.0.0
