'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { createHedyStore } = require('../private_runtime/hedy_financial_store.cjs');
const clone = v => JSON.parse(JSON.stringify(v));
const digest = async s => createHash('sha256').update(s).digest('hex');
function setup(n = 3) {
  let now = 100, hook = null; const rows = new Map();
  const scope = { client:'jespersen-painting', environment:'staging', root:'synthetic-root', authorized:true, killSwitch:false };
  const data = {
    async getWithMeta(c,k) { return rows.has(k) ? clone(rows.get(k)) : null; },
    async put(c,k,v,opts) {
      if (hook) await hook(k,v,opts);
      const old = rows.get(k);
      if ((opts.ifNotExists && old) || (opts.ifVersion !== undefined && (old?.version ?? 0) !== opts.ifVersion)) {
        const e = new Error('conflict'); e.name = 'ConflictError'; throw e;
      }
      rows.set(k,{value:clone(v),version:(old?.version ?? 0)+1}); return {version:rows.get(k).version};
    },
    async batchGet(c,keys) { assert.ok(keys.length<=25);return {items:keys.map(key=>rows.has(key)?{key,found:true,...clone(rows.get(key))}:{key,found:false})}; },
    async batchPut(c,items) { assert.ok(items.length<=25);for(const item of items)await data.put(c,item.key,item.value,{});return {items:items.map(x=>({key:x.key,version:rows.get(x.key).version}))}; }
  };
  const store = createHedyStore({data,digest,scope,clock:()=>now});
  const initial = {version:'v2',client:scope.client,environment:scope.environment,root:scope.root,phase:'pilot',items:Array.from({length:n},(_,i)=>({ref:{id:'file'+i,sourceId:'source'+i,sha256:String(i%10).repeat(64),parent:scope.root,client:scope.client,environment:scope.environment},state:'inventoried',attempts:0}))};
  return {store,initial,rows,scope,setNow:v=>now=v,setHook:v=>hook=v};
}
async function claimed(s) {
  await s.store.cas('task',null,s.initial); const saved=await s.store.get('task');
  saved.value.items[0].state='reconciled'; saved.value.lease={owner:'owner',expiresAt:200};
  await s.store.cas('task',saved.revision,saved.value); return s.store.get('task');
}
function acceptance(saved) {
  const next=clone(saved.value),ref=next.items[0].ref;
  next.items[0].state='accepted'; delete next.lease;
  return {next,key:'v2:'+ref.sourceId+':'+ref.sha256,record:{ref,version:'v2',evidence:{synthetic:true}},lease:clone(saved.value.lease)};
}
const accept = (s,saved,a) => s.store.accept('task',saved.revision,a.next,a.key,a.record,a.lease);
test('atomic visible output and replay reject stale revision',async()=>{
  const s=setup(), saved=await claimed(s),a=acceptance(saved);
  assert.equal(await accept(s,saved,a),true); assert.deepEqual(await s.store.getOutput('task',a.key),a.record);
  assert.equal((await s.store.get('task')).value.items[0].state,'accepted');
  assert.equal(await accept(s,saved,a),false);
});
test('unreachable staged acceptance is invisible and replayable',async()=>{
  const s=setup(),saved=await claimed(s),a=acceptance(saved);
  s.setHook(async k=>{if(k.endsWith(':head'))throw new Error('crash');});
  await assert.rejects(accept(s,saved,a),/crash/);
  assert.equal(await s.store.getOutput('task',a.key),null);
  s.setHook(null); assert.equal(await accept(s,saved,a),true);
});
test('cancel while candidate stages fences acceptance',async()=>{
  const s=setup(),saved=await claimed(s),a=acceptance(saved); let fired=false;
  s.setHook(async k=>{if(k.includes(':blob:')&&!fired){fired=true;s.setHook(null);
    const cancel=clone(saved.value);cancel.phase='cancelled';delete cancel.lease;
    assert.equal(await s.store.cas('task',saved.revision,cancel),true);}});
  assert.equal(await accept(s,saved,a),false);assert.equal(await s.store.getOutput('task',a.key),null);
});
test('expired during staging cannot initiate final CAS',async()=>{
  const s=setup(),saved=await claimed(s),a=acceptance(saved);
  s.setHook(async k=>{if(k.includes(':blob:'))s.setNow(201);});
  assert.equal(await accept(s,saved,a),false);assert.equal(await s.store.getOutput('task',a.key),null);
});
test('initiated unexpired CAS may complete later without takeover',async()=>{
  const s=setup(),saved=await claimed(s),a=acceptance(saved);
  s.setHook(async k=>{if(k.endsWith(':head'))s.setNow(201);});
  assert.equal(await accept(s,saved,a),true);assert.deepEqual(await s.store.getOutput('task',a.key),a.record);
});
test('takeover during final CAS fences stale owner',async()=>{
  const s=setup(),saved=await claimed(s),a=acceptance(saved);let fired=false;
  s.setHook(async k=>{if(k.endsWith(':head')&&!fired){fired=true;s.setHook(null);s.setNow(201);
    const takeover=clone(saved.value);takeover.lease={owner:'new',expiresAt:300};
    assert.equal(await s.store.cas('task',saved.revision,takeover),true);}});
  assert.equal(await accept(s,saved,a),false);assert.equal(await s.store.getOutput('task',a.key),null);
});
test('large corpus shards below per-row cap and shares unchanged blobs',async()=>{
  const s=setup(352);for(const i of s.initial.items)i.evidence={synthetic:'x'.repeat(2000)};
  assert.ok(JSON.stringify(s.initial).length>380000);
  assert.equal(await s.store.cas('task',null,s.initial),false);assert.equal(await s.store.get('task'),null);
  assert.equal(s.rows.size,25);
  let complete=false;for(let wake=1;wake<15;wake++){const before=s.rows.size;
    complete=await s.store.cas('task',null,s.initial);assert.ok(s.rows.size-before<=26);}
  assert.equal(complete,true);assert.deepEqual((await s.store.get('task')).value,s.initial);
  for(const row of s.rows.values())assert.ok(Buffer.byteLength(JSON.stringify(row.value))<370000);
  const before=s.rows.size,saved=await s.store.get('task');saved.value.items[3].attempts++;
  assert.equal(await s.store.cas('task',saved.revision,saved.value),true);assert.equal(s.rows.size,before+1);
});
test('tenant roots and oversized single blobs fail closed',async()=>{
  const s=setup();const other=clone(s.initial);other.items[0].ref.parent='other';
  await assert.rejects(s.store.cas('task',null,other),/store_scope_halt/);
  s.initial.items[0].evidence='x'.repeat(380000);await assert.rejects(s.store.cas('task',null,s.initial),/store_size_limit/);
});
test('cancellation remains possible after authority revoked',async()=>{
  for(const field of ['killSwitch','authorized']) {
    const s=setup(),saved=await claimed(s),a=acceptance(saved);
    s.scope[field]=field==='killSwitch';
    const latest=await s.store.get('task');const cancel=clone(latest.value);cancel.phase='cancelled';delete cancel.lease;
    assert.equal(await s.store.cas('task',latest.revision,cancel),true);
    await assert.rejects(accept(s,saved,a),/scope_halt/);
    assert.equal(await s.store.getOutput('task',a.key),null);
  }
});
test('runner cancellation integrates with revoked store scope',async()=>{
  const {createRunner}=require('../private_runtime/financial_runner.cjs');
  for(const field of ['killSwitch','authorized']) {
    const s=setup();
    const runner=createRunner({store:s.store,scope:s.scope,key:'task',profiles:[],qa:{},
      clock:()=>100,transport:{inventory:async()=>s.initial.items.map(i=>clone(i.ref)),
        fingerprint:async r=>({sha256:r.sha256,signature:'a'.repeat(64)})}});
    await runner.tick();s.scope[field]=field==='killSwitch';
    assert.equal(await runner.cancel(),true);
    assert.equal((await s.store.get('task')).value.phase,'cancelled');
  }
});
test('assembled read mutation cannot poison cached immutable snapshots',async()=>{
  const s=setup();await s.store.cas('task',null,s.initial);
  const first=await s.store.get('task');first.value.items[0].state='accepted';first.value.items[0].ref.parent='other';
  assert.deepEqual((await s.store.get('task')).value,s.initial);
});
test('backend object property order does not change snapshot integrity',async()=>{
  const s=setup();await s.store.cas('task',null,s.initial);
  const reverse=v=>Array.isArray(v)?v.map(reverse):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).reverse().map(k=>[k,reverse(v[k])])):v;
  for(const row of s.rows.values())row.value=reverse(row.value);
  // A fresh instance forces reads from reordered backend values rather than cache.
  const data={getWithMeta:async(c,k)=>s.rows.has(k)?clone(s.rows.get(k)):null,
    put:async()=>{throw new Error('unexpected write');},batchGet:async(c,keys)=>({items:keys.map(key=>({key,found:true,...clone(s.rows.get(key))}))}),batchPut:async()=>{throw new Error('unexpected write');}};
  const fresh=createHedyStore({data,digest,scope:s.scope});
  assert.deepEqual((await fresh.get('task')).value,s.initial);
});
