#!/usr/bin/env python3
"""Deterministically bundle the accepted synthetic-only decoder into the action source.

No package installation, provider invocation or network access. Fails closed if the
accepted decoder's CommonJS envelope changes rather than silently dropping code.
"""
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'private_runtime' / 'xlsx_decoder.cjs'
TEMPLATE = ROOT / 'private_runtime' / 'nango_action.template.mjs'
HEADER = "// PRIVATE-DATA-007 synthetic-source-only decoder. No provider access or formula evaluation.\n'use strict';\nconst {createHash} = require('node:crypto');\nconst {inflateRawSync} = require('node:zlib');\n"
FOOTER = '\nmodule.exports={decode,LIMIT};'
MARKER = '// INSERT_ACCEPTED_DECODER'


def build():
    decoder = SOURCE.read_text(encoding='utf-8')
    template = TEMPLATE.read_text(encoding='utf-8')
    if not decoder.startswith(HEADER) or not decoder.rstrip().endswith(FOOTER) or template.count(MARKER) != 1:
        raise ValueError('accepted decoder envelope changed: review required')
    body = decoder[len(HEADER):].rstrip()[:-len(FOOTER)]
    rewrites = [
        (
            'function archive(b) {',
            'async function archive(b) {',
            'archive async boundary',
        ),
        (
            "method===0 ? part(from,packed) : inflateRawSync(part(from,packed),{maxOutputLength:Math.max(1,plain)})",
            "method===0 ? part(from,packed) : await inflateRawBounded(part(from,packed),plain)",
            'Nango raw-deflate adapter',
        ),
        (
            'function decode(bytes) {\n  const files=archive(bytes),',
            'async function decode(bytes) {\n  const files=await archive(bytes),',
            'decoder async boundary',
        ),
    ]
    for old, new, label in rewrites:
        if body.count(old) != 1:
            raise ValueError(f'accepted decoder {label} changed: review required')
        body = body.replace(old, new, 1)
    artifact = template.replace(MARKER, '// Inlined accepted decoder with Nango-only decompression plumbing.\n' + body)
    if any(word in artifact for word in ('require(', 'module.exports', 'eval(', 'new Function(', "import { inflateRawSync }", 'inflateRawSync(')):
        raise ValueError('runtime module loader, evaluation, or unsupported zlib import detected')
    if "DecompressionStream('deflate-raw')" not in artifact or 'const files=await archive(bytes)' not in artifact:
        raise ValueError('Nango decompression adapter missing: review required')
    return artifact + '\n' if not artifact.endswith('\n') else artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True, help='local untracked compile candidate')
    args = parser.parse_args()
    artifact = build().encode('utf-8')
    args.output.write_bytes(artifact)
    print('sha256 ' + hashlib.sha256(artifact).hexdigest() + '  ' + args.output.name)


if __name__ == '__main__':
    main()
