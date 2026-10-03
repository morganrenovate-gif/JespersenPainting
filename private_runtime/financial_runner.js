// PRIVATE-DATA-006. Staging-only; transport, durable CAS, and independent QA are injected.
'use strict';
const VERSION = 'financial-runner/v1';
const MAX = 3;
const validId = x => typeof x === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(x);
function fail(code) { throw Error(code); }
function guard(config) {
  if (!config || config.client !== 'jespersen-painting' || config.environment !== 'staging' ||
      config.enabled !== true || !validId(config.rootId)) fail('scope_invalid');
}
function manifestGuard(refs, config) {
  if (!Array.isArray(refs) || refs.length < 3) fail('pilot_incomplete');
  const sources = new Set(), files = new Set();
  for (const r of refs) {
    if (!r || !validId(r.sourceId) || !validId(r.fileId) || r.parentId !== config.rootId ||
        !/^[a-f0-9]{64}$/.test(r.sha256) || sources.has(r.sourceId) || files.has(r.fileId)) fail('manifest_invalid');
    sources.add(r.sourceId); files.add(r.fileId);
  }
}
function same(state, refs, config) {
  if (!state || state.version !== VERSION || state.client !== config.client || state.environment !== config.environment ||
      state.rootId !== config.rootId || state.items.length !== refs.length || state.items.some((i, n) =>
        ['sourceId','fileId','parentId','sha256'].some(k => i.ref[k] !== refs[n][k]))) fail('source_changed');
}
function counters(s) {
  const counts = {inventoried:s.items.length, fingerprinted:0, extracted:0, reconciled:0, needsReview:0, failed:0, accepted:0};
  for (const item of s.items) {
    for (const stage of ['fingerprinted','extracted','reconciled']) if (item.stages.includes(stage)) counts[stage]++;
    if (item.status === 'NEEDS_REVIEW') counts.needsReview++;
    if (item.status === 'FAILED') counts.failed++;
    if (item.status === 'ACCEPTED') counts.accepted++;
  }
  return counts;
}
function decimal(value, scale=2) {
  if (typeof value !== 'string' || !/^-?(?:0|[1-9]\d*)(?:\.\d{1,6})?$/.test(value)) fail('numeric_unsupported');
  const minus = value.startsWith('-');
  const [whole, fraction=''] = (minus ? value.slice(1) : value).split('.');
  const raw = BigInt(whole)*1000000n + BigInt(fraction.padEnd(6,'0'));
  const divisor = 10n**BigInt(6-scale);
  return (minus ? -1n : 1n)*((raw+divisor/2n)/divisor);
}
function divide(n,d) {
  if (d === 0n) fail('division_by_zero');
  const sign = (n < 0n) !== (d < 0n) ? -1n : 1n;
  return sign * (((n < 0n ? -n : n)+(d < 0n ? -d : d)/2n)/(d < 0n ? -d : d));
}
function money(n) {
  const abs = n < 0n ? -n : n;
  return `${n < 0n ? '-' : ''}${abs/100n}.${String(abs%100n).padStart(2,'0')}`;
}
const label = x => typeof x === 'string' ? x.trim().toLowerCase().replace(/\s+/g,' ') : '';
const HEADERS = {labor:['hours','hourly cost'],material:['quantity','unit cost']};
const TOTAL = {'labor total':'labor','material total':'material','revenue total':'revenue',
  'payment total':'payments','gross profit':'profit','gross margin':'margin','outstanding balance':'outstanding',
  'revenue':'revenue','payment':'payments'};
