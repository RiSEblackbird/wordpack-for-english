import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchJson } from '../../lib/fetcher';
import { WordPack, WordPackMessage } from '../../hooks/useWordPack';

export interface LemmaLookupResponseData {
  found: boolean;
  id?: string | null;
  lemma?: string | null;
  sense_title?: string | null;
}

export interface LemmaExplorerState {
  lemma: string;
  senseTitle?: string | null;
  wordPackId: string;
  status: 'loading' | 'ready' | 'error';
  data?: WordPack | null;
  errorMessage?: string | null;
  minimized: boolean;
  width: number;
}

interface UseLemmaExplorerOptions {
  apiBase: string;
  requestTimeoutMs?: number;
  onStatusMessage: (message: WordPackMessage) => void;
}

interface UseLemmaExplorerResult {
  explorer: LemmaExplorerState | null;
  explorerContent: React.ReactNode;
  openLemmaExplorer: (raw: string) => Promise<void>;
  closeLemmaExplorer: () => void;
  minimizeLemmaExplorer: () => void;
  restoreLemmaExplorer: () => void;
  resizeLemmaExplorer: (nextWidth: number) => void;
  lookupLemmaMetadata: (lemmaText: string) => Promise<LemmaLookupResponseData>;
  invalidateLemmaCache: (lemmaText: string) => void;
}

const defaultCategories: (keyof WordPack['examples'])[] = ['Dev', 'CS', 'LLM', 'Business', 'Common'];

const normalizeWordPack = (wp: WordPack): WordPack => ({
  ...wp,
  checked_only_count: wp.checked_only_count ?? 0,
  learned_count: wp.learned_count ?? 0,
});

/**
 * WordPack概要のミニウィンドウを管理するカスタムフック。
 * - 状態遷移: 初期(null) → loading → ready|error。
 * - イベント: onLemmaOpenでAPI検索→取得成功ならready、失敗時はerrorへ遷移。
 * - 副作用: メタデータキャッシュはウィンドウ単位で共有し、fetch回数を抑える。
 */
