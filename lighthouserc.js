// Lighthouse CI の測定対象 URL を環境変数から必須入力にして、誤った測定を防ぐ。
const targetUrl = process.env.WORDPACK_LIST_URL;
if (!targetUrl) {
  throw new Error("WORDPACK_LIST_URL が未設定です。Lighthouse CI の計測対象 URL を指定してください。");
}

const lighthouseConfig = {
  ci: {
    collect: {
      url: [targetUrl],
      numberOfRuns: 3,
      settings: {
        preset: "desktop",
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["error", { minScore: 0.8 }],
        "categories:best-practices": ["error", { minScore: 0.9 }],
        "categories:seo": ["error", { minScore: 0.9 }],
        "categories:pwa": ["error", { minScore: 0.6 }],
      },
    },
    upload: {
      target: "github",
      token: process.env.LHCI_GITHUB_APP_TOKEN,
    },
  },
};

export default lighthouseConfig;
