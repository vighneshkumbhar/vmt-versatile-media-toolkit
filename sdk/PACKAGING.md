# Packaging a VMT Extension

1. Create your extension directory structure.
2. Write your `manifest.json` ensuring the ID is in reverse-domain format (e.g., `com.example.myext`).
3. Test locally by loading the directory in VMT.
4. Package by running `build_vmte.py ./my_extension/`. This creates a `.vmte` ZIP archive.
5. Compute the SHA-256 hash (the script does this automatically).
6. Upload the `.vmte` to the VMT Ecosystem portal.
7. Wait for verification review.
