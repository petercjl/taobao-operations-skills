import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { CliError } from './errors.mjs';

export const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifestPath = path.join(packageRoot, 'skills-manifest.json');

export function readManifest() {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (manifest.schemaVersion !== 1 || !Array.isArray(manifest.skills)) {
    throw new CliError('INVALID_MANIFEST', 'skills-manifest.json is invalid.');
  }
  const names = new Set();
  const aliases = new Set();
  for (const skill of manifest.skills) {
    if (!skill.name || names.has(skill.name) || aliases.has(skill.name)) throw new CliError('INVALID_MANIFEST', `Duplicate or missing Skill name: ${skill.name || '<empty>'}.`);
    names.add(skill.name);
    for (const alias of skill.aliases || []) {
      if (!alias || aliases.has(alias) || names.has(alias)) throw new CliError('INVALID_MANIFEST', `Duplicate or invalid Skill alias: ${alias || '<empty>'}.`);
      aliases.add(alias);
    }
    const entry = path.resolve(packageRoot, skill.entry);
    if (!entry.startsWith(`${path.join(packageRoot, 'skills')}${path.sep}`) || !fs.existsSync(entry)) {
      throw new CliError('INVALID_MANIFEST', `Missing or unsafe entry for Skill "${skill.name}".`);
    }
  }
  return manifest;
}

export function findSkill(name) {
  const skill = readManifest().skills.find((item) => item.name === name || (item.aliases || []).includes(name));
  if (!skill) throw new CliError('UNKNOWN_SKILL', `Unknown Skill "${name}".`, { exitCode: 2 });
  return skill;
}

export function skillSource(name) {
  const skill = findSkill(name);
  return path.dirname(path.resolve(packageRoot, skill.entry));
}
