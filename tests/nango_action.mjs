// Synthetic-only executable Nango contract stub; no network or provider access.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { deflateRawSync } from 'node:zlib';
const action = (await import(pathToFileURL(process.argv[2]).href)).default;
assert.equal(action.endpoint.method, 'POST');
assert.equal(typeof action.exec, 'function');
const crcTable = Array.from({length:256},(_,i)=>{let c=i;for(let n=0;n<8;n++)c=c&1?c>>>1^0xedb88320:c>>>1;return c>>>0;});
function crc(b){let c=0xffffffff;for(const v of b)c=crcTable[(c^v)&255]^(c>>>8);return(c^0xffffffff)>>>0;}
function zip(files,compressed=false){let offset=0;const locals=[],central=[];
  for(const [name,body] of Object.entries(files)){
    const n=Buffer.from(name),b=Buffer.from(body),check=crc(b),packed=compressed?deflateRawSync(b):b,method=compressed?8:0;
    const l=Buffer.alloc(30);l.writeUInt32LE(0x04034b50);l.writeUInt16LE(20,4);l.writeUInt16LE(method,8);l.writeUInt32LE(check,14);l.writeUInt32LE(packed.length,18);l.writeUInt32LE(b.length,22);l.writeUInt16LE(n.length,26);
    locals.push(l,n,packed);
    const h=Buffer.alloc(46);h.writeUInt32LE(0x02014b50);h.writeUInt16LE(20,4);h.writeUInt16LE(20,6);h.writeUInt16LE(method,10);h.writeUInt32LE(check,16);h.writeUInt32LE(packed.length,20);h.writeUInt32LE(b.length,24);h.writeUInt16LE(n.length,28);h.writeUInt32LE(offset,42);
    central.push(h,n);offset+=l.length+n.length+packed.length;
  }
  const directory=Buffer.concat(central),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50);end.writeUInt16LE(central.length/2,8);end.writeUInt16LE(central.length/2,10);end.writeUInt32LE(directory.length,12);end.writeUInt32LE(offset,16);
  return Buffer.concat([...locals,directory,end]);
}
const files={
  '[Content_Types].xml':'<Types/>',
  '_rels/.rels':'<Relationships><Relationship Id="r0" Target="xl/workbook.xml"/></Relationships>',
  'xl/workbook.xml':'<workbook><sheets><sheet name="Synthetic" r:id="r1"/></sheets></workbook>',
  'xl/_rels/workbook.xml.rels':'<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>',
  'xl/worksheets/sheet1.xml':'<worksheet><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Invented</t></is></c><c r="B1"><f>2+3</f><v>5</v></c><c r="C1"/></row></sheetData></worksheet>'
};
const bytes=zip(files), digest=(algorithm)=>createHash(algorithm).update(bytes).digest('hex');
const input={source:'synthetic-source',parent:'synthetic-parent',version:'synthetic-version',sha256:digest('sha256'),md5:digest('md5')};
const meta={id:input.source,parents:[input.parent],version:input.version,md5Checksum:input.md5,mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',size:String(bytes.length)};
function stub(changes={}){const calls=[];let reads=0;
  const nango={async proxy(options){calls.push(options);assert.equal(options.method,'GET');assert.equal(options.endpoint,'/drive/v3/files/synthetic-source');
    if(options.params.alt==='media'){reads++;return {data:changes.bytes ?? new Uint8Array(bytes)};}
    return {data:changes.meta?.(calls.length) ?? meta};
  }};
  return {nango,calls,get reads(){return reads;}};
}
const good=stub(), result=await action.exec(good.nango,input);
assert.equal(result.state,'evidence');assert.equal(result.evidence.version,'xlsx-evidence/v1');
assert.deepEqual(result.evidence.nonempty,['Synthetic!A1','Synthetic!B1']);
assert.equal(result.evidence.worksheets[0].cells[1].formula,'2+3');
assert.equal(result.evidence.worksheets[0].cells[1].result,'5');
assert.equal(result.evidence.sha256,input.sha256);assert.equal(result.evidence.md5,input.md5);
assert.deepEqual(good.calls.map(x=>x.params.alt||'metadata'),['metadata','media','metadata']);
assert.equal(good.reads,1);
const compressed=zip(files,true), compressedDigest=(algorithm)=>createHash(algorithm).update(compressed).digest('hex');
const compressedInput={...input,sha256:compressedDigest('sha256'),md5:compressedDigest('md5')};
const compressedMeta={...meta,md5Checksum:compressedInput.md5,size:String(compressed.length)};
const compressedTransport=stub({bytes:new Uint8Array(compressed),meta:()=>compressedMeta});
const compressedResult=await action.exec(compressedTransport.nango,compressedInput);
assert.equal(compressedResult.state,'evidence');assert.deepEqual(compressedResult.evidence.nonempty,['Synthetic!A1','Synthetic!B1']);
assert.equal(compressedResult.evidence.sha256,compressedInput.sha256);assert.equal(compressedTransport.reads,1);
for(const [invalid,reason] of [
  [{...input,parent:''},'source_boundary'],
  [{...input,sha256:'0'.repeat(64)},'stale_source'],
  [{...input,md5:'0'.repeat(32)},'stale_source']
]) {const transport=stub();const r=await action.exec(transport.nango,invalid);
  assert.equal(r.state,'needs_review');assert.equal(r.reason,reason);assert.equal(r.evidence,null);
  if(reason==='source_boundary')assert.equal(transport.calls.length,0);
}
for(const changes of [
  {meta:()=>({...meta,parents:['synthetic-other']})},
  {meta:i=>i===3?{...meta,version:'changed'}:meta},
  {bytes:new Uint8Array(bytes.subarray(0,bytes.length-1))},
  {bytes:'not raw bytes'},
  {bytes:new Uint8Array(8388609)}
]) {const transport=stub(changes);const r=await action.exec(transport.nango,input);
  assert.equal(r.state,'needs_review');assert.equal(r.evidence,null);
}
const unsupported=zip({...files,'xl/worksheets/sheet1.xml':files['xl/worksheets/sheet1.xml'].replace('<f>2+3</f>','<f t="shared">2+3</f>')});
const bad=stub({bytes:new Uint8Array(unsupported)});
const badInput={...input,sha256:createHash('sha256').update(unsupported).digest('hex'),md5:createHash('md5').update(unsupported).digest('hex')};
const badMeta={...meta,md5Checksum:badInput.md5,size:String(unsupported.length)};
const badTransport=stub({bytes:new Uint8Array(unsupported),meta:()=>badMeta});
assert.equal((await action.exec(badTransport.nango,badInput)).reason,'unsupported_cell');
let tries=0;const failing={async proxy(){tries++;throw new Error('private provider payload');}};
assert.deepEqual(await action.exec(failing,input),{state:'needs_review',evidence:null,reason:'provider_read_error'});
assert.equal(tries,2);
console.log('synthetic action preflight: OK');
