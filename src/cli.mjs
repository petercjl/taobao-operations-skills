import childProcess from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { invariant, CliError } from './errors.mjs';
import { packageRoot, readManifest, skillSource } from './registry.mjs';
import { installSkill, skillStatus, updateSkill } from './skill-manager.mjs';
import { autoUpdateIfNeeded, checkForUpdate, installUpdate, readUpdateState, writeUpdateState } from './update-manager.mjs';

const HELP = `taobao-operations-skills — manage independent Taobao operations Skills

Usage:
  taobao-operations-skills version
  taobao-operations-skills capabilities --json
  taobao-operations-skills doctor --json
  taobao-operations-skills skill list [--group <group>] --json
  taobao-operations-skills skill source --name <skill> --json
  taobao-operations-skills skill status [--name <skill>] [--agent codex|agents|sealseek] --json
  taobao-operations-skills skill install --name <skill>|--all --agent <agent> [--adopt] [--mode auto|link|copy] --json
  taobao-operations-skills skill update --name <skill>|--all --agent <agent> [--reconcile] [--mode auto|link|copy] --json
  taobao-operations-skills update status|check|install|config [--auto-update true|false] [--interval-hours N] --json
`;

function parse(argv) {
  const positional = []; const flags = {};
  for (let i = 0; i < argv.length; i += 1) {
    const value = argv[i];
    if (!value.startsWith('--')) positional.push(value);
    else {
      const key = value.slice(2);
      if (['json', 'all', 'adopt', 'reconcile', 'version', 'help'].includes(key)) flags[key] = true;
      else { invariant(argv[i + 1] && !argv[i + 1].startsWith('--'), 'MISSING_FLAG_VALUE', `--${key} requires a value.`, { exitCode: 2 }); flags[key] = argv[++i]; }
    }
  }
  return { positional, flags };
}

function output(value) { process.stdout.write(`${JSON.stringify(value, null, 2)}\n`); }
function bool(value) { return value === true || value === 'true'; }

function versionParts(value) {
  return String(value || '').replace(/^v/, '').split('.').map((part) => Number.parseInt(part, 10) || 0);
}

function versionAtLeast(actualValue, minimumValue) {
  const actual = versionParts(actualValue);
  const minimum = versionParts(minimumValue);
  for (let index = 0; index < 3; index += 1) {
    if ((actual[index] || 0) > (minimum[index] || 0)) return true;
    if ((actual[index] || 0) < (minimum[index] || 0)) return false;
  }
  return true;
}

export function evaluateSycmContract(result, contract) {
  if (result?.status !== 0) return { ok: false, value: 'unavailable', reason: 'command-failed' };
  let payload;
  try { payload = JSON.parse(result.stdout); } catch { return { ok: false, value: 'invalid-response', reason: 'capabilities-json-invalid' }; }
  const versionOk = versionAtLeast(payload.version, contract.minimumVersion);
  const available = new Set((payload.capabilities || []).map((entry) => entry.id));
  const missingCapabilities = (contract.requiredCapabilities || []).filter((id) => !available.has(id));
  return { ok: versionOk && missingCapabilities.length === 0, value: payload.version || 'unknown', minimumVersion: contract.minimumVersion, versionOk, missingCapabilities };
}

function selectedNames(flags) {
  const manifest = readManifest();
  if (flags.all) return manifest.skills.map((item) => item.name);
  invariant(flags.name, 'MISSING_ARGUMENT', 'Pass --name <skill> or --all.', { exitCode: 2 });
  return [String(flags.name)];
}

function doctor() {
  const manifest = readManifest();
  const checks = [
    { id: 'node', ok: Number(process.versions.node.split('.')[0]) >= 20, value: process.version },
    { id: 'skill-count', ok: manifest.skills.length === 26, value: manifest.skills.length },
    { id: 'capabilities-file', ok: fs.existsSync(path.join(packageRoot, 'capabilities.json')) }
  ];
  for (const skill of manifest.skills) {
    const text = fs.readFileSync(path.join(packageRoot, skill.entry), 'utf8');
    const declared = text.match(/^---\r?\n[\s\S]*?^name:\s*([^\r\n]+)$/m)?.[1]?.trim();
    checks.push({ id: `skill:${skill.name}`, ok: declared === skill.name, value: declared || null, migrationStatus: skill.migrationStatus });
  }
  const sycm = childProcess.spawnSync(process.platform === 'win32' ? 'sycmcli.cmd' : 'sycmcli', ['capabilities', '--json'], { encoding: 'utf8', timeout: 15_000, env: { ...process.env, SYCMCLI_DISABLE_AUTO_UPDATE: '1' } });
  checks.push({ id: 'sycmcli', ...evaluateSycmContract(sycm, manifest.capabilityContracts.sycmcli) });
  const validationPending = manifest.skills.filter((item) => item.migrationStatus === 'implemented-awaiting-validation').map((item) => item.name);
  const implementationGaps = manifest.skills.filter((item) => !['implemented-local-validation', 'implemented-awaiting-validation'].includes(item.migrationStatus)).map((item) => item.name);
  const migrationGaps = [...implementationGaps, ...validationPending];
  return {
    ok: checks.every((item) => item.ok) && migrationGaps.length === 0,
    package: manifest.package,
    version: manifest.packageVersion,
    checks,
    implementationGaps,
    validationPending,
    migrationGaps,
    platformStatus: manifest.platforms
  };
}

