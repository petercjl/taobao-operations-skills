export class CliError extends Error {
  constructor(code, message, options = {}) {
    super(message);
    this.name = 'CliError';
    this.code = code;
    this.exitCode = options.exitCode || 1;
    this.details = options.details;
    this.hint = options.hint;
  }
}

export function invariant(condition, code, message, options) {
  if (!condition) throw new CliError(code, message, options);
}
