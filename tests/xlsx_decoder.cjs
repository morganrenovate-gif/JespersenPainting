// Synthetic workbook constructed in memory; no client source bytes.
'use strict';
const {test}=require('node:test'), assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {decode,LIMIT}=require('../private_runtime/xlsx_decoder.cjs');
const {createAdapter}=require('../private_runtime/xlsx_provider_adapter.cjs');
const table=Array.from({length:256},(_,i)=>{let c=i;for(let n=0;n<8;n++) c=c&1?c>>>1^0xedb88320:c>>>1;return c>>>0;});
function crc(b){let c=0xffffffff;for(const v of b)c=table[(c^v)&255]^(c>>>8);return(c^0xffffffff)>>>0;}
const base={
  '[Content_Types].xml':'<Types><Default Extension="xml" ContentType="text/xml"/></Types>',
  '_rels/.rels':'<Relationships><Relationship Id="r0" Target="xl/workbook.xml"/></Relationships>',
  'xl/workbook.xml':'<workbook><sheets><sheet name="Invented Sheet" r:id="r1"/></sheets></workbook>',
  'xl/_rels/workbook.xml.rels':'<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/><Relationship Id="r2" Target="sharedStrings.xml"/></Relationships>',
  'xl/sharedStrings.xml':'<sst><si><t>Invented &amp; Blue</t></si><si><r><t>Rich</t></r><r><t> text</t></r></si></sst>',
  'xl/worksheets/sheet1.xml':'<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="inlineStr"><is><t>Inline &lt; text</t></is></c><c r="C1"><f>2+3</f><v>5</v></c><c r="D1" t="s"><v>1</v></c><c r="E1"/></row></sheetData></worksheet>'
};
function workbook(changes={}) {
  const files={...base,...changes}, local=[], central=[]; let offset=0;
  for(const [name,body] of Object.entries(files)) {
    const n=Buffer.from(name), b=Buffer.from(body), c=crc(b);
    const l=Buffer.alloc(30);l.writeUInt32LE(0x04034b50);l.writeUInt16LE(20,4);l.writeUInt32LE(c,14);l.writeUInt32LE(b.length,18);l.writeUInt32LE(b.length,22);l.writeUInt16LE(n.length,26);
    local.push(l,n,b);
    const h=Buffer.alloc(46);h.writeUInt32LE(0x02014b50);h.writeUInt16LE(20,4);h.writeUInt16LE(20,6);h.writeUInt32LE(c,16);h.writeUInt32LE(b.length,20);h.writeUInt32LE(b.length,24);h.writeUInt16LE(n.length,28);h.writeUInt32LE(offset,42);
    central.push(h,n);offset+=l.length+n.length+b.length;
  }
  const directory=Buffer.concat(central), end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50);end.writeUInt16LE(central.length/2,8);end.writeUInt16LE(central.length/2,10);end.writeUInt32LE(directory.length,12);end.writeUInt32LE(offset,16);
  return Buffer.concat([...local,directory,end]);
}
const sha=b=>createHash('sha256').update(b).digest('hex');
test('original bytes, separate formula/cache, strings and complete nonempty inventory',()=>{
  const bytes=workbook(), copy=Buffer.from(bytes), a=decode(bytes);
  assert.deepEqual(bytes,copy);assert.equal(a.sha256,sha(bytes));assert.equal(a.md5,createHash('md5').update(bytes).digest('hex'));
  assert.deepEqual(decode(bytes),a);assert.deepEqual(a.nonempty,['Invented Sheet!A1','Invented Sheet!B1','Invented Sheet!C1','Invented Sheet!D1']);
  assert.deepEqual(a.worksheets[0].cells.map(c=>c.raw),['Invented & Blue','Inline < text',null,'Rich text']);
  assert.equal(a.worksheets[0].cells[2].formula,'2+3');assert.equal(a.worksheets[0].cells[2].result,'5');
});
test('unsupported and malformed source facts remain rejected',()=>{
  const sheet=base['xl/worksheets/sheet1.xml'];
  for(const changed of [sheet.replace('<v>5</v>',''),sheet.replace('<f>2+3</f>','<f t="shared">2+3</f>'),
    sheet.replace('<v>0</v>','<v>99</v>'),sheet.replace('<v>5</v>','<v>&outside;</v>'),sheet.replace('<v>5</v>','<v>5</c>')])
    assert.throws(()=>decode(workbook({'xl/worksheets/sheet1.xml':changed})));
  assert.throws(()=>decode(workbook({'xl/workbook.xml':base['xl/workbook.xml'].replace('</workbook>','<externalReferences/></workbook>')})),/unsupported_layout/);
  assert.throws(()=>decode(workbook({'xl/_rels/workbook.xml.rels':base['xl/_rels/workbook.xml.rels'].replace('sharedStrings.xml','https://elsewhere.invalid')})),/external_relationship/);
});
test('archive size, expansion, CRC, XML and response bounds',()=>{
  assert.throws(()=>decode(Buffer.alloc(LIMIT.bytes+1)),/archive_limit/);
  assert.throws(()=>decode(workbook({'xl/sharedStrings.xml':'x'.repeat(LIMIT.entry+1)})),/archive_limit/);
  assert.throws(()=>decode(workbook({'xl/sharedStrings.xml':'<sst>'+('<si><t>x</t></si>'.repeat(81000))+'</sst>'})));
  const b=workbook();b[60]^=1;assert.throws(()=>decode(b),/archive_crc/);
  assert.throws(()=>decode(workbook({'xl/sharedStrings.xml':'<!DOCTYPE s><sst/>'})),/malformed_xml/);
});
test('injected read-only metadata and root/version/hash fencing',async()=>{
  const b=workbook(), expected={id:'synthetic-id',parent:'synthetic-root',version:'v1',sha256:sha(b)};
  let reads=0, calls=0, version='v1';
  const provider={async metadata(id){calls++;return {...expected,id,version,mime:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'};},async read(id){reads++;return b;}};
  const adapter=createAdapter({provider,root:'synthetic-root'});
  assert.equal((await adapter.extract(expected)).sha256,sha(b));assert.equal(calls,2);assert.equal(reads,1);
  await assert.rejects(adapter.extract({...expected,parent:'synthetic-other'}),/source_boundary/);
  version='v2';await assert.rejects(adapter.extract(expected),/stale_source/);
  version='v1';provider.read=async()=>{version='v2';return b;};await assert.rejects(adapter.extract(expected),/stale_source/);
  provider.read=async()=>Buffer.from(b.subarray(0,b.length-1));version='v1';await assert.rejects(adapter.extract(expected));
  await assert.rejects(createAdapter({provider:{...provider,read:async()=>Buffer.alloc(LIMIT.bytes+1)},root:'synthetic-root'}).extract(expected),/response_limit/);
});
