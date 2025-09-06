import React, { useRef, useState, useEffect } from 'react';
import { useSettings } from '../SettingsContext';

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
  const abortRef = useRef<AbortController>();

  const getCard = async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    try {
      const res = await fetch(`${settings.apiBase}/cards/next`, { signal: ctrl.signal });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setCard(data);
      setMsg({ kind: 'status', text: 'Card loaded' });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      setMsg({ kind: 'alert', text: 'Failed to load card' });
    } finally {
      setLoading(false);
    }
  };

  const reviewCard = async () => {
    if (!card) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    setMsg(null);
    try {
      const res = await fetch(`${settings.apiBase}/cards/${card.id}/review`, { method: 'POST', signal: ctrl.signal });
      if (!res.ok) throw new Error();
      setMsg({ kind: 'status', text: 'Reviewed' });
      setCard(null);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      setMsg({ kind: 'alert', text: 'Failed to review' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return (
    <section>
      <button onClick={getCard} ref={focusRef as React.RefObject<HTMLButtonElement>}>Get Card</button>
      {loading && <div role="status">Loading…</div>}
      {card && (
        <div>
          <p><strong>{card.front}</strong></p>
          <p>{card.back}</p>
          <button onClick={reviewCard}>Review</button>
        </div>
      )}
      {msg && <div role={msg.kind}>{msg.text}</div>}
    </section>
  );
};
