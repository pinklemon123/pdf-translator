# PDF Translator — multi-modal prototype

This repository contains a small prototype to translate English PDFs/images/HTML into Chinese while attempting to preserve layout. It's designed for local development and can be deployed to Linux hosts (for example, runpod) via Docker.

## Quick start (local)

1. Create and activate a Python venv in `backend/`:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # on Windows PowerShell
pip install -r requirements.txt
```

2. Run the backend (development):

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

3. Open the front-end (served from backend): http://127.0.0.1:8000/

## Docker (recommended for runpod / Linux)

Build the Docker image and push to a container registry (Docker Hub, GitHub Container Registry, etc.).

```bash
# from repo root
cd backend
docker build -t YOUR_DOCKERHUB_USER/pdf-translator:latest .
docker push YOUR_DOCKERHUB_USER/pdf-translator:latest
```

On runpod you can create a new server from a Docker image and point it to this image.

## GitHub

To publish this repository to GitHub (run locally):

```powershell
git init
git add .
git commit -m "Initial local import"
git remote add origin git@github.com:<youruser>/pdf-translator.git
git branch -M main
git push -u origin main
```

Note: I cannot push to your GitHub from here — you'll need to run the above commands locally with your credentials.

## Deploy notes for runpod

- Use the Docker image flow (preferred). Build the image locally or with GitHub Actions and push to a registry.
- On runpod, choose "Start from Docker image" and specify the image name.
- Ensure you expose port 8000 and set any environment variables (for example, to choose CPU/GPU options).

## Files of interest

- `backend/app/main.py` — FastAPI app and routes
- `backend/app/translator.py` — PDF translation pipeline
- `backend/app/translator_html.py` — HTML translation
- `backend/app/translator_image.py` — Image OCR+translate pipeline (easyocr)
- `backend/Dockerfile` — Dockerfile for backend
- `backend/requirements.txt` — Python dependencies
