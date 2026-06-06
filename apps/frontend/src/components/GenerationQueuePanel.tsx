import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNotifications, type NotificationItem } from '../NotificationsContext';

const formatElapsed = (ms: number): string => {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
};

const extractLemma = (title: string): string => {
  const match = title.match(/【(.+?)】/);
  if (match?.[1]) return match[1];
  return title.replace(/の生成(処理中|完了|失敗).*$/, '').trim() || 'WordPack';
};

const notificationStatusLabel = (status: NotificationItem['status']): string => (
  status === 'progress' ? '生成中' : status === 'success' ? '完了' : '失敗'
);

const buildLiveMessage = (item: NotificationItem): string => {
  const lemma = extractLemma(item.title);
  const statusLabel = notificationStatusLabel(item.status);
  return `${lemma} の生成状態は${statusLabel}です${item.message ? `。${item.message}` : ''}`;
};

const QueueItem: React.FC<{ item: NotificationItem; nowMs: number; onRemove: (id: string) => void }> = ({ item, nowMs, onRemove }) => {
  const elapsedMs = item.status === 'progress' ? nowMs - item.createdAt : item.updatedAt - item.createdAt;
  const lemma = extractLemma(item.title);
  const statusLabel = notificationStatusLabel(item.status);
  const progressValue = item.status === 'progress' ? 68 : item.status === 'success' ? 100 : 100;

  return (
    <article className={`generation-queue-item is-${item.status}`}>
      <div className="generation-queue-item__status" aria-hidden="true">
        {item.status === 'progress' ? <span className="generation-queue-spinner" /> : item.status === 'success' ? '✓' : '!'}
      </div>
      <div className="generation-queue-item__body">
        <div className="generation-queue-item__heading">
          <strong>{lemma}</strong>
          <span>{statusLabel}</span>
        </div>
        {item.status !== 'success' ? (
          <p>{item.message || (item.status === 'progress' ? 'LLM応答を待機しています' : '生成履歴に保存されました')}</p>
        ) : null}
        <div className="generation-queue-item__meta">
          <span>{item.category ? `${item.category}: ` : ''}{item.model || 'gpt-5.4-mini'}</span>
          <span>{item.status === 'progress' ? `経過 ${formatElapsed(elapsedMs)}` : `${formatElapsed(elapsedMs)}前後`}</span>
        </div>
        {item.status === 'progress' ? (
          <div
            className="generation-queue-progress"
            role="progressbar"
            aria-label={`${lemma} の生成進行状況`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progressValue}
          >
            <span style={{ width: `${progressValue}%` }} />
          </div>
        ) : null}
        {item.status === 'progress' ? (
          <button type="button" className="generation-queue-item__remove" onClick={() => onRemove(item.id)}>
            キューから隠す
          </button>
        ) : null}
      </div>
    </article>
  );
};

export const GenerationQueuePanel: React.FC = () => {
  const { notifications, clearAll, remove } = useNotifications();
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [liveMessage, setLiveMessage] = useState('');
  const lastAnnouncementKeyRef = useRef<string | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const { progressItems, doneItems } = useMemo(() => {
    const progress = notifications.filter((item) => item.status === 'progress');
    const done = notifications
      .filter((item) => item.status !== 'progress')
      .sort((a, b) => b.updatedAt - a.updatedAt)
      .slice(0, 3);
    return { progressItems: progress, doneItems: done };
  }, [notifications]);

  useEffect(() => {
    const latest = notifications.reduce<NotificationItem | null>((current, item) => {
      if (!current) return item;
      return item.updatedAt > current.updatedAt ? item : current;
    }, null);
    const nextKey = latest ? `${latest.id}:${latest.status}:${latest.updatedAt}` : 'empty';
    if (lastAnnouncementKeyRef.current === null) {
      lastAnnouncementKeyRef.current = nextKey;
      return;
    }
    if (lastAnnouncementKeyRef.current === nextKey) return;
    lastAnnouncementKeyRef.current = nextKey;
    setLiveMessage(latest ? buildLiveMessage(latest) : '生成キューを空にしました。');
  }, [notifications]);

  return (
    <section className="generation-queue-panel" aria-label="生成キュー">
      <p className="visually-hidden" role="status" aria-live="polite" aria-atomic="true">
        {liveMessage}
      </p>
      <div className="generation-queue-panel__header">
        <h2>生成キュー</h2>
        <span className="generation-queue-count" aria-label={`生成履歴 ${notifications.length}件`}>
          {notifications.length}
        </span>
      </div>

      <div className="generation-queue-section">
        <div className="generation-queue-section__header">
          <h3>進行中</h3>
          <span>{progressItems.length}</span>
          <b aria-hidden="true">⌃</b>
        </div>
        {progressItems.length ? (
          <div className="generation-queue-list">
            {progressItems.map((item) => <QueueItem key={item.id} item={item} nowMs={nowMs} onRemove={remove} />)}
          </div>
        ) : (
          <p className="generation-queue-empty">今は生成待ちのWordPackはありません。</p>
        )}
      </div>

      <div className="generation-queue-section">
        <div className="generation-queue-section__header">
          <h3>完了</h3>
          <span>{doneItems.length}</span>
          <b aria-hidden="true">⌄</b>
        </div>
        {doneItems.length ? (
          <div className="generation-queue-list">
            {doneItems.map((item) => <QueueItem key={item.id} item={item} nowMs={nowMs} onRemove={remove} />)}
          </div>
        ) : (
          <p className="generation-queue-empty">完了した生成はここに残ります。</p>
        )}
      </div>

      {notifications.length ? (
        <button type="button" className="generation-queue-history-button" onClick={clearAll}>
          すべての履歴を消去
        </button>
      ) : null}
    </section>
  );
};
