#!/usr/bin/env node
import { main } from '../src/cli.mjs';

main(process.argv.slice(2)).catch((error) => {
  const payload = {
    ok: false,
    error: {
      code: error.code || 'UNEXPECTED_ERROR',
      message: error.message,
      ...(error.details ? { details: error.details } : {}),
      ...(error.hint ? { hint: error.hint } : {})
    }
  };
  process.stderr.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exitCode = error.exitCode || 1;
});
