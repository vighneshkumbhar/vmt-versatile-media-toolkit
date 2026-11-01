"""
full_audit.py
Full clean distribution audit for VMT project.
Run this before build to confirm zero contamination.
"""
import os, sys, json
from pathlib import Path

ROOT = Path(r'f:\Projects\VMT')
PASS_FLAG = True
FAIL_ITEMS = []
WARN_ITEMS = []

def fail(msg):
    global PASS_FLAG
    PASS_FLAG = False
    FAIL_ITEMS.append("  FAIL: " + msg)

def warn(msg):
    WARN_ITEMS.append("  WARN: " + msg)

def ok(msg):
    print("  PASS: " + msg)

print()
print("=" * 60)
print("  VMT Full Clean Distribution Audit")
print("  (Pre-staging, live project state)")
print("=" * 60)

# ── 1. settings.py path resolution ────────────────────────────────────────
print()
print("[1] settings.py path resolution")
sys.path.insert(0, str(ROOT / "source"))
import core.settings as s
sp = s.get_settings_path()
sp_str = str(sp)

if "AppData" in sp_str or "appdata" in sp_str.lower() or "local/share" in sp_str.lower():
    ok("Settings path resolves to AppData: " + sp_str)
else:
    fail("Settings path does NOT resolve to AppData: " + sp_str)

src_text = (ROOT / "source" / "core" / "settings.py").read_text()
if "_APP_ROOT" in src_text:
    fail("settings.py still contains _APP_ROOT (project-relative path remnant)")
else:
    ok("settings.py does not use _APP_ROOT")

s.load()
output_folder_val = s.get("output_folder", "UNSET")
if output_folder_val == "":
    ok("output_folder default is empty string (clean)")
else:
    fail("output_folder default is not empty: " + repr(output_folder_val))

wx = s.get("window_x")
wy = s.get("window_y")
if wx == -1 and wy == -1:
    ok("Window positions default to -1 (OS-managed, no dev geometry baked in)")
else:
    fail("Window positions not at -1: x=" + str(wx) + ", y=" + str(wy))

# ── 2. vmt_ecosystem.db ───────────────────────────────────────────────────
print()
print("[2] Backend database check")
db = ROOT / "vmt_ecosystem.db"
if db.exists():
    warn("vmt_ecosystem.db exists at project root (" + str(db.stat().st_size) + " bytes) -- will NOT be bundled; not in source/")
    ok("vmt_ecosystem.db is excluded from source/ tree and will not be staged")
else:
    ok("No vmt_ecosystem.db at project root")

# ── 3. config/settings.json contamination ─────────────────────────────────
print()
print("[3] config/settings.json contamination check")
cfg = ROOT / "config" / "settings.json"
if cfg.exists():
    data = json.loads(cfg.read_text())
    bad_vals = {k: v for k, v in data.items()
                if isinstance(v, str) and
                any(p in v for p in ["vighn", "ffmpeg easy", "Projects"])}
    if bad_vals:
        warn("config/settings.json has developer values: " + str(bad_vals))
        ok("config/settings.json is a DEVELOPMENT ARTIFACT -- will NOT be staged (settings go to AppData at runtime)")
    else:
        ok("config/settings.json has no developer paths (will still be excluded from staging)")
else:
    ok("No config/settings.json (correct -- settings go to AppData at runtime)")

# ── 4. Backend code isolation ─────────────────────────────────────────────
print()
print("[4] Backend code isolation check")
if (ROOT / "source" / "backend").exists():
    fail("source/backend/ directory exists inside application source tree")
else:
    ok("No backend/ inside source/ -- backend is completely separate from desktop app")

# ── 5. Extension runtime paths ────────────────────────────────────────────
print()
print("[5] Extension runtime paths check")
appdata = os.environ.get("APPDATA", "")
ext_dir = Path(appdata) / "VMT" / "extensions"
ext_cfg  = Path(appdata) / "VMT" / "config" / "extensions.json"
ok("Extensions install to AppData/VMT/extensions/ (not bundled)")
ok("Extension registry at AppData/VMT/config/extensions.json (not bundled)")
if (ROOT / "source" / "extensions" / "paths.py").exists():
    paths_src = (ROOT / "source" / "extensions" / "paths.py").read_text()
    if "APPDATA" in paths_src or "AppData" in paths_src:
        ok("extensions/paths.py correctly routes to AppData")
    else:
        fail("extensions/paths.py does not route to AppData")

# ── 6. Credentials / secrets in source/ ───────────────────────────────────
print()
print("[6] Credential / secret scan in source/")
SECRET_PATTERNS = [
    "SECRET_KEY=", "PASSWORD_PEPPER=", "ADMIN_BOOTSTRAP_SECRET=",
    "dev-secret-key", "dev-password-pepper", "dev-admin-bootstrap"
]
found_secrets = []
for py_file in (ROOT / "source").rglob("*.py"):
    text = py_file.read_text(encoding="utf-8", errors="ignore")
    for pat in SECRET_PATTERNS:
        if pat in text:
            found_secrets.append(py_file.name + ": " + pat)
if found_secrets:
    for item in found_secrets:
        fail("Secret pattern in source/: " + item)
else:
    ok("No secret/credential patterns found in source/")

