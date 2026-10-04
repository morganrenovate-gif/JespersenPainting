// @ts-nocheck
// PRIVATE-DATA-008 source template. Build script inlines the accepted decoder at the marker.
import { createAction } from 'nango';
import { z } from 'zod';
import { createHash } from 'node:crypto';
// Nango remote compiler cannot package the zlib module; use the Node 22 Web decompression stream.
async function inflateRawBounded(data, expected) {
  if (!Number.isInteger(expected) || expected < 0 || expected > LIMIT.entry) fail('archive_limit');
  let stream;
  try {
    stream = new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
  } catch {
    fail('archive_limit');
  }
  const reader = stream.getReader(), chunks = [];
  let total = 0;
  try {
    for (;;) {
      const part = await reader.read();
      if (part.done) break;
      const chunk = Buffer.from(part.value);
      total += chunk.length;
      if (total > expected) fail('archive_limit');
      chunks.push(chunk);
    }
  } catch (error) {
    if (error?.code) throw error;
    fail('archive_limit');
  }
  if (total !== expected) fail('archive_crc');
  return Buffer.concat(chunks, total);
}
// INSERT_ACCEPTED_DECODER

const hex256 = /^[a-f0-9]{64}$/;
const hex128 = /^[a-f0-9]{32}$/;
const mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const review = reason => ({ state: 'needs_review', evidence: null, reason });
const input = z.object({
  source: z.string().min(1), parent: z.string().min(1),
  version: z.string().min(1), sha256: z.string().regex(hex256),
  md5: z.string().regex(hex128)
}).strict();
const output = z.object({
  state: z.enum(['evidence', 'needs_review']),
  evidence: z.any().nullable(), reason: z.string().nullable()
});

// Only two fixed GET requests are available to this action. No caller-controlled
// endpoint, method, query, authorization, or provider operation is accepted.
async function extract(nango, request) {
  if (!request || typeof request.source !== 'string' || !request.source ||
      request.source === '.' || request.source === '..' ||
      /[\/\\\u0000-\u001f\u007f]/.test(request.source) ||
      typeof request.parent !== 'string' || !request.parent ||
      typeof request.version !== 'string' || !request.version ||
      !hex256.test(request.sha256 || '') || !hex128.test(request.md5 || '')) fail('source_boundary');
  const endpoint = '/drive/v3/files/' + encodeURIComponent(request.source);
  async function get(params, responseType) {
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        return await nango.proxy({ method: 'GET', endpoint, params, responseType });
      } catch {
        if (attempt === 1) fail('provider_read_error');
      }
    }
  }
  async function metadata() {
    const response = await get({ fields: 'id,parents,version,md5Checksum,mimeType,size', supportsAllDrives: 'true' });
    const m = response?.data;
    if (!m || m.id !== request.source || !Array.isArray(m.parents) ||
        m.parents.length !== 1 || m.parents[0] !== request.parent ||
        m.version !== request.version || m.md5Checksum !== request.md5 ||
        m.mimeType !== mime || typeof m.size !== 'string' ||
        !/^(0|[1-9]\d*)$/.test(m.size) || Number(m.size) > LIMIT.bytes) fail('stale_source');
    return JSON.stringify([m.id, m.parents, m.version, m.md5Checksum, m.mimeType, m.size]);
  }
  const before = await metadata();
  const response = await get({ alt: 'media', supportsAllDrives: 'true' }, 'arraybuffer');
  // Never coerce a JSON, string, base64 or truncated HTTP response to bytes.
  const data = response?.data;
  if (!(data instanceof ArrayBuffer) && !ArrayBuffer.isView(data)) fail('response_limit');
  if (data.byteLength > LIMIT.bytes) fail('response_limit');
  const bytes = Buffer.from(data instanceof ArrayBuffer ? new Uint8Array(data) :
    new Uint8Array(data.buffer, data.byteOffset, data.byteLength));
  if (String(bytes.length) !== JSON.parse(before)[5] ||
      digest(bytes, 'sha256') !== request.sha256 || digest(bytes, 'md5') !== request.md5) fail('stale_source');
  if (await metadata() !== before) fail('stale_source');
  return decode(bytes);
}

export default createAction({
  description: 'Read-only generic XLSX cell evidence; no workbook profile',
  version: '1.0.0',
  endpoint: { method: 'POST', path: '/xlsx-evidence' },
  input, output,
  exec: async (nango, request) => {
    try {
      const evidence = await extract(nango, request);
      return { state: 'evidence', evidence, reason: null };
    } catch (error) {
      // Never return provider error bodies or partially decoded cell content.
      const known = new Set(['source_boundary', 'stale_source', 'provider_read_error',
        'archive_limit', 'malformed_archive', 'unsupported_archive', 'archive_crc',
        'malformed_xml', 'xml_limit', 'unsupported_layout', 'unsupported_cell',
        'external_relationship', 'missing_formula_cache', 'response_limit']);
      return review(known.has(error?.code) ? error.code : 'unsupported_format');
    }
  }
});