function fact(sheet, cell, facts, formulas) {
  if (typeof cell.value !== 'string') fail('numeric_unsupported');
  const result = {sheet,cell:cell.address,value:cell.value}; facts.push(result);
  if (cell.formula !== undefined) {
    if (typeof cell.formula !== 'string' || !cell.formula.startsWith('=')) fail('shape_unknown');
    formulas.push({sheet,cell:cell.address,formula:cell.formula,cachedResult:cell.value});
  }
  return result;
}
function extract(snapshot) {
  if (!snapshot || snapshot.complete !== true || !validId(snapshot.fingerprint) || !Array.isArray(snapshot.sheets) ||
      !snapshot.sheets.length || !snapshot.coverage) fail('shape_unknown');
  const sourceFacts=[], formulaResults=[], rows={labor:[],material:[],revenue:[],payments:[]}, totals={};
  for (const sheet of snapshot.sheets) {
    if (!sheet || !validId(sheet.name) || !Array.isArray(sheet.cells) || !sheet.cells.length) fail('shape_unknown');
    const lines=new Map(), addresses=new Set();
    for (const cell of sheet.cells) {
      if (!cell || !/^[A-Z]{1,3}[1-9]\d*$/.test(cell.address) || addresses.has(cell.address)) fail('shape_unknown');
      addresses.add(cell.address);
      const [,letters,rowText]=/^([A-Z]+)(\d+)$/.exec(cell.address);
      const col=[...letters].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0), row=Number(rowText);
      if (!lines.has(row)) lines.set(row,[]);
      lines.get(row).push({cell,col});
    }
    let kind=null, columns=null;
    for (const [, cells] of [...lines].sort((a,b)=>a[0]-b[0])) {
      const labels=cells.map(v=>label(v.cell.value));
      const match=Object.entries(HEADERS).find(([,heads])=>heads.every(h=>labels.includes(h)));
      if (match) {
        if (kind || cells.length !== 2) fail('shape_unknown');
        kind=match[0]; columns=match[1].map(h=>cells.find(v=>label(v.cell.value)===h).col);
      } else if (kind) {
        const selected=columns.map(col=>cells.find(v=>v.col===col));
        if (!selected.every(Boolean) || cells.length !== columns.length) fail('shape_unknown');
        rows[kind].push(selected.map(v=>fact(sheet.name,v.cell,sourceFacts,formulaResults)));
      } else {
        if (cells.length !== 2 || cells[1].col !== cells[0].col+1) {
          cells.sort((a,b)=>a.col-b.col);
          if (cells.length !== 2 || cells[1].col !== cells[0].col+1) fail('shape_unknown');
        }
        const key=TOTAL[label(cells[0].cell.value)];
        if (!key) fail('label_unknown');
        const value=fact(sheet.name,cells[1].cell,sourceFacts,formulaResults);
        if (key === 'revenue' || key === 'payments') rows[key].push([value]);
        else { if (totals[key]) fail('label_unknown'); totals[key]=value; }
      }
    }
  }
  const derived={}, discrepancies=[];
  for (const category of ['labor','material','revenue','payments']) {
    const inputs=rows[category].flat();
    if (snapshot.coverage[category] !== true || !rows[category].length) {
      derived[category]={state:'unknown',value:null,inputs}; continue;
    }
    let cents=0n;
    for (const parts of rows[category]) {
      const values=parts.map(p=>decimal(p.value,parts.length===2 ? 6 : 2));
      cents+=parts.length===2 ? divide(values[0]*values[1],10000000000n) : values[0];
    }
    derived[category]={state:'computed',value:money(cents),inputs};
  }
  function combine(key,keys,operation) {
    const inputs=keys.flatMap(k=>derived[k].inputs);
    derived[key]=keys.every(k=>derived[k].state==='computed')
      ? {state:'computed',value:money(operation(...keys.map(k=>decimal(derived[k].value)))),inputs}
      : {state:'unknown',value:null,inputs};
  }
  combine('cost',['labor','material'],(a,b)=>a+b);
  combine('profit',['revenue','cost'],(a,b)=>a-b);
  combine('outstanding',['revenue','payments'],(a,b)=>a-b);
  derived.margin=derived.profit.state==='computed' && derived.revenue.state==='computed' && decimal(derived.revenue.value)!==0n
    ? {state:'computed',value:money(divide(decimal(derived.profit.value)*10000n,decimal(derived.revenue.value))),inputs:derived.profit.inputs}
    : {state:'unknown',value:null,inputs:derived.profit.inputs};
  for (const [key, source] of Object.entries(totals)) {
    const result=derived[key];
    const delta=result.state==='computed' ? decimal(result.value)-decimal(source.value) : null;
    discrepancies.push({field:key,source,recomputed:result.value,
      state:delta===null ? 'unresolved' : delta===0n ? 'agrees' : 'conflict',delta:delta===null ? null : money(delta)});
  }
  return {fingerprint:snapshot.fingerprint,sourceFacts,formulaResults,derived,discrepancies,
    reconciliation:['labor','material','revenue','payments','profit','margin','outstanding'].every(k=>derived[k].state==='computed') &&
      ['labor','material','profit','margin','outstanding'].every(k=>discrepancies.some(d=>d.field===k && d.state==='agrees')) &&
      discrepancies.every(d=>d.state==='agrees')};
}
function evolve(s,index,change) {
  const items=s.items.slice(); items[index]={...items[index],...change}; return {...s,items};
}
// Durable store must implement linearizable load and atomic CAS; whole queue and outputs share one record.
async function cas(store, update) {
  for (let tries=0;tries<20;tries++) {
    const current=await store.load(), next=update(current?.value || null);
    if (!next) return current.value;
    if (await store.cas(current ? current.revision : null,next)) return next;
  }
  fail('cas_contention');
}
async function scheduled({config,manifest,store,transport,qa,now,batch=10}) {
  guard(config); manifestGuard(manifest,config);
  if (!Number.isSafeInteger(now) || now<0 || !Number.isInteger(batch) || batch<1 || batch>10 ||
      !store || !transport || !qa) fail('configuration_invalid');
  let s=await cas(store,current=>{
    if (current) {same(current,manifest,config); return null;}
    return {version:VERSION,client:config.client,environment:config.environment,rootId:config.rootId,
      phase:'PILOT',cancelled:false,items:manifest.map(ref=>({ref:{...ref},status:'PENDING',attempts:0,
        stages:[],claim:null,output:null,reason:null}))};
  });
  for (let step=0;step<batch;step++) {
    let index=-1, token=null, exhausted=false;
    s=await cas(store,current=>{
      same(current,manifest,config);
      if (current.cancelled || current.phase==='BLOCKED') return null;
      index=current.items.findIndex((item,i)=>i<(current.phase==='PILOT'?3:current.items.length) &&
        (item.status==='PENDING' || (item.status==='CLAIMED' && item.claim.until<now)));
      if (index<0) return null;
      const item=current.items[index];
      if (item.attempts>=MAX) {exhausted=true; return evolve(current,index,{status:'FAILED',claim:null,reason:'retry_exhausted'});}
      token=`${now}_${index}_${item.attempts+1}`;
      return evolve(current,index,{status:'CLAIMED',attempts:item.attempts+1,claim:{token,until:now+300}});
    });
    if (index<0 || s.cancelled || s.phase==='BLOCKED') break;
    if (!exhausted) {
      const ref=manifest[index]; let change;
      try {
        // Injected read-only transport attests original binary SHA-256 and containment before XLSX decoding.
        const snapshot=await transport.readXlsx(ref,config.rootId);
        if (!snapshot || snapshot.sha256!==ref.sha256 || snapshot.sourceId!==ref.sourceId ||
            snapshot.fileId!==ref.fileId || snapshot.parentId!==config.rootId) fail('source_changed');
        const output=extract(snapshot), stages=['fingerprinted','extracted','reconciled'];
        if (!output.reconciliation) change={status:'NEEDS_REVIEW',reason:'reconciliation_unresolved',output,stages};
        else {
          const verdict=await qa.verify({ref,output,version:VERSION});
          change=verdict?.pass===true && verdict.version===VERSION && verdict.sha256===ref.sha256
            ? {status:'ACCEPTED',reason:null,output,stages}
            : {status:'NEEDS_REVIEW',reason:'qa_not_passed',output,stages};
        }
      } catch (error) {
        const reason=['source_changed','shape_unknown','label_unknown','numeric_unsupported'].includes(error?.message)
          ? error.message : 'extraction_error';
        change={status:reason==='extraction_error' ? 'PENDING':'NEEDS_REVIEW',reason,output:null,stages:[]};
      }
      s=await cas(store,current=>{
        same(current,manifest,config);
        if (current.cancelled || current.phase==='BLOCKED' || current.items[index].claim?.token!==token ||
            current.items[index].status!=='CLAIMED') return null;
        return evolve(current,index,{...change,claim:null});
      });
    }
    s=await cas(store,current=>{
      same(current,manifest,config);
      if (current.phase!=='PILOT' || current.cancelled) return null;
      const pilot=current.items.slice(0,3);
      if (pilot.every(i=>i.status==='ACCEPTED')) return {...current,phase:'CORPUS'};
      if (pilot.some(i=>['NEEDS_REVIEW','FAILED'].includes(i.status))) return {...current,phase:'BLOCKED'};
      return null;
    });
  }
  return counters(s);
}
async function cancel({config,store}) {
  guard(config);
  return cas(store,s=>{
    if (!s || s.client!==config.client || s.environment!==config.environment || s.rootId!==config.rootId) fail('scope_invalid');
    return s.cancelled ? null : {...s,cancelled:true};
  });
}
module.exports={VERSION,scheduled,cancel,extract,counters};
