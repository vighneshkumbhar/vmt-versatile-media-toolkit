"""
prebuild_check.py
Pre-build contamination scanner for VMT clean distribution build.
Run before PyInstaller. Exits 0 on pass, 1 on failure.
"""
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
STAGING = ROOT / "dist" / "staging"
PASS = True

FAIL_ITEMS = []
WARN_ITEMS = []


def fail(msg: str):
    global PASS
    PASS = False
    FAIL_ITEMS.append(f"  [FAIL] FAIL: {msg}")


def warn(msg: str):
    WARN_ITEMS.append(f"  [WARN] WARN: {msg}")


def ok(msg: str):
    print(f"  [OK] PASS: {msg}")


print("\n" + "=" * 60)
print("  VMT Pre-Build Contamination Scan")
print("=" * 60)

# ── 1. vmt_ecosystem.db must NOT be in staging ────────────────────────────
print("\n[1] Backend database check")
db_paths = [
    STAGING / "vmt_ecosystem.db",
    ROOT / "dist" / "vmt_ecosystem.db",
]
for p in db_paths:
    if p.exists():
        fail(f"Backend database found in staging: {p}")
    else:
        ok(f"No database at {p.relative_to(ROOT)}")

# ── 2. No .env or credential files ────────────────────────────────────────
print("\n[2] Credential / secret file check")
for p in STAGING.rglob("*.env*"):
    fail(f".env file in staging: {p}")
for p in STAGING.rglob("*.key"):
    fail(f".key file in staging: {p}")
if not FAIL_ITEMS:
    ok("No .env or .key files found in staging")

# ── 3. No vmt_ecosystem.db anywhere in staging ───────────────────────────
print("\n[3] SQLite / database file check")
for p in STAGING.rglob("*.db"):
    fail(f"Database file in staging: {p}")
for p in STAGING.rglob("*.sqlite"):
    fail(f"SQLite file in staging: {p}")
ok("No .db/.sqlite files in staging")

# ── 4. No backend directory in staging ────────────────────────────────────
print("\n[4] Backend code check")
backend_staging = STAGING / "backend"
if backend_staging.exists():
    fail(f"backend/ directory found in staging: {backend_staging}")
else:
    ok("No backend/ in staging")

# ── 5. No extension registry in staging ───────────────────────────────────
print("\n[5] Extension registry check")
for p in STAGING.rglob("extensions.json"):
    fail(f"Extension registry found in staging: {p}")
ok("No extensions.json in staging")

# ── 6. No .vmte packages in staging ───────────────────────────────────────
print("\n[6] Extension package (.vmte) check")
vmte_files = list(STAGING.rglob("*.vmte"))
if vmte_files:
    for p in vmte_files:
        fail(f".vmte package in staging: {p}")
else:
    ok("No .vmte files in staging")

# ── 7. No sample_video.mp4 ────────────────────────────────────────────────
print("\n[7] Sample video check")
for p in STAGING.rglob("*.mp4"):
    fail(f"MP4 file in staging: {p}")
for p in STAGING.rglob("*.mkv"):
    fail(f"MKV file in staging: {p}")
for p in STAGING.rglob("*.mp3"):
    fail(f"MP3 file in staging: {p}")
ok("No media files in staging")

# ── 8. settings.json — check clean defaults ───────────────────────────────
print("\n[8] Settings.json contamination check")
settings_path = STAGING / "config" / "settings.json"
if settings_path.exists():
    try:
        with open(settings_path) as f:
            s = json.load(f)
        dirty_keys = []
        # These fields must NOT contain developer data
        BAD_PATTERNS = ["vighn", "ffmpeg easy", "Projects", "Users\\vighn",
                        "C:\\Users", "D:\\", "E:\\", "F:\\"]
        for key, val in s.items():
            if isinstance(val, str):
                for pattern in BAD_PATTERNS:
                    if pattern.lower() in val.lower():
                        dirty_keys.append(f"{key}={val!r}")
        if dirty_keys:
            for d in dirty_keys:
                fail(f"Developer path found in settings: {d}")
        else:
            ok("settings.json contains no developer paths")
        # output_folder must be empty or absent
        if s.get("output_folder", "") not in ("", None):
            warn(f"output_folder is not empty: {s['output_folder']!r}")
        else:
            ok("output_folder is clean (empty / null)")
    except Exception as e:
        fail(f"Could not parse settings.json: {e}")
else:
    ok("No settings.json in staging (correct — settings live at runtime in AppData)")

# ── 9. settings.py must point to AppData ──────────────────────────────────
print("\n[9] settings.py AppData path check")
settings_py = STAGING / "source" / "core" / "settings.py"
if not settings_py.exists():
    # Try non-staged source
    settings_py = ROOT / "source" / "core" / "settings.py"
content = settings_py.read_text(encoding="utf-8")
if "APPDATA" in content or "AppData" in content or "XDG_DATA_HOME" in content:
    ok("settings.py resolves to AppData (not project-relative)")
else:
    fail("settings.py does NOT reference AppData — user settings would write into _internal/")

if "config/settings.json" in content.replace("\\", "/") and "_APP_ROOT" in content:
    fail("settings.py still uses project-relative _APP_ROOT path — must be patched")
else:
    ok("settings.py does not use _APP_ROOT for settings path")

# ── 10. No scratch, quarantine, output dirs in staging ────────────────────
print("\n[10] Dev-only directory check")
for bad_dir in ["scratch", "quarantine", "output", "backend", "FFmpeg", "sdk", "containers"]:
    p = STAGING / bad_dir
    if p.exists():
        fail(f"Dev directory in staging: {p}")
ok("No dev-only directories in staging")

# ── 11. Confirm AppData NOT referenced as source for bundling ─────────────
print("\n[11] AppData source bundling check")
appdata = os.environ.get("APPDATA", "")
build_bat = ROOT / "build.bat"
if build_bat.exists():
    bat_content = build_bat.read_text(encoding="utf-8")
    if appdata and appdata.lower() in bat_content.lower():
        fail(f"build.bat references APPDATA path: {appdata}")
    else:
        ok("build.bat does not reference AppData path")

# ── 12. Secret/credential patterns in staged source ──────────────────────
print("\n[12] Secret/credential scan in staged source")
DANGEROUS_PATTERNS = [
    "SECRET_KEY", "PASSWORD_PEPPER", "ADMIN_BOOTSTRAP_SECRET",
    "dev-secret-key", "dev-password-pepper", "dev-admin-bootstrap"
]
found_secrets = []
for py_file in (STAGING / "source").rglob("*.py"):
    text = py_file.read_text(encoding="utf-8", errors="ignore")
    for pat in DANGEROUS_PATTERNS:
        if pat in text:
            found_secrets.append(f"{py_file.name}: {pat}")
if found_secrets:
    for s in found_secrets:
        fail(f"Secret pattern found in staged source: {s}")
else:
    ok("No secret/credential patterns in staged source")

# ── Summary ───────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if WARN_ITEMS:
    print("  Warnings:")
    for w in WARN_ITEMS:
        print(w)
if PASS:
    print("\n  CLEAN BUILD AUDIT — PASS")
    print("  All contamination checks passed. Safe to build.")
    print("=" * 60)
    sys.exit(0)
else:
    print("\n  CLEAN BUILD AUDIT — FAIL")
    print("  Contamination detected:")
    for f_item in FAIL_ITEMS:
        print(f_item)
    print("=" * 60)
    sys.exit(1)

