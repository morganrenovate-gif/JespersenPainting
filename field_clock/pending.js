/* TIME-004 · development-preview local queue only. No network or production adapter. */
(function (root) {
  'use strict';
  var KEY = 'jespersen-field-clock-synthetic-preview-v1';
  var LIMIT = 100;

  function copy(value) { return JSON.parse(JSON.stringify(value)); }
  function validEvent(e) {
    return e && typeof e.id === 'string' && e.id.length > 0 &&
      (e.kind === 'in' || e.kind === 'out') && typeof e.job === 'string' && e.job.length > 0 &&
      typeof e.at === 'string' && !isNaN(Date.parse(e.at)) &&
      (e.kind === 'in' ? e.startId === null : typeof e.startId === 'string' && e.startId.length > 0);
  }
  function valid(state) {
    return state && state.version === 1 && Array.isArray(state.pending) &&
      state.pending.length <= LIMIT && state.pending.every(validEvent) &&
      new Set(state.pending.map(function (e) { return e.id; })).size === state.pending.length &&
      (state.active === null || (validEvent(state.active) && state.active.kind === 'in'));
  }
  function createQueue(storage, receiver, makeId) {
    // A failed or malformed read never silently replaces the old queue.
    var raw = storage.getItem(KEY);
    var state = raw === null ? { version: 1, pending: [], active: null } : JSON.parse(raw);
    if (!valid(state)) throw new Error('Preview queue cannot be read');
    function save(next) {
      storage.setItem(KEY, JSON.stringify(next)); // commit before changing in-memory state
      state = next;
    }
    return {
      snapshot: function () { return copy(state); },
      capture: function (kind, job, at) {
        if (state.pending.length >= LIMIT) throw new Error('Preview queue full');
        if ((kind !== 'in' && kind !== 'out') || typeof job !== 'string' || !job ||
            !(at instanceof Date) || isNaN(at.getTime())) throw new Error('Invalid preview event');
        if (kind === 'in' && state.active !== null) throw new Error('Already clocked in');
        if (kind === 'out' && (state.active === null || state.active.job !== job))
          throw new Error('No matching active clock');
        var id = makeId();
        if (typeof id !== 'string' || !id || state.pending.some(function (e) { return e.id === id; }) ||
            (state.active && state.active.id === id)) throw new Error('Preview event identity unavailable');
        var event = { id: id, kind: kind, job: job, at: at.toISOString(),
          startId: kind === 'out' ? state.active.id : null };
        save({ version: 1, pending: state.pending.concat([event]),
          active: kind === 'in' ? event : null });
        return copy(event);
      },
      // Receiver contract: accept(event) must dedupe by stable id; success means acknowledged.
      // On any failure, including a storage failure after accept, retain the same id for retry.
      replay: function () {
        var accepted = 0;
        while (state.pending.length) {
          receiver.accept(copy(state.pending[0]));
          save({ version: 1, pending: state.pending.slice(1), active: state.active });
          accepted++;
        }
        return accepted;
      }
    };
  }
  function memoryReceiver() {
    var events = new Map();
    return {
      accept: function (event) {
        if (!validEvent(event)) throw new Error('Invalid preview event');
        if (events.has(event.id) && JSON.stringify(events.get(event.id)) !== JSON.stringify(event))
          throw new Error('Conflicting preview event');
        var duplicate = events.has(event.id);
        if (!duplicate) events.set(event.id, copy(event));
        return { id: event.id, duplicate: duplicate };
      },
      accepted: function () { return Array.from(events.values()).map(copy); }
    };
  }
  var api = { createQueue: createQueue, memoryReceiver: memoryReceiver, KEY: KEY };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.FieldClockPreviewQueue = api;
})(this);
