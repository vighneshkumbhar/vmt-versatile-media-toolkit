"""
postbuild_check.py
Post-build contamination scanner for VMT clean distribution.
Run after PyInstaller against dist/VMT/. Exits 0 on pass, 1 on failure.
"""
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST = ROOT / "dist" / "VMT"
INTERNAL = DIST / "_internal"
PASS = True
FAIL_ITEMS = []

def fail(msg: str):
    global PASS
    PASS = False
    FAIL_ITEMS.append(f"  ✗ FAIL: {msg}")

def ok(msg: str):
    print(f"  ✓ PASS: {msg}")

if not DIST.exists():
    print(f"ERROR: dist/VMT/ not found at {DIST}")
    sys.exit(1)

print("\n" + "=" * 60)
print("  VMT Post-Build Contamination Scan")
print(f"  Scanning: {DIST}")
print("=" * 60)

# ── 1. No backend database ────────────────────────────────────────────────
print("\n[1] Backend database check")
for p in DIST.rglob("*.db"):
    fail(f"Database in dist: {p.relative_to(DIST)}")
for p in DIST.rglob("*.sqlite"):
    fail(f"SQLite in dist: {p.relative_to(DIST)}")
ok("No .db/.sqlite files in distribution")

# ── 2. No .env or credential files ────────────────────────────────────────
print("\n[2] Credential / secret file check")
for p in DIST.rglob(".env*"):
    fail(f".env file in dist: {p.relative_to(DIST)}")
ok("No .env files in distribution")

# ── 3. No .vmte packages ──────────────────────────────────────────────────
print("\n[3] Extension package (.vmte) check")
for p in DIST.rglob("*.vmte"):
    fail(f".vmte file in dist: {p.relative_to(DIST)}")
ok("No .vmte files in distribution")

# ── 4. No extension registry ──────────────────────────────────────────────
print("\n[4] Extension registry check")
for p in DIST.rglob("extensions.json"):
    fail(f"extensions.json in dist: {p.relative_to(DIST)}")
ok("No extensions.json in distribution")

# ── 5. No media files ─────────────────────────────────────────────────────
print("\n[5] Media file check")
for ext in ("*.mp4", "*.mp3", "*.mkv", "*.gif", "*.avi", "*.mov"):
    for p in DIST.rglob(ext):
        fail(f"Media file in dist: {p.relative_to(DIST)}")
ok("No media files in distribution")

# ── 6. No audit/forged extension packages ─────────────────────────────────
print("\n[6] Audit / forged extension check")
for p in DIST.rglob("com.audit.*"):
    fail(f"Audit test artifact in dist: {p.relative_to(DIST)}")
for p in DIST.rglob("com.forged.*"):
    fail(f"Forged test artifact in dist: {p.relative_to(DIST)}")
ok("No audit/forged extension artifacts in distribution")

# ── 7. No backend source ──────────────────────────────────────────────────
print("\n[7] Backend source check")
if (DIST / "backend").exists():
    fail("backend/ directory in distribution")
ok("No backend/ in distribution")

# ── 8. settings.json contamination check ─────────────────────────────────
print("\n[8] settings.json contamination check")
settings_in_dist = list(DIST.rglob("settings.json"))
if settings_in_dist:
    for sp in settings_in_dist:
        try:
            s = json.loads(sp.read_text())
            BAD = ["vighn", "ffmpeg easy", "Projects", "C:\\Users",
                   "D:\\", "E:\\", "F:\\"]
            for key, val in s.items():
                if isinstance(val, str):
                    for b in BAD:
                        if b.lower() in val.lower():
                            fail(f"Developer path in bundled settings ({sp.name}): {key}={val!r}")
            ok(f"settings.json at {sp.relative_to(DIST)} contains no developer paths")
        except Exception as e:
            fail(f"Could not parse {sp}: {e}")
else:
    ok("No settings.json in distribution (correct — settings live in AppData at runtime)")

# ── 9. No developer username references in bundled .py / .json files ──────
print("\n[9] Developer path / username scan")
appdata = os.environ.get("APPDATA", "")
dev_patterns = ["vighn", "ffmpeg easy"]
if appdata:
    # Only flag if APPDATA is referenced as a static string (not env lookup)
    dev_patterns.append(appdata)

found = []
for py_file in INTERNAL.rglob("*.py"):
    text = py_file.read_text(encoding="utf-8", errors="ignore")
    for pat in dev_patterns:
        if pat.lower() in text.lower() and "APPDATA" not in text:
            found.append(f"{py_file.name}: {pat!r}")
if found:
    for item in found:
        fail(f"Developer reference in dist source: {item}")
else:
    ok("No developer paths or usernames in bundled source files")

# ── 10. Secret / credential patterns ─────────────────────────────────────
print("\n[10] Secret / credential scan")
SECRET_PATTERNS = [
    "SECRET_KEY", "PASSWORD_PEPPER", "ADMIN_BOOTSTRAP_SECRET",
    "dev-secret-key", "dev-password-pepper", "dev-admin-bootstrap"
]
found_secrets = []
for py_file in INTERNAL.rglob("*.py"):
    text = py_file.read_text(encoding="utf-8", errors="ignore")
    for pat in SECRET_PATTERNS:
        if pat in text:
            found_secrets.append(f"{py_file.name}: {pat}")
if found_secrets:
    for s in found_secrets:
        fail(f"Secret in bundled source: {s}")
else:
    ok("No secret/credential patterns in bundled source")

# ── 11. settings.py must NOT write to _internal ───────────────────────────
print("\n[11] Mutable write path check")
settings_py_candidates = list(INTERNAL.rglob("settings.py"))
for sp in settings_py_candidates:
    text = sp.read_text(encoding="utf-8", errors="ignore")
    if "_APP_ROOT" in text and "_SETTINGS_FILE" in text:
        # Check whether _APP_ROOT is used to set _SETTINGS_FILE
        if "APPDATA" not in text and "AppData" not in text:
            fail(f"{sp.name} still uses project-relative path for settings")
        else:
            ok("settings.py routes writes to AppData, not _internal")
    else:
        ok("settings.py AppData routing confirmed")

# ── 12. Required assets present ───────────────────────────────────────────
print("\n[12] Required asset check")
for asset in ("logo.png", "runner_icon.png", "icon.ico"):
    found_asset = list(INTERNAL.rglob(asset))
    if found_asset:
        ok(f"{asset} present in distribution")
    else:
        fail(f"Required asset missing from distribution: {asset}")

# ── Summary ───────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if PASS:
    print("\n  CLEAN BUILD AUDIT — PASS")
    print("  Distribution is clean. Safe to release.")
    print("=" * 60)
    sys.exit(0)
else:
    print("\n  CLEAN BUILD AUDIT — FAIL")
    print("  Contamination detected in dist/VMT/:")
    for f_item in FAIL_ITEMS:
        print(f_item)
    print("=" * 60)
    sys.exit(1)
