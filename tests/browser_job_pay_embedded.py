#!/usr/bin/env python3
"""DOM integration smoke test without HTTP navigation or calls to external services.

Useful for restricted test environments: load the real page and scripts into a blank
browser document, fake the public feed, and exercise their actual DOM behavior.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'assets'
RECORDS = json.loads((ROOT / 'tests/fixtures/job-pay-sample.json').read_text())
FILTERS = json.loads((ROOT / 'filters.json').read_text())


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    markup = (ROOT / 'index.html').read_text()
    # We inject the local JavaScript below, preserving exact script order without network calls.
    markup = re.sub(r'<script\b[^>]*\bsrc="[^"]+"[^>]*></script>', '', markup)
    markup = re.sub(r'<link\s+rel="stylesheet"[^>]*>', '', markup)
    markup = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', '', markup)  # the test adds scripts by hand
    markup = markup.replace('</main>', '<div id="app-status-message"></div></main>')  # the shell adds this in the real app
    with sync_playwright() as pw:
        executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE')
        browser = pw.chromium.launch(executable_path=executable) if executable else pw.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 1200, 'height': 900})
            errors = []
            page.on('pageerror', lambda exc: errors.append(str(exc)))
            page.set_content(markup)
            page.evaluate("""([records, filters]) => {
                window.__downloads = [];
                window.__lastURL = '';
                window.history.replaceState = (state, title, url) => { window.__lastURL = url; };
                window.marinDownload = (download) => { window.__downloads.push(download); };
                window.fetch = async (url) => ({ ok: true, json: async () => (String(url).includes('filters.json') ? filters : records) });
            }""", [RECORDS, FILTERS])
            page.add_script_tag(content=(ROOT / 'vendor/marinos/marinos.js').read_text())
            # The shell defines its own download helper; the test records downloads instead of saving them.
            page.evaluate("() => { window.marinDownload = (download) => { window.__downloads.push(download); }; }")
            for filename in ('job-pay-core.js', 'app.js'):
                page.add_script_tag(content=(SCRIPTS / filename).read_text())
            page.wait_for_function("document.querySelector('#job-total').textContent === '5'")
            require(page.locator('#job-results > li').count() == 5, 'All rows rendered')
            require(page.locator('#job-error').is_hidden(), 'Data available')
            require(page.locator('#job-results script').count() == 0, 'Untrusted HTML escaped')
            require(page.locator('#job-step-patterns').inner_text() == '3', 'Step patterns computed')
            require(page.locator('#job-pay-schedules').inner_text() == '2', 'Schedules computed')
            require(page.locator('#job-highest').inner_text() == '$312,728', 'Maximum computed')
            page.locator('#job-results > li[data-job-id="2"] .job-card-details > summary').click()
            require(page.locator('#job-results > li[data-job-id="2"] table tbody tr').count() == 3, 'Published steps only')
            page.locator('#job-search-input').fill('037A')
            page.wait_for_function("document.querySelector('#job-results-count').textContent === '1 of 5 job classes'")
            require(page.evaluate("window.__lastURL.includes('q=037A')"), 'URL state updated: ' + repr(page.evaluate('window.__lastURL')))
            require(page.locator('#job-results > li:visible').count() == 1, 'Query filters list')
            page.locator('#job-classes-filter-panel .action-button').click()
            require(page.locator('#job-results > li:visible').count() == 5, 'Reset shows all')
            page.locator('#payband-facet details').evaluate('(element) => element.open = true')
            page.locator('#payband-facet input[value="250k-plus"]').check()
            require(page.locator('#job-results > li:visible').count() == 1, 'Pay-band filter works')
            page.locator('#job-classes-filter-panel .action-button').click()
            page.locator('#job-sort').select_option('max_yearly')
            page.locator('#job-sort-direction').select_option('desc')
            require(page.locator('#job-results > li').first.locator('.job-card-title').inner_text() == 'ASSISTANT COUNTY COUNSEL', 'Numeric sort desc')
            page.locator('#job-results > li[data-job-id="0"] .job-compare-checkbox').check()
            page.locator('#job-results > li[data-job-id="1"] .job-compare-checkbox').check()
            page.locator('#job-results > li[data-job-id="2"] .job-compare-checkbox').check()
            require(page.locator('#job-compare').is_visible(), 'Comparison panel displayed')
            require(page.locator('#job-compare table thead th').count() == 4, 'Comparison has three classes')
            require(page.locator('#job-results > li[data-job-id="3"] .job-compare-checkbox').is_disabled(), 'Fourth class cannot be added')
            page.locator('#job-clear-compare').click()
            require(page.locator('#job-compare').is_hidden(), 'Comparison cleared')
            page.locator('#job-search-input').fill('037A')
            page.wait_for_function("document.querySelector('#job-results-count').textContent.startsWith('1 of 5')")
            page.locator('#job-export-json').click()
            page.locator('#job-export-csv').click()
            downloads = page.evaluate('window.__downloads')
            require(len(downloads) == 2, 'Both exports produced')
            require(json.loads(downloads[0]['content'])[0]['job_class_code'] == '037A', 'JSON contains filtered source record')
            require(downloads[1]['content'].count('\r\n') == 2 and '"41.09"' in downloads[1]['content'], 'CSV contains salary step')
            page.locator('#job-classes-filter-panel .action-button').click()
            page.locator('#job-search-input').fill('DANGEROUS')
            page.wait_for_function("document.querySelector('#job-results-count').textContent.startsWith('1 of 5')")
            page.locator('#job-export-csv').click()
            risky_csv = page.evaluate('window.__downloads.at(-1).content')
            require('"\'=DANGEROUS()' in risky_csv, 'CSV formula injection blocked')
            require(not errors, 'No JavaScript exceptions: ' + repr(errors))
            page.close()
        finally:
            browser.close()
    print('Marin Jobs embedded browser integration (mock feed, no network): PASS')


if __name__ == '__main__':
    try:
        main()
    except AssertionError as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
