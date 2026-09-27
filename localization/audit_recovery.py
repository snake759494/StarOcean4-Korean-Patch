"""Verify every failed-build region against the installed recovery baseline."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    baseline = json.loads((ROOT / 'build/manifest.json').read_text(encoding='utf-8'))
    failed = json.loads((ROOT / 'build_failed_5381/manifest.json').read_text(encoding='utf-8'))
    archive = Path(baseline['game_directory']) / baseline['game_archive']
    active = {(r['offset'], r['span']): r for r in baseline['resources']}
    results = []
    with archive.open('rb') as stream:
        for region in failed['resources']:
            key = region['offset'], region['span']
            replacement = active.get(key)
            expected = replacement['patched_sha256'] if replacement else region['original_sha256']
            stream.seek(region['offset'])
            actual = hashlib.sha256(stream.read(region['span'])).hexdigest()
            assert actual == expected, f'Recovery mismatch: {key}'
            results.append({'offset': region['offset'], 'span': region['span'],
                            'state': 'baseline_patch' if replacement else 'original',
                            'sha256': actual})
    report = {'installed_translation_count': sum(map(len, baseline['translations'].values())),
              'failed_build_translation_count': 5381,
              'runtime_verified': False,
              'user_report': 'Opening glyph corruption and missing captions; difficulty descriptions missing; initial dialogue untranslated.',
              'regions': results}
    (ROOT / 'build/recovery_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'PASS: {len(results)} failed-build regions checked; {len(active)} recovery regions installed.')

if __name__ == '__main__':
    main()
