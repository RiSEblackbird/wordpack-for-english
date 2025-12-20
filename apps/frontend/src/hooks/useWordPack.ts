import { useCallback, useEffect, useRef, useState } from 'react';
import { useNotifications } from '../NotificationsContext';
import { useSettings } from '../SettingsContext';
import { ApiError, fetchJson } from '../lib/fetcher';
import { composeModelRequestFields, enqueueRegenerateWordPack, fetchRegenerateJobStatus, regenerateWordPackRequest } from '../lib/wordpack';

export interface Pronunciation {
  ipa_GA?: string | null;
  ipa_RP?: string | null;
  syllables?: number | null;
  stress_index?: number | null;
  linking_notes: string[];
}

export interface Sense {
  id: string;
  gloss_ja: string;
  definition_ja?: string | null;
  nuances_ja?: string | null;
  term_overview_ja?: string | null;
  term_core_ja?: string | null;
  patterns: string[];
  synonyms?: string[];
  antonyms?: string[];
  register?: string | null;
  notes_ja?: string | null;
}

interface CollocationLists { verb_object: string[]; adj_noun: string[]; prep_noun: string[] }
interface Collocations { general: CollocationLists; academic: CollocationLists }

interface ContrastItem { with: string; diff_ja: string }

export interface ExampleItem { en: string; ja: string; grammar_ja?: string; llm_model?: string; llm_params?: string }
export interface Examples { Dev: ExampleItem[]; CS: ExampleItem[]; LLM: ExampleItem[]; Business: ExampleItem[]; Common: ExampleItem[] }

interface Etymology { note: string; confidence: 'low' | 'medium' | 'high' }

interface Citation { text: string; meta?: Record<string, any> }

export interface WordPack {
  lemma: string;
  sense_title: string;
  pronunciation: Pronunciation;
  senses: Sense[];
  collocations: Collocations;
  contrast: ContrastItem[];
  examples: Examples;
  etymology: Etymology;
  study_card: string;
  citations: Citation[];
  confidence: 'low' | 'medium' | 'high';
  checked_only_count?: number;
  learned_count?: number;
}

export type WordPackMessage = { kind: 'status' | 'alert'; text: string } | null;

interface UseWordPackOptions {
  model: string;
  onWordPackGenerated?: (wordPackId: string | null) => void;
  onStudyProgressRecorded?: (payload: { wordPackId: string; checked_only_count: number; learned_count: number }) => void;
}

interface AiMeta {
  model?: string | null;
  params?: string | null;
}

interface UseWordPackResult {
  aiMeta: AiMeta | null;
  currentWordPackId: string | null;
  data: WordPack | null;
  loading: boolean;
  progressUpdating: boolean;
  message: WordPackMessage;
  clearMessage: () => void;
  setStatusMessage: (next: WordPackMessage) => void;
  generateWordPack: (lemma: string) => Promise<void>;
  createEmptyWordPack: (lemma: string) => Promise<void>;
  loadWordPack: (wordPackId: string) => Promise<void>;
  regenerateWordPack: (wordPackId: string, lemma: string) => Promise<void>;
  recordStudyProgress: (kind: 'checked' | 'learned') => Promise<void>;
}

/**
 * WordPack取得・生成関連のAPI呼び出しと通知更新をまとめ、UIから責務を分離するカスタムフック。
 * UIは本フックが返す状態と関数を用い、描画と入力ハンドリングに専念させる。
 */
