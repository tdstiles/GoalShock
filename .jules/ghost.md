# Ghost's Journal

## 2025-02-18 - Phantom Package.json
**Target:** `backend/package.json`
**Trap:** It looked like a standard project file, but `backend/` is a Python environment. The file contained "my-v0-project" and Next.js dependencies, indicating it was a leftover artifact from a generative AI tool (v0).
**Learning:** Always check `package.json` "name" and "dependencies" in non-JS directories. If a directory is clearly Python (has `__init__.py`, `requirements.txt`), a `package.json` is likely a zombie unless there's a specific Node.js integration.
