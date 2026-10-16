import childProcess from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import assert from 'node:assert/strict';
import { packageRoot } from '../src/registry.mjs';
import { evaluateSycmContract } from '../src/cli.mjs';

const cli = path.join(packageRoot, 'scripts', 'taobao-operations-skills.mjs');

function run(args) {
  return childProcess.spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8', env: { ...process.env, TAOSKILLS_DISABLE_AUTO_UPDATE: '1', SYCMCLI_DISABLE_AUTO_UPDATE: '1' } });
}

test('version and named source are machine-readable', () => {
  const version = run(['version']);
  assert.equal(version.status, 0, version.stderr);
  assert.equal(JSON.parse(version.stdout).version, '0.2.0');
  const versionFlag = run(['--version']);
  assert.equal(versionFlag.status, 0, versionFlag.stderr);
  assert.equal(JSON.parse(versionFlag.stdout).version, '0.2.0');
  const source = run(['skill', 'source', '--name', 'dmp-shop-insight', '--json']);
  assert.equal(source.status, 0, source.stderr);
  assert.match(JSON.parse(source.stdout).source, /skills[/\\]dmp-shop-insight$/);
  const alias = run(['skill', 'source', '--name', 'mkt_insight-marketing-knowledge', '--json']);
  assert.equal(alias.status, 0, alias.stderr);
  assert.match(JSON.parse(alias.stdout).source, /skills[/\\]mkt-insight-marketing-knowledge$/);
});

test('doctor separates completed implementation from pending real validation', () => {
  const result = run(['doctor', '--json']);
  assert.equal(result.status, 1, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.ok, false);
  assert.deepEqual(payload.implementationGaps, []);
  assert.ok(payload.validationPending.includes('daily-shop-inspection'));
  assert.ok(payload.validationPending.includes('category-market-analysis'));
  assert.equal(payload.validationPending.length, 15);
  assert.equal(payload.validationPending.includes('sycm-item-rank-helper'), false);
});

test('sycmcli dependency requires both minimum version and declared capabilities', () => {
  const contract = { minimumVersion: '0.4.0', requiredCapabilities: ['sycm.shop.performance.read'] };
  const old = evaluateSycmContract({ status: 0, stdout: JSON.stringify({ version: '0.3.2', capabilities: [] }) }, contract);
  assert.equal(old.ok, false);
  assert.equal(old.versionOk, false);
  assert.deepEqual(old.missingCapabilities, ['sycm.shop.performance.read']);
  const current = evaluateSycmContract({ status: 0, stdout: JSON.stringify({ version: '0.4.0', capabilities: [{ id: 'sycm.shop.performance.read' }] }) }, contract);
  assert.equal(current.ok, true);
  const newerMajor = evaluateSycmContract({ status: 0, stdout: JSON.stringify({ version: '1.0.0', capabilities: [{ id: 'sycm.shop.performance.read' }] }) }, contract);
  assert.equal(newerMajor.ok, true);
});
