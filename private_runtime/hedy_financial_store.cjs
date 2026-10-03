'use strict';

// Immutable snapshots become authoritative only through the versioned head.
// This is a CAS publication protocol, not a multi-item database transaction.
function createHedyStore({ data, digest, scope, collection = 'source_records',
  prefix = 'financial-v2:', clock = () => Date.now(), maxBytes = 370000 }) {
  const copy = value => JSON.parse(JSON.stringify(value));
  const fail = code => { const error = new Error(code); error.code = code; throw error; };
  const canonical = value => Array.isArray(value) ? value.map(canonical) :
    value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])) : value;
  const same = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
  const size = value => { const s = JSON.stringify(canonical(value)); let bytes = 0;
    for (const c of s) { const p = c.codePointAt(0); bytes += p < 128 ? 1 : p < 2048 ? 2 : p < 65536 ? 3 : 4; }
    if (bytes > maxBytes) fail('store_size_limit'); return s; };
  function check(state, active = false) {
    if (!scope || scope.client !== 'jespersen-painting' || scope.environment !== 'staging' ||
      !scope.root || (active && (scope.authorized !== true || scope.killSwitch !== false))) fail('scope_halt');
    if (state && (state.client !== scope.client || state.environment !== scope.environment ||
      state.root !== scope.root || !Array.isArray(state.items) || !state.version || state.items.length > 1000)) fail('store_scope_halt');
    if (state) { const ids = new Set(); for (const item of state.items) {
      const r = item?.ref;
      if (!r || r.client !== scope.client || r.environment !== scope.environment || r.parent !== scope.root ||
        !r.sourceId || !r.id || !/^[a-f0-9]{64}$/.test(r.sha256) || ids.has(r.sourceId)) fail('store_scope_halt');
      ids.add(r.sourceId);
    } }
  }
  if (!data || typeof data.getWithMeta !== 'function' || typeof data.put !== 'function' ||
    typeof data.batchGet !== 'function' || typeof data.batchPut !== 'function' ||
    typeof digest !== 'function' || typeof clock !== 'function' || !Number.isInteger(maxBytes) ||
    maxBytes < 1024 || maxBytes > 370000 || !/^[A-Za-z0-9:_-]{1,80}$/.test(prefix)) fail('store_configuration');
  check();
  const cache = new Map();
  async function base(key) {
    check();
    if (typeof key !== 'string' || !key.length || key.length > 300) fail('store_key');
    const hash = await digest(key); if (!/^[a-f0-9]{64}$/.test(hash)) fail('store_digest');
    return prefix + hash;
  }
  async function head(key) {
    const b = await base(key), row = await data.getWithMeta(collection, b + ':head');
    if (!row) return { b, row: null };
    const h = row.value;
    if (!h || h.format !== 1 || h.client !== scope.client || h.environment !== scope.environment ||
      h.root !== scope.root || !Array.isArray(h.refs) || h.refs.length > 1000) fail('store_head_corrupt');
    return { b, row };
  }
  async function blob(b, ref) {
    if (!/^[a-f0-9]{64}$/.test(ref)) fail('store_head_corrupt');
    if (cache.has(b + ref)) return cache.get(b + ref);
    const row = await data.getWithMeta(collection, b + ':blob:' + ref);
    if (!row || await digest(size(row.value)) !== ref) fail('store_blob_corrupt');
    cache.set(b + ref, row.value);
    return row.value;
  }
  async function preload(b, refs) {
    if (typeof data.batchGet !== 'function') return;
    const missing = [...new Set(refs)].filter(ref => !cache.has(b + ref));
    for (let i = 0; i < missing.length; i += 25) {
      const group = missing.slice(i, i + 25);
      if (group.some(ref => !/^[a-f0-9]{64}$/.test(ref))) fail('store_head_corrupt');
      const response = await data.batchGet(collection, group.map(ref => b + ':blob:' + ref));
      for (const ref of group) {
        const row = response.items?.find(v => v.key === b + ':blob:' + ref);
        if (!row || row.found === false || await digest(size(row.value)) !== ref) fail('store_blob_corrupt');
        cache.set(b + ref, row.value);
      }
    }
  }
  async function assemble(b, row) {
    if (!row) return null;
    const h = row.value, items = [];
    await preload(b, h.refs);
    for (const ref of h.refs) { const v = await blob(b, ref); items.push(copy(v.item)); }
    const state = { ...copy(h.state), items }; check(state);
    return { revision: row.version, value: state };
  }
  async function get(key) { const { b, row } = await head(key); return assemble(b, row); }
  async function stage(b, value) {
    const json = size(value), hash = await digest(json);
    if (!/^[a-f0-9]{64}$/.test(hash)) fail('store_digest');
    try { await data.put(collection, b + ':blob:' + hash, value, { ifNotExists: true }); }
    catch (error) {
      if (error.name !== 'ConflictError') throw error;
      const existing = await blob(b, hash);
      if (!same(existing, value)) fail('store_blob_conflict');
    }
    return hash;
  }
  async function stageMany(b, values, writeBudget) {
    if (typeof data.batchGet !== 'function' || typeof data.batchPut !== 'function') {
      const refs = []; for (const v of values) refs.push(await stage(b, v)); return {refs, ready:true};
    }
    const refs = [], pending = new Map();
    for (const value of values) {
      const hash = await digest(size(value));
      if (!/^[a-f0-9]{64}$/.test(hash)) fail('store_digest');
      refs.push(hash);
      if (cache.has(b + hash)) { if (!same(cache.get(b + hash), value)) fail('store_blob_conflict'); }
      else pending.set(hash, value);
    }
    const hashes = [...pending.keys()]; let remaining = writeBudget, ready = true;
    for (let i = 0; i < hashes.length; i += 25) {
      const group = hashes.slice(i, i + 25);
      const response = await data.batchGet(collection, group.map(ref => b + ':blob:' + ref));
      const writes = [];
      for (const ref of group) {
        const row = response.items?.find(v => v.key === b + ':blob:' + ref);
        if (!row) fail('store_batch_response');
        const value = pending.get(ref);
        if (row.found !== false && !same(row.value, value)) fail('store_blob_conflict');
        if (row.found === false) {
          if (remaining > 0) { writes.push({ key: b + ':blob:' + ref, value }); remaining--; }
          else ready = false;
        } else cache.set(b + ref, value);
      }
      // Unconditional writes are safe only for verified content-addressed immutable
      // candidates. Concurrent writers for a digest stage exactly the same bytes.
      // This batch does not publish output or checkpoints.
      if (writes.length) await data.batchPut(collection, writes);
      for (const item of writes) cache.set(b + item.key.slice((b + ':blob:').length), item.value);
    }
    return {refs, ready};
  }
  async function publish(key, revision, next, acceptance) {
    check(next, !!acceptance || next.phase !== 'cancelled');
    const { b, row } = await head(key);
    if ((row ? row.version : null) !== revision) return false;
    const current = await assemble(b, row);
    if (!current && next.phase === 'cancelled') return false;
    if (current && next.phase === 'cancelled' && !same(current.value.items, next.items)) fail('store_cancellation_invalid');
    if (current && (current.value.version !== next.version || current.value.phase === 'cancelled')) return false;
    if (current && !same(current.value.items.map(i => i.ref), next.items.map(i => i.ref))) fail('store_manifest_changed');
    let acceptedIndex = -1;
    if (acceptance) {
      if (!current || !same(current.value.lease, acceptance.lease) ||
        clock() >= acceptance.lease.expiresAt || !acceptance.lease.owner || next.lease) return false;
      acceptedIndex = next.items.findIndex(i => i.ref.sourceId === acceptance.record.ref.sourceId &&
        i.ref.sha256 === acceptance.record.ref.sha256);
      if (acceptedIndex < 0 || next.items[acceptedIndex].state !== 'accepted' ||
        current.value.items[acceptedIndex].state !== 'reconciled' ||
        acceptance.record.version !== next.version || !same(acceptance.record.ref, next.items[acceptedIndex].ref)) fail('store_acceptance_invalid');
      const expected = next.version + ':' + acceptance.record.ref.sourceId + ':' + acceptance.record.ref.sha256;
      if (acceptance.outputKey !== expected) fail('store_output_key');
    }
    const values = [];
    for (let i = 0; i < next.items.length; i++) {
      let previous = null;
      if (row) previous = await blob(b, row.value.refs[i]);
      const output = i === acceptedIndex ? { key: acceptance.outputKey, record: copy(acceptance.record) } : previous?.output;
      if (previous?.output && (!same(previous.item, next.items[i]) ||
        (i === acceptedIndex && !same(previous.output, output)))) fail('store_immutable_output');
      if (!output && next.items[i].state === 'accepted') fail('store_missing_output');
      const v = { item: copy(next.items[i]), ...(output ? { output } : {}) };
      values.push(v);
    }
    const staged = await stageMany(b, values, row ? Infinity : 25);
    if (!staged.ready) return false;
    const refs = staged.refs;
    // Preserve top-level property order because the runner's checkpoint equality
    // compares JSON serializations. Replacing this slot preserves its position.
    const state = copy(next); state.items = null;
    const candidate = { format: 1, client: scope.client, environment: scope.environment, root: scope.root, state, refs };
    size(candidate);
    // Last check before the single publication CAS. The backend has no clock predicate.
    check(next, !!acceptance || next.phase !== 'cancelled');
    if (acceptance && clock() >= acceptance.lease.expiresAt) return false;
    try { await data.put(collection, b + ':head', candidate, { ifVersion: revision ?? 0 }); return true; }
    catch (error) { if (error.name === 'ConflictError') return false; throw error; }
  }
  async function cas(key, revision, next) { return publish(key, revision, next, null); }
  async function accept(key, revision, next, outputKey, record, lease) {
    return publish(key, revision, next, { outputKey, record, lease });
  }
  async function getOutput(key, outputKey) {
    const { b, row } = await head(key); if (!row) return null;
    await preload(b, row.value.refs);
    for (const ref of row.value.refs) { const v = await blob(b, ref);
      if (v.output?.key === outputKey) return copy(v.output.record); }
    return null;
  }
  return { get, cas, accept, getOutput };
}
module.exports = { createHedyStore };
