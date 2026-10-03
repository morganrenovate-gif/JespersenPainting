"""Strict verdict extraction; formatting prose cannot silently discard QA."""
import pathlib
import re
import sys


def parse(text):
    # Accept one standalone marker anywhere, never ambiguous/conflicting decisions.
    markers = re.findall(r'^\s*VERDICT: (PASS|FAIL)\s*$', text, re.M)
    if len(markers) != 1:
        raise ValueError('review must contain exactly one standalone verdict')
    return markers[0]


if __name__ == '__main__':
    try:
        verdict = parse(pathlib.Path(sys.argv[1]).read_text())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    print('pass=' + str(verdict == 'PASS').lower())
