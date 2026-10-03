"""Synthetic compile-target and read-only provider-boundary preflight.

Uses local contract stubs: not a claim of an actual Nango compiler invocation.
"""
import hashlib
import pathlib
import subprocess
import tempfile

from private_runtime.build_nango_action import build

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_nango_source_bundle_and_contract():
    artifact = build()
    assert artifact == build()
    assert 'module.exports' not in artifact and 'require(' not in artifact
    assert 'createAction({' in artifact
    with tempfile.TemporaryDirectory() as directory:
        target = pathlib.Path(directory)
        (target / 'action.mjs').write_text(artifact, encoding='utf-8')
        for package, source in {
            'nango': 'export function createAction(definition) { return definition; }',
            'zod': "const chain = {min(){return this},regex(){return this},strict(){return this},nullable(){return this}}; export const z={string:()=>({...chain}),any:()=>({...chain}),object:()=>({...chain}),enum:()=>({...chain})};",
        }.items():
            folder = target / 'node_modules' / package
            folder.mkdir(parents=True)
            (folder / 'package.json').write_text('{"type":"module","exports":"./index.mjs"}')
            (folder / 'index.mjs').write_text(source)
        subprocess.run(['node', '--check', str(target / 'action.mjs')], check=True, timeout=15)
        runner = ROOT / 'tests' / 'nango_action.mjs'
        subprocess.run(['node', str(runner), str(target / 'action.mjs')], check=True, timeout=60)
        digest = hashlib.sha256((target / 'action.mjs').read_bytes()).hexdigest()
        assert digest == hashlib.sha256(artifact.encode('utf-8')).hexdigest()