export const useLemmaExplorer = ({ apiBase, requestTimeoutMs, onStatusMessage }: UseLemmaExplorerOptions): UseLemmaExplorerResult => {
  const [explorer, setExplorer] = useState<LemmaExplorerState | null>(null);
  const lemmaCacheRef = useRef<Map<string, LemmaLookupResponseData>>(new Map());
  // アンマウント後にsetStateしないためのフラグ。リクエスト完了前にウィンドウが閉じられても安全に無視できる。
  const mountedRef = useRef(true);

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  /**
   * window単位で共有されるキャッシュを返却し、未作成時は初期化する。
   */
  const ensureLemmaCache = useCallback((): Map<string, LemmaLookupResponseData> => {
    if (typeof window === 'undefined') {
      return lemmaCacheRef.current;
    }
    const w = window as typeof window & { __lemmaCache?: Map<string, LemmaLookupResponseData> };
    if (!w.__lemmaCache) {
      w.__lemmaCache = lemmaCacheRef.current;
    }
    lemmaCacheRef.current = w.__lemmaCache;
    return lemmaCacheRef.current;
  }, []);

  /**
   * API経由でLemma情報を取得し、結果をキャッシュへ保存して返す。
   */
  const lookupLemmaMetadata = useCallback(
    async (lemmaText: string): Promise<LemmaLookupResponseData> => {
      const target = lemmaText.trim();
      if (!target) return { found: false };
      const cache = ensureLemmaCache();
      const key = `lemma:${target.toLowerCase()}`;
      const cached = cache.get(key);
      if (cached) return cached;

      let info: LemmaLookupResponseData = { found: false };
      try {
        info = await fetchJson<LemmaLookupResponseData>(`${apiBase}/word/lemma/${encodeURIComponent(target)}`, {
          timeoutMs: requestTimeoutMs,
        });
      } catch {
        info = { found: false };
      }
      // 取得結果は存在有無を含めてキャッシュし、短時間で同じ語義を開いた際のリクエストを省く。
      cache.set(key, info);
      return info;
    },
    [apiBase, ensureLemmaCache, requestTimeoutMs],
  );

  /**
   * LemmaExplorerを開き、WordPack概要を取得する。成功時はready、失敗時はerrorへ遷移する。
   */
  const openLemmaExplorer = useCallback(
    async (raw: string) => {
      const target = raw.trim();
      if (!target) return;
      const info = await lookupLemmaMetadata(target);
      if (!info || !info.found || !info.id) {
        onStatusMessage({ kind: 'alert', text: `「${target}」のWordPackは保存されていません` });
        return;
      }
      if (!mountedRef.current) return;
      setExplorer((prev) => ({
        lemma: info!.lemma || target,
        senseTitle: info!.sense_title ?? null,
        wordPackId: info!.id!,
        status: 'loading',
        // 同じWordPackを再度開いた場合は前回データを再利用し、読み込み中も内容を見せる。
        data: prev && prev.wordPackId === info!.id ? prev.data : null,
        errorMessage: null,
        minimized: false,
        width: prev?.width ?? 360,
      }));
      try {
        const detail = await fetchJson<WordPack>(`${apiBase}/word/packs/${info.id}`, {
          timeoutMs: requestTimeoutMs,
        });
        if (!mountedRef.current) return;
        setExplorer((prev) => {
          if (!prev || prev.wordPackId !== info!.id) return prev;
          return {
            ...prev,
            status: 'ready',
            senseTitle: (detail.sense_title || prev.senseTitle) ?? null,
            data: normalizeWordPack(detail),
            errorMessage: null,
          };
        });
      } catch (error) {
        if (!mountedRef.current) return;
        setExplorer((prev) => {
          if (!prev || prev.wordPackId !== info!.id) return prev;
          return {
            ...prev,
            status: 'error',
            errorMessage: error instanceof Error ? error.message : null,
          };
        });
      }
    },
    [apiBase, lookupLemmaMetadata, onStatusMessage, requestTimeoutMs],
  );

  /**
   * 画面上からウィンドウを閉じて状態を破棄する。
   */
  const closeLemmaExplorer = useCallback(() => setExplorer(null), []);

  /**
   * 内容を保持したまま最小化状態へ遷移する。
   */
  const minimizeLemmaExplorer = useCallback(
    () => setExplorer((prev) => (prev ? { ...prev, minimized: true } : prev)),
    [],
  );

  /**
   * 最小化から元のサイズ表示へ復元する。
   */
  const restoreLemmaExplorer = useCallback(
    () => setExplorer((prev) => (prev ? { ...prev, minimized: false } : prev)),
    [],
  );

  /**
   * ドラッグ操作などから横幅を更新する。
   */
  const resizeLemmaExplorer = useCallback(
    (nextWidth: number) => setExplorer((prev) => (prev ? { ...prev, width: nextWidth } : prev)),
    [],
  );

  /**
   * 指定したLemmaのキャッシュを削除し、次回取得を強制する。
   */
  const invalidateLemmaCache = useCallback(
    (lemmaText: string) => {
      const cache = ensureLemmaCache();
      cache.delete(`lemma:${lemmaText.trim().toLowerCase()}`);
    },
    [ensureLemmaCache],
  );

  /**
   * 取得済みのWordPack概要から表示用メタ情報を構築する。
   */
  const explorerContent = useMemo(() => {
    if (!explorer || !explorer.data) return null;
    const pack = explorer.data;
    const senses = pack.senses?.slice(0, 3) ?? [];
    // 例文数はカテゴリ順で固定表示し、実体がなくても0件として扱う。
    const exampleSummary = defaultCategories.map((category) => ({
      category,
      count: pack.examples?.[category]?.length ?? 0,
    }));
    return (
      <div className="lemma-window-meta">
        <div>
          <strong>語義タイトル</strong>
          <div>{pack.sense_title || '-'}</div>
        </div>
        <div>
          <strong>語義（上位3件）</strong>
          {senses.length ? (
            <ol>
              {senses.map((sense) => (
                <li key={sense.id}>
                  <span>{sense.gloss_ja}</span>
                  {sense.definition_ja ? (
                    <div style={{ fontSize: '0.85em', color: '#555' }}>{sense.definition_ja}</div>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : (
            <p>語義情報なし</p>
          )}
        </div>
        <div>
          <strong>例文数</strong>
          <ul>
            {exampleSummary.map(({ category, count }) => (
              <li key={category}>{category}: {count}件</li>
            ))}
          </ul>
        </div>
        {pack.study_card ? (
          <div>
            <strong>学習カード</strong>
            <p>{pack.study_card}</p>
          </div>
        ) : null}
        {pack.confidence ? (
          <div>
            <strong>信頼度</strong>
            <span>{pack.confidence}</span>
          </div>
        ) : null}
      </div>
    );
  }, [explorer]);

  return {
    explorer,
    explorerContent,
    openLemmaExplorer,
    closeLemmaExplorer,
    minimizeLemmaExplorer,
    restoreLemmaExplorer,
    resizeLemmaExplorer,
    lookupLemmaMetadata,
    invalidateLemmaCache,
  };
};

