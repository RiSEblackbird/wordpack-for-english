import { useCallback, useEffect, useRef } from 'react';

/**
 * AbortError は useAbortableAsync から返却される中断例外の共通型。
 * fetch が AbortSignal により中断された場合に throw され、
 * 呼び出し側はこのエラーを握りつぶして副作用を避けられる。
 */
export class AbortError extends Error {
  constructor(message = 'Operation aborted') {
    super(message);
    this.name = 'AbortError';
  }
}

/**
 * UI から実行する API 呼び出しを安全に中断するための共通フック。
 * 複数回連続で呼び出した場合は前回の AbortController を破棄し、
 * アンマウント時には自動で abort() を呼び出してリークを防ぐ。
 */
export function useAbortableAsync() {
  const controllerRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    const controller = controllerRef.current;
    if (controller) {
      controller.abort();
      controllerRef.current = null;
    }
  }, []);

  const run = useCallback(
    async <T>(task: (signal: AbortSignal) => Promise<T>): Promise<T> => {
      // 直前の非同期処理をキャンセルし、最新の要求のみを実行する。
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
      const controller = new AbortController();
      controllerRef.current = controller;
      try {
        const result = await task(controller.signal);
        return result;
      } catch (error) {
        if (controller.signal.aborted) {
          // 呼び出し元が AbortError を検知できるように型を統一する。
          throw new AbortError();
        }
        throw error;
      } finally {
        if (controllerRef.current === controller) {
          controllerRef.current = null;
        }
      }
    },
    [],
  );

  useEffect(() => abort, [abort]);

  return { run, abort };
}
