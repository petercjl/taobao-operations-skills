import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export const MANAGED_FILE = '.taobao-operations-skills-managed.json';
export const HOST_METADATA_FILES = new Set(['.skill-ui.json', '.sealseek-skill.json', 'ui.json']);

export function treeFiles(root) {
  const result = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (entry.name === MANAGED_FILE || HOST_METADATA_FILES.has(entry.name)) continue;
      const absolute = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(absolute);
      else if (entry.isFile()) result.push(path.relative(root, absolute).split(path.sep).join('/'));
    }
  };
  walk(root);
  return result;
}

export function digestTree(root, files = treeFiles(root)) {
  const hash = crypto.createHash('sha256');
  for (const relative of [...files].sort()) {
    const absolute = path.join(root, ...relative.split('/'));
    if (!fs.existsSync(absolute)) return null;
    hash.update(relative);
    hash.update('\0');
    hash.update(fs.readFileSync(absolute));
    hash.update('\0');
  }
  return hash.digest('hex');
}
