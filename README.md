# N1 Spec Portal

Upload a 3GPP DOCX or ZIP containing DOCX files under `spec-source/<spec>/<version>/`, for example `spec-source/24.501/19.0.0/24501-j00.zip`. The generated portal groups Clause, Message, and IE data; Stack and Trace remain `미설정` until evidence is connected. A push runs extraction and the Docusaurus build. GitHub Pages deploy runs only in `Areit0122/n1-spec-portal`.

Run locally:

```sh
npm ci
python3 tools/classify_spec.py
npm run start
```

For a production-like local preview, build and serve the static output:

```sh
python3 tools/classify_spec.py
npm run build
npm run serve -- --host 0.0.0.0
```

The version selector lists only uploaded versions. Diff is unavailable until at least two versions exist. Cross-spec links require an explicit mapping in `mapping/references.json`; no release/version is inferred.

Generated pages under `docs/spec/` and the catalog under `static/spec-catalog.json` are recreated from `spec-source/` on every run. Removing a source version and pushing the deletion removes its generated pages on the next run. No C++ Stack implementation or build/test evidence is included in this portal yet.
