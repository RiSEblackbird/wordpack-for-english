import type React from 'react';
import { useCallback, useEffect, useRef } from 'react';
import { LemmaLookupResponseData } from '../LemmaExplorer/useLemmaExplorer';

interface LemmaTooltipState {
  tooltip: HTMLElement;
  aborter: AbortController | null;
  outsideHandler?: (ev: MouseEvent) => void;
  keyHandler?: (ev: KeyboardEvent) => void;
  blockHandler?: (ev: Event) => void;
}

interface UseLemmaTooltipOptions {
  lookupLemmaMetadata: (lemmaText: string) => Promise<LemmaLookupResponseData>;
}

interface LemmaTooltipHandlers {
  handleMouseOver: (event: React.MouseEvent<HTMLDivElement>) => Promise<void>;
  handleMouseOut: (event: React.MouseEvent<HTMLDivElement>) => void;
  detachTooltip: () => void;
}

/**
 * 例文行のトークンに紐づくツールチップ表示を集約するカスタムフック。
 * DOM操作を一箇所に閉じ込め、UI側ではハンドラを渡すだけにする。
 */
export const useLemmaTooltip = ({ lookupLemmaMetadata }: UseLemmaTooltipOptions): LemmaTooltipHandlers => {
  const lemmaActionRef = useRef<LemmaTooltipState | null>(null);

  const detachTooltip = useCallback(() => {
    const active = lemmaActionRef.current;
    if (!active) return;
    const { tooltip, aborter, outsideHandler, keyHandler, blockHandler } = active;
    if (aborter) {
      try { aborter.abort(); } catch {}
    }
    if (outsideHandler) document.removeEventListener('click', outsideHandler, true);
    if (keyHandler) tooltip.removeEventListener('keydown', keyHandler);
    if (blockHandler) tooltip.removeEventListener('pointerdown', blockHandler, true);
    if (tooltip.isConnected) tooltip.remove();
    lemmaActionRef.current = null;
  }, []);

  useEffect(() => () => detachTooltip(), [detachTooltip]);

  const showTooltip = useCallback((target: HTMLElement, text: string) => {
    document.querySelectorAll('.lemma-tooltip').forEach((n) => n.remove());
    const tooltip = document.createElement('div');
    tooltip.className = 'lemma-tooltip';
    tooltip.setAttribute('role', 'tooltip');
    tooltip.textContent = text;
    const rect = target.getBoundingClientRect();
    const pad = 6;
    document.body.appendChild(tooltip);
    const x = Math.min(Math.max(rect.left, 8), (window.innerWidth - tooltip.offsetWidth - 8));
    const y = Math.max(rect.top - tooltip.offsetHeight - pad, 8);
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
    return tooltip;
  }, []);

  const handleMouseOver = useCallback(
    async (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement;
      const highlight = target.closest('span.lemma-highlight') as HTMLElement | null;
      const token = highlight ? null : (target.closest('span.lemma-token') as HTMLElement | null);
      const container = e.currentTarget as HTMLElement;
      let matchedInfo: LemmaLookupResponseData | null = null;
      let matchedCandidate: { idxs: number[]; text: string } | null = null;
      const cleanup = detachTooltip;

      if (highlight) {
        cleanup();
        const display = container.getAttribute('data-sense-title') || '';
        if (!display) return;
        try { window.clearTimeout((highlight as any).__ttimer); } catch {}
        ;(highlight as any).__ttimer = window.setTimeout(() => {
          const tip = showTooltip(highlight, display);
          lemmaActionRef.current = { tooltip: tip, aborter: null };
        }, 500);
        return;
      }

      if (!token) {
        cleanup();
        return;
      }
      cleanup();
      const row = container;
      const tokens = Array.from(row.querySelectorAll('span.lemma-token')) as HTMLElement[];
      row.removeAttribute('data-last-lemma');
      row.removeAttribute('data-pending-lemma');
      tokens.forEach((el) => {
        el.classList.remove('lemma-known', 'lemma-unknown');
        el.removeAttribute('data-lemma-match');
        el.removeAttribute('data-lemma-sense');
        el.removeAttribute('data-lemma-id');
        el.removeAttribute('data-pending-lemma');
      });
      const iTok = Number(token.getAttribute('data-tok-idx')) || 0;
      const getText = (el: HTMLElement) => (el.textContent || '').replace(/[\s\u00A0]+/g, ' ').trim();
      const cands: { idxs: number[]; text: string }[] = [];
      const push = (idxs: number[]) => {
        const txt = idxs.map((k) => getText(tokens[k])).join(' ').trim();
        if (txt) cands.push({ idxs, text: txt });
      };
      if (iTok > 0 && iTok < tokens.length - 1) push([iTok - 1, iTok, iTok + 1]);
      if (iTok < tokens.length - 1) push([iTok, iTok + 1]);
      if (iTok > 0) push([iTok - 1, iTok]);
      push([iTok]);

      let foundSense = '';
      let foundIdxs: number[] | null = null;
      for (const cand of cands) {
        const info = await lookupLemmaMetadata(cand.text);
        if (info && info.found && info.sense_title) {
          foundSense = info.sense_title;
          foundIdxs = cand.idxs;
          matchedInfo = info;
          matchedCandidate = cand;
          break;
        }
      }
      if (!foundSense || !foundIdxs) {
        const candidateTextRaw = matchedCandidate?.text || token.textContent || '';
        const candidateText = candidateTextRaw.trim();
        if (candidateText) {
          row.setAttribute('data-last-lemma', candidateText);
          row.setAttribute('data-pending-lemma', candidateText);
          token.setAttribute('data-pending-lemma', candidateText);
          token.classList.add('lemma-unknown');
        }
        const tooltip = showTooltip(token, '未生成');
        lemmaActionRef.current = {
          tooltip,
          aborter: null,
        };
        return;
      }
      const lemmaValue = (matchedInfo?.lemma || matchedCandidate?.text || '').trim();
      foundIdxs.forEach((k) => {
        const tokenEl = tokens[k];
        if (!tokenEl) return;
        tokenEl.classList.remove('lemma-unknown');
        tokenEl.classList.add('lemma-known');
        if (lemmaValue) tokenEl.setAttribute('data-lemma-match', lemmaValue);
        if (matchedInfo?.sense_title) tokenEl.setAttribute('data-lemma-sense', matchedInfo.sense_title);
        if (matchedInfo?.id) tokenEl.setAttribute('data-lemma-id', matchedInfo.id);
      });
      if (lemmaValue) {
        container.setAttribute('data-last-lemma', lemmaValue);
      }
      if (matchedInfo?.sense_title) {
        container.setAttribute('data-last-sense', matchedInfo.sense_title);
      }
      try { window.clearTimeout((token as any).__ttimer); } catch {}
      ;(token as any).__ttimer = window.setTimeout(() => {
        const tip = showTooltip(token, foundSense);
        lemmaActionRef.current = { tooltip: tip, aborter: null };
      }, 500);
    },
    [detachTooltip, lookupLemmaMetadata, showTooltip],
  );

  const handleMouseOut = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement;
      const related = e.relatedTarget as Node | null;
      const highlight = target.closest('span.lemma-highlight') as HTMLElement | null;
      const token = target.closest('span.lemma-token') as HTMLElement | null;
      if (highlight) { try { window.clearTimeout((highlight as any).__ttimer); } catch {} }
      if (token) { try { window.clearTimeout((token as any).__ttimer); } catch {} }
      const activeTooltip = lemmaActionRef.current?.tooltip || null;
      if (activeTooltip && related && activeTooltip.contains(related)) {
        return;
      }
      const row = e.currentTarget as HTMLElement;
      detachTooltip();
      row.removeAttribute('data-pending-lemma');
      row.querySelectorAll('span.lemma-token').forEach((el) => {
        el.classList.remove('lemma-known', 'lemma-unknown');
        el.removeAttribute('data-pending-lemma');
      });
      document.querySelectorAll('.lemma-tooltip').forEach((n) => n.remove());
    },
    [detachTooltip],
  );

  return { handleMouseOver, handleMouseOut, detachTooltip };
};
