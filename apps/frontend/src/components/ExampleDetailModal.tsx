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
}

export const ExampleDetailModal: React.FC<ExampleDetailModalProps> = ({ isOpen, onClose, item, onStudyProgressRecorded }) => {
  const { settings } = useSettings();
  const [progressUpdating, setProgressUpdating] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [localCounts, setLocalCounts] = useState<{ checked: number; learned: number }>({ checked: 0, learned: 0 });

  useEffect(() => {
    if (!item) return;
    setLocalCounts({
      checked: item.checked_only_count ?? 0,
      learned: item.learned_count ?? 0,
    });
    setFeedback(null);
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
      setLocalCounts({ checked: res.checked_only_count, learned: res.learned_count });
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
        </div>
      </section>
    </Modal>
  );
};


