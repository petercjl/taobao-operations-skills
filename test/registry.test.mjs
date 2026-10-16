import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import assert from 'node:assert/strict';
import { packageRoot, readManifest, skillSource } from '../src/registry.mjs';
import { digestTree } from '../src/digest.mjs';

test('manifest registers 26 independent Skills with matching entries', () => {
  const manifest = readManifest();
  assert.equal(manifest.skills.length, 26);
  assert.equal(new Set(manifest.skills.map((item) => item.name)).size, 26);
  for (const skill of manifest.skills) {
    const text = fs.readFileSync(path.join(packageRoot, skill.entry), 'utf8');
    assert.match(text, new RegExp(`^name:\\s*${skill.name}$`, 'm'));
    assert.match(skill.skillVersion, /^\d+\.\d+\.\d+$/);
    assert.ok(digestTree(skillSource(skill.name)));
  }
});

test('package and manifest versions stay synchronized', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(packageRoot, 'package.json'), 'utf8'));
  assert.equal(readManifest().packageVersion, pkg.version);
});

test('suite registry contains every Skill exactly once', () => {
  const suite = JSON.parse(fs.readFileSync(path.join(packageRoot, 'suite-manifest.json'), 'utf8'));
  const expected = readManifest().skills.map((item) => item.name).sort();
  assert.deepEqual(suite.nodes.map((item) => item.skill).sort(), expected);
  assert.equal(new Set(suite.nodes.map((item) => item.id)).size, expected.length);
});

test('published Skills do not contain machine-private absolute paths', () => {
  for (const skill of readManifest().skills) {
    for (const relative of walk(skillSource(skill.name))) {
      const file = path.join(skillSource(skill.name), relative);
      const content = fs.readFileSync(file);
      if (content.includes(0)) continue;
      const text = content.toString('utf8');
      assert.doesNotMatch(text, /\/Users\/[A-Za-z0-9._-]+\//, `${skill.name}/${relative}`);
      assert.doesNotMatch(text, /C:\\Users\\[A-Za-z0-9._-]+\\/i, `${skill.name}/${relative}`);
    }
  }
});

function walk(root, current = '') {
  const result = [];
  for (const entry of fs.readdirSync(path.join(root, current), { withFileTypes: true })) {
    const relative = path.join(current, entry.name);
    if (entry.isDirectory()) result.push(...walk(root, relative));
    else result.push(relative);
  }
  return result;
}