async function handleSkill(action, flags) {
  const manifest = readManifest();
  if (action === 'list') {
    const skills = flags.group ? manifest.skills.filter((item) => item.group === flags.group) : manifest.skills;
    return output({ ok: true, package: manifest.package, packageVersion: manifest.packageVersion, skills });
  }
  if (action === 'source') {
    if (flags.name) return output({ ok: true, name: flags.name, source: skillSource(String(flags.name)) });
    return output({ ok: true, sources: manifest.skills.map((item) => ({ name: item.name, source: skillSource(item.name) })) });
  }
  if (action === 'status') return output({ ok: true, skills: skillStatus({ name: flags.name && String(flags.name), agent: flags.agent && String(flags.agent) }) });
  if (action === 'install' || action === 'update') {
    invariant(flags.agent, 'MISSING_ARGUMENT', '--agent is required.', { exitCode: 2 });
    const names = selectedNames(flags);
    const results = names.map((name) => action === 'install'
      ? installSkill(name, String(flags.agent), { adopt: bool(flags.adopt), mode: String(flags.mode || 'auto') })
      : updateSkill(name, String(flags.agent), { reconcile: bool(flags.reconcile), mode: String(flags.mode || 'auto') }));
    return output({ ok: true, action, results });
  }
  throw new CliError('UNKNOWN_COMMAND', `Unknown skill command "${action || ''}".`, { exitCode: 2 });
}

async function handleUpdate(action, flags) {
  if (action === 'status') return output({ ok: true, packageVersion: readManifest().packageVersion, ...readUpdateState() });
  if (action === 'check') return output({ ok: true, ...(await checkForUpdate({ force: true })) });
  if (action === 'install') return output({ ok: true, ...(await installUpdate()) });
  if (action === 'config') {
    const patch = {};
    if (flags['auto-update'] !== undefined) patch.autoUpdate = bool(flags['auto-update']);
    if (flags['interval-hours'] !== undefined) {
      const value = Number(flags['interval-hours']);
      invariant(Number.isInteger(value) && value >= 1 && value <= 720, 'INVALID_ARGUMENT', '--interval-hours must be an integer from 1 to 720.', { exitCode: 2 });
      patch.intervalHours = value;
    }
    invariant(Object.keys(patch).length, 'MISSING_ARGUMENT', 'Pass --auto-update or --interval-hours.', { exitCode: 2 });
    return output({ ok: true, ...writeUpdateState(patch) });
  }
  throw new CliError('UNKNOWN_COMMAND', `Unknown update command "${action || ''}".`, { exitCode: 2 });
}

export async function main(argv) {
  const { positional, flags } = parse(argv);
  const [command, action] = positional;
  if (flags.version) return output({ ok: true, package: readManifest().package, version: readManifest().packageVersion });
  if (flags.help || !command || ['help', '--help', '-h'].includes(command)) { process.stdout.write(HELP); return; }
  if (!['update', 'version'].includes(command)) await autoUpdateIfNeeded();
  if (command === 'version') return output({ ok: true, package: readManifest().package, version: readManifest().packageVersion });
  if (command === 'capabilities') return output({ ok: true, ...JSON.parse(fs.readFileSync(path.join(packageRoot, 'capabilities.json'), 'utf8')), skills: readManifest().skills });
  if (command === 'doctor') {
    const result = doctor();
    output(result);
    if (!result.ok) process.exitCode = 1;
    return;
  }
  if (command === 'skill') return handleSkill(action, flags);
  if (command === 'update') return handleUpdate(action, flags);
  throw new CliError('UNKNOWN_COMMAND', `Unknown command "${command}".`, { exitCode: 2, hint: HELP });
}
