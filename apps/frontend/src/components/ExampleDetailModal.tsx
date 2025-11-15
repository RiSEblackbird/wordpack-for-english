import React, { useEffect, useState } from 'react';
import { Modal } from './Modal';
import { TTSButton } from './TTSButton';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';

export interface ExampleItemData {
  id: number;
  word_pack_id: string;
  lemma: string;
  category: 'Dev' | 'CS' | 'LLM' | 'Business' | 'Common';
  en: string;
  ja: string;
  grammar_ja?: string | null;
  created_at: string;
  word_pack_updated_at?: string | null;
  checked_only_count?: number;
  learned_count?: number;
  transcription_typing_count?: number;
}

interface ExampleDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: ExampleItemData | null;
  onStudyProgressRecorded?: (payload: {
    id: number;
    word_pack_id: string;
    checked_only_count: number;
    learned_count: number;
  }) => void;
  onTranscriptionTypingRecorded?: (payload: {
    id: number;
    word_pack_id: string;
    transcription_typing_count: number;
  }) => void;
}

export const ExampleDetailModal: React.FC<ExampleDetailModalProps> = ({
  isOpen,
  onClose,
  item,
  onStudyProgressRecorded,
  onTranscriptionTypingRecorded,
}) => {
  const { settings } = useSettings();
  const [progressUpdating, setProgressUpdating] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [localCounts, setLocalCounts] = useState<{ checked: number; learned: number; transcriptionTyping: number }>({
    checked: 0,
    learned: 0,
    transcriptionTyping: 0,
  });
  const [transcriptionFormVisible, setTranscriptionFormVisible] = useState(false);
  const [transcriptionInput, setTranscriptionInput] = useState('');
  const [transcriptionUpdating, setTranscriptionUpdating] = useState(false);
  const [transcriptionFeedback, setTranscriptionFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!item) return;
    setLocalCounts({
      checked: item.checked_only_count ?? 0,
      learned: item.learned_count ?? 0,
      transcriptionTyping: item.transcription_typing_count ?? 0,
    });
    setFeedback(null);
    setTranscriptionFeedback(null);
    setTranscriptionFormVisible(false);
    setTranscriptionInput('');
    setTranscriptionUpdating(false);
  }, [item]);

  const recordProgress = async (kind: 'checked' | 'learned') => {
    if (!item) return;
    if (!settings.apiBase) {
      setFeedback('APIベースURLが未設定です');
      return;
    }
    setProgressUpdating(true);
    try {
      const res = await fetchJson<{ id: number; word_pack_id: string; checked_only_count: number; learned_count: number }>(
        `${settings.apiBase}/word/examples/${item.id}/study-progress`,
        {
          method: 'POST',
          body: { kind },
        },
      );
      // 学習記録更新後も最新の文字起こし回数を保持するため、既存値を引き継ぎつつ2項目のみ上書きする。
      setLocalCounts((prev) => ({
        checked: res.checked_only_count,
        learned: res.learned_count,
        transcriptionTyping: prev.transcriptionTyping,
      }));
      try {
        onStudyProgressRecorded?.({
          id: res.id,
          word_pack_id: res.word_pack_id,
          checked_only_count: res.checked_only_count,
          learned_count: res.learned_count,
        });
      } catch {}
      setFeedback(kind === 'learned' ? '学習済みとして記録しました' : '確認済みとして記録しました');
    } catch (e) {
      const m = e instanceof ApiError ? e.message : '学習状況の記録に失敗しました';
      setFeedback(m);
    } finally {
      setProgressUpdating(false);
    }
  };

  // 入力フォームの表示/非表示はトグルのみで制御し、直前の入力値を保持する
  const toggleTranscriptionForm = () => {
    setTranscriptionFormVisible((visible) => !visible);
  };

  // 文字起こしタイピングの送信処理。APIと連携しローカル状態および親へ反映させる。
  const recordTranscriptionTyping = async () => {
    if (!item) return;
    if (!settings.apiBase) {
      setTranscriptionFeedback('APIベースURLが未設定です');
      return;
    }
    setTranscriptionUpdating(true);
    setTranscriptionFeedback(null);
    try {
      const res = await fetchJson<{
        id: number;
        word_pack_id: string;
        transcription_typing_count: number;
      }>(`${settings.apiBase}/word/examples/${item.id}/transcription-typing`, {
        method: 'POST',
        body: { content: transcriptionInput },
      });
      setLocalCounts((prev) => ({
        checked: prev.checked,
        learned: prev.learned,
        transcriptionTyping: res.transcription_typing_count,
      }));
      try {
        onTranscriptionTypingRecorded?.({
          id: res.id,
          word_pack_id: res.word_pack_id,
          transcription_typing_count: res.transcription_typing_count,
        });
      } catch {}
      setTranscriptionFeedback('タイピング記録を保存しました');
    } catch (e) {
      const m = e instanceof ApiError ? e.message : '文字起こしタイピングの記録に失敗しました';
      setTranscriptionFeedback(m);
    } finally {
      setTranscriptionUpdating(false);
    }
  };

  const transcriptionLengthDiff = transcriptionInput.length - (item?.en.length ?? 0);
  const isTranscriptionWithinRange = Math.abs(transcriptionLengthDiff) <= 10; // ±10文字差以内なら許容する
  const transcriptionRecordDisabled =
    transcriptionUpdating || !isTranscriptionWithinRange || transcriptionInput.trim().length === 0;

  if (!isOpen || !item) return null;
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`例文 詳細（${item.lemma} / ${item.category}）`}>
      <section>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <strong>原文</strong>
              <TTSButton text={item.en} style={{ fontSize: '0.75em', padding: '0.15rem 0.5rem', borderRadius: 4 }} />
            </div>
            <p style={{ marginTop: 4 }}>{item.en}</p>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <strong>日本語訳</strong>
              <TTSButton text={item.ja} style={{ fontSize: '0.75em', padding: '0.15rem 0.5rem', borderRadius: 4 }} />
            </div>
            <p style={{ marginTop: 4 }}>{item.ja}</p>
          </div>
          {item.grammar_ja ? (
            <div>
              <strong>解説</strong>
              <p style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{item.grammar_ja}</p>
            </div>
          ) : null}
          <div style={{ color: 'var(--color-subtle)', fontSize: '0.85em' }}>
            <span>ID: {item.id}</span>
            <span> / WordPack: {item.word_pack_id}</span>
            {item.word_pack_updated_at ? <span> / Pack更新: {item.word_pack_updated_at}</span> : null}
            <span> / 例文作成: {item.created_at}</span>
          </div>
          <div
            style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}
            aria-label="例文の学習記録"
          >
            <strong style={{ fontSize: '0.9em' }}>学習記録</strong>
            <button
              type="button"
              onClick={() => recordProgress('checked')}
              disabled={progressUpdating}
              style={{
                padding: '0.3rem 0.6rem',
                borderRadius: 6,
                border: '1px solid #ffa726',
                backgroundColor: '#fff3e0',
                color: '#ef6c00',
              }}
            >
              確認した ({localCounts.checked})
            </button>
            <button
              type="button"
              onClick={() => recordProgress('learned')}
              disabled={progressUpdating}
              style={{
                padding: '0.3rem 0.6rem',
                borderRadius: 6,
                border: '1px solid #81c784',
                backgroundColor: '#e8f5e9',
                color: '#1b5e20',
              }}
            >
              学習した ({localCounts.learned})
            </button>
            {feedback ? (
              <span
                role="status"
                aria-live="polite"
                style={{
                  fontSize: '0.8em',
                  color: feedback.includes('失敗') || feedback.includes('未設定') ? '#c62828' : '#2e7d32',
                }}
              >
                {feedback}
              </span>
            ) : null}
          </div>
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={toggleTranscriptionForm}
              style={{
                padding: '0.3rem 0.6rem',
                borderRadius: 6,
                border: '1px solid #64b5f6',
                backgroundColor: transcriptionFormVisible ? '#e3f2fd' : '#f5faff',
                color: '#1e88e5',
                textAlign: 'left',
              }}
            >
              文字起こしタイピング ({localCounts.transcriptionTyping})
            </button>
            {transcriptionFormVisible ? (
              <div style={{ display: 'grid', gap: '0.5rem' }}>
                <label style={{ display: 'grid', gap: '0.25rem' }}>
                  <span style={{ fontWeight: 600 }}>英文を入力してください</span>
                  <textarea
                    value={transcriptionInput}
                    onChange={(event) => setTranscriptionInput(event.target.value)}
                    rows={5}
                    style={{
                      borderRadius: 6,
                      border: '1px solid #90caf9',
                      padding: '0.5rem',
                      fontFamily: 'inherit',
                    }}
                    aria-label="文字起こしタイピング入力"
                  />
                </label>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    onClick={recordTranscriptionTyping}
                    disabled={transcriptionRecordDisabled}
                    style={{
                      padding: '0.3rem 0.6rem',
                      borderRadius: 6,
                      border: '1px solid #64b5f6',
                      backgroundColor: transcriptionRecordDisabled ? '#e3f2fd' : '#bbdefb',
                      color: '#0d47a1',
                    }}
                  >
                    タイピング記録
                  </button>
                  <span style={{ fontSize: '0.8em', color: isTranscriptionWithinRange ? '#2e7d32' : '#c62828' }}>
                    入力文字数差: {transcriptionLengthDiff}
                  </span>
                  {transcriptionFeedback ? (
                    <span
                      role="status"
                      aria-live="polite"
                      style={{
                        fontSize: '0.8em',
                        color:
                          transcriptionFeedback.includes('失敗') || transcriptionFeedback.includes('未設定')
                            ? '#c62828'
                            : '#2e7d32',
                      }}
                    >
                      {transcriptionFeedback}
                    </span>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </Modal>
  );
};


