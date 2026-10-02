// Synthetic-only TIME-003 interaction checks using a small DOM stand-in (no network).
const assert = require('node:assert/strict');
const { mount, formatElapsed } = require('../field_clock/clock.js');

function fixture(labels) {
  const nodes = {};
  for (const id of ['main', 'choices', 'action', 'shift-heading', 'status', 'running',
    'active-job', 'elapsed', 'started', 'finished', 'selected-job']) {
    nodes[id] = { textContent: '', hidden: false, disabled: false, dataset: {},
      listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; } };
  }
  nodes.main.dataset.assignmentCount = String(labels.length);
  nodes['selected-job'].textContent = labels[0] || '';
  nodes.action.textContent = 'Clock In';
  nodes.action.disabled = labels.length !== 1;
  nodes.running.hidden = true;
  nodes.finished.hidden = true;
  let current = new Date('2026-01-01T09:00:00Z'); // invented time for deterministic checks
  let tick, cancelled = false;
  const doc = { getElementById(id) { return nodes[id]; } };
  mount(doc, () => current, fn => { tick = fn; return 1; }, () => { cancelled = true; });
  return {
    nodes,
    click() { if (!nodes.action.disabled) nodes.action.listeners.click(); },
    select(index) {
      nodes.choices.listeners.change({ target: {
        matches: () => true,
        parentElement: { querySelector: () => ({ textContent: labels[index] }) }
      } });
    },
    advance(ms) { current = new Date(current.getTime() + ms); tick(); },
    get cancelled() { return cancelled; }
  };
}

assert.equal(formatElapsed(3661000), '01:01:01');
{
  const f = fixture(['Synthetic Bridge Repaint']);
  assert.equal(f.nodes.action.disabled, false);
  f.click();
  assert.equal(f.nodes['active-job'].textContent, 'Synthetic Bridge Repaint');
  assert.equal(f.nodes['shift-heading'].textContent, 'Clocked in');
  assert.equal(f.nodes.status.textContent, 'Clock running · Synthetic Bridge Repaint');
  assert.equal(f.nodes.action.textContent, 'Clock Out');
  assert.equal(f.nodes.running.hidden, false);
  assert.equal(f.nodes.choices.hidden, true);
  assert.equal(f.nodes.started.dateTime, '2026-01-01T09:00:00.000Z');
  f.advance(3661000);
  assert.equal(f.nodes.elapsed.textContent, '01:01:01');
  f.click();
  assert.equal(f.cancelled, true);
  assert.equal(f.nodes.running.hidden, true);
  assert.equal(f.nodes.choices.hidden, false);
  assert.equal(f.nodes['shift-heading'].textContent, 'Clocked out');
  assert.match(f.nodes.status.textContent, /^Clocked out · Synthetic Bridge Repaint$/);
  assert.equal(f.nodes.finished.hidden, false);
  assert.equal(f.nodes.action.textContent, 'Clock In');
}
{
  const f = fixture(['Synthetic Bridge Repaint', 'Synthetic Workshop Walls']);
  f.click();
  assert.equal(f.nodes['shift-heading'].textContent, '');
  // Even a programmatically triggered click without a selection cannot start time.
  f.nodes.action.listeners.click();
  assert.equal(f.nodes.running.hidden, true);
  f.select(1);
  assert.equal(f.nodes.action.disabled, false);
  f.click();
  assert.equal(f.nodes['active-job'].textContent, 'Synthetic Workshop Walls');
  f.click();
  f.select(0);
  f.click();
  assert.equal(f.nodes['active-job'].textContent, 'Synthetic Bridge Repaint');
}
{
  const f = fixture([]);
  assert.equal(f.nodes.action.disabled, true);
  f.nodes.action.listeners.click();
  assert.equal(f.nodes.running.hidden, true);
}
console.log('Synthetic field-clock interaction checks completed');
