/* TIME-003 · ephemeral field interaction; no time event is stored or sent. */
(function (root) {
  'use strict';

  function formatElapsed(milliseconds) {
    var seconds = Math.max(0, Math.floor(milliseconds / 1000));
    var hours = Math.floor(seconds / 3600);
    var minutes = Math.floor(seconds % 3600 / 60);
    return [hours, minutes, seconds % 60].map(function (part) {
      return String(part).padStart(2, '0');
    }).join(':');
  }

  function mount(doc, clock, schedule, cancel) {
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
    var selected = count === 1 ? doc.getElementById('selected-job').textContent : null;
    var start = null;
    var ticker = null;

    function drawTimer() {
      elapsed.textContent = formatElapsed(clock().getTime() - start.getTime());
    }

    choices.addEventListener('change', function (event) {
      if (start || !event.target.matches('input[name="job"]')) return;
      selected = event.target.parentElement.querySelector('span').textContent;
      action.disabled = false;
      finished.hidden = true;
    });

    action.addEventListener('click', function () {
      if (start) {
        var end = clock();
        cancel(ticker);
        ticker = null;
        start = null;
        running.hidden = true;
        heading.textContent = 'Clocked out';
        status.textContent = 'Clocked out · ' + activeJob.textContent;
        finished.textContent = 'Clocked out at ' + end.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
        finished.hidden = false;
        action.textContent = 'Clock In';
        choices.hidden = false;
        return;
      }
      if (!selected) return;
      start = clock();
      activeJob.textContent = selected;
      started.dateTime = start.toISOString();
      started.textContent = start.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
      finished.hidden = true;
      choices.hidden = true;
      heading.textContent = 'Clocked in';
      status.textContent = 'Clock running · ' + selected;
      running.hidden = false;
      action.textContent = 'Clock Out';
      drawTimer();
      ticker = schedule(drawTimer, 1000);
    });
    return { dispose: function () { if (ticker !== null) cancel(ticker); } };
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { mount: mount, formatElapsed: formatElapsed };
  } else {
    mount(document, function () { return new Date(); }, setInterval, clearInterval);
  }
})(this);
