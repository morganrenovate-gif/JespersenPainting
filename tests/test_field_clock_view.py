"""Synthetic-only TIME-004 field clock structure and interaction checks."""
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

from field_clock.view import render_field_clock, stylesheet


class ClockMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)

    def find(self, tag, element_id):
        return next(attrs for name, attrs in self.tags if name == tag and attrs.get('id') == element_id)


class FieldClockViewTests(unittest.TestCase):
    def test_one_job_opens_directly_to_clock_in(self):
        html = render_field_clock(('Synthetic Bridge Repaint',))
        tree = ClockMarkup()
        tree.feed(html)
        self.assertIn('Synthetic Bridge Repaint', tree.text)
        self.assertNotIn('disabled', tree.find('button', 'action'))
        self.assertNotIn('fieldset', [tag for tag, _ in tree.tags])
        self.assertIn('Clock In', tree.text)

    def test_multiple_jobs_require_selection(self):
        tree = ClockMarkup()
        tree.feed(render_field_clock(('Synthetic Bridge Repaint', 'Synthetic Workshop Walls')))
        self.assertIn('disabled', tree.find('button', 'action'))
        self.assertEqual(len([1 for tag, attrs in tree.tags if tag == 'input' and attrs.get('name') == 'job']), 2)
        self.assertIn('Choose today’s job', tree.text)
        self.assertNotIn('checked', [attrs for tag, attrs in tree.tags if tag == 'input'][0])

    def test_empty_and_ambiguous_assignments_fail_safe(self):
        html = render_field_clock(())
        self.assertIn('No current assignment', html)
        tree = ClockMarkup()
        tree.feed(html)
        self.assertIn('disabled', tree.find('button', 'action'))
        with self.assertRaises(ValueError):
            render_field_clock(('Synthetic Bridge Repaint', 'Synthetic Bridge Repaint'))
        with self.assertRaises(ValueError):
            render_field_clock((' ',))

    def test_escaping_and_field_only_structure(self):
        html = render_field_clock(('Synthetic <img src=x onerror=alert(1)>',))
        self.assertNotIn('<img', html)
        self.assertIn('&lt;img', html)
        tree = ClockMarkup()
        tree.feed(html)
        self.assertEqual(tree.find('p', 'status')['role'], 'status')
        self.assertEqual(tree.find('p', 'sync-status')['role'], 'status')
        self.assertEqual(tree.find('p', 'sync-status')['aria-live'], 'polite')
        self.assertEqual(tree.find('p', 'elapsed')['role'], 'timer')
        self.assertEqual(tree.find('time', 'started'), {})
        self.assertEqual(tree.find('div', 'running')['hidden'], None)
        self.assertEqual(tree.find('button', 'retry')['disabled'], None)
        self.assertEqual(tree.find('input', 'connection')['type'], 'checkbox')
        self.assertIn('src="pending.js" defer', html)
        self.assertLess(html.index('src="pending.js"'), html.index('src="clock.js"'))
        self.assertIn('Not a work-time record', html)
        self.assertIn('name="viewport"', html)
        self.assertIn('href="#main"', html)
        self.assertNotIn('QuickBooks', html)
        for word in ('payroll', 'reconciliation', 'provider', 'accounting'):
            self.assertNotIn(word, html.lower())
        css = stylesheet()
        for expected in ('min-height: 64px', 'min-height: var(--row)', ':focus-visible',
                         'prefers-reduced-motion: reduce', 'safe-area-inset-bottom',
                         'font-variant-numeric: tabular-nums', '[hidden]', '.sync-pending',
                         '.sync-error'):
            self.assertIn(expected, css)

    @unittest.skipUnless(shutil.which('node'), 'Node unavailable; browser interaction checks require Node')
    def test_synthetic_interaction_transitions(self):
        script = Path(__file__).with_name('field_clock_interaction.cjs')
        subprocess.run(['node', str(script)], check=True, timeout=15)


if __name__ == '__main__':
    unittest.main()
