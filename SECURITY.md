# VMT Extension Ecosystem — Security Architecture & Policy

---

## 1. Reporting Vulnerabilities

If you discover a security vulnerability in VMT Core or the VMT Extension Ecosystem, please submit a responsible disclosure report to the VMT security team via email at `security@vmt.dev`.

Please include:
- A clear description of the vulnerability and affected components
- Step-by-step proof-of-concept (PoC) or reproduction steps
- Potential security impact assessment

We request that you refrain from disclosing vulnerabilities publicly until we have reviewed and addressed the report.

---

## 2. Developer Identity & Authentication Controls

- **Role-Based Access Control (RBAC)**: Server-side authorization distinguishes between `user`, `developer`, and `admin` roles. Developer roles permit profile management and submission creation, but **NEVER** grant elevated admin permissions, auto-verification capabilities, or catalog manipulation rights.
- **Argon2id Password Security**: Passwords are hashed using Argon2id with unique per-user salts and a server-side `PASSWORD_PEPPER` from environment configuration. Legacy bcrypt hashes are supported with automatic migration to Argon2id upon successful authentication.
- **Timing Defense & Anti-Enumeration**: Failed login attempts execute a dummy Argon2id hash verification path when an account is not found, ensuring indistinguishable timing between valid and invalid usernames. Generic `"Invalid credentials"` responses prevent email/username enumeration.
- **Short-Lived Access & Rotatable Refresh Sessions**: Short-lived JWT access tokens (15 mins) and rotatable refresh tokens stored as SHA-256 hashes in `user_sessions`. Detection of token reuse triggers automatic security revocation of all active sessions for the user.

---

## 3. Extension Submission & Quarantine Pipeline

- **Hostile Submitted Content Isolation**: Extension packages submitted via GitHub URLs or upload are placed in a configurable `QUARANTINE_PATH` (`backend/quarantine/`).
- **No Code Execution During Inspection**: Quarantined extension code is **NEVER executed, imported, or run** (no `setup.py`, build scripts, shell/PowerShell scripts, or module imports) during initial inspection.
- **SSRF-Hardened GitHub URL Validation**: Submissions require HTTPS `github.com` URLs with exact release tags and versions. Host resolution checks enforce strict IP filtering blocking loopback (`127.0.0.0/8`), private RFC1918, link-local (`169.254.0.0/16`), and multicast/reserved IP ranges across all redirects.
- **Static Security Analysis**: Zip archive headers are checked for path traversal (`../`, drive letters, UNC paths), executable binaries (`.exe`, `.dll`, `.ps1`), zip bombs, and Python AST AST/token patterns (`subprocess`, `os.system`, `eval`, `exec`, SSH keys, credential access) to produce review warnings for human admins.
- **Replaceable Malware Scanner Interface**: `MalwareScanner` abstraction allows plugging in local or cloud antivirus engines (`LocalScanner`, `DummyScanner`).

---

## 4. Application Append-Only Audit Logging

Security-sensitive operations (`login_success`, `login_failure`, `account_creation`, `extension_submission`, `admin_submission_approved`, `admin_version_verified`) produce immutable append-only audit entries in `audit_logs`. No API endpoints permit updating or deleting audit records. Passwords, hashes, secrets, peppers, and tokens are **never** logged.

---

## 5. Fundamental Architectural Limitations & Verification Guarantees

> [!WARNING]
> **No OS-Level Sandboxing**: VMT Python extensions run directly within the desktop application Python runtime without OS-level sandboxing.

### What Extension Verification Means:
- The extension package passed static archive validation and security scanning without flagged malware.
- The VMT security team manually reviewed the extension source code for malicious intent.
- The author developer account is verified and in good standing.

### What Extension Verification Does NOT Mean:
- Verification does **NOT** guarantee absolute runtime safety or absence of zero-day vulnerabilities.
- Verification does **NOT** isolate the extension from filesystem or network access permitted to the main application process.

Users should exercise standard caution when installing third-party extensions.
