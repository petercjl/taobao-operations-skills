import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import assert from 'node:assert/strict';
import { CliError } from '../src/errors.mjs';
import { installSkill, skillStatus, updateSkill } from '../src/skill-manager.mjs';

function sandbox() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'taobao-operations-skills-'));
  process.env.TAOSKILLS_CODEX_DIR = path.join(root, 'codex');
  process.env.TAOSKILLS_AGENTS_DIR = path.join(root, 'agents');
  process.env.TAOSKILLS_SEALSEEK_DIR = path.join(root, 'sealseek');
  return root;
}

test('copy install returns ownership and digest evidence', (t) => {
  const root = sandbox(); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const result = installSkill('category-market-analysis', 'codex', { mode: 'copy' });
  assert.equal(result.action, 'installed');
  assert.equal(result.after.managed, true);
  assert.equal(result.after.current, true);
  assert.equal(result.after.mode, 'copy');
});

test('unmanaged target is refused and explicit adoption creates a backup', (t) => {
  const root = sandbox(); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const target = path.join(process.env.TAOSKILLS_CODEX_DIR, 'category-market-analysis');
  fs.mkdirSync(target, { recursive: true });
  fs.writeFileSync(path.join(target, 'user.txt'), 'owned by user\n');
  assert.throws(() => installSkill('category-market-analysis', 'codex', { mode: 'copy' }), (error) => error instanceof CliError && error.code === 'UNMANAGED_SKILL_EXISTS');
  const result = installSkill('category-market-analysis', 'codex', { mode: 'copy', adopt: true });
  assert.equal(result.action, 'adopted');
  assert.ok(result.backup && fs.existsSync(path.join(result.backup, 'user.txt')));
});

test('local edits stop update; reconciliation backs up and preserves host metadata', (t) => {
  const root = sandbox(); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const installed = installSkill('category-market-analysis', 'sealseek', { mode: 'copy' });
  const target = installed.after.target;
  fs.writeFileSync(path.join(target, '.sealseek-skill.json'), '{"pinned":true}\n');
  fs.appendFileSync(path.join(target, 'SKILL.md'), '\nlocal edit\n');
  assert.equal(skillStatus({ name: 'category-market-analysis', agent: 'sealseek' })[0].localEdits, true);
  assert.throws(() => updateSkill('category-market-analysis', 'sealseek', { mode: 'copy' }), (error) => error.code === 'LOCAL_EDITS');
  const result = updateSkill('category-market-analysis', 'sealseek', { mode: 'copy', reconcile: true });
  assert.ok(result.backup && fs.existsSync(result.backup));
  assert.equal(fs.readFileSync(path.join(target, '.sealseek-skill.json'), 'utf8'), '{"pinned":true}\n');
  assert.equal(result.after.current, true);
});

test('unknown Agent and unknown Skill are rejected', () => {
  sandbox();
  assert.throws(() => skillStatus({ name: 'missing-skill', agent: 'codex' }), (error) => error.code === 'UNKNOWN_SKILL');
  assert.throws(() => skillStatus({ name: 'category-market-analysis', agent: 'missing-agent' }), (error) => error.code === 'INVALID_AGENT');
});
