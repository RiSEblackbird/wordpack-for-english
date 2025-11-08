#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import { once } from 'node:events';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import process from 'node:process';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../../..');
const backendDir = path.join(repoRoot, 'apps', 'backend');
const frontendDir = path.join(repoRoot, 'apps', 'frontend');
const dataDir = path.join(repoRoot, '.data');
const sqlitePath = path.join(dataDir, 'ui-smoke.sqlite3');
const chromeExecutable = process.env.CHROME_EXECUTABLE || '/usr/bin/google-chrome-stable';
const nodeBinDir = path.dirname(process.execPath);
const npmBin = path.join(nodeBinDir, 'npm');
const packageDir = __dirname;

const processes = [];
let chromeUserDataDir;
let client;
let transport;

function logStep(message) {
  const timestamp = new Date().toISOString();
  console.log(`ℹ️ [${timestamp}] ${message}`);
}

function prefixLog(name, line, stream = 'stdout') {
  if (!line) return;
  const trimmed = line.toString().trimEnd();
  if (!trimmed) return;
  const lines = trimmed.split(/\r?\n/);
  for (const l of lines) {
    if (!l) continue;
    const prefix = `[${name}]`;
    if (stream === 'stderr') {
      console.error(`${prefix} ${l}`);
    } else {
      console.log(`${prefix} ${l}`);
    }
  }
}

function spawnWithLogs(name, command, args, options = {}) {
  const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'], ...options });
  processes.push({ name, child });
  child.stdout.setEncoding('utf8');
  child.stderr.setEncoding('utf8');
  child.stdout.on('data', (chunk) => prefixLog(name, chunk, 'stdout'));
  child.stderr.on('data', (chunk) => prefixLog(name, chunk, 'stderr'));
  child.on('exit', (code, signal) => {
    const tag = code !== null ? `code=${code}` : `signal=${signal}`;
    console.log(`[${name}] exited (${tag})`);
  });
  return child;
}

async function terminate(child, name) {
  if (!child) return;
  if (child.exitCode !== null || child.signalCode) return;
  try {
    child.kill('SIGTERM');
  } catch {
    return;
  }
  const timeout = delay(2000);
  try {
    await Promise.race([once(child, 'exit'), timeout]);
  } catch {}
  if (child.exitCode === null && !child.killed) {
    try {
      child.kill('SIGKILL');
    } catch {}
  }
}

async function waitForHttp(url, { timeoutMs = 30000, validate } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!validate || (await validate(res))) {
        if (res.body) {
          try { await res.arrayBuffer(); } catch {}
        }
        return;
      }
    } catch {}
    await delay(500);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function ensure(cond, message) {
  if (!cond) {
    throw new Error(message);
  }
}

async function waitForSelector(clientInstance, selector, { timeoutMs = 10000 } = {}) {
  const start = Date.now();
  const serializedSelector = JSON.stringify(selector);
  while (Date.now() - start < timeoutMs) {
    const exists = await callEvaluate(
      clientInstance,
      `() => Boolean(document.querySelector(${serializedSelector}))`
    );
    if (exists === true) {
      return;
    }
    await delay(250);
  }
  throw new Error(`Timed out waiting for selector: ${selector}`);
}

function parseEvaluateResultContent(res) {
  if (Array.isArray(res.content)) {
    for (const part of res.content) {
      if (typeof part?.json !== 'undefined') {
        return part.json;
      }
    }

    const combinedText = res.content
      .map((part) => (typeof part?.text === 'string' ? part.text : ''))
      .filter(Boolean)
      .join('\n');

    if (combinedText) {
      const match = combinedText.match(/```json\s*([\s\S]+?)\s*```/);
      ensure(match && match[1], 'JSON block not found in evaluate_script response');
      return JSON.parse(match[1]);
    }
  }

  throw new Error('evaluate_script response did not include JSON payload');
}

async function callEvaluate(clientInstance, fn) {
  const res = await clientInstance.callTool({ name: 'evaluate_script', arguments: { function: fn } });
  ensure(!res.isError, `evaluate_script failed: ${res.content?.[0]?.text || ''}`);
  return parseEvaluateResultContent(res);
}

