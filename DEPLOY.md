# Deploy guide (free hosting)

One container, listens on `$PORT` (default 8000). No model files, database or secrets.

## Option A: Render (free web service)
1. Push this branch to GitHub.
2. In Render choose **New, Blueprint**, pick the repo and the `fair-shift-roster` branch. `render.yaml` defines a free Docker web service with `/health` as its health check.
3. Open the `onrender.com` URL when the build finishes. The free tier sleeps when idle, so the first request is slow.

## Option B: Hugging Face Spaces (Docker SDK)
1. Create a Space with SDK **Docker** and free CPU hardware.
2. Put this front-matter at the top of the Space's `README.md`:
   ```yaml
   ---
   title: Fair Shift Roster
   sdk: docker
   app_port: 8000
   ---
   ```
3. Push the repo to the Space remote: `git push space fair-shift-roster:main`.

## Run locally
```bash
docker build -t fair-shift-roster .
docker run --rm -p 8000:8000 fair-shift-roster   # http://localhost:8000
```

Behind a TLS-intercepting proxy, pass your CA bundle as the optional build secret:
`docker build --secret id=cacert,src=/path/ca.pem -t fair-shift-roster .`

> Status: tested locally with Docker. The live hosted URL needs your own Render or Hugging Face account.
