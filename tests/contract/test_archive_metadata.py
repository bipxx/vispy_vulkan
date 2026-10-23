"""Git archives build from the same pinned vendor bytes as checkouts."""

import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("archive_dependency_verifier", ROOT / "cmake/verify_dependencies.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
METADATA = "third_party/parity/vispy/.git_archival.txt"
PAYLOAD = "third_party/parity/vispy/payload.py"
ATTRIBUTES = "third_party/parity/vispy/.gitattributes"


@pytest.fixture
def exported(tmp_path, monkeypatch):
    repo = tmp_path / "fixture-repository"
    repo.mkdir()

    def git(*args):
        return subprocess.check_output([
            "git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
            "-c", "user.name=Archive fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "core.hooksPath=" + str(repo / ".git/hooks"), *args,
        ], cwd=repo)

    git("init", "--quiet")
    (repo / ".git/info/attributes").write_bytes(b"* -text -eol -filter -ident\n")
    (repo / METADATA).parent.mkdir(parents=True)
    (repo / METADATA).write_bytes(verifier.VISPY_ARCHIVE_METADATA)
    (repo / ATTRIBUTES).write_bytes(b".git_archival.txt export-subst\n")
    (repo / PAYLOAD).write_bytes(b"original_source = True\n")
    git("add", "--force", ".")
    git("commit", "--quiet", "-m", "Archive fixture")
    pin = verifier.source_digest(repo / "third_party/parity/vispy", [])
    archive = tmp_path / "exported-source"
    archive.mkdir()
    with tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", "HEAD"))) as bundle:
        for name in (METADATA, PAYLOAD, ATTRIBUTES):
            target = archive / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.extractfile(name).read())
    require_expanded = (archive / METADATA).read_bytes()
    assert require_expanded != verifier.VISPY_ARCHIVE_METADATA
    lock = archive / "dependency-lock.json"
    lock.write_text(json.dumps({"dependencies": [{
        "name": "vispy", "path": "third_party/parity/vispy",
        "tree_sha256": pin[0], "file_count": pin[1], "exclude_directory_names": [],
    }]}))
    monkeypatch.setattr(verifier, "ROOT", archive)
    monkeypatch.setattr(verifier, "LOCK", lock)
    return repo, archive, lock, pin


def test_real_git_export_restores_original_bytes_and_unchanged_pin(exported, monkeypatch):
    repo, archive, lock, pin = exported
    lock_before = lock.read_bytes()
    expanded = (archive / METADATA).read_bytes()
    with pytest.raises(RuntimeError, match="source checksum mismatch"):
        verifier.verify()
    assert (archive / METADATA).read_bytes() == expanded, "Default verification must remain read-only"
    monkeypatch.setattr(sys, "argv", ["verify_dependencies.py", "--restore-archive-metadata"])
    verifier.main()
    assert (archive / METADATA).read_bytes() == (repo / METADATA).read_bytes()
    assert verifier.source_digest(archive / "third_party/parity/vispy", []) == pin
    assert lock.read_bytes() == lock_before
    assert verifier.restore_archive_metadata(archive) is False


def test_checkout_metadata_edits_are_not_rewritten(exported):
    repo, archive, _, _ = exported
    assert verifier.restore_archive_metadata(repo) is False
    expanded = (archive / METADATA).read_bytes()
    (repo / METADATA).write_bytes(expanded)
    assert verifier.restore_archive_metadata(repo) is False
    assert (repo / METADATA).read_bytes() == expanded


def test_other_source_changes_still_fail_the_original_pin(exported, monkeypatch):
    _, archive, _, _ = exported
    changed = b"original_source = False\n"
    (archive / PAYLOAD).write_bytes(changed)
    monkeypatch.setattr(sys, "argv", ["verify_dependencies.py", "--restore-archive-metadata"])
    with pytest.raises(RuntimeError, match="source checksum mismatch"):
        verifier.main()
    assert (archive / METADATA).read_bytes() == verifier.VISPY_ARCHIVE_METADATA
    assert (archive / PAYLOAD).read_bytes() == changed


def test_unrecognized_metadata_remains_unchanged_and_fails(exported):
    _, archive, _, _ = exported
    edited = b"Manually edited archival metadata\n"
    (archive / METADATA).write_bytes(edited)
    assert verifier.restore_archive_metadata(archive) is False
    assert (archive / METADATA).read_bytes() == edited
    with pytest.raises(RuntimeError, match="source checksum mismatch"):
        verifier.verify()


def test_explicit_origins_cannot_request_archive_restoration(exported, monkeypatch):
    _, archive, lock, _ = exported
    expanded = (archive / METADATA).read_bytes()
    names = ("workspace", "module-sha256", "context", "context-sha256", "capture", "capture-sha256",
             "capture-seal", "capture-seal-sha256", "admission", "admission-sha256",
             "admission-seal", "admission-seal-sha256")
    arguments = ["verify_dependencies.py", "--restore-archive-metadata", "--dependency-lock", str(lock)]
    for name in names:
        arguments += ["--origin-" + name, "fixture"]
    monkeypatch.setattr(sys, "argv", arguments)
    with pytest.raises(SystemExit) as error:
        verifier.main()
    assert error.value.code == 2
    assert (archive / METADATA).read_bytes() == expanded


def test_literal_metadata_matches_the_vendored_input():
    assert (ROOT / METADATA).read_bytes() == verifier.VISPY_ARCHIVE_METADATA
