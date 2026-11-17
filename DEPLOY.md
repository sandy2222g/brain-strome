# Deploy guide (free hosting)

The app is a single container listening on `$PORT` (default 8000). No model files or secrets are needed.

## Option A — Render (free web service)
1. Push this branch to GitHub (already done if you are reading this there).
2. In Render: **New → Blueprint**, select the repo and this branch. `render.yaml` defines a free Docker web service with `/health` as the health check.
   (Or **New → Web Service → Docker**, plan *Free*, no env vars required.)
3. Wait for the build; open the `onrender.com` URL. The free tier sleeps after ~15 min idle, so the first request is slow.

## Option B — Hugging Face Spaces (Docker SDK)
1. Create a new Space, SDK **Docker**, hardware *CPU basic (free)*.
2. Add this front-matter to the top of the Space's `README.md` and set the port:
   ```yaml
   ---
   title: Transit Pass Chooser
   sdk: docker
   app_port: 8000
   ---
   ```
3. Push the repo contents to the Space git remote (`git push space <branch>:main`).

## Run locally
```bash
docker build -t kmeanslab .
docker run --rm -p 8000:8000 kmeanslab   # http://localhost:8000
```

> Status: deployment files are tested locally with Docker; the live hosted URL is not created by the automated build (it requires the owner's Render/HF account).
