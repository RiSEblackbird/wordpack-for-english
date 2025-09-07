import React, { useRef, useState, useEffect } from 'react';
import { useSettings } from '../SettingsContext';
import { fetchJson, ApiError } from '../lib/fetcher';

interface Card {
  id: string;
  front: string;
  back: string;
}

interface Props {
  focusRef: React.RefObject<HTMLElement>;
}

export const CardPanel: React.FC<Props> = ({ focusRef }) => {
  const { settings } = useSettings();
  const [card, setCard] = useState<Card | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'status' | 'alert'; text: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const getCard = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    try {
      const data = await fetchJson<{ items: Card[] }>(`${settings.apiBase}/review/today`, { signal: ctrl.signal });
      setCard(data.items?.[0] ?? null);
      setMsg({ kind: 'status', text: 'カードを読み込みました' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const msg = e instanceof ApiError ? e.message : 'カードの読み込みに失敗しました';
      setMsg({ kind: 'alert', text: msg });
    } finally {
      setLoading(false);
    }
  };

  const reviewCard = async (grade: 0 | 1 | 2) => {
    if (!card) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    try {
      await fetchJson(`${settings.apiBase}/review/grade`, {
        method: 'POST',
        body: { item_id: card.id, grade },
        signal: ctrl.signal,
      });
      setMsg({ kind: 'status', text: '復習しました（次のカードに進みます）' });
      setCard(null);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const msg = e instanceof ApiError ? e.message : '復習に失敗しました';
      setMsg({ kind: 'alert', text: msg });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return (
    <section id="card-panel" tabIndex={-1}>
      <button onClick={getCard}>カードを取得</button>
      {loading && <div role="status">読み込み中…</div>}
      {card && (
        <div>
          <p><strong>{card.front}</strong></p>
          <p>{card.back}</p>
          <div>
            <button onClick={() => reviewCard(0)}>× わからない</button>
            <button onClick={() => reviewCard(1)}>△ あいまい</button>
            <button onClick={() => reviewCard(2)}>○ できた</button>
          </div>
        </div>
      )}
      {msg && <div role={msg.kind}>{msg.text}</div>}
    </section>
  );
};
