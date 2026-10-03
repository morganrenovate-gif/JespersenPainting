# PRIVATE-DATA-008 — Nango action source handoff (synthetic only)

`nango_action.template.mjs` is a source-only Nango `createAction` contract: `POST /xlsx-evidence`, strict input `{source,parent,version,sha256,md5}`, and output `{state,evidence,reason}`. `source` and `parent` are opaque caller-provided strings. There is no embedded root, tenant, connection, token, or workbook profile. The only transport calls are fixed Drive v3 `GET` file metadata, `GET` file media, and `GET` metadata again via injected `nango.proxy`; `source` is encoded as one path segment. The provider installation must separately restrict the connection to read-only access and enforce server-side ancestry, authorization, byte caps, timeouts and rate limits. Metadata's direct parent check is **not** proof of provider ancestry. Source identity, parent, version, provider MD5, file size, and original-byte SHA-256/MD5 are checked; changed metadata or bytes returns `needs_review` with a generic reason. Up to two attempts are allowed for thrown transport errors only, without retrying stale or invalid responses. There is no provider/source write entrypoint.

The accepted PRIVATE-DATA-007 decoder is inlined unchanged (apart from its CommonJS envelope) by `build_nango_action.py` into an ES module with static imports of `nango`, `zod`, `node:crypto`, `node:zlib`. It does not evaluate formulas. ZIP/CRC/XML/cell/output bounds and the generic `xlsx-evidence/v1` shape are inherited from `XLSX_DECODER.md`; no financial categories or workbook layout semantics are inferred. An unsupported workbook, unknown format, or missing approved financial profile must remain **needs review** outside this action. A generic evidence result is not an approved financial profile or financial analysis.

## Reproducible preflight / hash

From the repository root with Python 3 and Node available, choose a local disposable output path outside the repository (`OUTPUT`):

```sh
python private_runtime/build_nango_action.py --output "$OUTPUT"
sha256sum "$OUTPUT"
node --check "$OUTPUT"
python -m pytest -q tests/test_xlsx_decoder_js.py tests/test_nango_action.py
```

The builder prints the exact SHA-256 of the UTF-8 artifact; `sha256sum` must match. The artifact is derived solely from the template and the accepted decoder in this checkout, no timestamps or path content. For a source-bound handoff, record the checkout revision, SHA-256 of both source files, builder hash, generated artifact hash, and trusted test output in a separately authorized staging record. Do not commit generated artifacts or private handoff inputs. The local preflight uses contract stubs for `nango` and `zod` and Node syntax checking; it does **not** claim the remote Nango compiler has run. A separately authorized installer must compile against the actual pinned Nango SDK/toolchain and reject unsupported imports, proxy binary-response semantics or schema signatures before installation. Never install based on these stub tests alone. Source and artifact hash must be rechecked against the exact approved code at that gate. The public repository runner's pytest discovery includes both synthetic decoder and action-boundary checks; independent QA is a separate merge gate.

No provider is called by the tests: the in-memory workbook and proxy are synthetic. No real source identifiers, digests, workbook profiles, runtime installation, three-file source-bound QA or live financial acceptance are present. Rollback: revert this template, build script, tests, and documentation. No runtime or provider/source state was created.