async function seedWordPack() {
  const response = await fetch('http://127.0.0.1:8000/api/word/packs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lemma: 'automation' }),
  });
  ensure(response.ok, `Failed to seed WordPack (status ${response.status})`);
  const data = await response.json();
  ensure(typeof data?.id === 'string', 'Unexpected response when creating WordPack');
  return data.id;
}

async function setupBackend(env) {
  logStep('バックエンド (uvicorn) の起動を開始します');
  await fs.mkdir(dataDir, { recursive: true });
  await fs.rm(sqlitePath, { force: true });
  const backendEnv = {
    ...env,
    PYTHONPATH: backendDir,
    STRICT_MODE: 'false',
    OPENAI_API_KEY: env.OPENAI_API_KEY || 'test-key',
    WORDPACK_DB_PATH: sqlitePath,
    LANGFUSE_ENABLED: 'false',
    DISABLE_SESSION_AUTH: 'true',
  };
  spawnWithLogs('backend', 'python', ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000', '--log-level', 'warning'], {
    cwd: repoRoot,
    env: backendEnv,
  });
  await waitForHttp('http://127.0.0.1:8000/healthz', {
    timeoutMs: 45000,
    validate: (res) => Promise.resolve(res.ok),
  });
  logStep('バックエンドのヘルスチェックに成功しました');
}

async function setupFrontend(env) {
  logStep('フロントエンド (Vite) の開発サーバーを起動します');
  const frontendEnv = {
    ...env,
    BACKEND_PROXY_TARGET: 'http://127.0.0.1:8000',
    BROWSER: 'none',
    NODE_ENV: 'development',
  };
  spawnWithLogs('frontend', npmBin, ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173', '--strictPort'], {
    cwd: frontendDir,
    env: frontendEnv,
  });
  await waitForHttp('http://127.0.0.1:5173', {
    timeoutMs: 60000,
    validate: (res) => Promise.resolve(res.status === 200),
  });
  await delay(1500);
  logStep('フロントエンドの起動が完了しました');
}

async function launchChrome(env) {
  try {
    await fs.access(chromeExecutable);
  } catch {
    throw new Error(`Chrome executable not found at ${chromeExecutable}. Set CHROME_EXECUTABLE env var to override.`);
  }
  logStep(`Headless Chrome を起動します (executable: ${chromeExecutable})`);
  chromeUserDataDir = await fs.mkdtemp(path.join(os.tmpdir(), 'wordpack-chrome-'));
  const args = [
    '--headless=new',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--window-size=1280,720',
    '--remote-debugging-port=9222',
    `--user-data-dir=${chromeUserDataDir}`,
  ];
  spawnWithLogs('chrome', chromeExecutable, args, {
    env,
  });
  await waitForHttp('http://127.0.0.1:9222/json/version', {
    timeoutMs: 20000,
    validate: (res) => Promise.resolve(res.ok),
  });
  await delay(500);
  logStep('Chrome DevTools のリモートデバッグエンドポイントに接続できました');
}

