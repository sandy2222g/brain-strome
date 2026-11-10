# Deploy guide (free hosting)

rent-check is a single container listening on `$PORT` (default 8000). The three quantile models are trained at image build time from the bundled synthetic data in `data/listings.csv`, so no external services or secrets are needed.

## Option A: Render (free web service)
1. Push this branch to GitHub.
2. In Render choose **New, Blueprint**, pick the repo and this branch. `render.yaml` defines a free Docker web service with `/health` as the health check.
3. Open the `onrender.com` URL once the build finishes. The free tier sleeps after about 15 minutes idle, so the first request is slow.

## Option B: Hugging Face Spaces (Docker SDK)
1. Create a Space with SDK **Docker** and hardware *CPU basic (free)*.
2. Put this front matter at the top of the Space's `README.md`:
   ```yaml
   ---
   title: Rent Check
   sdk: docker
   app_port: 8000
   ---
   ```
3. Push the repo contents to the Space remote (`git push space rent-check:main`).

## Run locally
```bash
docker build -t rent-check .
docker run --rm -p 8000:8000 rent-check   # http://localhost:8000
```

Behind a TLS-intercepting proxy, pass your CA bundle as an optional BuildKit secret:
`docker build --secret id=cacert,src=/path/ca.pem -t rent-check .`

> Status: the deployment files are tested locally with Docker. A live hosted URL needs the owner's Render or Hugging Face account.
