// TIME-003 field clock presentation/controller. No storage, provider calls or offline queue.
// Callbacks must acknowledge successful capture before the visible state changes.
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[char]);

export function elapsed(startedAt, now) {
  const seconds = Math.max(0, Math.floor((now - startedAt) / 1000));
  const hours = Math.floor(seconds / 3600);
  return `${String(hours).padStart(2, '0')}:${String(Math.floor(seconds % 3600 / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

export function renderClock(state, now = new Date()) {
  const { assignments, selected, active, startedAt, pending, message } = state;
  const running = active !== null;
  const status = running ? 'Clocked in' : 'Clocked out';
  const header = `<header class="clock-header"><div class="brand">JESPERSEN <span> / FIELD TIME</span></div><div class="header-rule" aria-hidden="true"></div><p class="eyebrow">FIELD / TODAY</p><h1>Job clock</h1></header>`;
  const stateLine = `<div class="state-line ${running ? 'is-running' : ''}" role="status" aria-live="polite"><span class="state-mark" aria-hidden="true"></span><span>${status}</span></div>`;
  let body;
  if (running) {
    body = `<section class="work-face" aria-label="Current shift"><p class="eyebrow">ON THE JOB</p><h2>${escapeHtml(active.label)}</h2><div class="time-block"><span class="eyebrow">TIME ON JOB</span><output class="elapsed" aria-label="Elapsed time">${elapsed(startedAt, now)}</output><p>Started ${escapeHtml(startedAt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }))}</p></div></section><button class="action action-out" type="button" data-action="out" ${pending ? 'disabled' : ''}>${pending === 'out' ? 'Clocking out…' : 'Clock Out'}</button>`;
  } else if (assignments.length === 0) {
    body = `<section class="work-face"><p class="eyebrow">NO JOB AVAILABLE</p><h2>No current assignment</h2><p>Ask your crew lead which job to use.</p></section>`;
  } else {
    const choices = assignments.length > 1
      ? `<fieldset class="job-choices"><legend>Choose your job</legend>${assignments.map((job, index) => `<button type="button" class="job-choice ${selected === index ? 'is-selected' : ''}" data-action="select" data-index="${index}" aria-pressed="${selected === index}" ${pending ? 'disabled' : ''}><span class="choice-number">${String(index + 1).padStart(2, '0')}</span><span>${escapeHtml(job.label)}</span><span class="choice-check" aria-hidden="true">${selected === index ? '✓' : ''}</span></button>`).join('')}</fieldset>`
      : `<div class="single-job"><p class="eyebrow">YOUR ASSIGNMENT</p><h2>${escapeHtml(assignments[0].label)}</h2></div>`;
    body = `<section class="work-face" aria-label="Current assignments">${choices}</section><button class="action action-in" type="button" data-action="in" ${selected === null || pending ? 'disabled' : ''}>${pending === 'in' ? 'Clocking in…' : 'Clock In'}</button>`;
  }
  return `${header}<main class="clock-main">${stateLine}${body}${message ? `<p class="feedback" role="alert">${escapeHtml(message)}</p>` : ''}<p class="surface-note">Field time / ${running ? 'Shift in progress' : 'Ready for work'}</p></main>`;
}

export function mountClock(root, { assignments, onClockIn, onClockOut, now = () => new Date(), setInterval: schedule = setInterval, clearInterval: cancel = clearInterval }) {
  if (!root || !Array.isArray(assignments) || typeof onClockIn !== 'function' || typeof onClockOut !== 'function' || typeof now !== 'function') throw new TypeError('Clock needs a root, assignments and capture callbacks');
  // No identity matching: the caller supplies already-authorized current assignments.
  const jobs = assignments.map((job) => {
    if (!job || typeof job.id !== 'string' || !job.id || typeof job.label !== 'string' || !job.label.trim()) throw new TypeError('Invalid assignment');
    return Object.freeze({ id: job.id, label: job.label });
  });
  if (new Set(jobs.map((job) => job.id)).size !== jobs.length) throw new TypeError('Duplicate assignment');
  const state = { assignments: jobs, selected: jobs.length === 1 ? 0 : null, active: null, startedAt: null, pending: null, message: '' };
  let disposed = false;
  const paint = (focus) => {
    if (disposed) return;
    root.innerHTML = renderClock(state, now());
    if (focus && typeof root.querySelector === 'function') root.querySelector(focus)?.focus();
  };
  // Update the counter only: rebuilding the DOM each second would discard keyboard focus.
  const tick = schedule(() => {
    if (disposed || state.active === null) return;
    const counter = root.querySelector?.('.elapsed');
    if (counter) counter.textContent = elapsed(state.startedAt, now());
  }, 1000);
  async function handleClick(event) {
    const button = event.target.closest('button[data-action]');
    if (disposed || !button || !root.contains(button) || state.pending || button.disabled) return;
    const action = button.dataset.action;
    if (action === 'select' && state.active === null) {
      const index = Number(button.dataset.index);
      if (!Number.isInteger(index) || index < 0 || index >= jobs.length) return;
      state.selected = index;
      state.message = '';
      paint(`[data-action="select"][data-index="${index}"]`);
    } else if (action === 'in' && state.active === null && state.selected !== null) {
      state.pending = 'in';
      state.message = '';
      paint();
      try {
        const started = await onClockIn(jobs[state.selected]);
        if (disposed) return;
        if (!(started instanceof Date) || !Number.isFinite(started.getTime())) throw new TypeError('Missing start time');
        state.active = jobs[state.selected];
        state.startedAt = started;
      } catch {
        if (!disposed) state.message = 'Could not clock in. Please try again.';
      } finally {
        state.pending = null;
        paint(state.active ? '[data-action="out"]' : '[data-action="in"]');
      }
    } else if (action === 'out' && state.active !== null) {
      state.pending = 'out';
      state.message = '';
      paint();
      try {
        await onClockOut(state.active, state.startedAt);
        if (disposed) return;
        state.active = null;
        state.startedAt = null;
        // In-memory preview returns to the same assignment list; no history is implied.
      } catch {
        if (!disposed) state.message = 'Could not clock out. Please try again.';
      } finally {
        state.pending = null;
        paint(state.active ? '[data-action="out"]' : '[data-action="in"]');
      }
    }
  }
  root.addEventListener('click', handleClick);
  paint();
  return () => { disposed = true; cancel(tick); root.removeEventListener('click', handleClick); };
}
