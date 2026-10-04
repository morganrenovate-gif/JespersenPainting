// PRIVATE-DATA-007 synthetic-source-only decoder. No provider access or formula evaluation.
'use strict';
const {createHash} = require('node:crypto');
const {inflateRawSync} = require('node:zlib');
const LIMIT = Object.freeze({bytes:8388608, entries:64, entry:2097152, expanded:12582912, xml:2097152, nodes:80000, cells:40000, sheets:32, response:12582912});
function fail(code) { const e = new Error(code); e.code = code; throw e; }
const digest = (b,a) => createHash(a).update(b).digest('hex');
const table = Array.from({length:256},(_,i) => {let c=i; for(let n=0;n<8;n++) c=c&1 ? c>>>1 ^ 0xedb88320 : c>>>1; return c>>>0;});
function crc(b) {let c=0xffffffff; for(const v of b) c=table[(c^v)&255]^(c>>>8); return (c^0xffffffff)>>>0;}
function archive(b) {
  if (!Buffer.isBuffer(b) || b.length>LIMIT.bytes) fail('archive_limit');
  const part=(p,n)=>{if(p<0 || n<0 || p+n>b.length) fail('malformed_archive'); return b.subarray(p,p+n);};
  let end=-1;
  for(let p=b.length-22;p>=Math.max(0,b.length-65557);p--) if(b.readUInt32LE(p)===0x06054b50 && p+22+b.readUInt16LE(p+20)===b.length){end=p;break;}
  if(end<0 || b.readUInt16LE(end+4) || b.readUInt16LE(end+6) || b.readUInt16LE(end+8)!==b.readUInt16LE(end+10)) fail('unsupported_archive');
  const count=b.readUInt16LE(end+10), size=b.readUInt32LE(end+12), start=b.readUInt32LE(end+16);
  if(count>LIMIT.entries || start+size!==end) fail('archive_limit');
  const files=new Map(), spans=[]; let p=start, expanded=0;
  for(let i=0;i<count;i++) {
    if(part(p,46).readUInt32LE(0)!==0x02014b50) fail('malformed_archive');
    const flags=b.readUInt16LE(p+8), method=b.readUInt16LE(p+10), checksum=b.readUInt32LE(p+16), packed=b.readUInt32LE(p+20), plain=b.readUInt32LE(p+24);
    const nl=b.readUInt16LE(p+28), extra=b.readUInt16LE(p+30), comment=b.readUInt16LE(p+32), offset=b.readUInt32LE(p+42);
    let name; try{name=new TextDecoder('utf-8',{fatal:true}).decode(part(p+46,nl));}catch{fail('malformed_archive');}
    p+=46+nl+extra+comment;
    if(p>end || (flags&(1|0x40|0x2000)) || ![0,8].includes(method) ||
       !/^(?:\[Content_Types\]\.xml|[A-Za-z0-9_./-]+)$/.test(name) || name.startsWith('/') || name.endsWith('/') || name.split('/').includes('..') || files.has(name) ||
       plain>LIMIT.entry || packed>LIMIT.bytes || (expanded+=plain)>LIMIT.expanded ||
       (!packed && plain) || (packed && plain>packed*100)) fail('archive_limit');
    if(part(offset,30).readUInt32LE(0)!==0x04034b50) fail('malformed_archive');
    const localFlags=b.readUInt16LE(offset+6), localMethod=b.readUInt16LE(offset+8), localCrc=b.readUInt32LE(offset+14), localPacked=b.readUInt32LE(offset+18), localPlain=b.readUInt32LE(offset+22);
    const localNameLength=b.readUInt16LE(offset+26), localExtraLength=b.readUInt16LE(offset+28);
    if(localFlags!==flags || localMethod!==method || localNameLength!==nl) fail('malformed_archive');
    const descriptor=(flags&8)!==0;
    if(!descriptor && (localCrc!==checksum || localPacked!==packed || localPlain!==plain)) fail('malformed_archive');
    if(descriptor && ((localCrc&&localCrc!==checksum)||(localPacked&&localPacked!==packed)||(localPlain&&localPlain!==plain))) fail('malformed_archive');
    if(!part(offset+30,localNameLength).equals(Buffer.from(name))) fail('malformed_archive');
    const from=offset+30+localNameLength+localExtraLength; if(from+packed>start) fail('malformed_archive');
    spans.push([offset,from+packed]);
    let data; try{data=method===0 ? part(from,packed) : inflateRawSync(part(from,packed),{maxOutputLength:Math.max(1,plain)});}catch{fail('archive_limit');}
    if(data.length!==plain || crc(data)!==checksum) fail('archive_crc');
    files.set(name,data);
  }
  spans.sort((a,b)=>a[0]-b[0]);
  if(p!==end || spans.some((s,i)=>i && s[0]<spans[i-1][1])) fail('malformed_archive');
  return files;
}
function xml(b) {
  if(!b || b.length>LIMIT.xml) fail('xml_limit');
  let s; try{s=new TextDecoder('utf-8',{fatal:true}).decode(b);}catch{fail('malformed_xml');}
  if(s.charCodeAt(0)===0xfeff)s=s.slice(1);
  const declaration=/^\s*<\?xml\s+version=(["'])1\.[01]\1(?:\s+encoding=(["'])UTF-8\2)?(?:\s+standalone=(["'])(?:yes|no)\3)?\s*\?>/i.exec(s);
  if(declaration)s=s.slice(declaration[0].length);
  if(/<!|<\?|[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(s)) fail('malformed_xml');
  function decode(t) {
    if(/&(?!(?:[^&;]+);)/.test(t)) fail('malformed_xml');
    return t.replace(/&([^;]+);/g,(_,e)=>{
      const known={amp:'&',lt:'<',gt:'>',quot:'"',apos:"'"}; if(Object.hasOwn(known,e)) return known[e];
      const n=/^#x[\da-fA-F]+$/.test(e)?parseInt(e.slice(2),16):/^#\d+$/.test(e)?Number(e.slice(1)):-1;
      if(!Number.isSafeInteger(n) || n<32 && ![9,10,13].includes(n) || n>0x10ffff || n>=0xd800 && n<=0xdfff) fail('malformed_xml');
      return String.fromCodePoint(n);
    });
  }
  const root={name:'#',children:[],value:''}, stack=[root]; let p=0, work=0;
  while(p<s.length) {
    if(++work>LIMIT.nodes) fail('xml_limit');
    if(s[p]!=='<') {let q=s.indexOf('<',p); if(q<0) q=s.length; stack.at(-1).value+=decode(s.slice(p,q)); p=q; continue;}
    const q=s.indexOf('>',p); if(q<0) fail('malformed_xml');
    let tag=s.slice(p+1,q), closing=tag.startsWith('/'), self=tag.endsWith('/');
    if(closing){if(stack.length<2 || tag!=='/'+stack.at(-1).name) fail('malformed_xml'); stack.pop();}
    else {
      if(self) tag=tag.slice(0,-1);
      const m=/^([A-Za-z][\w.-]*)(.*)$/s.exec(tag); if(!m || stack.length>32) fail('malformed_xml');
      const attrs={}; let rest=m[2];
      while(rest.trim()) {const a=/^\s+([\w:.-]+)\s*=\s*(["'])(.*?)\2/s.exec(rest);
        if(!a || Object.hasOwn(attrs,a[1])) fail('malformed_xml'); attrs[a[1]]=decode(a[3]); rest=rest.slice(a[0].length);}
      const node={name:m[1],attrs,children:[],value:''}; stack.at(-1).children.push(node); if(!self) stack.push(node);
    }
    p=q+1;
  }
  if(stack.length!==1 || root.children.length!==1 || root.value.trim()) fail('malformed_xml');
  return root.children[0];
}
const children=(n,k)=>n.children.filter(x=>x.name===k);
function one(n,k){const x=children(n,k); if(x.length>1) fail('unsupported_layout'); return x[0];}
function named(n,k){if(!n || n.name!==k) fail('unsupported_layout'); return n;}
function relationships(n){
  named(n,'Relationships'); const ids=new Set();
  for(const r of n.children){
    if(r.name!=='Relationship' || r.attrs.TargetMode || !r.attrs.Id || ids.has(r.attrs.Id) || typeof r.attrs.Target!=='string' || !r.attrs.Target) fail('external_relationship');
    ids.add(r.attrs.Id);
  }
  return n.children;
}
function workbookTarget(t){
  if(typeof t!=='string'||!t||t.includes('\\')||t.split('/').includes('..')) fail('external_relationship');
  if(t.startsWith('/xl/'))return t.slice(4);
  if(t.startsWith('xl/'))return t.slice(3);
  if(t.startsWith('/'))fail('external_relationship');
  return t;
}
function passivePath(p){
  return ['[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/_rels/workbook.xml.rels','xl/sharedStrings.xml','xl/styles.xml','xl/calcChain.xml'].includes(p) ||
    /^docProps\/(?:core|app|custom)\.xml$/.test(p) ||
    /^xl\/theme\/theme[1-9]\d*\.xml$/.test(p) ||
    /^xl\/worksheets\/sheet[1-9]\d*\.xml$/.test(p) ||
    /^xl\/worksheets\/_rels\/sheet[1-9]\d*\.xml\.rels$/.test(p) ||
    /^xl\/tables\/table[1-9]\d*\.xml$/.test(p) ||
    /^xl\/drawings\/drawing[1-9]\d*\.xml$/.test(p) ||
    /^xl\/drawings\/_rels\/drawing[1-9]\d*\.xml\.rels$/.test(p) ||
    /^xl\/comments[1-9]\d*\.xml$/.test(p) ||
    /^xl\/threadedComments\/threadedComment[1-9]\d*\.xml$/.test(p) ||
    /^xl\/persons\/person\.xml$/.test(p) ||
    /^xl\/media\/[A-Za-z0-9._-]+$/.test(p);
}
function stringItem(n) {
  if(n.children.length===1 && n.children[0].name==='t') return n.children[0].value;
  if(n.children.length && n.children.every(c=>c.name==='r')) return n.children.map(r=>{
    const t=one(r,'t'); if(!t || r.children.some(c=>!['rPr','t'].includes(c.name))) fail('unsupported_layout'); return t.value;
  }).join('');
  fail('unsupported_layout');
}
function decode(bytes) {
  const files=archive(bytes), read=p=>xml(files.get(p));
  const required=['[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/_rels/workbook.xml.rels'];
  if(required.some(p=>!files.has(p))) fail('unsupported_layout');
  const pkg=relationships(read('_rels/.rels')); let workbookLinks=0;
  for(const r of pkg){
    const target=r.attrs.Target.startsWith('/')?r.attrs.Target.slice(1):r.attrs.Target;
    if(target==='xl/workbook.xml')workbookLinks++;
    else if(!/^docProps\/(?:core|app|custom)\.xml$/.test(target))fail('external_relationship');
  }
  if(workbookLinks!==1)fail('external_relationship');
  const types=named(read('[Content_Types].xml'),'Types');
  if(types.children.some(c=>!['Default','Override'].includes(c.name))) fail('unsupported_layout');
  const book=named(read('xl/workbook.xml'),'workbook');
  if(book.children.some(c=>!['sheets','bookViews','workbookPr','calcPr','fileVersion','definedNames','extLst'].includes(c.name))) fail('unsupported_layout');
  const mapping=new Map(); let sharedTarget=null;
  for(const r of relationships(read('xl/_rels/workbook.xml.rels'))){
    const target=workbookTarget(r.attrs.Target);
    if(/^worksheets\/sheet[1-9]\d*\.xml$/.test(target)){if(mapping.has(r.attrs.Id))fail('external_relationship');mapping.set(r.attrs.Id,target);}
    else if(target==='sharedStrings.xml'){if(sharedTarget)fail('external_relationship');sharedTarget=target;}
    else if(!/^(?:styles\.xml|calcChain\.xml|theme\/theme[1-9]\d*\.xml)$/.test(target))fail('external_relationship');
  }
  const sheetList=one(book,'sheets'), sheets=sheetList?.children||[];
  if(!sheets.length || sheets.length>LIMIT.sheets || sheets.some(s=>s.name!=='sheet')) fail('unsupported_layout');
  const names=new Set(), used=new Set(), nonempty=[], worksheets=[];
  let shared=[];
  if(files.has('xl/sharedStrings.xml')) {const s=named(read('xl/sharedStrings.xml'),'sst');
    if(s.children.some(si=>si.name!=='si')) fail('unsupported_layout'); shared=s.children.map(stringItem);}
  let count=0;
  for(const s of sheets) {
    const name=s.attrs.name, target=mapping.get(s.attrs['r:id']);
    if(!name || names.has(name) || !target?.startsWith('worksheets/') || used.has(target) || s.attrs.state && s.attrs.state!=='visible') fail('unsupported_layout');
    names.add(name); used.add(target);
    const sheet=named(read('xl/'+target),'worksheet'), data=one(sheet,'sheetData');
    const allowedSheetChildren=new Set(['sheetPr','dimension','sheetViews','sheetFormatPr','cols','sheetData','sheetCalcPr','sheetProtection','protectedRanges','scenarios','autoFilter','sortState','dataConsolidate','customSheetViews','mergeCells','phoneticPr','conditionalFormatting','dataValidations','hyperlinks','printOptions','pageMargins','pageSetup','headerFooter','rowBreaks','colBreaks','customProperties','cellWatches','ignoredErrors','smartTags','drawing','legacyDrawing','legacyDrawingHF','picture','webPublishItems','tableParts','extLst']);
    if(!data || sheet.children.some(c=>!allowedSheetChildren.has(c.name))) fail('unsupported_layout');
    const cells=[], addresses=new Set();
    for(const row of data.children){if(row.name!=='row') fail('unsupported_layout');
      for(const c of row.children){
        if(c.name!=='c' || !/^[A-Z]{1,3}[1-9]\d{0,6}$/.test(c.attrs.r||'') || addresses.has(c.attrs.r) || ++count>LIMIT.cells) fail('unsupported_layout');
        addresses.add(c.attrs.r);
        const f=one(c,'f'),v=one(c,'v'),inline=one(c,'is'),type=c.attrs.t||'n';
        if(c.children.some(x=>!['f','v','is'].includes(x.name)) || !['n','s','inlineStr','str','b','e','d'].includes(type) ||
          f && (Object.keys(f.attrs).length || inline) || inline && type!=='inlineStr' || type==='inlineStr' && v || type==='s' && !v) fail('unsupported_cell');
        if(!f && !v && !inline) continue;
        const raw=inline ? stringItem(inline) : v ? type==='s' ? shared[Number(v.value)] : v.value : null;
        if(type==='s' && (!/^(0|[1-9]\d*)$/.test(v.value) || raw===undefined) || type==='b' && !['0','1'].includes(raw) ||
          f && (!v || !v.value)) fail(f && !v ? 'missing_formula_cache' : 'unsupported_cell');
        cells.push({sheet:name,address:c.attrs.r,type,raw:f?null:raw,formula:f?f.value:null,result:f?raw:null});
        nonempty.push(name+'!'+c.attrs.r);
      }
    }
    worksheets.push({name,cells});
  }
  for(const [path,data] of files){
    if(!passivePath(path))fail('unsupported_layout');
    if(path.endsWith('.rels')&&path!=='_rels/.rels'&&path!=='xl/_rels/workbook.xml.rels')relationships(xml(data));
  }
  if(sharedTarget&&!files.has('xl/sharedStrings.xml'))fail('unsupported_layout');
  if(files.has('xl/sharedStrings.xml')&&!sharedTarget)fail('unsupported_layout');
  if([...mapping.values()].some(t=>!used.has(t))) fail('unsupported_layout');
  const output={version:'xlsx-evidence/v1',sha256:digest(bytes,'sha256'),md5:digest(bytes,'md5'),complete:true,worksheets,nonempty};
  if(Buffer.byteLength(JSON.stringify(output))>LIMIT.response) fail('response_limit');
  return output;
}
module.exports={decode,LIMIT};
