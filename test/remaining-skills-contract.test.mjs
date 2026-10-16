import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import assert from 'node:assert/strict';
import { packageRoot, readManifest } from '../src/registry.mjs';

const pending = [
  'alimama-insight',
  'category-market-analysis',
  'category-market-insight',
  'category-top-shops-profile',
  'competitor-comparison-action-tracking',
  'competitor-shop-analysis',
  'daily-shop-inspection',
  'dmp-shop-insight',
  'item-ops-event-impact-analysis',
  'item-promotion-analysis',
  'item-traffic-fluctuation-analysis',
  'market-blue-ocean-opportunity-mining',
  'marketing-price-check-pro',
  'mkt-insight-marketing-knowledge',
  'sycm-item-competitor-analysis'
];

test('all remaining Skills are implemented with portable contracts and pending honest validation', () => {
  const byName = new Map(readManifest().skills.map((entry) => [entry.name, entry]));
  for (const name of pending) {
    const root = path.join(packageRoot, 'skills', name);
    const skill = fs.readFileSync(path.join(root, 'SKILL.md'), 'utf8');
    const capabilities = JSON.parse(fs.readFileSync(path.join(root, 'capabilities.json'), 'utf8'));
    assert.equal(byName.get(name)?.migrationStatus, 'implemented-awaiting-validation');
    assert.equal(capabilities.skill, name);
    assert.deepEqual(capabilities.target_platforms, ['codex', 'sealseek']);
    assert.ok(capabilities.capabilities.length >= 1);
    assert.doesNotMatch(skill, /agent_task\s*\(|agent_type:\s*["']?sycm-agent/i, `${name} retains the legacy remote-agent runtime`);
    for (const platform of capabilities.target_platforms) {
      const adapter = JSON.parse(fs.readFileSync(path.join(root, 'adapters', `${platform}.json`), 'utf8'));
      assert.equal(adapter.platform, platform);
      assert.ok(adapter.mappings.every((mapping) => mapping.status === 'implemented'));
    }
  }
});

test('item ranking helper records Codex main-run evidence without overstating SealSeek', () => {
  const byName = new Map(readManifest().skills.map((entry) => [entry.name, entry]));
  assert.equal(byName.get('sycm-item-rank-helper')?.migrationStatus, 'implemented-local-validation');
  const root = path.join(packageRoot, 'skills', 'sycm-item-rank-helper', 'adapters');
  const codex = JSON.parse(fs.readFileSync(path.join(root, 'codex.json'), 'utf8'));
  const sealseek = JSON.parse(fs.readFileSync(path.join(root, 'sealseek.json'), 'utf8'));
  assert.equal(codex.mappings[0].status, 'tested');
  assert.ok(codex.mappings[0].evidence.length >= 1);
  assert.equal(sealseek.mappings[0].status, 'implemented');
});

test('suite nested-Skill dependencies resolve to exact registered names', () => {
  const suite = JSON.parse(fs.readFileSync(path.join(packageRoot, 'suite-manifest.json'), 'utf8'));
  const registered = new Set(suite.nodes.map((node) => node.skill));
  for (const node of suite.nodes) {
    for (const dependency of node.requires_skills) assert.ok(registered.has(dependency), `${node.skill} -> ${dependency}`);
  }
  assert.deepEqual(suite.nodes.find((node) => node.skill === 'item-traffic-fluctuation-analysis').requires_skills, ['item-traffic-analysis']);
  assert.ok(suite.nodes.find((node) => node.skill === 'category-market-insight').requires_skills.includes('category-market-analysis'));
});