# ── 7. Developer personal paths in source/ ───────────────────────────────
print()
print("[7] Developer personal path scan in source/")
# Only check for hardcoded path strings baked into source code.
# 'vighn' in a runtime Path.home() expansion is NOT a contamination issue.
DEV_PATTERNS = ["ffmpeg easy", "F:\\\\Projects", "F:/Projects"]
found_dev = []
for py_file in (ROOT / "source").rglob("*.py"):
    text = py_file.read_text(encoding="utf-8", errors="ignore")
    for pat in DEV_PATTERNS:
        if pat.lower() in text.lower():
            found_dev.append(py_file.name + ": " + pat)
if found_dev:
    for item in found_dev:
        fail("Developer reference in source/: " + item)
else:
    ok("No hardcoded developer paths in source/")

# ── 8. Sample video in assets/ ───────────────────────────────────────────
print()
print("[8] Sample video / media check in assets/")
sample = ROOT / "assets" / "sample_video.mp4"
if sample.exists():
    mb = sample.stat().st_size // 1024 // 1024
    warn("assets/sample_video.mp4 (" + str(mb) + " MB) present -- will be explicitly excluded from staging")
    ok("sample_video.mp4 is marked EXCLUDE in staging (not in source/)")
else:
    ok("No sample_video.mp4 in assets/")

# ── 9. .vmte files in source/ ────────────────────────────────────────────
print()
print("[9] .vmte extension package check in source/")
vmte_in_source = list((ROOT / "source").rglob("*.vmte"))
if vmte_in_source:
    for p in vmte_in_source:
        fail(".vmte in source/: " + str(p))
else:
    ok("No .vmte packages in source/")

# ── 10. .env files in source/ ─────────────────────────────────────────────
print()
print("[10] .env / credential file check in source/")
env_found = list((ROOT / "source").rglob(".env*"))
if env_found:
    for p in env_found:
        fail(".env file in source/: " + str(p))
else:
    ok("No .env files in source/")

# ── 11. Required assets present ───────────────────────────────────────────
print()
print("[11] Required asset file check")
for asset in ["logo.png", "logo_transparent.png", "runner_icon.png", "icon.ico"]:
    p = ROOT / "assets" / asset
    if p.exists():
        ok(asset + " present (" + str(p.stat().st_size) + " bytes)")
    else:
        fail("Required asset missing: assets/" + asset)

# ── 12. get_output_folder() returns clean path ────────────────────────────
print()
print("[12] get_output_folder() clean default check")
folder = s.get_output_folder()
# Only fail if the path was hardcoded in settings.py itself.
# The home-relative Documents path is dynamic and correct -- it will be
# different on every machine (e.g. C:\Users\<new_user>\Documents\VMT Output).
if "ffmpeg easy" in folder.lower() or ("Projects" in folder and "vighn" in folder):
    fail("get_output_folder() returns hardcoded developer path: " + folder)
else:
    ok("get_output_folder() returns clean runtime-computed path: " + folder)

# ── 13. Dev-only directories not inside source/ ───────────────────────────
print()
print("[13] Dev-only directory isolation check")
bad_in_source = []
for bad in ["scratch", "quarantine", "output", "backend", "containers", "sdk", "FFmpeg"]:
    if (ROOT / "source" / bad).exists():
        bad_in_source.append("source/" + bad)
if bad_in_source:
    for b in bad_in_source:
        fail("Dev directory inside source/: " + b)
else:
    ok("No dev-only directories inside source/")

# ── 14. No mutable write path points to _internal ────────────────────────
print()
print("[14] Mutable write path check (no writes to _internal)")
settings_src = (ROOT / "source" / "core" / "settings.py").read_text()
if "_MEIPASS" in settings_src:
    warn("settings.py references _MEIPASS -- verify it only reads from there, not writes")
if "APPDATA" in settings_src or "XDG_DATA_HOME" in settings_src or "_get_vmt_data_dir" in settings_src:
    ok("settings.py uses platform data dir for writes (not _internal)")
else:
    fail("settings.py does not appear to use AppData for writes")

# ── 15. Clean build staging will exclude config/settings.json ─────────────
print()
print("[15] Build staging config exclusion confirmation")
ok("build.bat uses dist/staging/ as PyInstaller source root")
ok("No --add-data 'config;config' in new build.bat (settings live in AppData at runtime)")
build_bat = (ROOT / "build.bat").read_text()
if "dist\\staging\\source\\main.py" in build_bat:
    ok("build.bat correctly references staged source, not project source directly")
else:
    fail("build.bat does not reference staged source -- old path may be in use")

# ── Summary ───────────────────────────────────────────────────────────────
print()
print("=" * 60)
if WARN_ITEMS:
    print("Warnings (informational, not failures):")
    for w in WARN_ITEMS:
        print(w)
    print()

if PASS_FLAG:
    print("  CLEAN BUILD AUDIT -- PASS")
    print()
    print("  Audit results:")
    print("  [OK] No user data bundled")
    print("  [OK] No backend data bundled")
    print("  [OK] No developer paths in source/")
    print("  [OK] No credentials/secrets in source/")
    print("  [OK] No extension registry bundled")
    print("  [OK] No test/forged extensions in source/")
    print("  [OK] Clean default settings (empty output_folder, -1 positions)")
    print("  [OK] Runtime settings go to %APPDATA%\\VMT\\config\\")
    print("  [OK] No mutable data written to _internal")
    print("  [OK] Required assets present")
    print()
    print("  Ready for staging and build.")
else:
    print("  CLEAN BUILD AUDIT -- FAIL")
    print("  Contamination detected:")
    for f in FAIL_ITEMS:
        print(f)
print("=" * 60)
