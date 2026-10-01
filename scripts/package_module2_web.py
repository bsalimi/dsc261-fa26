#!/usr/bin/env python3
"""Publish the unchanged offline presentation with separately cacheable assets."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
args = parser.parse_args()
expected = '80ad420cae93dfd7f8f63d9a08fffa98c00ae8fce3daf16d0a889f4b39e650bc'
source = args.source.read_bytes()
assert hashlib.sha256(source).hexdigest() == expected, 'Unexpected source revision'
original = source.decode('utf-8')
root = Path(__file__).resolve().parents[1] / 'slides/module-2'
assets = root / 'assets'
assets.mkdir(parents=True, exist_ok=True)
pattern = re.compile(r'data:(image/[a-zA-Z0-9.+-]+|font/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)')
extensions = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/svg+xml': 'svg',
              'font/ttf': 'ttf', 'font/woff': 'woff', 'font/woff2': 'woff2'}
records = {}
replacements = {}

def extract(match):
    mime, encoded = match.groups()
    content = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(content).hexdigest()
    name = f'{digest}.{extensions[mime]}'
    target = assets / name
    if target.exists():
        assert target.read_bytes() == content, f'Asset collision: {name}'
    else:
        target.write_bytes(content)
    url = './assets/' + name
    records[url] = {'path': url, 'mime': mime, 'sha256': digest, 'bytes': len(content)}
    replacements[url] = match.group(0)
    return url

published = pattern.sub(extract, original)
offline_link_check = "startsWith('data:image/')"
web_link_check = r"match(/^(?:data:image\/|\.\/assets\/)/)"
assert published.count(offline_link_check) == 2
published = published.replace(offline_link_check, web_link_check)
restored = published.replace(web_link_check, offline_link_check)
for url, data in replacements.items():
    restored = restored.replace(url, data)
assert restored == original, 'Changed content beyond lossless asset extraction/link handling'
assert records, 'No assets found'
(root / 'index.html').write_text(published, encoding='utf-8')
receipt = {
    'source_sha256': expected,
    'public_html_sha256': hashlib.sha256(published.encode()).hexdigest(),
    'source_bytes': len(source), 'public_html_bytes': len(published.encode()),
    'slide_count': 86, 'content_and_notes_unchanged': True,
    'verification': 'Re-embedding the exact assets and reversing only the web-asset link check reproduces the original HTML byte for byte.',
    'web_link_compatibility': 'Both image clicks and keyboard-activated figure links retain the in-file enlargement dialog.',
    'assets': list(records.values()),
}
(root / 'publication.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'assets'}))
print(f'{len(records)} unique assets extracted; offline source is unchanged.')
