// Synthetic-only PRIVATE-DATA-006 tests. No real workbook, identifier or provider.
'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const {scheduled, cancel, extract, VERSION} = require('../private_runtime/financial_runner');
const crypto = require('node:crypto');
const config = {client:'jespersen-painting', environment:'staging', rootId:'synthetic_root', enabled:true};
const hash = n => crypto.createHash('sha256').update(`invented workbook ${n}`).digest('hex');
const refs = n => Array.from({length:n}, (_, i) => ({sourceId:`synthetic_source_${i}`, fileId:`synthetic_file_${i}`, parentId:config.rootId, sha256:hash(i)}));
function workbook(ref, opts = {}) {
  const cells = [], add = (a, value, formula) => cells.push({address:a, value, ...(formula ? {formula} : {})});
  add('A1','Hours'); add('B1','Hourly Cost'); add('A2','1.25'); add('B2','10.00');
  const material = [{address:'A1', value:'Quantity'}, {address:'B1', value:'Unit Cost'},
    {address:'A2', value:'1'}, {address:'B2', value:'2.25'}];
  const totals = [
    ['Labor Total','12.50'], ['Material Total','2.25'], ['Revenue','20.00'],
    ['Payment','5.00'], ['Gross Profit','5.25'], ['Gross Margin','26.25'],
    ['Outstanding Balance','15.00']
  ];
  const summary = totals.filter(([label]) => !opts.noPayment || label !== 'Payment').map(([label,value], i) =>
    [{address:`A${i+1}`,value:label},{address:`B${i+1}`,value:label === 'Revenue' && opts.zeroRevenue ? '0.00' : value,
      ...(label === 'Gross Profit' ? {formula:'=SUM(A1:A2)'} : {})}]).flat();
  if (opts.unknownLabel) summary[0].value = 'Mystery';
  return {sourceId:ref.sourceId, fileId:ref.fileId, parentId:ref.parentId, sha256:ref.sha256,
    fingerprint:'synthetic_shape', complete:true,
    coverage:{labor:true, material:true, revenue:!opts.noRevenue, payments:!opts.noPayment},
    sheets:[{name:'SyntheticLabor', cells}, {name:'SyntheticMaterial', cells:material}, {name:'SyntheticSummary',cells:summary}]};
}
class Store {
  constructor() {this.value = null; this.revision = 0; this.commits = 0;}
  async load() {return this.value ? {revision:this.revision,value:structuredClone(this.value)} : null;}
  async cas(revision, value) {
    if (revision !== (this.value ? this.revision : null)) return false;
    this.value = structuredClone(value); this.revision++; this.commits++; return true;
  }
}
function harness(n=5, options={}) {
  const manifest=refs(n), store=new Store(), calls=[];
  const transport={async readXlsx(ref) {calls.push(ref.sourceId); if (options.bad === ref.sourceId) throw Error('private payload MUST NOT ESCAPE');
    const snapshot=workbook(ref, options); if (options.stale === ref.sourceId) snapshot.sha256=hash(999);
    return snapshot;}};
  const qa={async verify({ref}) {return {version:VERSION, sha256:ref.sha256, pass:!options.reject};}};
  const run = (batch=10, overrides={}) => scheduled({config, manifest, store, transport, qa, now:100, batch, ...overrides});
  return {run,store,manifest,calls,transport,qa};
}
test('automatic three-item pilot to corpus; replay and restart do not duplicate outputs', async () => {
  const h=harness();
  await h.run(2);
  assert.equal(h.store.value.phase,'PILOT');
  assert.equal(h.store.value.items[3].status,'PENDING');
  // Reuse persisted state through a new handler invocation.
  const progress=await h.run();
  assert.equal(h.store.value.phase,'CORPUS');
  assert.deepEqual(progress,{inventoried:5,fingerprinted:5,extracted:5,reconciled:5,needsReview:0,failed:0,accepted:5});
  assert.equal(h.store.value.items.filter(i=>i.output).length,5);
  const commits=h.store.commits;
  await h.run(); await h.run();
  assert.equal(h.store.commits,commits);
  assert.equal(h.calls.length,5);
  assert.equal(h.store.value.items[0].output.formulaResults[0].formula,'=SUM(A1:A2)');
});
test('QA failure blocks advancement, unknowns stay reviewable and missing coverage unknown', async () => {
  const h=harness(4,{reject:true}); await h.run();
  assert.equal(h.store.value.phase,'BLOCKED');
  assert.equal(h.store.value.items[3].status,'PENDING');
  assert.equal(h.calls.length,1);
  const r=refs(3)[0];
  for (const opts of [{unknownLabel:true}, {noPayment:true}, {noRevenue:true}, {zeroRevenue:true}]) {
    const w=workbook(r,opts);
    if (opts.unknownLabel) assert.throws(()=>extract(w),/label_unknown/);
    else {
      const output=extract(w);
      if (opts.noPayment) {assert.equal(output.derived.payments.state,'unknown'); assert.equal(output.derived.outstanding.state,'unknown');}
      if (opts.noRevenue) {assert.equal(output.derived.revenue.state,'unknown'); assert.equal(output.derived.profit.state,'unknown');}
      if (opts.zeroRevenue) assert.equal(output.derived.margin.state,'unknown');
      assert.equal(output.reconciliation,false);
    }
  }
});
test('decimal arithmetic, immutable source facts and formula separation', () => {
  const w=workbook(refs(3)[0]); const original=structuredClone(w);
  const out=extract(w);
  assert.equal(out.derived.labor.value,'12.50');
  assert.equal(out.derived.profit.value,'5.25');
  assert.equal(out.derived.margin.value,'26.25');
  assert.equal(out.derived.outstanding.value,'15.00');
  assert.equal(out.reconciliation,true);
  assert.deepEqual(w,original);
  assert.equal(out.sourceFacts.some(f=>f.formula),false);
  assert.ok(out.derived.labor.inputs[0].cell);
});
test('changed manifest and stale read hash fail closed; tenant/environment halt', async () => {
  const h=harness(4); await h.run(1);
  const reads=h.calls.length;
  const changed=h.manifest.map(x=>({...x})); changed[0].sha256=hash(999);
  await assert.rejects(h.run(1,{manifest:changed}),/source_changed/);
  assert.equal(h.calls.length,reads);
  await assert.rejects(h.run(1,{config:{...config,environment:'production'}}),/scope_invalid/);
  await assert.rejects(h.run(1,{config:{...config,client:'other'}}),/scope_invalid/);
  const stale=harness(4,{stale:refs(4)[0].sourceId}); await stale.run();
  assert.equal(stale.store.value.phase,'BLOCKED');
  assert.equal(stale.store.value.items[0].reason,'source_changed');
});
test('bounded retries, malformed isolation after pilot, cancellation and kill switch', async () => {
  const h=harness(5,{bad:refs(5)[3].sourceId});
  await h.run();
  assert.equal(h.store.value.items[4].status,'ACCEPTED');
  assert.equal(h.store.value.items[3].attempts,3);
  assert.equal(h.store.value.items[3].reason,'extraction_error');
  assert.equal(h.store.value.items[3].status,'FAILED');
  assert.ok(!JSON.stringify(h.store.value).includes('private payload'));
  const before=h.calls.length;
  await cancel({config,store:h.store}); await h.run();
  assert.equal(h.calls.length,before);
  await assert.rejects(h.run(1,{config:{...config,enabled:false}}),/scope_invalid/);
});
test('expired claims resume; CAS losers cannot double-write', async () => {
  const h=harness(3);
  await h.run(1);
  const i=h.store.value.items[1]; i.status='CLAIMED'; i.attempts=1; i.claim={token:'expired',until:0};
  const progress=await h.run();
  assert.equal(progress.accepted,3);
  assert.equal(h.store.value.items[1].attempts,2);
  assert.equal(h.store.value.items.filter(i=>i.output).length,3);
});
