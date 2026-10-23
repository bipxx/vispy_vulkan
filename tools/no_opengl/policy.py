"""Classify API-specific runtimes without rejecting shared Vulkan drivers."""
from __future__ import annotations

import re

_LIBRARIES = re.compile(
    r"^(?:opengl32|libegl|libglesv1_cm|libglesv2|osmesa|qt[56]?opengl(?:widgets)?)\.dll$"
    r"|^(?:libgl|libopengl|libgldispatch|libglapi|libglx(?:_[a-z0-9_-]+)?|libegl(?:_[a-z0-9_-]+)?|libglesv[12](?:_cm)?|libosmesa)\.so(?:\.\d+)*$"
    r"|^(?:qtopengl(?:widgets)?)(?:\.[a-z0-9_-]+)?\.(?:pyd|so)$",
    # Qt module ELF/dylib names are distinct from its Python binding names.
    re.IGNORECASE,
)
_PYTHON = ("OpenGL", "PyQt5.QtOpenGL", "PyQt6.QtOpenGL", "PyQt6.QtOpenGLWidgets",
           "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "vispy.gloo.gl._pyopengl2",
           "vispy.gloo.gl.es2", "vispy.ext.egl", "vispy.ext.osmesa")
_API = re.compile(r"^(?:gl[A-Z]|wgl[A-Z]|glX[A-Z]|egl[A-Z]|OSMesa[A-Z])")


def library_reason(path: str) -> str | None:
    name = str(path).replace("\\", "/").rsplit("/", 1)[-1]
    if _LIBRARIES.match(name):
        return "OpenGL-specific runtime library"
    if re.match(r'^libqt[56]opengl(?:widgets)?(?:\.so(?:\.\d+)*|(?:\.\d+)*\.dylib)$', name, re.IGNORECASE):
        return "Qt OpenGL-specific runtime library"
    if "/OpenGL.framework/" in str(path).replace("\\", "/"):
        return "OpenGL framework"
    if re.search(r'/(?:QtOpenGL|QtOpenGLWidgets)\.framework/', str(path).replace('\\', '/'), re.IGNORECASE):
        return "Qt OpenGL framework"
    return None


def import_reason(name: str) -> str | None:
    if any(name == prefix or name.startswith(prefix + ".") for prefix in _PYTHON):
        return "OpenGL implementation or QtOpenGL module"
    return None


def is_gl_entrypoint(name: str) -> bool:
    return bool(_API.match(name))


def assess(events: list[dict], *, native_loads_complete: bool,
           native_api_complete: bool, execution_succeeded: bool) -> dict:
    violations = []
    for event in events:
        kind = event.get("kind")
        reason = None
        if kind in ("native_load", "ctypes_load_request", "dependency"):
            reason = library_reason(event.get("path", event.get("name", "")))
        elif kind == "python_import":
            reason = import_reason(event.get("name", ""))
        elif kind in ("native_gl_call", "native_gl_binding", "ctypes_symbol"):
            if is_gl_entrypoint(event.get("name", "")):
                reason = "OpenGL API call or entry-point resolution"
        if reason:
            violations.append({**event, "reason": reason})
    # A positive observation disproves the relevant claim even if a collector
    # lacks complete coverage. Absence only becomes a pass with full coverage.
    execution_bad = any(v["kind"] in ("native_gl_call", "native_gl_binding", "ctypes_symbol") for v in violations)
    load_bad = any(v["kind"] == "native_load" for v in violations)
    return {
        "no_gl_execution": "FAIL" if execution_bad else ("PASS" if native_api_complete and execution_succeeded else "UNVERIFIED"),
        "no_gl_loads": "FAIL" if load_bad else ("PASS" if native_loads_complete and execution_succeeded else "UNVERIFIED"),
        "violations": violations,
    }
