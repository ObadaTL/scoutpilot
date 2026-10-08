"""Move a ScoutPilot install's data between machines: `export` -> one zip,
`import` -> restore it on another PC.

What travels (and what deliberately does not):

  state/   (the ~/.applypilot folder)
    applypilot.db        consistent snapshot via SQLite's backup API, so it is
                         safe to export while WAL files exist
    profile.json, resume.txt, resume.pdf, searches.yaml
    tailored_resumes/, cover_letters/
    .env                 only with include_env -- it holds API keys, and the
                         other PC usually has its own LLM_URL / LLM_MODEL
  repo/    (the git checkout -- all of this is gitignored, so `git clone`
            does NOT bring it)
    facts.yaml, my_profile/, and CV / cover-letter documents in the repo root

NOT exported: chrome-workers/ and apply-workers/ (GBs of browser profile
cache that rebuilds itself), logs/, dashboard.html (regenerated).

The database stores absolute paths to the tailored CV / cover letter files
(e.g. C:\\Users\\<name>\\.applypilot\\tailored_resumes\\x.txt). Import
rewrites those to the destination's own app dir, whatever OS or username the
source used.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

FORMAT_VERSION = 1
MANIFEST = "manifest.json"

STATE_FILES = ["profile.json", "resume.txt", "resume.pdf", "searches.yaml"]
STATE_DIRS = ["tailored_resumes", "cover_letters"]
DB_NAME = "applypilot.db"
# DB columns holding an absolute path into the app dir: column -> subdir.
PATH_COLUMNS = {"tailored_resume_path": "tailored_resumes", "cover_letter_path": "cover_letters"}
# Repo-root documents (gitignored): see .gitignore "Personal documents".
REPO_DOC_GLOBS = ["*CV*.pdf", "*CV*.docx", "*CV*.txt", "CoverLetter*", "Cover?Letter*"]


class TransferError(Exception):
    pass


def _git_commit(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def _repo_docs(repo_root: Path) -> list[Path]:
    found: dict[str, Path] = {}
    for pattern in REPO_DOC_GLOBS:
        for p in repo_root.glob(pattern):
            if p.is_file():
                found[p.name] = p
    return list(found.values())


def _snapshot_db(db_path: Path, dest: Path) -> None:
    """Consistent copy of a (possibly live, WAL-mode) SQLite database."""
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def export_bundle(app_dir: Path, repo_root: Path, out: Path | None = None,
                  include_env: bool = False) -> tuple[Path, dict]:
    """Write the export zip. Returns (zip_path, manifest)."""
    db_path = app_dir / DB_NAME
    if not db_path.exists():
        raise TransferError(f"No database at {db_path} -- nothing to export.")

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out = Path(out) if out else Path.cwd() / f"scoutpilot-export-{stamp}.zip"
    if out.is_dir():
        out = out / f"scoutpilot-export-{stamp}.zip"

    with tempfile.TemporaryDirectory() as tmp:
        snap = Path(tmp) / DB_NAME
        _snapshot_db(db_path, snap)
        conn = sqlite3.connect(snap)
        try:
            jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        finally:
            conn.close()

        entries: list[str] = []
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            def add(path: Path, arc: str) -> None:
                zf.write(path, arc)
                entries.append(arc)

            add(snap, f"state/{DB_NAME}")
            for name in STATE_FILES + ([".env"] if include_env else []):
                if (app_dir / name).is_file():
                    add(app_dir / name, f"state/{name}")
            for d in STATE_DIRS:
                for p in sorted((app_dir / d).rglob("*")):
                    if p.is_file():
                        add(p, f"state/{d}/{p.relative_to(app_dir / d).as_posix()}")

            if (repo_root / "facts.yaml").is_file():
                add(repo_root / "facts.yaml", "repo/facts.yaml")
            profile_dir = repo_root / "my_profile"
            if profile_dir.is_dir():
                for p in sorted(profile_dir.rglob("*")):
                    if p.is_file():
                        add(p, f"repo/my_profile/{p.relative_to(profile_dir).as_posix()}")
            for p in _repo_docs(repo_root):
                add(p, f"repo/{p.name}")

            manifest = {
                "format_version": FORMAT_VERSION,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "source_app_dir": str(app_dir),
                "source_commit": _git_commit(repo_root),
                "includes_env": include_env,
                "jobs": jobs,
                "files": len(entries),
            }
            zf.writestr(MANIFEST, json.dumps(manifest, indent=2))
    return out, manifest


def read_manifest(bundle: Path) -> dict:
    try:
        with zipfile.ZipFile(bundle) as zf:
            manifest = json.loads(zf.read(MANIFEST))
    except (KeyError, zipfile.BadZipFile, ValueError) as e:
        raise TransferError(f"{bundle} is not a ScoutPilot export ({e}).") from e
    if manifest.get("format_version") != FORMAT_VERSION:
        raise TransferError(
            f"Export format {manifest.get('format_version')} is not supported by this "
            f"version (expects {FORMAT_VERSION}). Update scoutpilot with `git pull`.")
    return manifest


def _rebase(value: str, subdir: str, app_dir: Path) -> str:
    """Rewrite a stored absolute path (Windows or POSIX) onto this app dir."""
    pure = PureWindowsPath(value) if ("\\" in value or ":" in value[:3]) else PurePosixPath(value)
    parts = list(pure.parts)
    if subdir not in parts:
        return value
    rest = parts[parts.index(subdir) + 1:]
    return str(app_dir.joinpath(subdir, *rest))


def rewrite_paths(db_path: Path, app_dir: Path) -> int:
    """Point the DB's file-path columns at `app_dir`. Returns rows changed."""
    changed = 0
    conn = sqlite3.connect(db_path)
    try:
        for col, subdir in PATH_COLUMNS.items():
            rows = conn.execute(
                f"SELECT url, {col} FROM jobs WHERE {col} IS NOT NULL").fetchall()
            for url, value in rows:
                new = _rebase(value, subdir, app_dir)
                if new != value:
                    conn.execute(f"UPDATE jobs SET {col} = ? WHERE url = ?", (new, url))
                    changed += 1
        conn.commit()
    finally:
        conn.close()
    return changed


