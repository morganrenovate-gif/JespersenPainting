/* PRIVATE-DATA-006 v1. No XLSX binary reader or provider access in public source. */
'use strict';
const VERSION = 'financial-runner/v2';
const categories = { labor: ['hours', 'hourly_cost'], material: ['quantity', 'unit_cost'], revenue: ['entry_type', 'amount'] };
const names = ['labor', 'materials', 'revenue', 'profit', 'margin', 'payments', 'outstanding'];
const stages = ['inventoried', 'fingerprinted', 'extracted', 'reconciled', 'needs_review', 'failed', 'accepted'];
const clone = x => JSON.parse(JSON.stringify(x));
const canonical = value => Array.isArray(value) ? value.map(canonical) :
  value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])])) : value;
const same = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
function halt(code) { const error = new Error(code); error.code = code; throw error; }
const hash = x => typeof x === 'string' && /^[a-f0-9]{64}$/.test(x);
const text = x => typeof x === 'string' && x.length > 0;
function decimal(x) {
  if (typeof x !== 'string' || !/^-?(?:0|[1-9]\d*)(?:\.\d{1,4})?$/.test(x)) halt('invalid_decimal');
  const negative = x.startsWith('-'), [whole, fraction = ''] = (negative ? x.slice(1) : x).split('.');
  const value = BigInt(whole) * 10000n + BigInt(fraction.padEnd(4, '0'));
  return negative ? -value : value;
}
function rounded(n, unit) {
  if (unit === 0n) halt('invalid_divisor');
  const abs = n < 0n ? -n : n, divisor = unit < 0n ? -unit : unit;
  const sign = (n < 0n) !== (unit < 0n) ? -1n : 1n;
  return sign * ((abs + divisor / 2n) / divisor);
}
function money(x) { const n = decimal(x); if (n % 100n) halt('money_precision'); return n / 100n; }
function format(n, unit) {
  const abs = n < 0n ? -n : n;
  return (n < 0n ? '-' : '') + (abs / unit) + '.' + (abs % unit).toString().padStart(unit.toString().length - 1, '0');
}
function source(cell, kind, seen) {
  if (!cell || !text(cell.sheet) || !/^[A-Z]+[1-9]\d*$/.test(cell.address) ||
      typeof cell.raw !== 'string' || !(cell.formula === null || typeof cell.formula === 'string') ||
      !(cell.result === null || typeof cell.result === 'string')) halt('invalid_cell');
  const id = cell.sheet + '!' + cell.address;
  if (seen.has(id)) halt('duplicate_cell');
  seen.add(id);
  const value = cell.formula === null ? cell.raw : cell.result;
  if (value === null) halt('missing_formula_result');
  if (kind === 'money') money(value);
  if (kind === 'decimal') decimal(value);
  return { source: clone(cell), normalized: value, origin: cell.formula === null ? 'literal' : 'formula_result' };
}
function extract(snapshot, profile) {
  // Exact runtime-approved profile only. Synthetic fixtures are NOT live coverage.
  if (!profile || !Array.isArray(profile.labels) || !text(profile.version) || !hash(profile.signature) ||
      !same(Object.keys(profile.sections || {}).sort(), Object.keys(categories).sort()) ||
      !same(Object.keys(profile.totals || {}).sort(), names.slice().sort()) ||
      Object.entries(categories).some(([k, v]) => !same(profile.sections[k], v)) ||
      names.some(k => profile.totals[k] !== k)) halt('invalid_profile');
  if (!snapshot || snapshot.complete !== true || snapshot.signature !== profile.signature ||
      !same(Object.keys(snapshot.sections || {}).sort(), Object.keys(categories).sort()) ||
      !same(Object.keys(snapshot.totals || {}).sort(), names.slice().sort())) halt('unknown_shape');
  const used = new Set(), rows = {};
  // Labels/metadata are exact approved literals, never arbitrary dropped cells.
  if (!Array.isArray(snapshot.labels) || !same(snapshot.labels, profile.labels)) halt('unknown_shape');
  const labels = snapshot.labels.map(cell => {
    if (cell.formula !== null || cell.result !== null) halt('invalid_profile');
    return source(cell, 'text', used);
  });
  for (const [category, fields] of Object.entries(categories)) {
    const part = snapshot.sections[category];
    if (!part || part.complete !== true || !same(part.headers, fields) || !Array.isArray(part.rows)) halt('unknown_shape');
    rows[category] = part.rows.map(row => {
      if (!row || !same(Object.keys(row).sort(), fields.slice().sort())) halt('unknown_shape');
      const facts = {};
      for (const field of fields) facts[field] = source(row[field], field === 'entry_type' ? 'text' : 'decimal', used);
      if (category === 'revenue' && !['invoice', 'revenue', 'payment'].includes(facts.entry_type.normalized)) halt('unknown_economics');
      return facts;
    });
  }
  const totals = {};
  for (const name of names) totals[name] = snapshot.totals[name] === null ? null :
    source(snapshot.totals[name], name === 'margin' ? 'decimal' : 'money', used);
  // Complete nonempty-cell inventory is essential: no unrecognized rows can be silently dropped.
  if (!Array.isArray(snapshot.nonempty) || !same(snapshot.nonempty.slice().sort(), [...used].sort())) halt('unknown_shape');
  return { profileVersion: profile.version, labels, rows, totals };
}
function calculate(e) {
  const sum = (rows, a, b) => rows.length ? rows.reduce((n, row) =>
    n + rounded(decimal(row[a].normalized) * decimal(row[b].normalized), 1000000n), 0n) : null;
  const labor = sum(e.rows.labor, 'hours', 'hourly_cost');
  const materials = sum(e.rows.material, 'quantity', 'unit_cost');
  const entries = payment => {
    const rows = e.rows.revenue.filter(r => (r.entry_type.normalized === 'payment') === payment);
    return rows.length ? rows.reduce((n, r) => n + money(r.amount.normalized), 0n) : null;
  };
  const revenue = entries(false), payments = entries(true);
  const profit = labor === null || materials === null || revenue === null ? null : revenue - labor - materials;
  const margin = profit === null || revenue === 0n ? null : rounded(profit * 10000n, revenue);
  const outstanding = revenue === null || payments === null ? null : revenue - payments;
  const values = { labor, materials, revenue, profit, margin, payments, outstanding };
  const computed = {}, comparisons = {};
  for (const name of names) {
    const value = values[name];
    computed[name] = value === null ? null : format(value, name === 'margin' ? 10000n : 100n);
    const sourceTotal = e.totals[name];
    const normalized = sourceTotal === null ? null : name === 'margin' ?
      format(decimal(sourceTotal.normalized), 10000n) : format(money(sourceTotal.normalized), 100n);
    comparisons[name] = { source: normalized, computed: computed[name],
      state: normalized === null || computed[name] === null ? 'unknown' :
        normalized === computed[name] ? 'match' : 'conflict' };
  }
  return { computed, comparisons };
}
function scopeCheck(scope) {
  if (!scope || scope.client !== 'jespersen-painting' || scope.environment !== 'staging' ||
      scope.authorized !== true || scope.killSwitch !== false || !text(scope.root)) halt('scope_halt');
}
function canonicalFiles(files) {
  return files.map(f => ({ id: f.id, sourceId: f.sourceId, sha256: f.sha256,
    parent: f.parent, client: f.client, environment: f.environment }))
    .sort((a, b) => a.sourceId < b.sourceId ? -1 : a.sourceId > b.sourceId ? 1 : 0);
}
function inventoryCheck(files, scope) {
  if (!Array.isArray(files) || files.length < 3) halt('manifest_halt');
  const ids = new Set(), locators = new Set();
  for (const f of files) {
    if (!f || !text(f.id) || !text(f.sourceId) || !hash(f.sha256) ||
        f.parent !== scope.root || f.client !== scope.client || f.environment !== scope.environment ||
        ids.has(f.sourceId) || locators.has(f.id)) halt('manifest_halt');
    ids.add(f.sourceId); locators.add(f.id);
  }
}
function progress(state) {
  const counts = Object.fromEntries(stages.map(s => [s, 0]));
  for (const item of state.items) counts[item.state]++;
  return { version: VERSION, phase: state.phase, counts };
}
// store.get(key) -> {revision,value}|null; store.cas(key, revision|null, value) -> boolean.
// CAS must be durable/atomic and reject stale revision across concurrent invocations.
// accept(key, revision, next, outputKey, record, lease) atomically checks revision,
// lease owner and non-cancelled scope, then inserts immutable output and updates
// checkpoint together. Check expiry immediately before initiating the commit.
// Expiry permits takeover; only an intervening revision advance revokes an in-flight
// commit. No separate output write, and no server-side time condition is assumed.
function createRunner({ store, transport, qa, profiles, scope, key,
  clock = () => Date.now(), leaseMs = 60000, token = () => `${Date.now()}:${Math.random()}` }) {
  scopeCheck(scope);
  if (!text(key) || !store || typeof store.accept !== 'function' || !transport || !qa ||
      !Array.isArray(profiles) || typeof clock !== 'function' || typeof token !== 'function' ||
      !Number.isSafeInteger(leaseMs) || leaseMs < 1) halt('configuration_halt');
  async function tick() {
    scopeCheck(scope);
    const manifest = await transport.inventory(scope.root);
    inventoryCheck(manifest, scope);
    const files = canonicalFiles(manifest);
    let saved = await store.get(key);
    if (!saved) {
      const initial = { version: VERSION, client: scope.client, environment: scope.environment,
        root: scope.root, phase: 'pilot', items: files.map((ref, n) =>
          ({ ref: clone(ref), state: 'inventoried', pilot: n < 3, attempts: 0 })) };
      await store.cas(key, null, initial);
      saved = await store.get(key);
      // Sharded stores may stage a bounded bootstrap batch without publishing a
      // head yet. This is healthy initialization, not a failed analysis attempt.
      if (!saved) return progress({ ...initial, phase: 'initializing' });
    }
    if (!saved) halt('checkpoint_halt');
    const original = saved.value;
    if (original.version !== VERSION || original.client !== scope.client ||
        original.environment !== scope.environment || original.root !== scope.root ||
        !same(original.items.map(i => i.ref), files)) halt('source_changed_halt');
    if (original.phase === 'cancelled') halt('scope_halt');
    if (original.phase === 'completed') return progress(original);
    const now = clock();
    if (!Number.isSafeInteger(now)) halt('configuration_halt');
    // An active claim is not a retry. Only expired work may be reclaimed.
    if (original.lease && original.lease.expiresAt > now) return progress(original);
    const index = original.items.findIndex(i => (original.phase === 'pilot' ? i.pilot : !i.pilot) &&
      !['accepted', 'needs_review', 'failed'].includes(i.state));
    if (index < 0) {
      if (original.phase === 'pilot' && original.items.filter(i => i.pilot).every(i => i.state === 'accepted')) {
        const next = clone(original); next.phase = 'corpus';
        delete next.lease;
        if (await store.cas(key, saved.revision, next)) return progress(next);
      } else if (original.phase === 'corpus') {
        const next = clone(original); next.phase = 'completed'; delete next.lease;
        if (await store.cas(key, saved.revision, next)) return progress(next);
      }
      return progress(original);
    }
    const claimed = clone(original), item = claimed.items[index];
    if (item.attempts >= 3) {
      item.state = 'failed'; item.reason = 'retry_exhausted'; delete claimed.lease;
      if (await store.cas(key, saved.revision, claimed)) return progress(claimed);
      return progress(original);
    }
    // Durable claim before side effects. Crash replay is bounded by attempts.
    item.attempts++;
    const owner = token();
    if (!text(owner)) halt('configuration_halt');
    claimed.lease = { owner, expiresAt: now + leaseMs };
    if (!await store.cas(key, saved.revision, claimed)) return progress(original);
    const claim = await store.get(key);
    if (!claim || !same(claim.value, claimed)) halt('checkpoint_halt');
    const next = clone(claimed), target = next.items[index], ref = target.ref;
    try {
      scopeCheck(scope);
      if (target.state === 'inventoried') {
        const fingerprint = await transport.fingerprint(clone(ref));
        if (!fingerprint || fingerprint.sha256 !== ref.sha256 || !hash(fingerprint.signature)) halt('stale_source');
        target.signature = fingerprint.signature; target.state = 'fingerprinted';
      } else if (target.state === 'fingerprinted') {
        const snapshot = await transport.extractCells(clone(ref));
        if (!snapshot || snapshot.sha256 !== ref.sha256 || snapshot.signature !== target.signature) halt('stale_source');
        const profile = profiles.find(p => p.signature === target.signature);
        if (!profile) halt('unknown_shape');
        target.evidence = extract(snapshot, profile); target.state = 'extracted';
      } else if (target.state === 'extracted') {
        target.financial = calculate(target.evidence);
        if (names.some(n => target.financial.comparisons[n].state !== 'match')) halt('unreconciled');
        target.state = 'reconciled';
      } else if (target.state === 'reconciled') {
        const payload = { evidence: target.evidence, financial: target.financial };
        const receipt = await qa.verify({ ref: clone(ref), signature: target.signature,
          payload: clone(payload), version: VERSION });
        if (!receipt || receipt.pass !== true || receipt.sha256 !== ref.sha256 ||
            receipt.signature !== target.signature || receipt.version !== VERSION ||
            receipt.evidence !== JSON.stringify(payload)) halt('qa_rejected');
        scopeCheck(scope);
        const current = await store.get(key);
        if (!current || current.revision !== claim.revision || !same(current.value, claimed) ||
            clock() >= claimed.lease.expiresAt) return progress(current ? current.value : claimed);
        const record = { ref: clone(ref), signature: target.signature, ...clone(payload),
          receipt: clone(receipt), version: VERSION };
        const committed = clone(next), accepted = committed.items[index];
        delete accepted.evidence; delete accepted.financial; accepted.state = 'accepted'; accepted.attempts = 0;
        delete committed.lease;
        // Runtime MUST commit immutable output and checkpoint in one revision-fenced transaction.
        if (!await store.accept(key, claim.revision, committed, `${VERSION}:${ref.sourceId}:${ref.sha256}`, record,
          clone(claimed.lease))) {
          const latest = await store.get(key); return progress(latest.value);
        }
        return progress(committed);
      } else halt('checkpoint_halt');
      target.attempts = 0;
    } catch (error) {
      if (['scope_halt', 'stale_source', 'claim_lost'].includes(error.code)) throw error;
      const review = ['unknown_shape', 'unknown_economics', 'unreconciled', 'qa_rejected',
        'invalid_decimal', 'money_precision', 'invalid_cell', 'missing_formula_result',
        'duplicate_cell', 'invalid_profile'].includes(error.code);
      if (review) { target.state = 'needs_review'; target.reason = error.code; }
      else if (target.attempts >= 3) { target.state = 'failed'; target.reason = 'retry_exhausted'; }
    }
    scopeCheck(scope);
    if (clock() >= claimed.lease.expiresAt) return progress((await store.get(key)).value);
    delete next.lease;
    if (!await store.cas(key, claim.revision, next)) return progress((await store.get(key)).value);
    return progress(next);
  }
  async function cancel() {
    const saved = await store.get(key);
    if (!saved || saved.value.version !== VERSION || saved.value.root !== scope.root ||
        saved.value.client !== scope.client || saved.value.environment !== scope.environment) halt('scope_halt');
    const next = clone(saved.value); next.phase = 'cancelled';
    return store.cas(key, saved.revision, next);
  }
  return { tick, cancel };
}
module.exports = { VERSION, createRunner, extract, calculate, progress };
