import { useCallback, useMemo, useState } from 'react';
import { Settings } from '../SettingsContext';
import { DEFAULT_LLM_MODEL, SUPPORTED_LLM_MODELS, normalizeLlmModel } from '../lib/wordpack';

type LemmaValidationResult = {
  valid: boolean;
  message: string;
  normalizedLemma: string;
};

type AdvancedSettingsControls = {
  reasoningEffort: NonNullable<Settings['reasoningEffort']>;
  textVerbosity: NonNullable<Settings['textVerbosity']>;
  handleChangeReasoningEffort: (value: NonNullable<Settings['reasoningEffort']>) => void;
  handleChangeTextVerbosity: (value: NonNullable<Settings['textVerbosity']>) => void;
};

type UseWordPackFormParams = {
  settings: Settings;
  setSettings: React.Dispatch<React.SetStateAction<Settings>>;
};

const LEMMA_PATTERN = /^[A-Za-z0-9-' ]+$/;
const LEMMA_MAX_LENGTH = 64;

export const useWordPackForm = ({ settings, setSettings }: UseWordPackFormParams) => {
  // フォーム入力とUI表示のために見出し語のテキストを保持し、他の入力からのセットにも対応する。
  const [lemma, setLemma] = useState('');
  // APIに送る値のぶれを抑えて重複生成を防ぐため、見出し語は常にトリムして扱う。
  const normalizedLemma = useMemo(() => lemma.trim(), [lemma]);

  // クライアント側で境界値を固定し、サーバーのバリデーションと乖離しないように事前に入力を判定する。
  const lemmaValidation = useMemo<LemmaValidationResult>(() => {
    if (!normalizedLemma) {
      return {
        valid: false,
        message: '見出し語を入力してください（英数字・ハイフン・アポストロフィ・半角スペースのみ）',
        normalizedLemma,
      };
    }
    if (normalizedLemma.length > LEMMA_MAX_LENGTH) {
      return {
        valid: false,
        message: `見出し語は最大${LEMMA_MAX_LENGTH}文字までです（英数字・半角スペース・ハイフン・アポストフィのみ）`,
        normalizedLemma,
      };
    }
    if (!LEMMA_PATTERN.test(normalizedLemma)) {
      return {
        valid: false,
        message: '英数字と半角スペース、ハイフン、アポストロフィのみ利用できます',
        normalizedLemma,
      };
    }
    return {
      valid: true,
      message: '英数字・半角スペース・ハイフン・アポストロフィのみ（最大64文字）',
      normalizedLemma,
    };
  }, [normalizedLemma]);

  // モデル選択はフォームのローカル状態で即時反映し、同時にSettingsContextへ同期して他画面と整合させる。
  const [model, setModel] = useState<string>(normalizeLlmModel(settings.model || DEFAULT_LLM_MODEL));
  const handleChangeModel = useCallback(
    (value: string) => {
      const normalized = normalizeLlmModel(value);
      setModel(normalized);
      setSettings((prev) => ({ ...prev, model: normalized }));
    },
    [setSettings],
  );

  // 現行ラインナップはすべて reasoning/text 指定を使うため、高度設定は常時表示する。
  const showAdvancedModelOptions = useMemo(() => {
    return SUPPORTED_LLM_MODELS.includes(model as any);
  }, [model]);

  // LLM設定の詳細はSettingsContextに一元化し、フォーム変更と永続化を揃える。
  const handleChangeReasoningEffort = useCallback(
    (value: NonNullable<Settings['reasoningEffort']>) => {
      setSettings((prev) => ({ ...prev, reasoningEffort: value }));
    },
    [setSettings],
  );
  const handleChangeTextVerbosity = useCallback(
    (value: NonNullable<Settings['textVerbosity']>) => {
      setSettings((prev) => ({ ...prev, textVerbosity: value }));
    },
    [setSettings],
  );

  // フォームが参照する高度設定一式をまとめ、UI側での条件分岐と依存を最小限に保つ。
  const advancedSettings: AdvancedSettingsControls = useMemo(
    () => ({
      reasoningEffort: settings.reasoningEffort || 'minimal',
      textVerbosity: settings.textVerbosity || 'medium',
      handleChangeReasoningEffort,
      handleChangeTextVerbosity,
    }),
    [handleChangeReasoningEffort, handleChangeTextVerbosity, settings.reasoningEffort, settings.textVerbosity],
  );

  return {
    lemma,
    setLemma,
    lemmaValidation,
    model,
    showAdvancedModelOptions,
    handleChangeModel,
    advancedSettings,
  };
};
