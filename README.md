# N1 Spec Portal

Upload a 3GPP DOCX or ZIP containing DOCX files under `spec-source/<spec>/<version>/`, for example `spec-source/24.501/19.0.0/24501-j00.zip`. A push runs the classifier and Docusaurus build. GitHub Pages deploy runs only in `Areit0122/n1-spec-portal`; the private test repository only checks the build.

Run locally:

```sh
npm ci
python3 tools/classify_spec.py
npm run start
```

Generated pages under `docs/spec/` are recreated from `spec-source/` on every run. Removing a source version and pushing the deletion removes its generated pages on the next run.
