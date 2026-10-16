#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const files = [
  path.join(root, 'scripts', 'taobao-operations-skills.mjs'),
  ...fs.readdirSync(path.join(root, 'src'))
    .filter((name) => name.endsWith('.mjs'))
    .sort()
    .map((name) => path.join(root, 'src', name))
];

for (const file of files) {
  const result = spawnSync(process.execPath, ['--check', file], { stdio: 'inherit' });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
