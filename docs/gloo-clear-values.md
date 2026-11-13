# Depth and stencil clear values

Status, 2026-11-13: source-tested on Windows Vulkan and WSL Mesa25.2.8 software
Vulkan; successor installed qualification is pending. This change is not in
the published Vulkan.2 wheels. [Exact Windows before/after evidence](../compat/api-acceptance/gloo-clear-zero-source-v1.json),
[nine WSL source cases](../compat/api-acceptance/qt-lifecycle-wsl-current-source-v1.json).

The current unreleased Windows wheel977357ad also passes these nine cases within
[21 selected installed checks](../compat/api-acceptance/lifecycle-windows-installed-selected-v1.json),
with zero source overrides. Linux installed acceptance and formal successor
qualification remain pending; the published Vulkan.2 wheels are unchanged.

The corresponding [Linux candidate8a793196 installed run](../compat/api-acceptance/lifecycle-linux-installed-selected-v1.json)
also passes the21selected cases with zero source overrides. Both local installed
observations are now complete; formal qualification and public delivery remain
pending. Earlier pending-Linux descriptions are historical checkpoints.

The exact [manylinux wheel30a40dcb](../compat/api-acceptance/lifecycle-linux-manylinux-installed-v1.json)
also passes these cases on the selected patched-Mesa profile, within21selected
plus56baseline installed tests. Retagging changes only packaging metadata;
runtime and installed origins are verified. Formal qualification remains pending.

`gloo.clear` distinguishes a numeric clear value from a disabled buffer flag:

| Argument | Effect |
| --- | --- |
| `depth=0.0` | Set the depth clear value to zero and clear depth. |
| `stencil=0` | Set the stencil clear value to zero and clear stencil. |
| `depth=False` / `stencil=False` | Leave that attachment unchanged. |
| `depth=None` / `stencil=None` | Leave that attachment unchanged, preserving existing behavior. |
| `depth=True` / `stencil=True` | Clear using that attachment's current clear value. |
| `depth=np.bool_(True)` / `stencil=np.bool_(True)` | Preserve the existing NumPy-true behavior: set the clear value to one and clear. Use Python `True` to retain the current clear value. |

For example, with a current canvas and the appropriate write masks:

```python
gloo.clear(color=False, depth=0.0, stencil=0)
```

This clears depth and stencil to zero while preserving color. The previous
wrapper tested the numeric arguments for truthiness and skipped both zeros.
This is an intentional correction rather than a claim of exact stock-wrapper
behavior. The selected test also covers NumPy numeric zeros, disabled NumPy
boolean false, finite-value refusal/recovery and nine zero shutdown gauges.
It uses single-sample 4×4 depth24plus-stencil8 targets with depth writes and
the full eight-bit stencil write mask enabled; other state combinations retain
their own coverage boundaries.

The historical eight stock wrapper/facade failures remain recorded. Their
[source investigation and practical disposition](stencil-wrapper-disposition.md)
now distinguish four supported public wrapper forms from four raw-call refusal
and wrapper-recovery cases, passing on Windows/WSL. This does not make the
unchanged stock wrapper pass or establish installed acceptance/full parity.

The review follow-up adds integer `depth=0` and NumPyTrue controls:11clear cases
pass on current Windows/WSL source within the [26case follow-up](../compat/api-acceptance/qt-close-state-wsl-source-v1.json).
Earlier9case installed reports retain their original test/source scope.
