"""Synthetic dispatcher DOM/clock test; never reads a device's location."""
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page()
    page.clock.install()
    now=time.time()
    page.set_content(f'<section id="location-panel" data-server-epoch="{now}"><article data-location-card data-expires="{now+40}" data-captured="{now}"><span data-freshness>Recent</span><p>Latitude 12.3456 Longitude 65.4321</p></article></section>')
    page.add_script_tag(path=str(ROOT/'static/dispatcher-expiry.js'))
    page.clock.fast_forward(31000)
    assert page.locator('[data-freshness]').inner_text()=='Stale'
    checks.append('Rendered sample marked Stale after 30 seconds without refresh')
    page.clock.fast_forward(10000)
    assert page.locator('[data-location-card]').count()==0 and '12.3456' not in page.content()
    checks.append('Expired coordinate card removed from DOM without refresh')
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    assert page.locator('[data-expired-message]').count()==1
    checks.append('Visibility-change expiry handler idempotent')
    browser.close()
result={'checks':checks,'fixture':'Fictional DOM and accelerated Chromium clock, not a device GPS test'}
(ROOT/'evidence/v0.4/dispatcher-expiry-browser.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