def _safe_target(root: Path, member: str) -> Path:
    target = (root / member).resolve()
    if root.resolve() not in target.parents and target != root.resolve():
        raise TransferError(f"Refusing unsafe path in bundle: {member}")
    return target


def import_bundle(bundle: Path, app_dir: Path, repo_root: Path,
                  overwrite_env: bool = False) -> dict:
    """Restore an export. Existing db / small config files are first copied to
    `<app_dir>/import-backup-<stamp>/`. Returns a summary dict."""
    manifest = read_manifest(bundle)
    app_dir.mkdir(parents=True, exist_ok=True)
    backup = app_dir / f"import-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    summary = {"manifest": manifest, "backup": None, "paths_rewritten": 0,
               "env": "not in bundle", "files": 0}

    def back_up(path: Path, rel: str) -> None:
        if path.is_file():
            dest = backup / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            summary["backup"] = str(backup)

    with zipfile.ZipFile(bundle) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        # Validate every member before touching anything.
        for n in names:
            if n != MANIFEST:
                _safe_target(app_dir if n.startswith("state/") else repo_root,
                             n.split("/", 1)[1] if "/" in n else n)

        # ---- database: stage, rewrite paths, then swap in ----
        staged = app_dir / f"{DB_NAME}.importing"
        with zf.open(f"state/{DB_NAME}") as src, open(staged, "wb") as dst:
            shutil.copyfileobj(src, dst)
        summary["paths_rewritten"] = rewrite_paths(staged, app_dir)
        back_up(app_dir / DB_NAME, DB_NAME)
        for suffix in ("-wal", "-shm"):  # stale WAL files would corrupt the new db
            (app_dir / f"{DB_NAME}{suffix}").unlink(missing_ok=True)
        staged.replace(app_dir / DB_NAME)

        # ---- everything else ----
        for n in names:
            if n in (MANIFEST, f"state/{DB_NAME}"):
                continue
            area, rel = n.split("/", 1)
            root = app_dir if area == "state" else repo_root
            target = _safe_target(root, rel)
            if n == "state/.env":
                if target.exists() and not overwrite_env:
                    summary["env"] = "kept your existing .env (use --overwrite-env to replace)"
                    continue
                back_up(target, ".env")
                summary["env"] = "restored"
            elif not rel.startswith(tuple(f"{d}/" for d in STATE_DIRS)):
                back_up(target, f"{area}/{rel}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            summary["files"] += 1
    return summary
