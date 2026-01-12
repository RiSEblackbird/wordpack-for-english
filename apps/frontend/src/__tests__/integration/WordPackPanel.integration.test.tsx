import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { App } from '../../App';
import { AppProviders } from '../../main';

const isIntegrationTest = process.env.INTEGRATION_TEST === 'true';
const describeIfIntegration = isIntegrationTest ? describe : describe.skip;
const integrationBackendOrigin = process.env.BACKEND_PROXY_TARGET || 'http://127.0.0.1:8000';
const INTEGRATION_TIMEOUT_MS = 180000;

/**
 * 実HTTP を通すため、相対パスの fetch をバックエンド起点に変換する。
 * なぜ: Vitest 環境では /api/... がテストランナー自身に向いてしまうため。
 */
const installIntegrationFetch = (origin: string): (() => void) => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.startsWith('/')) {
      return originalFetch(new URL(url, origin).toString(), init);
    }
    return originalFetch(input, init);
  };
  return () => {
    globalThis.fetch = originalFetch;
  };
};

const renderApp = () =>
  render(
    <AppProviders googleClientId="">
      <App />
    </AppProviders>,
  );

const generateUniqueLemma = () => `integration-${Date.now()}`;

/**
 * バックエンドが起動している前提で WordPack 生成フローを確認する統合テスト。
 * なぜ: fetch -> API -> UI 反映までの連携をローカルで保証するため。
 */
describeIfIntegration('WordPackPanel integration (real backend)', () => {
  let uninstallFetch: (() => void) | null = null;

  beforeAll(() => {
    uninstallFetch = installIntegrationFetch(integrationBackendOrigin);
  });

  afterAll(() => {
    uninstallFetch?.();
    uninstallFetch = null;
  });

  it(
    'POST /api/word/pack の結果が画面に反映される',
    async () => {
      renderApp();

      const lemmaInput = await screen.findByLabelText('見出し語', {}, { timeout: INTEGRATION_TIMEOUT_MS });
      const generateButton = await screen.findByRole('button', { name: '生成' }, { timeout: INTEGRATION_TIMEOUT_MS });
      const lemma = generateUniqueLemma();

      await userEvent.clear(lemmaInput);
      await userEvent.type(lemmaInput, lemma);
      await userEvent.click(generateButton);

      const status = await screen.findByRole('status', {}, { timeout: INTEGRATION_TIMEOUT_MS });
      expect(status).toHaveTextContent('WordPack を生成しました');
      expect(await screen.findByRole('heading', { name: '概要' }, { timeout: INTEGRATION_TIMEOUT_MS })).toBeInTheDocument();
      expect(screen.getAllByText(lemma, { exact: false }).length).toBeGreaterThan(0);
    },
    INTEGRATION_TIMEOUT_MS,
  );
});
