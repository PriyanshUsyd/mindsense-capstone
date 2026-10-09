"""
Owner-only permissions for files that contain participant uids
(`docs/privacy/local-demo-privacy-check.md`; `docs/statistics/
week7-calibration-concerns.md` item 2). Shared by `bootstrap_cache` and
`tier1_runner`.

**Fail-closed.** Anything here that cannot be restricted *and verified*
raises `PermissionRestrictionError`; callers must not write uid-bearing
content afterwards. A file left unrestricted is worse than a file not
written.

**"The command succeeded" is not "the file is restricted".** After setting,
the permissions are read back and checked:

  POSIX    `stat` mode is exactly 0o700 (dir) / 0o600 (file).
  Windows  `icacls <path>` is re-read and parsed; every ACE must belong to
           the current user (`whoami`), with Full control. Inherited ACEs
           count: a file under a restricted directory is accepted because
           the *principals* are what matter, not how the ACE got there.
           Any other principal (SYSTEM, Administrators, a sandbox group, an
           unresolved SID) fails the check.

`PermissionRestrictionError` deliberately does not derive from
`BootstrapCacheError`: a cache mismatch is a statistical failure of one
feature, a permission failure means no uid-bearing output is safe anywhere.

This module must stay out of the estimation import path
(`bootstrap`, `feature_specs`, ... never import it), so it is not part of the
bootstrap fingerprint (`test_bootstrap_cache.py` asserts that).

CLI (re-restrict existing output, printing the ACL before and after):
  python -m backend.statistics.private_files <path> [<path> ...]
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


class PermissionRestrictionError(RuntimeError):
    """A uid-bearing path could not be restricted to its owner, or the
    restriction could not be verified. Nothing may be written."""


# ---------------------------------------------------------------------------
# Reading permissions
# ---------------------------------------------------------------------------

_ACE_RE = re.compile(r"^\s*(?P<principal>\S.*?):(?P<flags>(?:\([^()]*\))+)\s*$")


def _icacls(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["icacls", *args],
            capture_output=True,
            text=True,
            encoding="mbcs",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PermissionRestrictionError(f"icacls could not run: {exc}") from exc
    if proc.returncode != 0:
        raise PermissionRestrictionError(
            f"icacls {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip() or proc.returncode}"
        )
    return proc.stdout


def current_identity() -> str:
    """`DOMAIN\\user` as `icacls` prints it (Windows)."""
    try:
        proc = subprocess.run(["whoami"], capture_output=True, text=True, encoding="mbcs", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        raise PermissionRestrictionError(f"cannot determine the current user (whoami: {exc})") from exc
    identity = proc.stdout.strip()
    if proc.returncode != 0 or "\\" not in identity:
        raise PermissionRestrictionError(f"cannot determine the current user (whoami returned {identity!r})")
    return identity


def parse_icacls(output: str, path: Path) -> list[tuple[str, list[str]]]:
    """`[(principal, [flag, ...]), ...]` from `icacls <path>` output. ACE lines
    are `PRINCIPAL:(flag)(flag)`; the first one is prefixed by the path, the
    trailing status message (localised) matches no ACE and is ignored."""
    aces: list[tuple[str, list[str]]] = []
    prefix = str(path)
    for line in output.splitlines():
        if line.startswith(prefix):
            line = line[len(prefix):]
        m = _ACE_RE.match(line)
        if m:
            flags = re.findall(r"\(([^()]*)\)", m.group("flags"))
            aces.append((m.group("principal").strip(), flags))
    return aces


def describe_acl(path: Path) -> str:
    """Human-readable permissions, for before/after records."""
    if os.name == "posix":
        return f"{path}: mode {oct(path.stat().st_mode & 0o777)}"
    aces = parse_icacls(_icacls([str(path)]), path)
    return f"{path}: " + "; ".join(f"{p}:({')('.join(f)})" for p, f in aces)


def acl_is_owner_only(aces: list[tuple[str, list[str]]], identity: str) -> bool:
    """Pure check on parsed ACEs: at least one, all of them Full control for
    `identity`, none a DENY."""
    if not aces:
        return False  # nothing parsed: not verified, so not restricted
    me = identity.casefold()
    for principal, flags in aces:
        if principal.casefold() != me:
            return False
        if "F" not in flags or any(f.upper().startswith("DENY") for f in flags):
            return False
    return True


def is_owner_only(path: Path, *, is_dir: bool) -> bool:
    """True iff the permissions, *read back*, are owner-only. Raises
    `PermissionRestrictionError` only if they cannot be read at all."""
    if os.name == "posix":
        return (path.stat().st_mode & 0o777) == (0o700 if is_dir else 0o600)
    return acl_is_owner_only(parse_icacls(_icacls([str(path)]), path), current_identity())


# ---------------------------------------------------------------------------
# Setting permissions
# ---------------------------------------------------------------------------


def restrict_to_owner(path: Path, *, is_dir: bool) -> None:
    """Restrict, then verify by reading back. Raises on any failure."""
    try:
        if os.name == "posix":
            os.chmod(path, 0o700 if is_dir else 0o600)
        else:
            grant = f"{current_identity()}:(OI)(CI)F" if is_dir else f"{current_identity()}:F"
            _icacls([str(path), "/inheritance:r", "/grant:r", grant])
    except PermissionRestrictionError:
        raise
    except Exception as exc:  # noqa: BLE001 - fail closed, whatever went wrong
        raise PermissionRestrictionError(f"could not restrict {path} ({type(exc).__name__}: {exc})") from exc
    if not is_owner_only(path, is_dir=is_dir):
        raise PermissionRestrictionError(
            f"restricted {path} but the permissions read back are not owner-only: {describe_acl(path)}"
        )


def ensure_owner_only(path: Path, *, is_dir: bool) -> None:
    """Existing path: verified as is; if not owner-only, one attempt to
    restrict it (which verifies again); otherwise `PermissionRestrictionError`."""
    if is_owner_only(path, is_dir=is_dir):
        return
    restrict_to_owner(path, is_dir=is_dir)


def private_dir(path: Path) -> None:
    """Create (with parents) and/or verify an owner-only directory. Parents
    created on the way are left as they are: they hold no uid-bearing file."""
    path.mkdir(parents=True, exist_ok=True)
    ensure_owner_only(path, is_dir=True)


def ensure_private_file(path: Path) -> None:
    """For an existing uid-bearing file that is about to be read or appended to."""
    ensure_owner_only(path, is_dir=False)


def write_private_text(path: Path, text: str) -> None:
    """Atomic write of uid-bearing text. The temp file is created empty and
    restricted *before* any content is written; the destination directory
    must already be private (`private_dir`). Nothing uid-bearing is ever
    written to an unverified file."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        os.close(fd)
        restrict_to_owner(Path(tmp), is_dir=False)
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
        if not is_owner_only(path, is_dir=False):  # rename must keep the descriptor
            raise PermissionRestrictionError(f"{path} lost its owner-only permissions on rename: {describe_acl(path)}")
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        if path.exists() and not is_owner_only(path, is_dir=False):
            path.unlink()
        raise


def restrict_tree(root: Path) -> list[Path]:
    """Restrict an existing directory and everything under it (the directory
    first, so files are checked against the final inheritance). Returns the
    paths handled."""
    handled = []
    ensure_owner_only(root, is_dir=True)
    handled.append(root)
    for p in sorted(root.rglob("*")):
        ensure_owner_only(p, is_dir=p.is_dir())
        handled.append(p)
    return handled


def main(argv: list[str] | None = None) -> int:
    paths = [Path(a) for a in (argv if argv is not None else sys.argv[1:])]
    if not paths:
        print(__doc__.split("CLI", 1)[1], file=sys.stderr)
        return 2
    for root in paths:
        targets = [root, *sorted(root.rglob("*"))] if root.is_dir() else [root]
        print(f"== BEFORE {root}")
        for t in targets:
            print("  " + describe_acl(t))
        if root.is_dir():
            restrict_tree(root)
        else:
            ensure_owner_only(root, is_dir=False)
        print(f"== AFTER  {root}")
        for t in targets:
            print("  " + describe_acl(t))
            if not is_owner_only(t, is_dir=t.is_dir()):
                raise PermissionRestrictionError(f"{t} is not owner-only after restriction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
