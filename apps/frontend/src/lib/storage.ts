/**
 * sessionStorage から JSON を読み取り、失敗時はデフォルト値を返すヘルパー。
 * localStorage とは異なりセッション単位でのみ状態を保持するため、
 * UI 状態の復元で利用する。
 */
export function loadSessionState<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') {
    return fallback;
  }
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    const parsed = JSON.parse(raw);
    return { ...fallback, ...parsed };
  } catch {
    return fallback;
  }
}

/**
 * sessionStorage に UI 状態を保存する際の例外吸収ロジックを共通化。
 * 保存に失敗してもアプリ自体が壊れないように try/catch を一元管理する。
 */
export function saveSessionState<T>(key: string, value: T) {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Safari プライベートモードなどでは書き込みが失敗することがあるため無視する。
  }
}