async function runSmokeAssertions(wordPackId) {
  logStep('chrome-devtools-mcp クライアントとの接続を開始します');
  const cliEntry = path.resolve(packageDir, 'node_modules/chrome-devtools-mcp/build/src/index.js');
  transport = new StdioClientTransport({
    command: process.execPath,
    args: [cliEntry, '--browserUrl', 'http://127.0.0.1:9222'],
    env: baseEnv,
    cwd: packageDir,
  });
  client = new Client({ name: 'wordpack-ui-smoke', version: '1.0.0' });
  await client.connect(transport);

  logStep('WordPack フロントエンドへのナビゲーションを開始します');
  await client.callTool({ name: 'navigate_page', arguments: { url: 'http://127.0.0.1:5173' } });
  logStep('"WordPack" 見出しの表示を待機しています');
  const waitMain = await client.callTool({ name: 'wait_for', arguments: { text: 'WordPack', timeout: 20000 } });
  ensure(!waitMain.isError, 'Failed to locate WordPack heading');

  logStep('トップ画面のスナップショットを取得します');
  const snapshot = await client.callTool({ name: 'take_snapshot', arguments: {} });
  const snapshotText = snapshot.content?.[0]?.text || '';
  const cardLemmas = await callEvaluate(
    client,
    `() => Array.from(document.querySelectorAll('.wp-card-title'), el => el.textContent.trim()).filter(Boolean)`
  );
  ensure(
    Array.isArray(cardLemmas) && cardLemmas.includes('automation'),
    'WordPack card did not render expected lemma'
  );
  ensure(
    snapshotText.includes(wordPackId.slice(3, 10)) || snapshotText.includes('例文未生成') || snapshotText.includes('automation'),
    'WordPack card snapshot missing expected metadata'
  );

  logStep('ナビゲーションタブのラベルを検証します');
  const navItems = await callEvaluate(
    client,
    '() => Array.from(document.querySelectorAll("nav[aria-label=\\"主要メニュー\\"] button"), el => el.textContent.trim()).filter(Boolean)'
  );
  ensure(Array.isArray(navItems), 'Navigation items response malformed');
  for (const label of ['WordPack', '文章インポート', '例文一覧', '設定']) {
    ensure(navItems.includes(label), `Navigation label "${label}" not found`);
  }

  logStep('ハンバーガーボタンの初期配置と状態を確認します');
  const hamburgerInfo = await callEvaluate(
    client,
    `() => {
      const btn = document.querySelector(".hamburger-toggle");
      if (!btn) return { found: false };
      const rect = btn.getBoundingClientRect();
      return {
        found: true,
        left: Math.round(rect.left),
        top: Math.round(rect.top),
        ariaExpanded: btn.getAttribute("aria-expanded"),
        ariaControls: btn.getAttribute("aria-controls"),
        ariaLabel: btn.getAttribute("aria-label"),
      };
    }`
  );
  ensure(hamburgerInfo?.found, 'ハンバーガーボタンが見つかりません');
  ensure(hamburgerInfo.left === 0 && hamburgerInfo.top === 0, 'ハンバーガーボタンが画面左上に固定されていません');
  ensure(hamburgerInfo.ariaExpanded === 'false', '初期状態でサイドバーが展開されています');
  ensure(hamburgerInfo.ariaLabel === 'メニューを開く', 'ハンバーガーボタンのラベルが想定外です');

  logStep('ハンバーガーボタンでサイドバーを開きます');
  const sidebarToggleResult = await callEvaluate(
    client,
    `() => {
      const btn = document.querySelector(".hamburger-toggle");
      if (!btn) return { clicked: false };
      btn.click();
      return { clicked: true, ariaExpanded: btn.getAttribute("aria-expanded") };
    }`
  );
  ensure(sidebarToggleResult?.clicked, 'サイドバーのトグルに失敗しました');
  ensure(sidebarToggleResult.ariaExpanded === 'true', 'サイドバーが展開状態になっていません');

  const sidebarState = await callEvaluate(
    client,
    `() => {
      const sidebar = document.querySelector(".sidebar");
      const appShell = document.querySelector(".app-shell");
      if (!sidebar || !appShell) return null;
      const rect = sidebar.getBoundingClientRect();
      return {
        ariaHidden: sidebar.getAttribute("aria-hidden"),
        widthStyle: sidebar.style.width,
        rectLeft: Math.round(rect.left),
        rectWidth: Math.round(rect.width),
        shellOpen: appShell.classList.contains("sidebar-open"),
      };
    }`
  );
  ensure(sidebarState, 'サイドバーの状態を取得できません');
  ensure(sidebarState.ariaHidden === 'false', 'サイドバーが非表示のままです');
  ensure(sidebarState.shellOpen, 'app-shell に sidebar-open クラスが付与されていません');
  ensure(sidebarState.rectLeft === 0, 'サイドバーの左端が 0px ではありません');
  ensure(sidebarState.rectWidth >= 270, `サイドバーの幅が想定よりも狭いです (${sidebarState.rectWidth}px)`);

  logStep('設定タブへ切り替えて初期設定値を確認します');
  const clickedSettings = await callEvaluate(
    client,
    `() => {
      const btn = Array.from(document.querySelectorAll("nav[aria-label=\\"主要メニュー\\"] button"), el => el.textContent?.trim() === "設定" ? el : null).find(Boolean);
      if (!btn) return { clicked: false };
      btn.click();
      return { clicked: true };
    }`
  );
  ensure(clickedSettings?.clicked, 'Failed to switch to 設定 tab');
  logStep('設定タブのコンテンツ表示を待機しています');
  const waitSettings = await client.callTool({ name: 'wait_for', arguments: { text: 'カラーテーマ', timeout: 10000 } });
  ensure(!waitSettings.isError, '設定パネルが表示されませんでした');
  const temperatureValue = await callEvaluate(client, '() => document.querySelector("input[aria-describedby=\\"temperature-help\\"]")?.value ?? null');
  ensure(temperatureValue === '0.6', `Unexpected temperature default: ${temperatureValue}`);

  logStep('例文一覧タブへ切り替えて初期ビューを確認します');
  const clickedExamples = await callEvaluate(
    client,
    `() => {
      const btn = Array.from(document.querySelectorAll("nav[aria-label=\\"主要メニュー\\"] button"), el => el.textContent?.trim() === "例文一覧" ? el : null).find(Boolean);
      if (!btn) return { clicked: false };
      btn.click();
      return { clicked: true };
    }`
  );
  ensure(clickedExamples?.clicked, 'Failed to switch to 例文一覧 tab');
  logStep('例文一覧のヘッディング表示を待機しています');
  const waitExamples = await client.callTool({ name: 'wait_for', arguments: { text: '例文一覧', timeout: 10000 } });
  ensure(!waitExamples.isError, '例文一覧の見出しが表示されませんでした');
  const exampleViewMode = await callEvaluate(client, '() => document.querySelector(".ex-list-container")?.getAttribute("data-view") || null');
  ensure(exampleViewMode === 'card', `例文一覧の初期ビューが想定外です (data-view=${exampleViewMode})`);

  const sidebarStateAfterExample = await callEvaluate(
    client,
    `() => {
      const sidebar = document.querySelector(".sidebar");
      if (!sidebar) return null;
      return { ariaHidden: sidebar.getAttribute("aria-hidden") };
    }`
  );
  ensure(sidebarStateAfterExample?.ariaHidden === 'false', 'タブ切り替え後にサイドバーが閉じてしまいました');

  logStep('WordPack タブへ戻ってカード一覧を検証します');
  const clickedWordPack = await callEvaluate(
    client,
    `() => {
      const btn = Array.from(document.querySelectorAll("nav[aria-label=\\"主要メニュー\\"] button"), el => el.textContent?.trim() === "WordPack" ? el : null).find(Boolean);
      if (!btn) return { clicked: false };
      btn.click();
      return { clicked: true };
    }`
  );
  ensure(clickedWordPack?.clicked, 'WordPack タブへの戻りに失敗しました');
  await waitForSelector(client, '[data-testid="wp-card"]', { timeoutMs: 15000 });
  const wordPackCardInfo = await callEvaluate(
    client,
    `() => {
      const cards = Array.from(document.querySelectorAll("[data-testid=\\"wp-card\\"]"));
      const first = cards[0];
      return {
        count: cards.length,
        firstLemma: first?.querySelector(".wp-card-title")?.textContent?.trim() || null,
        firstHasSense: Boolean(first?.querySelector("[data-testid=\\"wp-card-sense-title\\"]")),
      };
    }`
  );
  ensure(wordPackCardInfo?.count >= 1, 'WordPack カードが 1 件も描画されていません');
  ensure(
    typeof wordPackCardInfo.firstLemma === 'string' && wordPackCardInfo.firstLemma.toLowerCase().includes('automation'),
    `WordPack カードのレマが想定外です (${wordPackCardInfo.firstLemma})`
  );
  const expectedLemma =
    typeof wordPackCardInfo.firstLemma === 'string' ? wordPackCardInfo.firstLemma : null;

  logStep('WordPack カードのプレビューを開きます');
  const openedPreview = await callEvaluate(
    client,
    `() => {
      const card = document.querySelector("[data-testid=\\"wp-card\\"]");
      if (!card) return { clicked: false };
      card.click();
      return { clicked: true };
    }`
  );
  ensure(openedPreview?.clicked, 'WordPack カードのクリックに失敗しました');

  await waitForSelector(client, '[role="dialog"][aria-label="WordPack プレビュー"]', { timeoutMs: 15000 });
  const modalInfo = await callEvaluate(
    client,
    `() => {
      const dialog = document.querySelector("[role=\\"dialog\\"][aria-label=\\"WordPack プレビュー\\"]");
      if (!dialog) return null;
      return {
        hasContent: Boolean(dialog.querySelector("[data-testid=\\"modal-wordpack-content\\"]")),
        hasLemmaInput: Boolean(dialog.querySelector("#wordpack-lemma-input")),
        lemmaText: dialog.querySelector(".wp-modal-lemma strong")?.textContent?.trim() || null,
        closeButton: dialog.querySelector("button[aria-label=\\"閉じる\\"]")?.textContent?.trim() || null,
      };
    }`
  );
  ensure(modalInfo?.hasContent, 'WordPack プレビューの内容が表示されていません');
  ensure(
    modalInfo?.hasLemmaInput || typeof modalInfo?.lemmaText === 'string',
    'WordPack プレビューで見出し語が表示されていません'
  );
  if (typeof modalInfo?.lemmaText === 'string' && typeof expectedLemma === 'string') {
    ensure(
      modalInfo.lemmaText.toLowerCase().includes(expectedLemma.toLowerCase()),
      `モーダルの見出し語が一覧と一致しません (${modalInfo.lemmaText})`
    );
  }
  ensure(modalInfo?.closeButton === '閉じる', 'モーダルの閉じるボタン表記が想定外です');

  logStep('WordPack プレビューのモーダルを閉じます');
  const closedPreview = await callEvaluate(
    client,
    `() => {
      const btn = document.querySelector("[role=\\"dialog\\"][aria-label=\\"WordPack プレビュー\\"] button[aria-label=\\"閉じる\\"]");
      if (!btn) return { clicked: false };
      btn.click();
      return { clicked: true };
    }`
  );
  ensure(closedPreview?.clicked, 'WordPack プレビューを閉じられませんでした');
  {
    let stillOpen = true;
    for (let i = 0; i < 20; i += 1) {
      const modalVisible = await callEvaluate(
        client,
        `() => Boolean(document.querySelector("[role=\\"dialog\\"][aria-label=\\"WordPack プレビュー\\"]"))`
      );
      if (!modalVisible) {
        stillOpen = false;
        break;
      }
      await delay(200);
    }
    ensure(!stillOpen, 'WordPack プレビューのモーダルが閉じませんでした');
  }

  logStep('コンソールログを収集します');
  const consoleRes = await client.callTool({ name: 'list_console_messages', arguments: {} });
  ensure(!consoleRes.isError, 'コンソールログの取得に失敗しました');
  const consoleText = consoleRes.content?.[0]?.text || '';
  ensure(!consoleText.includes('Error>'), `コンソールにエラーが出力されています\n${consoleText}`);
  ensure(!consoleText.includes('Exception>'), `コンソールに例外が出力されています\n${consoleText}`);

  console.log('✅ UI smoke test completed successfully');
  await client.close();
  await transport.close();
  client = undefined;
  transport = undefined;
}

const baseEnv = {
  ...process.env,
  PATH: `${nodeBinDir}:${process.env.PATH}`,
};

async function main() {
  try {
    await setupBackend(baseEnv);
    logStep('WordPack のシードデータを投入します');
    const wordPackId = await seedWordPack();
    logStep(`Seeded WordPack: ${wordPackId}`);
    await setupFrontend(baseEnv);
    await launchChrome(baseEnv);
    await runSmokeAssertions(wordPackId);
  } catch (err) {
    console.error('❌ UI smoke test failed:', err instanceof Error ? err.stack || err.message : err);
    process.exitCode = 1;
  } finally {
    if (client) {
      try { await client.close(); } catch {}
      client = undefined;
    }
    if (transport) {
      try { await transport.close(); } catch {}
      transport = undefined;
    }
    for (const { child, name } of processes.reverse()) {
      await terminate(child, name);
    }
    if (chromeUserDataDir) {
      try { await fs.rm(chromeUserDataDir, { recursive: true, force: true }); } catch {}
    }
  }
}

await main();
process.exit(process.exitCode ?? 0);
