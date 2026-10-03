/* Build adapter: bundle with `npx esbuild private_runtime/hedy_financial_handler.cjs
   --bundle --platform=browser --format=iife --global-name=JespersenFinancial
   --outfile=financial-handler.js`. Source-only: installation remains private. */
'use strict';
const { createRunner } = require('./financial_runner.cjs');
// The Hedy project-scoped executor injects a durable CAS store, read-only XLSX
// transport, independently operated QA, immutable additive output and profiles.
// No credentials/configuration/data are serialized in the bundle.
function createHandler(dependencies) {
  const runner = createRunner(dependencies);
  return async function scheduledHandler(event) {
    if (!event || event.task !== 'PRIVATE-DATA-006' || event.environment !== 'staging')
      throw new Error('scope_halt');
    return runner.tick();
  };
}
module.exports = { createHandler };
