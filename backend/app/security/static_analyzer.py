import zipfile
import ast
import re
from pathlib import Path
from typing import List, Dict, Any

DANGEROUS_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".sh", ".so", ".dylib", ".scr", ".pif", ".com"
}

SUSPICIOUS_PATTERNS = [
    (r"\bsubprocess\b", "Subprocess execution detected"),
    (r"\bos\.system\b", "os.system command execution detected"),
    (r"\bos\.popen\b", "os.popen command execution detected"),
    (r"\beval\s*\(", "Dynamic eval() invocation detected"),
    (r"\bexec\s*\(", "Dynamic exec() invocation detected"),
    (r"\bpowershell\b", "PowerShell string reference detected"),
    (r"\bcmd\.exe\b", "cmd.exe reference detected"),
    (r"\b__import__\b", "Dynamic __import__() invocation detected"),
    (r"id_rsa|\.ssh|cookies|\.aws|credentials", "Access to sensitive credentials/SSH/cookies detected"),
    (r"os\.environ|settings\.SECRET_KEY", "Access to environment variables or secret keys detected"),
    (r"\bsocket\b|\burllib\b|\brequests\b|\baiohttp\b", "Network socket or HTTP client usage detected")
]


def analyze_package_statically(package_path: Path) -> List[Dict[str, Any]]:
    """
    Statically analyzes a quarantined extension zip package WITHOUT executing Python code.
    Checks:
    1. Zip entry path traversal (../, drive letters, UNC paths)
    2. Executable binaries or script extensions (.exe, .dll, .bat, .ps1, etc.)
    3. Compression ratio / zip bomb defense
    4. Python source AST & regex token scanning for risky security patterns.
    Returns a list of warning dicts for human admin review.
    """
    warnings: List[Dict[str, Any]] = []

    if not package_path.exists():
        warnings.append({"severity": "CRITICAL", "message": "Quarantined package file does not exist"})
        return warnings

    try:
        with zipfile.ZipFile(package_path, "r") as zf:
            total_uncompressed = 0
            total_compressed = 0

            for zinfo in zf.infolist():
                total_uncompressed += zinfo.file_size
                total_compressed += zinfo.compress_size

                filename = zinfo.filename
                # Path traversal checks
                if ".." in filename or filename.startswith("/") or filename.startswith("\\") or ":" in filename:
                    warnings.append({
                        "severity": "CRITICAL",
                        "file": filename,
                        "message": f"Path traversal attempt in archive entry: {filename}"
                    })

                ext = Path(filename).suffix.lower()
                if ext in DANGEROUS_EXTENSIONS:
                    warnings.append({
                        "severity": "HIGH",
                        "file": filename,
                        "message": f"Forbidden binary/executable extension detected: {ext}"
                    })

                # Scan Python files statically via regex & AST parsing
                if filename.endswith(".py"):
                    try:
                        content = zf.read(filename).decode("utf-8", errors="ignore")
                        
                        # Regex pattern scanning
                        for pattern, desc in SUSPICIOUS_PATTERNS:
                            if re.search(pattern, content, re.IGNORECASE):
                                warnings.append({
                                    "severity": "MEDIUM",
                                    "file": filename,
                                    "message": desc
                                })

                        # AST syntax tree parsing
                        try:
                            tree = ast.parse(content, filename=filename)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Call):
                                    if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "compile", "__import__"):
                                        warnings.append({
                                            "severity": "HIGH",
                                            "file": filename,
                                            "line": getattr(node, "lineno", 0),
                                            "message": f"AST Warning: Dynamic code execution function '{node.func.id}'"
                                        })
                        except SyntaxError as se:
                            warnings.append({
                                "severity": "LOW",
                                "file": filename,
                                "message": f"Python syntax error in static parse: {se}"
                            })

                    except Exception as e:
                        warnings.append({
                            "severity": "LOW",
                            "file": filename,
                            "message": f"Could not read source file: {e}"
                        })

            # Check compression ratio (Zip bomb check)
            if total_compressed > 0 and (total_uncompressed / total_compressed) > 100:
                warnings.append({
                    "severity": "HIGH",
                    "message": f"Suspicious compression ratio: {total_uncompressed / total_compressed:.1f}x"
                })

    except zipfile.BadZipFile:
        warnings.append({"severity": "CRITICAL", "message": "File is not a valid ZIP archive"})
    except Exception as e:
        warnings.append({"severity": "HIGH", "message": f"Error inspecting package zip: {e}"})

    return warnings
