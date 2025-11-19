# backend-ai

This folder contains a minimal AI microservice helper for face recognition, image utilities, and other related functionality, used by the CareerTrust platform.

---

## Quickstart (your simple flow)

If you prefer the direct approach you described (go into `backend-ai`, install dependencies, update C++ tooling if needed, install `insightface`, then run the server), this will work. The only strong recommendation is to avoid installing heavy packages globally — use a virtual environment where possible. Example (PowerShell):

```powershell
cd backend-ai
# (optional but recommended) create + activate a venv first:
# python -m venv .venv
# .\.venv\Scripts\Activate.ps1

# Install dependencies (global or in an activated venv):
pip install -r requirements.txt

# If insightface fails to build, install Visual C++ Build Tools and retry (see Troubleshooting below)

# Run the microservice (global python or the venv python):
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

This is the fastest path and matches your described workflow. It will work, but using an isolated `.venv` avoids polluting the system Python and makes reproducing the environment easier.

## Recommended: isolated virtual environment (preferred)

Using a local virtual environment keeps dependencies scoped to the service and is the recommended approach:

```powershell
cd backend-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start the server with the venv's python so it uses the installed packages:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Notes:
- The `.venv` folder is intentionally local to this project. Do not commit `.venv` to source control. Add it to `.gitignore` if not already excluded.
- The `--host 0.0.0.0` option binds the server to all interfaces; for local-only testing you can omit that or use `127.0.0.1`.

---

## requirements

This repository includes a `requirements.txt` in this folder. Install it with `pip install -r requirements.txt` (recommended inside a venv).

---

## Troubleshooting (InsightFace / Windows builds)

- If `insightface` (or other packages) fail to build on Windows, install the Visual C++ Build Tools (select "Desktop development with C++"):
  https://visualstudio.microsoft.com/visual-cpp-build-tools/

- After installing the build tools, re-open your PowerShell (so PATH/env updates apply) and reinstall:

```powershell
# In the activated venv (recommended) or global python
pip install insightface
```

- If problems persist, capture the pip build output (use `pip install insightface -v`) and share the log.

---

## Alternatives / Notes

- Global install: `pip install -r requirements.txt` without a venv will install packages globally. This is quick but not recommended for repeatable development.
- If you prefer to use Conda, create a conda environment and install dependencies accordingly; adjust the `uvicorn` run command to use the conda python.

---

This microservice provides face detection and embedding extraction functionality, optimized for integration with the CareerTrust system architecture using InsightFace models and FastAPI.
