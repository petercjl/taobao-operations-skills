import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { CliError } from './errors.mjs';
import { digestTree, HOST_METADATA_FILES, MANAGED_FILE, treeFiles } from './digest.mjs';
import { readManifest, skillSource } from './registry.mjs';

const MANAGER = '@petercjl/taobao-operations-skills';

export function agentRoots(env = process.env, home = os.homedir()) {
  return {
    codex: env.TAOSKILLS_CODEX_DIR || path.join(env.CODEX_HOME || path.join(home, '.codex'), 'skills'),
    agents: env.TAOSKILLS_AGENTS_DIR || path.join(home, '.agents', 'skills'),
    sealseek: env.TAOSKILLS_SEALSEEK_DIR || path.join(home, '.sealseek', 'skill_pool')
  };
}

function targetInfo(name, agent, roots = agentRoots()) {
  if (!roots[agent]) throw new CliError('INVALID_AGENT', `Unknown agent "${agent}".`, { exitCode: 2, hint: `Use one of: ${Object.keys(roots).join(', ')}` });
  return { name, agent, source: skillSource(name), target: path.join(roots[agent], name) };
}

function readMarker(target) {
  try { return JSON.parse(fs.readFileSync(path.join(target, MANAGED_FILE), 'utf8')); } catch { return null; }
}

function inspect(name, agent, roots = agentRoots()) {
  const info = targetInfo(name, agent, roots);
  const sourceDigest = digestTree(info.source);
  if (!fs.existsSync(info.target)) return { ...info, sourceDigest, installed: false, managed: false, current: false, localEdits: false };
  const stat = fs.lstatSync(info.target);
  if (stat.isSymbolicLink()) {
    const linkedSource = path.resolve(path.dirname(info.target), fs.readlinkSync(info.target));
    const managed = linkedSource === info.source;
    return { ...info, sourceDigest, installed: true, managed, current: managed, localEdits: false, mode: 'link', linkedSource };
  }
  const marker = readMarker(info.target);
  const managed = marker?.manager === MANAGER && marker?.skill === name;
  const installedDigest = managed ? digestTree(info.target, marker.files || []) : null;
  const localEdits = managed && installedDigest !== marker.digest;
  return { ...info, sourceDigest, installed: true, managed, current: managed && !localEdits && installedDigest === sourceDigest, localEdits, mode: 'copy', installedDigest, marker };
}

export function skillStatus({ name, agent } = {}) {
  const manifest = readManifest();
  const names = name ? [name] : manifest.skills.map((item) => item.name);
  const agents = agent ? [agent] : Object.keys(agentRoots());
  return names.flatMap((skillName) => agents.map((agentName) => inspect(skillName, agentName)));
}

function backupPath(target) {
  return `${target}.backup-${new Date().toISOString().replaceAll(/[:.]/g, '-')}`;
}

function readHostMetadata(target) {
  const result = new Map();
  if (!fs.existsSync(target) || fs.lstatSync(target).isSymbolicLink()) return result;
  for (const filename of HOST_METADATA_FILES) {
    const file = path.join(target, filename);
    if (fs.existsSync(file) && fs.statSync(file).isFile()) result.set(filename, fs.readFileSync(file));
  }
  return result;
}

function restoreHostMetadata(target, metadata) {
  for (const [filename, content] of metadata) fs.writeFileSync(path.join(target, filename), content);
}

function copySource(info) {
  fs.cpSync(info.source, info.target, { recursive: true, preserveTimestamps: true });
  const files = treeFiles(info.source);
  const digest = digestTree(info.source, files);
  const marker = { schemaVersion: 1, manager: MANAGER, skill: info.name, skillVersion: readManifest().skills.find((item) => item.name === info.name).skillVersion, digest, files, installedAt: new Date().toISOString() };
  fs.writeFileSync(path.join(info.target, MANAGED_FILE), `${JSON.stringify(marker, null, 2)}\n`, { mode: 0o600 });
}

function replaceTarget(info, { mode, preserveMetadata = true } = {}) {
  const metadata = preserveMetadata ? readHostMetadata(info.target) : new Map();
  let backup = null;
  let lockedDirectoryFallback = false;
  if (fs.existsSync(info.target)) {
    backup = backupPath(info.target);
    try {
      fs.renameSync(info.target, backup);
    } catch (error) {
      if (!['EPERM', 'EACCES', 'EBUSY'].includes(error.code) || fs.lstatSync(info.target).isSymbolicLink()) throw error;
      fs.cpSync(info.target, backup, { recursive: true, preserveTimestamps: true });
      fs.rmSync(info.target, { recursive: true, force: true });
      lockedDirectoryFallback = true;
    }
  }
  fs.mkdirSync(path.dirname(info.target), { recursive: true });
  if (mode === 'link') fs.symlinkSync(info.source, info.target, 'dir');
  else {
    fs.mkdirSync(info.target, { recursive: true });
    copySource(info);
    restoreHostMetadata(info.target, metadata);
  }
  return { backup, lockedDirectoryFallback, preservedMetadata: [...metadata.keys()] };
}

export function installSkill(name, agent, { adopt = false, mode = 'auto' } = {}) {
  const before = inspect(name, agent);
  if (before.installed && !before.managed && !adopt) {
    throw new CliError('UNMANAGED_SKILL_EXISTS', `Refusing to replace unmanaged Skill at ${before.target}.`, { hint: 'Review it first, then repeat with --adopt to create a backup and transfer ownership.' });
  }
  if (before.installed && before.managed) return { action: 'unchanged', before, after: before, backup: null };
  const resolvedMode = mode === 'auto' ? (process.platform === 'win32' ? 'copy' : 'link') : mode;
  if (!['copy', 'link'].includes(resolvedMode)) throw new CliError('INVALID_MODE', '--mode must be auto, copy, or link.', { exitCode: 2 });
  if (resolvedMode === 'link' && process.platform === 'win32') throw new CliError('UNSUPPORTED_MODE', 'Link mode is not enabled on Windows; use copy mode.');
  const evidence = replaceTarget(before, { mode: resolvedMode });
  return { action: before.installed ? 'adopted' : 'installed', before, after: inspect(name, agent), ...evidence };
}

export function updateSkill(name, agent, { reconcile = false, mode = 'auto' } = {}) {
  const before = inspect(name, agent);
  if (!before.installed) return installSkill(name, agent, { mode });
  if (!before.managed) throw new CliError('UNMANAGED_SKILL_EXISTS', `Refusing to update unmanaged Skill at ${before.target}.`);
  if (before.localEdits && !reconcile) throw new CliError('LOCAL_EDITS', `Managed Skill "${name}" has local edits.`, { hint: 'Review the backup/reconciliation boundary, then repeat with --reconcile.' });
  if (before.current) return { action: 'unchanged', before, after: before, backup: null };
  const resolvedMode = mode === 'auto' ? (before.mode === 'link' ? 'link' : process.platform === 'win32' ? 'copy' : 'link') : mode;
  const evidence = replaceTarget(before, { mode: resolvedMode });
  return { action: 'updated', before, after: inspect(name, agent), ...evidence };
}
