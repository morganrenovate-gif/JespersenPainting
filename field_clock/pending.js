/* TIME-005 · synthetic dev-preview time register. No remote or production adapter. */
(function (root) {
  'use strict';
  var KEY = 'jespersen-field-clock-synthetic-preview-v1';
  var LIMIT = 100;
  function copy(value) { return JSON.parse(JSON.stringify(value)); }
  function validEvent(e) {
    return e && typeof e.id === 'string' && e.id.length > 0 &&
      (e.kind === 'in' || e.kind === 'out' || e.kind === 'review') &&
      typeof e.job === 'string' && e.job.length > 0 &&
      typeof e.at === 'string' && !isNaN(Date.parse(e.at)) &&
      (e.kind === 'in' ? e.startId === null : typeof e.startId === 'string' && e.startId.length > 0) &&
      (e.location === undefined || ['ok', 'unavailable', 'suspicious'].includes(e.location)) &&
      (e.kind !== 'review' || (['forgotten-out', 'correction'].includes(e.reason) &&
        typeof e.note === 'string' && e.note.length > 0 && e.note.length <= 500));
  }
  function valid(state) {
    if (!state || state.version !== 1 || !Array.isArray(state.pending) ||
        state.pending.length > LIMIT || !state.pending.every(validEvent) ||
        !(state.active === null || (validEvent(state.active) && state.active.kind === 'in'))) return false;
    var history = state.history || state.pending.concat(state.active && !state.pending.some(function (e) {
      return e.id === state.active.id;
    }) ? [state.active] : []);
    if (!Array.isArray(history) || !history.every(validEvent)) return false;
    var ids = history.map(function (e) { return e.id; });
    if (new Set(ids).size !== ids.length) return false;
    return state.pending.every(function (e) {
      return history.some(function (h) { return h.id === e.id && JSON.stringify(h) === JSON.stringify(e); });
    }) && (state.active === null || history.some(function (e) {
      return e.id === state.active.id && JSON.stringify(e) === JSON.stringify(state.active);
    }));
  }
  function createQueue(storage, receiver, makeId) {
    var raw = storage.getItem(KEY);
    var state = raw === null ? { version: 1, pending: [], active: null, history: [] } : JSON.parse(raw);
    if (!valid(state)) throw new Error('Preview queue cannot be read');
    // Legacy preview records have no history; preserve their active and pending records.
    if (!state.history) state.history = state.pending.concat(state.active && !state.pending.some(function (e) {
      return e.id === state.active.id;
    }) ? [state.active] : []);
    function save(next) {
      storage.setItem(KEY, JSON.stringify(next));
      state = next;
    }
    function newEvent(kind, job, at, startId, extra, used) {
      if (typeof job !== 'string' || !job || !(at instanceof Date) || isNaN(at.getTime()))
        throw new Error('Invalid preview event');
      var id = makeId();
      if (typeof id !== 'string' || !id || state.history.some(function (e) { return e.id === id; }) ||
          used.some(function (e) { return e.id === id; })) throw new Error('Preview event identity unavailable');
      return Object.assign({ id: id, kind: kind, job: job, at: at.toISOString(), startId: startId }, extra);
    }
    function append(events, active) {
      if (state.pending.length + events.length > LIMIT) throw new Error('Preview queue full');
      save({ version: 1, pending: state.pending.concat(events), active: active,
        history: state.history.concat(events) });
    }
    function capture(kind, job, at, location) {
      if (kind !== 'in' && kind !== 'out') throw new Error('Invalid preview event');
      if (location !== undefined && !['ok', 'unavailable', 'suspicious'].includes(location))
        throw new Error('Invalid preview location');
      if (kind === 'in' && state.active !== null) throw new Error('Already clocked in');
      if (kind === 'out' && (state.active === null || state.active.job !== job))
        throw new Error('No matching active clock');
      if (kind === 'out' && at instanceof Date && at.getTime() < Date.parse(state.active.at))
        throw new Error('Clock out precedes clock in');
      var event = newEvent(kind, job, at, kind === 'out' ? state.active.id : null,
        location === undefined ? {} : { location: location }, []);
      append([event], kind === 'in' ? event : null);
      return copy(event);
    }
    function switchJob(job, at, location) {
      if (!state.active) throw new Error('No active clock to switch');
      if (job === state.active.job) throw new Error('Already on this job');
      if (location !== undefined && !['ok', 'unavailable', 'suspicious'].includes(location))
        throw new Error('Invalid preview location');
      if (!(at instanceof Date) || isNaN(at.getTime()) || at.getTime() < Date.parse(state.active.at))
        throw new Error('Invalid switch time');
      if (state.pending.length + 2 > LIMIT) throw new Error('Preview queue full');
      var old = state.active;
      var out = newEvent('out', old.job, at, old.id, location === undefined ? {} : { location: location }, []);
      var into = newEvent('in', job, at, null, location === undefined ? {} : { location: location }, [out]);
      append([out, into], into); // one storage write: no overlapping or half-switch interval
      return copy([out, into]);
    }
    function requestReview(reason, referenceId, note, at) {
      if (!['forgotten-out', 'correction'].includes(reason) || typeof note !== 'string' ||
          !note.trim() || note.length > 500) throw new Error('Invalid review request');
      var original = state.history.find(function (e) { return e.id === referenceId && e.kind !== 'review'; });
      if (!original || (reason === 'forgotten-out' && (!state.active || state.active.id !== referenceId)))
        throw new Error('Unknown review reference');
      if (reason === 'forgotten-out' && state.history.some(function (e) {
        return e.kind === 'review' && e.reason === reason && e.startId === referenceId;
      })) throw new Error('Review already requested');
      var request = newEvent('review', original.job, at, referenceId, { reason: reason, note: note.trim() }, []);
      append([request], state.active);
      return copy(request);
    }
    return {
      snapshot: function () { return copy(state); },
      capture: capture, switchJob: switchJob, requestReview: requestReview,
      needsClockOutReview: function (at) {
        return !!state.active && at instanceof Date && !isNaN(at.getTime()) &&
          at.getTime() - Date.parse(state.active.at) >= 16 * 3600000 &&
          !state.history.some(function (e) {
            return e.kind === 'review' && e.reason === 'forgotten-out' && e.startId === state.active.id;
          });
      },
      // Receiver must dedupe stable IDs. Only a matching acknowledgement permits removal.
      replay: function () {
        var accepted = 0;
        while (state.pending.length) {
          var event = copy(state.pending[0]);
          var ack = receiver.accept(event);
          if (!ack || ack.id !== event.id || (ack.duplicate !== true && ack.duplicate !== false))
            throw new Error('Invalid preview acknowledgement');
          save({ version: 1, pending: state.pending.slice(1), active: state.active, history: state.history });
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
