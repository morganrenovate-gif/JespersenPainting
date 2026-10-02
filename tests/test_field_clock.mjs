// SYNTHETIC TIME-003 interaction tests: no employee or provider data.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mountClock, elapsed } from '../field_clock/clock.mjs';

const jobs = [
  { id: 'synthetic-yard', label: 'North Yard • Exterior coating' },
  { id: 'synthetic-bay', label: 'Workshop Bay • Interior finish' },
];
const start = new Date('2026-01-02T08:00:00Z');
function harness(assignments, callbacks = {}) {
  const counter = { textContent: '' };
  const root = {
    innerHTML: '', listener: null,
    addEventListener(type, fn) { this.listener = fn; },
    removeEventListener(type, fn) { if (this.listener === fn) this.listener = null; },
    contains(button) { return button.owner === this; },
    querySelector(selector) { return selector === '.elapsed' ? counter : null; },
  };
  let tick;
  let now = start;
  const calls = [];
  const dispose = mountClock(root, {
    assignments,
    now: () => now,
    setInterval: (fn) => { tick = fn; return 1; },
    clearInterval: () => {},
    onClockIn: callbacks.onClockIn ?? (async (job) => { calls.push(['in', job]); return start; }),
    onClockOut: callbacks.onClockOut ?? (async (job, time) => { calls.push(['out', job, time]); }),
  });
  async function click(action, index = '') {
    const button = { owner: root, dataset: { action, index: String(index) }, disabled: false };
    await root.listener({ target: { closest: () => button } });
  }
  return { root, counter, calls, click, dispose, advance: (ms) => { now = new Date(start.getTime() + ms); tick(); } };
}

test('one synthetic assignment opens directly to Clock In, then running job/time and Clock Out', async () => {
  const h = harness([jobs[0]]);
  assert.match(h.root.innerHTML, /YOUR ASSIGNMENT.*North Yard/s);
  assert.match(h.root.innerHTML, /data-action="in" >Clock In/);
  assert.doesNotMatch(h.root.innerHTML, /Choose your job/);
  await h.click('in');
  assert.deepEqual(h.calls, [['in', jobs[0]]]);
  assert.match(h.root.innerHTML, /Clocked in/);
  assert.match(h.root.innerHTML, /ON THE JOB.*North Yard.*TIME ON JOB.*00:00:00.*Started/s);
  assert.match(h.root.innerHTML, /Clock Out/);
  h.advance(65000);
  assert.equal(h.counter.textContent, '00:01:05');
  await h.click('out');
  assert.deepEqual(h.calls[1], ['out', jobs[0], start]);
  assert.match(h.root.innerHTML, /Clocked out/);
  assert.doesNotMatch(h.root.innerHTML, /Clock Out/);
  h.dispose();
});

test('multiple synthetic jobs require explicit selection, retain selected job while running', async () => {
  const h = harness(jobs);
  assert.match(h.root.innerHTML, /Choose your job/);
  assert.match(h.root.innerHTML, /data-action="in" disabled/);
  await h.click('in');
  assert.equal(h.calls.length, 0);
  await h.click('select', 1);
  assert.match(h.root.innerHTML, /aria-pressed="true"/);
  await h.click('in');
  assert.deepEqual(h.calls, [['in', jobs[1]]]);
  assert.match(h.root.innerHTML, /ON THE JOB.*Workshop Bay/s);
  assert.doesNotMatch(h.root.innerHTML, /Choose your job/);
  await h.click('in');
  assert.equal(h.calls.length, 1);
  await h.click('out');
  assert.deepEqual(h.calls[1], ['out', jobs[1], start]);
  assert.match(h.root.innerHTML, /Choose your job/);
  h.dispose();
});

test('pending capture blocks duplicate actions; failed capture leaves state truthful', async () => {
  let release;
  let count = 0;
  const h = harness([jobs[0]], { onClockIn: () => { count++; return new Promise((resolve) => { release = resolve; }); } });
  const first = h.click('in');
  assert.match(h.root.innerHTML, /Clocking in…/);
  await h.click('in');
  assert.equal(count, 1);
  release(null);
  await first;
  assert.match(h.root.innerHTML, /Could not clock in/);
  assert.match(h.root.innerHTML, /Clocked out/);
  h.dispose();
});

test('clock-out failure preserves running state; no assignments show no action', async () => {
  const h = harness([jobs[0]], { onClockOut: async () => { throw new Error('private detail'); } });
  await h.click('in');
  await h.click('out');
  assert.match(h.root.innerHTML, /Clocked in/);
  assert.match(h.root.innerHTML, /Could not clock out/);
  assert.doesNotMatch(h.root.innerHTML, /private detail/);
  h.dispose();
  const empty = harness([]);
  assert.match(empty.root.innerHTML, /No current assignment/);
  assert.doesNotMatch(empty.root.innerHTML, /data-action="in"/);
  empty.dispose();
});

test('labels are escaped and elapsed time uses tabular hh:mm:ss', () => {
  const h = harness([{ id: 'synthetic-x', label: '<img src=x onerror=alert(1)>' }]);
  assert.match(h.root.innerHTML, /&lt;img/);
  assert.doesNotMatch(h.root.innerHTML, /<img/);
  assert.equal(elapsed(start, new Date(start.getTime() + 3600000 + 2000)), '01:00:02');
  h.dispose();
});
