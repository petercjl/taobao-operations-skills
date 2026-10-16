import childProcess from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { CliError } from './errors.mjs';
import { readManifest } from './registry.mjs';
import { skillStatus, updateSkill } from './skill-manager.mjs';

const PACKAGE_NAME = '@petercjl/taobao-operations-skills';
const REGISTRY = 'https://registry.npmjs.org';

function stateRoot(env = process.env) {
  return env.TAOSKILLS_STATE_DIR || path.join(os.homedir(), '.taobao-operations-skills');
}

function stateFile() { return path.join(stateRoot(), 'update.json'); }
function defaults() { return { schemaVersion: 1, autoUpdate: true, intervalHours: 24, channel: 'latest', lastCheckedAt: null, lastResult: null }; }

export function readUpdateState() {
  try { return { ...defaults(), ...JSON.parse(fs.readFileSync(stateFile(), 'utf8')) }; } catch { return defaults(); }
}

export function writeUpdateState(patch) {
  const next = { ...readUpdateState(), ...patch, schemaVersion: 1 };
  fs.mkdirSync(stateRoot(), { recursive: true, mode: 0o700 });
  const temporary = `${stateFile()}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(next, null, 2)}\n`, { mode: 0o600, flag: 'wx' });
  fs.renameSync(temporary, stateFile());
  return next;
}

function parts(version) {
  const match = String(version).match(/^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$/);
  if (!match) throw new CliError('INVALID_VERSION', `Invalid semver "${version}".`);
  return match.slice(1).map(Number);
}

export function compareVersions(left, right) {
  const a = parts(left); const b = parts(right);
  for (let i = 0; i < 3; i += 1) if (a[i] !== b[i]) return a[i] > b[i] ? 1 : -1;
  return 0;
}

async function registryJson(route) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 7000);
  try {
    const response = await fetch(`${REGISTRY}${route}`, { headers: { Accept: 'application/json' }, signal: controller.signal });
    if (!response.ok) throw new CliError('UPDATE_CHECK_FAILED', `npm registry returned HTTP ${response.status}.`);
    return await response.json();
  } catch (error) {
    if (error instanceof CliError) throw error;
    throw new CliError('UPDATE_CHECK_FAILED', 'Could not check npm for updates.', { details: error.message });
  } finally { clearTimeout(timer); }
}

export async function checkForUpdate({ force = false } = {}) {
  const currentVersion = readManifest().packageVersion;
  const state = readUpdateState();
  const age = state.lastCheckedAt ? Date.now() - Date.parse(state.lastCheckedAt) : Infinity;
  if (!force && age < Number(state.intervalHours) * 3_600_000) return { checked: false, reason: 'interval-not-elapsed', currentVersion, ...state.lastResult };
  const tags = await registryJson('/-/package/%40petercjl%2Ftaobao-operations-skills/dist-tags');
  const latestVersion = tags[state.channel || 'latest'];
  if (!latestVersion) throw new CliError('UPDATE_CHECK_FAILED', `npm did not return the ${state.channel || 'latest'} dist-tag.`);
  const result = { checked: true, currentVersion, latestVersion, updateAvailable: compareVersions(latestVersion, currentVersion) > 0, channel: state.channel || 'latest' };
  writeUpdateState({ lastCheckedAt: new Date().toISOString(), lastResult: result });
  return result;
}

function currentPrefix() {
  const modulePath = fileURLToPath(import.meta.url);
  const marker = `${path.sep}lib${path.sep}node_modules${path.sep}@petercjl${path.sep}taobao-operations-skills${path.sep}`;
  const index = modulePath.indexOf(marker);
  return index > 0 ? modulePath.slice(0, index) : null;
}

export async function installUpdate() {
  const check = await checkForUpdate({ force: true });
  if (!check.updateAvailable) return { ...check, updated: false };
  const prefix = currentPrefix();
  if (!prefix) throw new CliError('UPDATE_PREFIX_UNRESOLVED', 'Automatic update requires a global npm installation.', { hint: `Ask the Agent to install ${PACKAGE_NAME}@${check.latestVersion}.` });
  const metadata = await registryJson(`/%40petercjl%2Ftaobao-operations-skills/${encodeURIComponent(check.latestVersion)}`);
  const tarball = metadata?.dist?.tarball;
  if (metadata?.name !== PACKAGE_NAME || metadata?.version !== check.latestVersion || !tarball?.startsWith(`${REGISTRY}/@petercjl/taobao-operations-skills/-/`)) {
    throw new CliError('UPDATE_METADATA_INVALID', 'npm returned unexpected package metadata.');
  }
  const command = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  const env = { ...process.env, TAOSKILLS_DISABLE_AUTO_UPDATE: '1' };
  for (const key of ['NPM_CONFIG_USERCONFIG', 'npm_config_userconfig', 'NPM_CONFIG_PREFIX', 'npm_config_prefix']) delete env[key];
  const run = childProcess.spawnSync(command, ['install', '--global', '--prefix', prefix, tarball], { encoding: 'utf8', timeout: 120_000, env });
  if (run.error || run.status !== 0) throw new CliError('UPDATE_INSTALL_FAILED', 'Automatic npm update failed.', { details: (run.stderr || run.error?.message || '').trim() });
  const refreshed = [];
  for (const item of skillStatus()) {
    if (item.installed && item.managed && item.mode === 'copy' && !item.localEdits && !item.current) refreshed.push(updateSkill(item.name, item.agent, { mode: 'copy' }));
  }
  const result = { ...check, updated: true, installedVersion: check.latestVersion, refreshed: refreshed.map((item) => ({ name: item.after.name, agent: item.after.agent, backup: item.backup })) };
  writeUpdateState({ lastCheckedAt: new Date().toISOString(), lastUpdatedAt: new Date().toISOString(), lastResult: result });
  return result;
}

export async function autoUpdateIfNeeded() {
  if (process.env.TAOSKILLS_DISABLE_AUTO_UPDATE === '1') return { checked: false, reason: 'disabled-by-environment' };
  const state = readUpdateState();
  if (!state.autoUpdate) return { checked: false, reason: 'disabled-by-config' };
  try {
    const result = await checkForUpdate();
    return result.updateAvailable ? installUpdate() : result;
  } catch (error) {
    writeUpdateState({ lastCheckedAt: new Date().toISOString(), lastResult: { checked: true, error: error.message } });
    return { checked: true, error: error.message };
  }
}
