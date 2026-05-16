import React, { useMemo, useRef } from 'react';
import { Modal } from './Modal';
import { WordPackPanel, type WordPackPreviewMeta } from './WordPackPanel';
import type { WordPackListItem } from '../features/wordpack/types';

interface WordPackPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  wordPackId: string | null;
  wordPacks: WordPackListItem[];
  onWordPackUpdated?: () => void;
  onStudyProgressRecorded?: (payload: { wordPackId: string; checked_only_count: number; learned_count: number }) => void;
}

export const WordPackPreviewModal: React.FC<WordPackPreviewModalProps> = ({
  isOpen,
  onClose,
  wordPackId,
  wordPacks,
  onWordPackUpdated,
  onStudyProgressRecorded,
}) => {
  const focusRef = useRef<HTMLElement>(null);
  const previewMeta = useMemo<WordPackPreviewMeta | null>(() => {
    if (!wordPackId) return null;
    const meta = wordPacks.find((wordPack) => wordPack.id === wordPackId);
    if (!meta) return null;
    return {
      id: meta.id,
      lemma: meta.lemma,
      senseTitle: meta.sense_title,
      created_at: meta.created_at,
      updated_at: meta.updated_at,
    };
  }, [wordPackId, wordPacks]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="WordPack プレビュー">
      {wordPackId ? (
        <WordPackPanel
          focusRef={focusRef}
          selectedWordPackId={wordPackId}
          selectedMeta={
            previewMeta?.created_at && previewMeta?.updated_at
              ? { created_at: previewMeta.created_at, updated_at: previewMeta.updated_at }
              : null
          }
          fallbackMeta={previewMeta ? { id: previewMeta.id, lemma: previewMeta.lemma, senseTitle: previewMeta.senseTitle } : null}
          onWordPackGenerated={() => {
            onWordPackUpdated?.();
          }}
          onStudyProgressRecorded={onStudyProgressRecorded}
        />
      ) : null}
    </Modal>
  );
};
