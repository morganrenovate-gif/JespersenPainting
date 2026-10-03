// Synthetic-only PRIVATE-DATA-006 tests; no real workbook structure or IDs.
'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { createRunner, extract, calculate } = require('../private_runtime/financial_runner.cjs');
const H = 'a'.repeat(64), S = 'b'.repeat(64);
const scope = () => ({ client: 'jespersen-painting', environment: 'staging', authorized: true, killSwitch: false, root: 'synthetic_root' });
const profile = { version: 'synthetic-only/v1', signature: S,
  sections: { labor: ['hours', 'hourly_cost'], material: ['quantity', 'unit_cost'], revenue: ['entry_type', 'amount'] },
  totals: Object.fromEntries(['labor', 'materials', 'revenue', 'profit', 'margin', 'payments', 'outstanding'].map(x => [x, x])) };
function snapshot() {
  let n = 1; const nonempty = [];
  const make = (value, formula = null) => {
    const c = { sheet: 'Synthetic Ledger', address: `A${n++}`, raw: value, formula, result: formula ? value : null };
    nonempty.push(c.sheet + '!' + c.address); return c;
  };
  const sections = {
    labor: { complete: true, headers: profile.sections.labor, rows: [{ hours: make('2.0000'), hourly_cost: make('10.00') }] },
    material: { complete: true, headers: profile.sections.material, rows: [{ quantity: make('1.2500'), unit_cost: make('8.00') }] },
    revenue: { complete: true, headers: profile.sections.revenue, rows: [
      { entry_type: make('invoice'), amount: make('50.00') },
      { entry_type: make('payment'), amount: make('20.00') }
    ] }
  };
  const totals = {};
  for (const [name, value] of Object.entries({ labor: '20.00', materials: '10.00', revenue: '50.00', profit: '20.00', margin: '0.4000', payments: '20.00', outstanding: '30.00' })) totals[name] = make(value, '=synthetic_formula');
  return { complete: true, signature: S, sha256: H, sections, totals, nonempty };
}
function refresh(s) {
  s.nonempty = Object.values(s.sections).flatMap(p => p.rows.flatMap(r => Object.values(r).map(c => c.sheet + '!' + c.address)))
    .concat(Object.values(s.totals).filter(Boolean).map(c => c.sheet + '!' + c.address));
}
function setup(count = 4, options = {}) {
  const files = Array.from({ length: count }, (_, i) => ({ id: `synthetic_file_${i}`, sourceId: `synthetic_source_${i}`,
    sha256: H, parent: 'synthetic_root', client: scope().client, environment: 'staging' }));
  let saved = null, reads = 0, qaCalls = 0;
  const writes = new Map();
  const store = {
    async get() { return saved && structuredClone(saved); },
    async cas(key, revision, value) {
      if ((saved && saved.revision) !== revision && !(saved === null && revision === null)) return false;
      saved = { revision: saved ? saved.revision + 1 : 1, value: structuredClone(value) }; return true;
    }
  };
  const transport = {
    async inventory() { return structuredClone(files); },
    async fingerprint() { return { signature: S, sha256: H }; },
    async extractCells(ref) { reads++; return options.bad === ref.id ? { ...snapshot(), complete: false } : snapshot(); }
  };
  const qa = { async verify({ ref, signature, payload, version }) {
    qaCalls++;
    return { pass: !options.qaFail, sha256: ref.sha256, signature, version, evidence: JSON.stringify(payload) };
  } };
  const output = { async putIfAbsent(key, value) { if (!writes.has(key)) writes.set(key, structuredClone(value)); } };
  const deps = { store, transport, qa, output, profiles: [profile], scope: scope(), key: 'synthetic_queue' };
  return { deps, files, writes, get reads() { return reads; }, get qaCalls() { return qaCalls; } };
}
async function ticks(runner, n = 40) { let p; for (let i = 0; i < n; i++) p = await runner.tick(); return p; }
test('pilot automatically opens corpus only after financial and source-bound QA; restart and duplicate replay', async () => {
  const x = setup(), runner = createRunner(x.deps);
  const first = await runner.tick();
  assert.equal(first.counts.fingerprinted, 1);
  assert.equal(first.counts.inventoried, 3);
  assert.equal(first.phase, 'pilot');
  const p = await ticks(createRunner(x.deps));
  assert.equal(p.phase, 'corpus'); assert.equal(p.counts.accepted, 4);
  assert.equal(x.writes.size, 4); assert.equal(x.qaCalls, 4);
  await ticks(runner); assert.equal(x.writes.size, 4); assert.equal(x.reads, 4);
});
test('QA rejection blocks pilot and malformed item is isolated', async () => {
  const x = setup(4, { qaFail: true });
  const p = await ticks(createRunner(x.deps));
  assert.equal(p.phase, 'pilot'); assert.equal(p.counts.needs_review, 3);
  assert.equal(p.counts.inventoried, 1); assert.equal(x.writes.size, 0);
  const y = setup(4, { bad: 'synthetic_file_1' });
  const q = await ticks(createRunner(y.deps));
  assert.equal(q.counts.needs_review, 1); assert.equal(q.counts.accepted, 2);
  assert.equal(q.phase, 'pilot');
});
test('facts and formulas stay separate; absent payment/revenue and rounding', () => {
  const s = snapshot(), before = structuredClone(s);
  const e = extract(s, profile), result = calculate(e);
  assert.deepEqual(s, before);
  assert.equal(e.totals.labor.source.formula, '=synthetic_formula');
  assert.equal(result.comparisons.profit.state, 'match');
  assert.equal(result.computed.outstanding, '30.00');
  const absent = snapshot(); absent.sections.revenue.rows.pop(); refresh(absent);
  const r = calculate(extract(absent, profile));
  assert.equal(r.computed.payments, null); assert.equal(r.computed.outstanding, null);
  const empty = snapshot(); empty.sections.revenue.rows = []; refresh(empty);
  assert.equal(calculate(extract(empty, profile)).computed.revenue, null);
  const zero = snapshot(); zero.sections.revenue.rows[0].amount.raw = '0.00';
  assert.equal(calculate(extract(zero, profile)).computed.margin, null);
  const fractional = snapshot(); fractional.sections.material.rows[0].quantity.raw = '1.2501';
  assert.equal(calculate(extract(fractional, profile)).computed.materials, '10.00');
});
test('unsupported shape/labels never become accepted', () => {
  for (const mutate of [s => { s.nonempty.push('Synthetic Ledger!Z99'); },
    s => { s.sections.revenue.rows[0].entry_type.raw = 'guess'; },
    s => { s.sections.labor.headers = ['wrong', 'hourly_cost']; }]) {
    const s = snapshot(); mutate(s); assert.throws(() => extract(s, profile));
  }
});
test('hash changes, cancellation, tenant and staging failures halt', async () => {
  const x = setup(), runner = createRunner(x.deps);
  await runner.tick(); x.files[0].sha256 = 'c'.repeat(64);
  await assert.rejects(runner.tick(), /source_changed_halt/);
  const y = setup(), r = createRunner(y.deps);
  await r.tick(); assert.equal(await r.cancel(), true);
  await assert.rejects(r.tick(), /scope_halt/);
  const z = setup(); z.deps.scope.environment = 'production';
  assert.throws(() => createRunner(z.deps), /scope_halt/);
  const w = setup(); w.deps.scope.killSwitch = true;
  assert.throws(() => createRunner(w.deps), /scope_halt/);
});
