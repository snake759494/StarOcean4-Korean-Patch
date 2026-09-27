"""Bind failure reports and runtime acceptance to actual patch payloads."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def payload_id(manifest):
    rows = sorted((r['offset'], r['span'], r['patched_sha256']) for r in manifest['resources'])
    value = [manifest['game_archive'], rows]
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()

def require_candidate(manifest):
    path = ROOT/'localization/known_failed_builds.json'
    failures = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    for failure in failures:
        if failure['payload_id'] == payload_id(manifest):
            raise RuntimeError('Known failed game build: identical payload cannot be reapplied. '+failure['reason'])

def require_runtime_acceptance(manifest, build):
    require_candidate(manifest)
    path = Path(build)/'runtime_acceptance.json'
    if not path.exists():
        raise RuntimeError('Packaging blocked: actual difficulty screens and complete opening playback have not passed runtime validation.')
    report = json.loads(path.read_text(encoding='utf-8'))
    assert report['payload_id'] == payload_id(manifest), 'Runtime evidence belongs to another build'
    assert report['status'] == 'PASS'
    for name in ('difficulty_earth', 'difficulty_galaxy', 'difficulty_universe', 'difficulty_chaos', 'opening_complete_timeline'):
        check = report['checks'][name]
        assert check['status'] == 'PASS' and check['evidence'] and check['observed_result'], name
        for evidence in check['evidence']:
            assert (ROOT/evidence).is_file(), f'Missing runtime evidence: {evidence}'
    return report