export const useWordPack = ({
  model,
  onWordPackGenerated,
  onStudyProgressRecorded,
}: UseWordPackOptions): UseWordPackResult => {
  const { settings } = useSettings();
  const { add: addNotification, update: updateNotification } = useNotifications();
  const { apiBase, pronunciationEnabled, regenerateScope, requestTimeoutMs, temperature, reasoningEffort, textVerbosity } = settings;

  const [data, setData] = useState<WordPack | null>(null);
  const [currentWordPackId, setCurrentWordPackId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<WordPackMessage>(null);
  const [aiMeta, setAiMeta] = useState<AiMeta | null>(null);
  const [progressUpdating, setProgressUpdating] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  const clearMessage = useCallback(() => setMessage(null), []);
  const setStatusMessage = useCallback((next: WordPackMessage) => setMessage(next), []);

  const normalizeWordPack = useCallback(
    (wp: WordPack): WordPack => ({
      ...wp,
      checked_only_count: wp.checked_only_count ?? 0,
      learned_count: wp.learned_count ?? 0,
    }),
    [],
  );

  const applyModelRequestFields = useCallback(
    (base: Record<string, unknown> = {}) => ({
      ...base,
      ...composeModelRequestFields({
        model,
        temperature,
        reasoningEffort,
        textVerbosity,
      }),
    }),
    [model, reasoningEffort, temperature, textVerbosity],
  );

  const extractAiMeta = useCallback((pack: WordPack) => {
    try {
      const categories: (keyof Examples)[] = ['Dev', 'CS', 'LLM', 'Business', 'Common'];
      for (const category of categories) {
        const items = pack.examples?.[category] || [];
        for (const item of items) {
          if (item && item.llm_model) {
            setAiMeta({ model: item.llm_model || null, params: item.llm_params || null });
            throw new Error('meta-found');
          }
        }
      }
    } catch {
      // 例外は探索完了の合図として扱う
    }
  }, []);

  useEffect(() => {
    // Strict Mode での再マウント時に mounted 状態を復元
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
    };
  }, []);

  const loadWordPack = useCallback(
    async (wordPackId: string) => {
      // 前のリクエストをキャンセルして Race Condition を防止
      // eslint-disable-next-line no-console
      console.log('[loadWordPack] START', { wordPackId, abortRefExists: !!abortRef.current });
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setLoading(true);
      setMessage(null);
      setData(null);
      try {
        // eslint-disable-next-line no-console
        console.log('[loadWordPack] fetching...', { url: `${apiBase}/word/packs/${wordPackId}` });
        const res = await fetchJson<WordPack>(`${apiBase}/word/packs/${wordPackId}`, {
          signal: ctrl.signal,
          timeoutMs: requestTimeoutMs,
        });
        // eslint-disable-next-line no-console
        console.log('[loadWordPack] response received', { lemma: res?.lemma, hasData: !!res, mounted: mountedRef.current });
        if (!mountedRef.current) {
          // eslint-disable-next-line no-console
          console.log('[loadWordPack] SKIP: component unmounted');
          return;
        }
        const normalized = normalizeWordPack(res);
        // eslint-disable-next-line no-console
        console.log('[loadWordPack] setData', { lemma: normalized?.lemma });
        setData(normalized);
        setCurrentWordPackId(wordPackId);
        extractAiMeta(normalized);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.log('[loadWordPack] CATCH', { aborted: ctrl.signal.aborted, error });
        if (ctrl.signal.aborted) return;
        let text = error instanceof ApiError ? error.message : 'WordPackの読み込みに失敗しました';
        if (error instanceof ApiError && error.status === 0 && /aborted|timed out/i.test(error.message)) {
          text = '読み込みがタイムアウトしました。時間をおいて再試行してください。';
        }
        setMessage({ kind: 'alert', text });
      } finally {
        // eslint-disable-next-line no-console
        console.log('[loadWordPack] FINALLY', { wordPackId });
        setLoading(false);
      }
    },
    [apiBase, extractAiMeta, normalizeWordPack, requestTimeoutMs],
  );

  const generateWordPack = useCallback(
    async (lemma: string) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      setLoading(true);
      setMessage(null);
      setData(null);
      const notifId = addNotification({
        title: `【${lemma}】の生成処理中...`,
        message: '新規のWordPackを生成しています（LLM応答の受信と解析を待機中）',
        status: 'progress',
      });
      try {
        const res = await fetchJson<WordPack>(`${apiBase}/word/pack`, {
          method: 'POST',
          body: applyModelRequestFields({
            lemma,
            pronunciation_enabled: pronunciationEnabled,
            regenerate_scope: regenerateScope,
          }),
          signal: ctrl.signal,
          timeoutMs: requestTimeoutMs,
        });
        const normalized = normalizeWordPack(res);
        if (mountedRef.current) {
          setData(normalized);
          setCurrentWordPackId(null);
          setMessage({ kind: 'status', text: 'WordPack を生成しました' });
          extractAiMeta(normalized);
        }
        updateNotification(notifId, {
          title: `【${res.lemma}】の生成完了！`,
          status: 'success',
          message: '新規生成が完了しました',
        });
        try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
        try { onWordPackGenerated?.(null); } catch {}
      } catch (error) {
        if (ctrl.signal.aborted) return;
        let text = error instanceof ApiError ? error.message : 'WordPack の生成に失敗しました';
        if (error instanceof ApiError && error.status === 0 && /aborted|timed out/i.test(error.message)) {
          text = 'タイムアウトしました（サーバ側で処理継続の可能性があります）。時間をおいて更新または保存済みを開いてください。';
        }
        setMessage({ kind: 'alert', text });
        updateNotification(notifId, {
          title: `【${lemma}】の生成失敗`,
          status: 'error',
          message: `新規生成に失敗しました（${text}）`,
        });
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    },
    [addNotification, apiBase, applyModelRequestFields, extractAiMeta, normalizeWordPack, onWordPackGenerated, pronunciationEnabled, regenerateScope, requestTimeoutMs, updateNotification],
  );

  const createEmptyWordPack = useCallback(
    async (lemma: string) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setLoading(true);
      setMessage(null);
      const notifId = addNotification({
        title: `【${lemma}】の生成処理中...`,
        message: '空のWordPackを作成しています',
        status: 'progress',
      });
      try {
        const res = await fetchJson<{ id: string }>(`${apiBase}/word/packs`, {
          method: 'POST',
          body: { lemma },
          signal: ctrl.signal,
          timeoutMs: requestTimeoutMs,
        });
        setCurrentWordPackId(res.id);
        await loadWordPack(res.id);
        try { onWordPackGenerated?.(res.id); } catch {}
        try { window.dispatchEvent(new CustomEvent('wordpack:updated')); } catch {}
        updateNotification(notifId, { title: `【${lemma}】の生成完了！`, status: 'success', message: '詳細読み込み完了' });
      } catch (error) {
        if (ctrl.signal.aborted) return;
        const text = error instanceof ApiError ? error.message : '空のWordPack作成に失敗しました';
        setMessage({ kind: 'alert', text });
        updateNotification(notifId, { title: `【${lemma}】の生成失敗`, status: 'error', message: `空のWordPackの作成に失敗しました（${text}）` });
      } finally {
        setLoading(false);
      }
    },
    [addNotification, apiBase, loadWordPack, onWordPackGenerated, requestTimeoutMs, updateNotification],
  );

  const recordStudyProgress = useCallback(
    async (kind: 'checked' | 'learned') => {
      if (!currentWordPackId) return;
      setProgressUpdating(true);
      try {
        const res = await fetchJson<{ checked_only_count: number; learned_count: number }>(
          `${apiBase}/word/packs/${currentWordPackId}/study-progress`,
          {
            method: 'POST',
            body: { kind },
          },
        );
        setData((prev) =>
          prev
            ? {
                ...prev,
                checked_only_count: res.checked_only_count,
                learned_count: res.learned_count,
              }
            : prev,
        );
        const detail = {
          wordPackId: currentWordPackId,
          checked_only_count: res.checked_only_count,
          learned_count: res.learned_count,
        };
        try { onStudyProgressRecorded?.(detail); } catch {}
        try { window.dispatchEvent(new CustomEvent('wordpack:study-progress', { detail })); } catch {}
        setMessage({
          kind: 'status',
          text: kind === 'learned' ? '学習済みとして記録しました' : '確認済みとして記録しました',
        });
      } catch (error) {
        const text = error instanceof ApiError ? error.message : '学習状況の記録に失敗しました';
        setMessage({ kind: 'alert', text });
      } finally {
        setProgressUpdating(false);
      }
    },
    [apiBase, currentWordPackId, onStudyProgressRecorded],
  );

  const regenerateWordPack = useCallback(
    async (wordPackId: string, lemma: string) => {
      const ctrl = new AbortController();
      setLoading(true);
      setMessage(null);
      try {
        const notifId = addNotification({
          title: `【${lemma}】の再生成ジョブ開始`,
          message: 'バックグラウンドで再生成しています（完了までしばらくお待ちください）',
          status: 'progress',
          model: model || undefined,
        });

        const job = await enqueueRegenerateWordPack({
          apiBase,
          wordPackId,
          settings: {
            pronunciationEnabled,
            regenerateScope,
            requestTimeoutMs,
            temperature,
            reasoningEffort,
            textVerbosity,
          },
          model,
          lemma,
          abortSignal: ctrl.signal,
        });

        // requestTimeoutMs が短くても（例: 60_000）再生成は数分かかり得るため、
        // ここでは最低 15 分相当までポーリングを継続する。
        const maxPolls = Math.max(3, Math.ceil(Math.max(requestTimeoutMs, 15 * 60 * 1000) / 2000));
        let latest = job;
        for (let i = 0; i < maxPolls; i += 1) {
          if (ctrl.signal.aborted) break;
          if (latest.status === 'succeeded' || latest.status === 'failed') break;
          await new Promise((resolve) => setTimeout(resolve, 1500));
          latest = await fetchRegenerateJobStatus({
            apiBase,
            wordPackId,
            jobId: job.job_id,
            abortSignal: ctrl.signal,
            timeoutMs: requestTimeoutMs,
          });
        }

        if (latest.status === 'succeeded' && latest.result) {
          const normalized = normalizeWordPack(latest.result as WordPack);
          if (mountedRef.current) {
            setData(normalized);
            setCurrentWordPackId(wordPackId);
            extractAiMeta(normalized);
            setMessage({ kind: 'status', text: 'WordPackを再生成しました' });
          }
          updateNotification(notifId, {
            title: `【${lemma}】の再生成完了`,
            status: 'success',
            message: 'バックグラウンド再生成が完了しました',
            model: model || undefined,
          });
          try { onWordPackGenerated?.(wordPackId); } catch {}
        } else {
          const errText = latest.error || '再生成が完了しませんでした（時間をおいて再試行してください）';
          if (mountedRef.current) setMessage({ kind: 'alert', text: errText });
          updateNotification(notifId, {
            title: `【${lemma}】の再生成失敗`,
            status: 'error',
            message: errText,
            model: model || undefined,
          });
        }
      } catch (error) {
        if (ctrl.signal.aborted) return;
        let text = error instanceof ApiError ? error.message : 'WordPackの再生成に失敗しました';
        if (error instanceof ApiError && error.status === 0 && /aborted|timed out/i.test(error.message)) {
          text = '再生成がタイムアウトしました（サーバ側で処理継続の可能性）。時間をおいて再試行してください。';
        }
        if (mountedRef.current) setMessage({ kind: 'alert', text });
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    },
    [
      addNotification,
      apiBase,
      extractAiMeta,
      model,
      normalizeWordPack,
      onWordPackGenerated,
      pronunciationEnabled,
      regenerateScope,
      reasoningEffort,
      requestTimeoutMs,
      temperature,
      textVerbosity,
      updateNotification,
    ],
  );

  return {
    aiMeta,
    currentWordPackId,
    data,
    loading,
    progressUpdating,
    message,
    clearMessage,
    setStatusMessage,
    generateWordPack,
    createEmptyWordPack,
    loadWordPack,
    regenerateWordPack,
    recordStudyProgress,
  };
};
