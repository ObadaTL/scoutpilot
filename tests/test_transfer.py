"""Tests for export/import (transfer.py): a round trip onto a different machine layout."""

import sqlite3
import zipfile

import pytest

from scoutpilot.transfer import TransferError, export_bundle, import_bundle, read_manifest, rewrite_paths


def _make_source(tmp_path):
    app, repo = tmp_path / "src_app", tmp_path / "src_repo"
    for d in (app / "tailored_resumes", app / "cover_letters", app / "chrome-workers", repo / "my_profile"):
        d.mkdir(parents=True)
    (app / "profile.json").write_text('{"name": "x"}')
    (app / "resume.txt").write_text("cv")
    (app / ".env").write_text("GEMINI_API_KEY=secret\n")
    (app / "chrome-workers" / "cache.bin").write_bytes(b"0" * 100)
    (app / "tailored_resumes" / "a.txt").write_text("tailored")
    (app / "cover_letters" / "a_CL.txt").write_text("letter")
    (repo / "facts.yaml").write_text("facts: []\n")
    (repo / "my_profile" / "transcript.pdf").write_bytes(b"pdf")
    (repo / "Someone_CV-aa.pdf").write_bytes(b"cv")
    (repo / "README.md").write_text("not exported")

    db = sqlite3.connect(app / "applypilot.db")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE jobs (url TEXT PRIMARY KEY, tailored_resume_path TEXT, cover_letter_path TEXT)")
    db.executemany("INSERT INTO jobs VALUES (?,?,?)", [
        ("u1", r"C:\Users\obada\.applypilot\tailored_resumes\a.txt", r"C:\Users\obada\.applypilot\cover_letters\a_CL.txt"),
        ("u2", "/home/old/.applypilot/tailored_resumes/sub/b.txt", None),
        ("u3", None, None),
    ])
    db.commit()  # left open on purpose: WAL file exists, export must still be consistent
    return app, repo, db


def test_round_trip_to_another_machine(tmp_path):
    app, repo, live = _make_source(tmp_path)
    bundle, manifest = export_bundle(app, repo, tmp_path / "out.zip")
    live.close()

    names = set(zipfile.ZipFile(bundle).namelist())
    assert "state/applypilot.db" in names and "repo/facts.yaml" in names
    assert "repo/my_profile/transcript.pdf" in names and "repo/Someone_CV-aa.pdf" in names
    assert "state/.env" not in names, ".env must be opt-in"
    assert not any("chrome-workers" in n or "README" in n for n in names)
    assert manifest["jobs"] == 3

    dst_app, dst_repo = tmp_path / "dst_app", tmp_path / "dst_repo"
    dst_repo.mkdir()
    summary = import_bundle(bundle, dst_app, dst_repo)

    assert summary["paths_rewritten"] == 3
    conn = sqlite3.connect(dst_app / "applypilot.db")
    rows = dict((u, (t, c)) for u, t, c in conn.execute("SELECT * FROM jobs"))
    conn.close()
    assert rows["u1"] == (str(dst_app / "tailored_resumes" / "a.txt"), str(dst_app / "cover_letters" / "a_CL.txt"))
    assert rows["u2"][0] == str(dst_app / "tailored_resumes" / "sub" / "b.txt")
    assert rows["u3"] == (None, None)
    assert (dst_app / "tailored_resumes" / "a.txt").read_text() == "tailored"
    assert (dst_repo / "facts.yaml").exists() and (dst_repo / "my_profile" / "transcript.pdf").exists()
    assert not (dst_app / ".env").exists()


def test_env_only_with_flag_and_never_clobbers_by_default(tmp_path):
    app, repo, live = _make_source(tmp_path)
    live.close()
    bundle, _ = export_bundle(app, repo, tmp_path / "out.zip", include_env=True)

    dst_app, dst_repo = tmp_path / "dst_app", tmp_path / "dst_repo"
    dst_app.mkdir(); dst_repo.mkdir()
    (dst_app / ".env").write_text("LLM_URL=http://localhost:11434\n")
    s = import_bundle(bundle, dst_app, dst_repo)
    assert "kept" in s["env"]
    assert (dst_app / ".env").read_text().startswith("LLM_URL")

    s = import_bundle(bundle, dst_app, dst_repo, overwrite_env=True)
    assert s["env"] == "restored"
    assert "GEMINI_API_KEY" in (dst_app / ".env").read_text()


def test_import_backs_up_existing_db_and_drops_stale_wal(tmp_path):
    app, repo, live = _make_source(tmp_path)
    live.close()
    bundle, _ = export_bundle(app, repo, tmp_path / "out.zip")

    dst_app, dst_repo = tmp_path / "dst_app", tmp_path / "dst_repo"
    dst_app.mkdir(); dst_repo.mkdir()
    old = sqlite3.connect(dst_app / "applypilot.db")
    old.execute("CREATE TABLE marker (x)")
    old.commit(); old.close()
    (dst_app / "applypilot.db-wal").write_bytes(b"stale")

    s = import_bundle(bundle, dst_app, dst_repo)
    assert s["backup"] and (tmp_path / "dst_app").glob("import-backup-*/applypilot.db")
    assert not (dst_app / "applypilot.db-wal").exists()
    tables = [r[0] for r in sqlite3.connect(dst_app / "applypilot.db").execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    assert "jobs" in tables and "marker" not in tables


def test_rejects_non_bundle_and_path_traversal(tmp_path):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("hello.txt", "x")
    with pytest.raises(TransferError):
        read_manifest(bad)

    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("manifest.json", '{"format_version": 1}')
        zf.writestr("state/applypilot.db", b"")
        zf.writestr("state/../../escaped.txt", "pwned")
    with pytest.raises(TransferError):
        import_bundle(evil, tmp_path / "app", tmp_path / "repo")
    assert not (tmp_path / "escaped.txt").exists()


def test_rewrite_paths_leaves_unrecognised_paths_alone(tmp_path):
    db = tmp_path / "x.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE jobs (url TEXT, tailored_resume_path TEXT, cover_letter_path TEXT)")
    c.execute("INSERT INTO jobs VALUES ('u', 'weird/place/a.txt', NULL)")
    c.commit(); c.close()
    assert rewrite_paths(db, tmp_path / "app") == 0
