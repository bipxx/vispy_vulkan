# Keeping an original wheel description during source renewal

The repository README also supplies the long description for fresh wheel
builds. Editing that landing page does not change an existing wheel's metadata.
Original Linux and experimental Metal CI reuse can explicitly select
`--package-current-python --keep-original-description` when retaining the
archived description while updating the existing declared Python members.
Without this option, a changed README still fails the original metadata guard.

This choice preserves the exact original METADATA bytes. The archived
description body must hash to the original producer's README source pin,
without newline or encoding normalization. The report records that original
source hash, the archived-description hash, the complete METADATA hash and the
current repository README hash, with `repository_readme_packaged: false`.
The changed README is not reported as an unchanged metadata input.

When no Python package member changes, the entire original wheel, including
RECORD, is reused byte-for-byte. When existing Python members change, only those
members and their regenerated RECORD change. Native outputs, notices/licenses,
manifest, other metadata, ABI, tags and membership remain exact. The option
does not waive pyproject, native/build/harness, original artifact, source-map or
installed-inventory checks, and requires the current-Python packaging mode.

The original producer identity and evidence remain historical. Selecting an
archived description does not claim that the wheel contains the updated
landing page, admit another installed environment or qualify Metal graphics.
A release that intentionally updates wheel metadata needs its own packaging
decision and evidence. See the [Tk baseline](qualified-tk-baseline.md) for the
current exact artifact claims and external runtime prerequisites.
