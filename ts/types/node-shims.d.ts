// Minimal declarations so this package type-checks with no network. When @types/node is installed, delete this file and set "types": ["node"].
declare module "node:crypto" {
  export function randomInt(min: number, max: number): number;
  export function randomBytes(n: number): { toString(enc: string): string };
  export function createHmac(alg: string, key: string): { update(d: string): { digest(enc: string): string } };
  export function createHash(alg: string): { update(d: string): { digest(enc: string): string } };
}
declare module "node:fs" { export function readFileSync(path: string, enc: string): string; }
declare module "node:test" { export function test(name: string, fn: () => void | Promise<void>): void; }
declare module "node:assert/strict" { const assert: { equal(a: unknown, b: unknown, m?: string): void; notEqual(a: unknown, b: unknown, m?: string): void;
  ok(v: unknown, m?: string): void; throws(fn: () => unknown, m?: unknown): void; deepEqual(a: unknown, b: unknown, m?: string): void; }; export default assert; }
declare const process: { cwd(): string };
declare const Buffer: { from(s: string, enc?: string): { toString(enc: string): string } };
