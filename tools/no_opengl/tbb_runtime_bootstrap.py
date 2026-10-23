# SPDX-License-Identifier: AGPL-3.0-only
"""Keep the selected Windows CPU runtime DLL directory registered."""
import os
from pathlib import Path

if os.name == 'nt':
    _runtime_directory = Path(__file__).resolve().parent / '_vispy_tbb' / 'bin'
    _dll_directory_cookie = os.add_dll_directory(str(_runtime_directory))
