// PRIVATE-DATA-007 read-only injected provider boundary. No provider configuration.
'use strict';
const {decode, LIMIT} = require('./xlsx_decoder.cjs');
function fail(code) {const e=new Error(code); e.code=code; throw e;}
const sha=/^[a-f0-9]{64}$/;
function createAdapter({provider, root, maxAttempts=2}) {
  if(!provider || typeof provider.metadata!=='function' || typeof provider.read!=='function' ||
     typeof root!=='string' || !root || !Number.isInteger(maxAttempts) || maxAttempts<1 || maxAttempts>3) fail('configuration_halt');
  async function metadata(id) {
    let value;
    for(let attempt=0;attempt<maxAttempts;attempt++) {
      try {value=await provider.metadata(id); break;} catch {if(attempt===maxAttempts-1) fail('provider_read_error');}
    }
    return value;
  }
  function validate(m, expected) {
    if(!m || m.id!==expected.id || m.parent!==root || m.parent!==expected.parent ||
       typeof m.version!=='string' || !m.version || m.version!==expected.version ||
       !sha.test(m.sha256||'') || m.sha256!==expected.sha256 || m.mime!=='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') fail('stale_source');
  }
  async function extract(expected) {
    if(!expected || typeof expected.id!=='string' || !expected.id || expected.parent!==root ||
       !sha.test(expected.sha256||'') || typeof expected.version!=='string' || !expected.version) fail('source_boundary');
    const before=await metadata(expected.id); validate(before,expected);
    let bytes;
    for(let attempt=0;attempt<maxAttempts;attempt++) {
      try {bytes=await provider.read(expected.id,{maxBytes:LIMIT.bytes}); break;} catch {if(attempt===maxAttempts-1) fail('provider_read_error');}
    }
    if(!Buffer.isBuffer(bytes) || bytes.length>LIMIT.bytes) fail('response_limit');
    const evidence=decode(bytes);
    if(evidence.sha256!==expected.sha256) fail('stale_source');
    const after=await metadata(expected.id); validate(after,expected);
    if(JSON.stringify(before)!==JSON.stringify(after)) fail('stale_source');
    return evidence;
  }
  return Object.freeze({extract});
}
module.exports={createAdapter};
