// Hedy scheduled handler entry: install through the separately authorized staging executor.
// Dependency injection keeps provider access, governed CAS storage and independent QA private.
'use strict';
const runner = require('./financial_runner');
function createScheduledHandler({configuration, inventory, queue, xlsx, independentQA, clock}) {
  if (![configuration, inventory, queue, xlsx, independentQA, clock].every(Boolean)) throw Error('installation_incomplete');
  return async function scheduledHandler() {
    const config = await configuration();
    const manifest = await inventory.list(config.rootId); // private, read-only; stable ordered snapshot
    return runner.scheduled({config, manifest, store:queue, transport:xlsx, qa:independentQA, now:clock()});
  };
}
module.exports = {createScheduledHandler};
