// Synthetic-only TIME-004 deterministic DOM, storage and receiver checks (no network).
const assert = require('node:assert/strict');
const { mount, formatElapsed } = require('../field_clock/clock.js');
const { createQueue, memoryReceiver, KEY } = require('../field_clock/pending.js');
const jobA = 'Synthetic Bridge Repaint';
const jobB = 'Synthetic Workshop Walls';
const at = new Date('2026-01-01T09:00:00Z');
function storage() {
  const values = new Map();
  return {
    getItem: key => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, value),
    raw: values
  };
}
function fixture(labels, store = storage(), receiver = memoryReceiver()) {
  const nodes = {};
  for (const id of ['main', 'choices', 'action', 'shift-heading', 'status', 'running',
    'active-job', 'elapsed', 'started', 'finished', 'selected-job', 'sync-status',
    'latest-event', 'connection', 'retry']) {
    nodes[id] = { textContent: '', hidden: false, disabled: false, checked: false, dataset: {},
      listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; } };
  }
  nodes.main.dataset.assignmentCount = String(labels.length);
  nodes['selected-job'].textContent = labels[0] || '';
  nodes.action.textContent = 'Clock In';
  nodes.action.disabled = labels.length !== 1;
  nodes.running.hidden = true;
  nodes.finished.hidden = true;
  let current = at, tick, cancelled = false, nextId = 0;
  const doc = { getElementById(id) { return nodes[id]; } };
  const mounted = mount(doc, () => current, fn => { tick = fn; return 1; },
    () => { cancelled = true; }, { storage: store, receiver, makeId: () => `synthetic-${++nextId}-${current.getTime()}` });
  return {
    nodes, store, receiver,
    click() { if (!nodes.action.disabled) nodes.action.listeners.click(); },
    select(index) { nodes.choices.listeners.change({ target: {
      matches: () => true,
      parentElement: { querySelector: () => ({ textContent: labels[index] }) }
    } }); },
    connect() { nodes.connection.checked = true; nodes.connection.listeners.change(); },
    retry() { if (!nodes.retry.disabled) nodes.retry.listeners.click(); },
    advance(ms) { current = new Date(current.getTime() + ms); tick(); },
    dispose: () => mounted.dispose(),
    get cancelled() { return cancelled; }
  };
}
assert.equal(formatElapsed(3661000), '01:01:01');
{
  const store = storage(), receiver = memoryReceiver();
  const f = fixture([jobA], store, receiver);
  assert.equal(f.nodes.action.disabled, false);
  f.click();
  assert.equal(f.nodes['active-job'].textContent, jobA);
  assert.equal(f.nodes['shift-heading'].textContent, 'Clocked in');
  assert.match(f.nodes.status.textContent, /Clock running/);
  assert.equal(f.nodes.action.textContent, 'Clock Out');
  assert.equal(f.nodes.running.hidden, false);
  assert.equal(f.nodes.choices.hidden, true);
  assert.equal(f.nodes.started.dateTime, at.toISOString());
  assert.match(f.nodes['sync-status'].textContent, /Pending · 1 local preview event/);
  assert.match(f.nodes['latest-event'].textContent, /Latest pending: Clock In · Synthetic Bridge Repaint/);
  assert.equal(f.nodes.retry.disabled, true);
  f.advance(3661000);
  assert.equal(f.nodes.elapsed.textContent, '01:01:01');
  f.dispose();
  const reloaded = fixture([jobA], store, receiver);
  assert.equal(reloaded.nodes.action.textContent, 'Clock Out');
  assert.match(reloaded.nodes['sync-status'].textContent, /Pending · 1/);
  assert.equal(reloaded.nodes['active-job'].textContent, jobA);
  reloaded.connect();
  reloaded.retry();
  assert.equal(receiver.accepted().length, 1);
  assert.match(reloaded.nodes['sync-status'].textContent, /Preview replay complete/);
  assert.equal(reloaded.nodes.retry.disabled, true);
  reloaded.click();
  assert.equal(reloaded.cancelled, true);
  assert.equal(reloaded.nodes.running.hidden, true);
  assert.equal(reloaded.nodes.choices.hidden, false);
  assert.equal(reloaded.nodes['shift-heading'].textContent, 'Clocked out');
  assert.match(reloaded.nodes.status.textContent, /Clocked out/);
  assert.equal(reloaded.nodes.finished.hidden, false);
  assert.equal(reloaded.nodes.action.textContent, 'Clock In');
  assert.match(reloaded.nodes['sync-status'].textContent, /Pending · 1/);
  reloaded.retry();
  assert.equal(receiver.accepted().length, 2);
  assert.equal(receiver.accepted()[1].startId, receiver.accepted()[0].id);
}
{
  const f = fixture([jobA, jobB]);
  f.click();
  assert.equal(f.nodes['shift-heading'].textContent, '');
  f.nodes.action.listeners.click();
  assert.equal(f.nodes.running.hidden, true);
  f.select(1);
  f.click();
  assert.equal(f.nodes['active-job'].textContent, jobB);
  f.click();
  f.select(0);
  f.click();
  assert.equal(f.nodes['active-job'].textContent, jobA);
}
{
  const f = fixture([]);
  assert.equal(f.nodes.action.disabled, true);
  f.nodes.action.listeners.click();
  assert.equal(f.nodes.running.hidden, true);
}
{
  const store = storage(), receiver = memoryReceiver();
  const q = createQueue(store, receiver, () => 'synthetic-id');
  const event = q.capture('in', jobA, at);
  assert.throws(() => q.capture('in', jobA, at), /Already clocked in/);
  assert.equal(createQueue(store, receiver, () => 'unused').snapshot().pending[0].id, event.id);
  // Ambiguous acknowledgement: receiver accepted but local acknowledgement write failed.
  const write = store.setItem;
  store.setItem = () => { throw Error('Synthetic quota failure'); };
  assert.throws(() => q.replay(), /Synthetic quota failure/);
  assert.equal(receiver.accepted().length, 1);
  store.setItem = write;
  assert.equal(q.snapshot().pending.length, 1);
  assert.equal(q.replay(), 1);
  assert.equal(receiver.accepted().length, 1);
  assert.equal(receiver.accept(event).duplicate, true);
  assert.equal(receiver.accepted().length, 1);
  assert.throws(() => receiver.accept({ ...event, job: jobB }), /Conflicting/);
  assert.equal(q.snapshot().pending.length, 0);
}
{
  const store = storage(), receiver = memoryReceiver();
  let fail = true;
  const transport = { accept(event) { if (fail) throw Error('Synthetic receiver outage'); return receiver.accept(event); } };
  const f = fixture([jobA], store, transport);
  f.click(); f.connect(); f.retry();
  assert.match(f.nodes['sync-status'].textContent, /Replay failed/);
  assert.equal(createQueue(store, receiver, () => 'unused').snapshot().pending.length, 1);
  fail = false;
  f.retry();
  assert.equal(receiver.accepted().length, 1);
  assert.match(f.nodes['sync-status'].textContent, /Preview replay complete/);
}
{
  const store = storage();
  store.raw.set(KEY, '{broken');
  const f = fixture([jobA], store);
  assert.equal(f.nodes.action.disabled, true);
  assert.match(f.nodes['sync-status'].textContent, /Preview error/);
  assert.equal(store.getItem(KEY), '{broken');
}
{
  const store = storage();
  store.setItem = () => { throw Error('Synthetic storage blocked'); };
  const f = fixture([jobA], store);
  f.click();
  assert.equal(f.nodes.running.hidden, true);
  assert.match(f.nodes['sync-status'].textContent, /Could not save/);
}
console.log('Synthetic field-clock pending/replay checks completed');
