/* TIME-004 · synthetic dev preview; never sends time to a service. */
(function (root) {
  'use strict';
  var pending = typeof module !== 'undefined' && module.exports ? require('./pending.js') : root.FieldClockPreviewQueue;

  function formatElapsed(milliseconds) {
    var seconds = Math.max(0, Math.floor(milliseconds / 1000));
    var hours = Math.floor(seconds / 3600);
    var minutes = Math.floor(seconds % 3600 / 60);
    return [hours, minutes, seconds % 60].map(function (part) {
      return String(part).padStart(2, '0');
    }).join(':');
  }

  function mount(doc, clock, schedule, cancel, options) {
    options = options || {};
    var main = doc.getElementById('main');
    var count = Number(main.dataset.assignmentCount);
    var choices = doc.getElementById('choices');
    var action = doc.getElementById('action');
    var heading = doc.getElementById('shift-heading');
    var status = doc.getElementById('status');
    var running = doc.getElementById('running');
    var activeJob = doc.getElementById('active-job');
    var elapsed = doc.getElementById('elapsed');
    var started = doc.getElementById('started');
    var finished = doc.getElementById('finished');
    var sync = doc.getElementById('sync-status');
    var latest = doc.getElementById('latest-event');
    var connection = doc.getElementById('connection');
    var retry = doc.getElementById('retry');
    var selected = count === 1 ? doc.getElementById('selected-job').textContent : null;
    var start = null;
    var ticker = null;
    var queue;
    var error = '';
    var captureBlocked = false;
    var success = false;
    var available = false;
    try {
      queue = pending.createQueue(options.storage || root.localStorage,
        options.receiver || pending.memoryReceiver(),
        options.makeId || function () { return root.crypto.randomUUID(); });
    } catch (_) {
      error = 'Local preview storage unavailable. Clock actions disabled; existing local events were not erased.';
      captureBlocked = true;
    }
    function drawTimer() { elapsed.textContent = formatElapsed(clock().getTime() - start.getTime()); }
    function drawSync() {
      var events = queue ? queue.snapshot().pending : [];
      var n = events.length;
      sync.className = 'sync-status ' + (error ? 'sync-error' : n ? 'sync-pending' : 'sync-ok');
      sync.textContent = error ? 'Preview error · ' + error : n ?
        'Pending · ' + n + ' local preview event' + (n === 1 ? '' : 's') +
          '. ' + (available ? 'Use Retry preview replay.' : 'Preview connection unavailable; restore it to retry.') :
        success ? 'Preview replay complete · accepted in this tab only. Not a work-time record.' :
          'No pending preview events · no work-time record.';
      var last = n ? events[n - 1] : null;
      latest.textContent = last ? 'Latest pending: Clock ' + (last.kind === 'in' ? 'In' : 'Out') +
        ' · ' + last.job + ' · ' + new Date(last.at).toLocaleString([], {
          year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
        }) : '';
      latest.hidden = !last;
      retry.disabled = !queue || !available || n === 0;
      action.disabled = !queue || captureBlocked || (!start && !selected);
    }
    function showActive(event) {
      start = new Date(event.at);
      activeJob.textContent = event.job;
      started.dateTime = event.at;
      started.textContent = start.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
      finished.hidden = true;
      choices.hidden = true;
      heading.textContent = 'Clocked in';
      status.textContent = 'Clock running · ' + event.job + ' (local preview)';
      running.hidden = false;
      action.textContent = 'Clock Out';
      drawTimer();
      ticker = schedule(drawTimer, 1000);
    }
    if (queue && queue.snapshot().active) showActive(queue.snapshot().active);
    choices.addEventListener('change', function (event) {
      if (start || !event.target.matches('input[name="job"]')) return;
      selected = event.target.parentElement.querySelector('span').textContent;
      finished.hidden = true;
      drawSync();
    });
    action.addEventListener('click', function () {
      if (!queue || captureBlocked) return;
      if (!start && !selected) return;
      var end = clock();
      try {
        var event = queue.capture(start ? 'out' : 'in', start ? activeJob.textContent : selected, end);
        success = false;
        error = '';
        if (start) {
          cancel(ticker);
          ticker = null;
          start = null;
          running.hidden = true;
          heading.textContent = 'Clocked out';
          status.textContent = 'Clocked out · ' + event.job + ' (local preview)';
          finished.textContent = 'Clocked out at ' + end.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
          finished.hidden = false;
          action.textContent = 'Clock In';
          choices.hidden = false;
        } else showActive(event);
      } catch (_) {
        error = 'Could not save preview event. No clock change was recorded; check local storage before trying again.';
        captureBlocked = true;
      }
      drawSync();
    });
    connection.addEventListener('change', function () {
      available = connection.checked;
      // Connectivity is simulated: no navigator.onLine, fetch or remote transport.
      drawSync();
    });
    retry.addEventListener('click', function () {
      if (!queue || !available) return;
      try {
        var count = queue.replay();
        success = count > 0;
        error = '';
      } catch (_) {
        error = 'Replay failed; pending events stay local. Check preview storage and retry.';
      }
      drawSync();
    });
    drawSync();
    return { dispose: function () { if (ticker !== null) cancel(ticker); } };
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { mount: mount, formatElapsed: formatElapsed };
  } else {
    mount(document, function () { return new Date(); }, setInterval, clearInterval);
  }
})(this);
