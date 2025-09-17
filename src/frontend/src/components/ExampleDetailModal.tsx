import React from 'react';
import { Modal } from './Modal';

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
}

interface ExampleDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: ExampleItemData | null;
}

export const ExampleDetailModal: React.FC<ExampleDetailModalProps> = ({ isOpen, onClose, item }) => {
  if (!isOpen || !item) return null;
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`例文 詳細（${item.lemma} / ${item.category}）`}>
      <section>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          <div>
            <strong>原文</strong>
            <p style={{ marginTop: 4 }}>{item.en}</p>
          </div>
          <div>
            <strong>日本語訳</strong>
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
        </div>
      </section>
    </Modal>
  );
};


