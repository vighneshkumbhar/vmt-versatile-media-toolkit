import zipfile
import json
import io
import re
from fastapi import HTTPException

ID_REGEX = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*){2,}$")

def validate_vmte_package(data: bytes) -> dict:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            if "manifest.json" not in zf.namelist():
                raise HTTPException(400, "Missing manifest.json in package")
            
            for info in zf.infolist():
                if info.filename.startswith("/") or ".." in info.filename:
                    raise HTTPException(400, "Invalid file path in zip")
            
            with zf.open("manifest.json") as f:
                manifest = json.load(f)
                
            if "id" not in manifest or not ID_REGEX.match(manifest["id"]):
                raise HTTPException(400, "Invalid or missing extension id in manifest")
            
            if "version" not in manifest:
                raise HTTPException(400, "Missing version in manifest")
                
            if "verified" in manifest:
                del manifest["verified"]
                
            return manifest
    except zipfile.BadZipFile:
        raise HTTPException(400, "Invalid zip file")
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON in manifest")
