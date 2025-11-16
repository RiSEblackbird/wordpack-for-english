#!/usr/bin/env node
import { promises as fs } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

// Copies apps/frontend/.env.example to apps/frontend/.env when the latter is
// missing so newcomers can bootstrap the Vite environment with one command.

// This helper resolves repository-relative paths even when npm runs the script
// from a nested working directory (e.g., via workspaces or prefix flags).
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, '..', 'apps', 'frontend');
const templatePath = path.join(frontendDir, '.env.example');
const envPath = path.join(frontendDir, '.env');

// fileExists inspects the given path and returns true when it can be read.
async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

// main orchestrates the copy flow and keeps log messages localized in Japanese
// so contributors immediately understand what happened.
async function main() {
  const hasEnv = await fileExists(envPath);
  if (hasEnv) {
    console.log(`[prepare:frontend-env] ${path.relative(process.cwd(), envPath)} は既に存在するため処理をスキップしました。`);
    return;
  }

  const hasTemplate = await fileExists(templatePath);
  if (!hasTemplate) {
    throw new Error(`テンプレート ${path.relative(process.cwd(), templatePath)} が見つかりません。先に apps/frontend/.env.example を作成してください。`);
  }

  await fs.copyFile(templatePath, envPath);
  console.log(`[prepare:frontend-env] ${path.relative(process.cwd(), templatePath)} から ${path.relative(process.cwd(), envPath)} へコピーしました。`);
}

main().catch((error) => {
  console.error('[prepare:frontend-env] 環境変数テンプレートのコピーに失敗しました:', error);
  process.exitCode = 1;
});
