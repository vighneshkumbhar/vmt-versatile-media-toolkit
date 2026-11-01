import sys
import os
import json
import zipfile
import hashlib

def build_vmte(ext_dir):
    if not os.path.isdir(ext_dir):
        print("Directory not found")
        return
        
    manifest_path = os.path.join(ext_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print("manifest.json not found")
        return
        
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    ext_id = manifest.get("id")
    version = manifest.get("version", "1.0.0")
    
    if not ext_id:
        print("Manifest missing id")
        return
        
    out_name = f"{os.path.basename(os.path.normpath(ext_dir))}-{version}.vmte"
    
    with zipfile.ZipFile(out_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(ext_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, ext_dir)
                zf.write(abs_path, rel_path)
                
    sha256_hash = hashlib.sha256()
    with open(out_name, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            
    print(f"Created: {out_name}")
    print(f"SHA-256: {sha256_hash.hexdigest()}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_vmte.py <extension_dir>")
        sys.exit(1)
    build_vmte(sys.argv[1])
