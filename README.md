# Marin Jobs

Marin Jobs lets County of Marin staff search and compare County of Marin job classifications and their published pay rates. It reads the County's public [Job Classifications and Pay Rates](https://data.marincounty.gov/d/w7uw-fvda) dataset in the browser. Nothing is stored on a server.

## Structure

- `index.html`: the app page
- `assets/job-pay-core.js`: reads the dataset into job classes and works out pay figures
- `assets/app.js`: the page: search, sort, filters, comparison and the CSV and JSON downloads
- `assets/search-layout.js`: the search and filter behavior shared by both
- `assets/app.css`: the look of the page
- `vendor/`: the installed MarinOS App Shell
- `security.json`: the security profile; the Content Security Policy in `index.html` is generated from it with `python3 scripts/sync-security-meta.py --write`

This app used to be a tool inside Marin Docs. Its old address there forwards here.

## Run locally

From this folder, run `python3 -m http.server 8765 --bind 127.0.0.1` and open `http://127.0.0.1:8765/`.

## Checks

Run `bash scripts/check.sh`. - `node tests/test_job_pay.js`: checks how the dataset is read
- `python3 tests/browser_job_pay_embedded.py` and `python3 tests/browser_job_pay.py`: browser tests that use a made-up copy of the dataset and never contact the live service

## Security

Marin Jobs follows the [MarinOS security standard](https://github.com/marincountygov/marin-digital-standards/blob/main/security/standard.md). See [`SECURITY.md`](SECURITY.md) to report an issue.
