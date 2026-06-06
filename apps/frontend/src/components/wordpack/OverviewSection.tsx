import React, { useEffect, useMemo, useState } from 'react';
import { TTSButton } from '../TTSButton';
import { WordPack } from '../../hooks/useWordPack';
import { useAuth } from '../../AuthContext';
import { GuestLock } from '../GuestLock';
import { GuestPublicToggle } from '../GuestPublicToggle';

interface ExampleStatItem {
  category: string;
  count: number;
}

interface MetaInfo {
  created_at: string;
  updated_at: string;
}

interface AiMetaInfo {
  model?: string | null;
  params?: string | null;
}

interface OverviewSectionProps {
  data: WordPack;
  selectedMeta?: MetaInfo | null;
  aiMeta: AiMetaInfo | null;
  exampleStats: { counts: ExampleStatItem[]; total: number };
  currentWordPackId: string | null;
  isActionLoading: boolean;
  packCheckedCount: number;
  packLearnedCount: number;
  guestPublic: boolean;
  guestPublicUpdating: boolean;
  guestPublicDisabledReason?: string | null;
  onGuestPublicChange: (next: boolean) => void;
  onRecordStudyProgress: (kind: 'checked' | 'learned') => void;
  onRegenerate?: () => void;
  formatDate: (dateStr?: string | null) => string;
  showTtsButton?: boolean;
}

/**
 * WordPackの概要・統計・学習カードなど、全体の入口となる情報をまとめるセクション。
 * 自己完結したカウントダウンや進捗操作を内包し、親からは必要なハンドラのみ受け取る。
 */
export const OverviewSection: React.FC<OverviewSectionProps> = ({
  data,
  selectedMeta,
  aiMeta,
  exampleStats,
  currentWordPackId,
  isActionLoading,
  packCheckedCount,
  packLearnedCount,
  guestPublic,
  guestPublicUpdating,
  guestPublicDisabledReason,
  onGuestPublicChange,
  onRecordStudyProgress,
  onRegenerate,
  formatDate,
  showTtsButton = true,
}) => {
  const { isGuest } = useAuth();
  const [reveal, setReveal] = useState(false);
  const [count, setCount] = useState(3);

  // WordPack切り替え時にセルフチェックのカウントダウンを初期化し、自動解除する。
  useEffect(() => {
    setReveal(false);
    setCount(3);
    const t1 = window.setTimeout(() => setCount(2), 1000);
    const t2 = window.setTimeout(() => setCount(1), 2000);
    const t3 = window.setTimeout(() => setReveal(true), 3000);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
    };
  }, [data.lemma]);

  const aiMetaItems = useMemo(() => {
    const items: { label: string; value: string | null | undefined }[] = [];
    if (aiMeta?.model) items.push({ label: 'AIモデル', value: aiMeta.model });
    if (aiMeta?.params) items.push({ label: 'AIパラメータ', value: aiMeta.params });
    return items;
  }, [aiMeta]);

  return (
    <section id="overview" className="wp-section">
      <h3>概要</h3>
      <div className="kv" style={{ fontSize: '1.7em', marginBottom: '0.8rem' }}>
        <div>見出し語</div>
        <div className="wp-modal-lemma">
          <strong>{data.lemma}</strong>
          {showTtsButton ? <TTSButton text={data.lemma} className="wp-modal-tts-btn" /> : null}
        </div>
      </div>
      {selectedMeta ? (
        <div className="kv" style={{ marginBottom: '0.5rem', fontSize: '0.7em' }}>
          <div>作成</div><div>{formatDate(selectedMeta.created_at)}</div>
          <div>更新</div><div>{formatDate(selectedMeta.updated_at)}</div>
          {aiMetaItems.map((item) => (
            <React.Fragment key={item.label}>
              <div>{item.label}</div><div>{item.value}</div>
            </React.Fragment>
          ))}
        </div>
      ) : null}
      <div style={{ marginTop: '0.75rem', padding: '0.75rem', backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <strong style={{ color: 'var(--color-accent)' }}>📊 例文統計</strong>
          <span style={{ fontSize: '1.1em', fontWeight: 'bold' }}>
            総数 {exampleStats.total}件
          </span>
        </div>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.9em' }}>
          {exampleStats.counts.map(({ category, count }) => (
            <span
              key={category}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                padding: '0.25rem 0.5rem',
                backgroundColor: count > 0 ? 'var(--color-accent-bg)' : 'var(--color-neutral-surface)',
                color: count > 0 ? 'var(--color-accent)' : 'var(--dict-text)',
                borderRadius: '4px',
                border: `1px solid ${count > 0 ? 'var(--color-accent)' : 'var(--color-border)'}`,
              }}
            >
              <span style={{ fontWeight: 'bold' }}>{category}</span>
              <span style={{ fontSize: '0.9em' }}>{count}件</span>
            </span>
          ))}
        </div>
      </div>
      <div
        style={{
          marginTop: '0.5rem',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.75rem',
          alignItems: 'center',
        }}
      >
        <div style={{ flex: '1 1 240px' }}>
          <GuestPublicToggle
            isGuest={isGuest}
            checked={guestPublic}
            disabled={guestPublicUpdating || !currentWordPackId}
            onChange={onGuestPublicChange}
            tooltip="ゲスト閲覧での表示可否を切り替えます（例文もWordPack単位で公開されます）"
            description="ゲスト閲覧モードに表示させる場合に有効化します。"
            disabledReason={guestPublicDisabledReason}
          />
        </div>
        <div
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}
          aria-label="用例メモの操作"
        >
          <strong style={{ fontSize: '0.9em' }}>用例メモ</strong>
          <button
            type="button"
            onClick={() => onRecordStudyProgress('checked')}
            disabled={!currentWordPackId || isActionLoading}
            title={!currentWordPackId ? '保存済みWordPackのみ記録できます' : undefined}
            style={{
              padding: '0.3rem 0.7rem',
              borderRadius: 6,
              border: '1px solid #ffa726',
              backgroundColor: '#fff3e0',
              color: '#7a3700',
            }}
          >
            確認した ({packCheckedCount})
          </button>
          <button
            type="button"
            onClick={() => onRecordStudyProgress('learned')}
            disabled={!currentWordPackId || isActionLoading}
            title={!currentWordPackId ? '保存済みWordPackのみ記録できます' : undefined}
            style={{
              padding: '0.3rem 0.7rem',
              borderRadius: 6,
              border: '1px solid #81c784',
              backgroundColor: '#e8f5e9',
              color: '#0d4f18',
            }}
          >
            使える ({packLearnedCount})
          </button>
        </div>
        {currentWordPackId && (
          <GuestLock isGuest={isGuest}>
            <button
              type="button"
              onClick={onRegenerate}
              disabled={isActionLoading}
              style={{ marginLeft: 'auto', backgroundColor: 'var(--color-neutral-surface)' }}
            >
              再生成
            </button>
          </GuestLock>
        )}
      </div>
      <div className="selfcheck" style={{ marginTop: '0.5rem' }}>
        <div className={!reveal ? 'blurred' : ''}>
          <div>
            <strong>辞書カード要点</strong>
            <span className="visually-hidden">学習カード要点</span>
          </div>
          <p>{data.study_card}</p>
        </div>
        {!reveal && (
          <div className="selfcheck-overlay" onClick={() => setReveal(true)} aria-label="セルフチェック解除">
            <span>セルフチェック中… {count}</span>
          </div>
        )}
      </div>
    </section>
  );
};
