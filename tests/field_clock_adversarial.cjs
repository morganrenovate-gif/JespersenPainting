// TIME-005: all people, jobs, timestamps and location flags are invented synthetic fixtures.
const assert = require('node:assert/strict');
const { createQueue, memoryReceiver, KEY } = require('../field_clock/pending.js');
const jobA = 'Synthetic Scaffold Bay';
const jobB = 'Synthetic Workshop Walls';
const person = 'Synthetic Painter One'; // fixture identity only, never persisted
const t = iso => new Date(iso);
function storage() {
  const raw = new Map();
  return { raw, getItem: key => raw.has(key) ? raw.get(key) : null,
    setItem: (key, value) => raw.set(key, value) };
}
function fixture(store = storage(), receiver = memoryReceiver()) {
  let seq = 0;
  return { store, receiver, person, queue: createQueue(store, receiver, () => `synthetic-event-${++seq}`) };
}
const morning = t('2026-01-01T23:45:00Z');
const afterMidnight = t('2026-01-02T01:15:00Z');
{
  const { queue, store } = fixture();
  const start = queue.capture('in', jobA, morning, 'unavailable');
  assert.throws(() => queue.capture('in', jobB, morning), /Already clocked in/);
  assert.equal(queue.snapshot().pending.length, 1);
  assert.deepEqual(queue.snapshot().active, start);
  assert.equal(start.location, 'unavailable');
  const end = queue.capture('out', jobA, afterMidnight, 'suspicious');
  assert.equal(end.location, 'suspicious');
  assert.equal(end.startId, start.id);
  assert.equal((Date.parse(end.at) - Date.parse(start.at)) / 60000, 90);
  assert.equal(queue.snapshot().active, null);
  assert.throws(() => queue.capture('out', jobA, afterMidnight), /No matching/);
  assert.equal(createQueue(store, memoryReceiver(), () => 'unused').snapshot().history.length, 2);
}
{
  const { queue } = fixture();
  const start = queue.capture('in', jobA, morning);
  assert.equal(queue.needsClockOutReview(t('2026-01-02T15:44:00Z')), false);
  assert.equal(queue.needsClockOutReview(t('2026-01-02T15:45:00Z')), true);
  const review = queue.requestReview('forgotten-out', start.id, 'Synthetic missed end; crew lead to review',
    t('2026-01-02T15:46:00Z'));
  assert.equal(review.startId, start.id);
  assert.equal(queue.needsClockOutReview(t('2026-01-02T16:00:00Z')), false);
  assert.throws(() => queue.requestReview('forgotten-out', start.id, 'again', afterMidnight), /already requested/);
  assert.deepEqual(queue.snapshot().active, start); // never silently invent an end
  assert.equal(queue.snapshot().history.length, 2);
  assert.throws(() => queue.capture('out', jobA, t('2026-01-01T22:00:00Z')), /precedes/);
}
{
  const { queue, store } = fixture();
  const start = queue.capture('in', jobA, morning);
  const [end, next] = queue.switchJob(jobB, afterMidnight, 'suspicious');
  assert.equal(end.startId, start.id);
  assert.equal(end.at, next.at);
  assert.equal(next.job, jobB);
  assert.equal(next.location, 'suspicious');
  assert.deepEqual(queue.snapshot().active, next);
  assert.deepEqual(queue.snapshot().pending.map(e => e.kind), ['in', 'out', 'in']);
  assert.throws(() => queue.switchJob(jobB, afterMidnight), /Already on/);
  assert.throws(() => queue.switchJob(jobA, morning), /Invalid switch time/);
  assert.throws(() => queue.capture('in', jobA, afterMidnight), /Already clocked in/);
  const request = queue.requestReview('correction', end.id, 'Synthetic end time needs review',
    t('2026-01-02T02:00:00Z'));
  assert.equal(request.startId, end.id);
  assert.deepEqual(queue.snapshot().history[1], end);
  assert.equal(queue.snapshot().pending.length, 4);
  assert.equal(createQueue(store, memoryReceiver(), () => 'unused').snapshot().history.length, 4);
  assert.throws(() => queue.requestReview('correction', 'missing', 'note', afterMidnight), /Unknown/);
}
{
  const { queue, store } = fixture();
  const start = queue.capture('in', jobA, morning);
  const originalWrite = store.setItem;
  store.setItem = () => { throw Error('Synthetic switch storage failure'); };
  assert.throws(() => queue.switchJob(jobB, afterMidnight), /storage failure/);
  store.setItem = originalWrite;
  assert.deepEqual(queue.snapshot().active, start);
  assert.deepEqual(queue.snapshot().pending, [start]);
  assert.deepEqual(createQueue(store, memoryReceiver(), () => 'unused').snapshot().history, [start]);
}
{
  const store = storage(), accepted = memoryReceiver();
  let down = true;
  const provider = { accept(event) {
    if (down) throw Error('Synthetic provider unavailable');
    return accepted.accept(event);
  } };
  const queue = fixture(store, provider).queue;
  const start = queue.capture('in', jobA, morning);
  assert.throws(() => queue.replay(), /provider unavailable/);
  assert.deepEqual(queue.snapshot().active, start);
  assert.equal(queue.snapshot().pending.length, 1);
  down = false;
  assert.equal(queue.replay(), 1);
  assert.equal(queue.replay(), 0);
  assert.equal(accepted.accepted().length, 1);
  assert.deepEqual(queue.snapshot().history, [start]);
  const correction = queue.requestReview('correction', start.id, 'Synthetic start time review', afterMidnight);
  assert.equal(correction.startId, start.id); // after replay, original still addressable
}
{
  const store = storage(), receiver = memoryReceiver();
  const queue = fixture(store, receiver).queue;
  const start = queue.capture('in', jobA, morning);
  const originalWrite = store.setItem;
  store.setItem = () => { throw Error('Synthetic acknowledgement storage outage'); };
  assert.throws(() => queue.replay(), /storage outage/);
  assert.equal(receiver.accepted().length, 1);
  store.setItem = originalWrite;
  assert.equal(queue.replay(), 1); // duplicate acknowledgement for the same ID
  assert.equal(receiver.accepted().length, 1);
  assert.equal(receiver.accept(start).duplicate, true);
  assert.deepEqual(queue.snapshot().history, [start]);
  const end = queue.capture('out', jobA, afterMidnight);
  const wrong = { accept: () => ({ id: 'synthetic-wrong', duplicate: false }) };
  const reload = createQueue(store, wrong, () => 'synthetic-unused');
  assert.throws(() => reload.replay(), /Invalid preview acknowledgement/);
  assert.deepEqual(reload.snapshot().pending, [end]);
  assert.equal(store.raw.has(KEY), true);
}
console.log('Synthetic TIME-005 adversarial checks completed');
