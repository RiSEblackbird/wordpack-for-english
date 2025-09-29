/**
 * Set をコピーして指定値の有無をトグルするユーティリティ。
 * React のステート更新で再利用されるケースが多いため、
 * 冗長な複製ロジックをここに集約する。
 */
export function toggleSetValue<T>(source: Set<T>, value: T): Set<T> {
  const next = new Set(source);
  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }
  return next;
}

/**
 * 現在の選択集合から存在しない値を除外するためのヘルパー。
 * 一覧がページングで入れ替わった際に古い選択を維持しないよう利用する。
 */
export function retainSetValues<T>(source: Set<T>, valid: Iterable<T>): Set<T> {
  const validSet = new Set(valid);
  const next = new Set<T>();
  source.forEach((value) => {
    if (validSet.has(value)) {
      next.add(value);
    }
  });
  return next;
}

/**
 * 一覧全体の選択/解除をまとめて行うためのヘルパー。
 */
export function assignSetValues<T>(source: Set<T>, values: Iterable<T>, shouldSelect: boolean): Set<T> {
  const next = new Set(source);
  if (shouldSelect) {
    for (const value of values) {
      next.add(value);
    }
    return next;
  }
  for (const value of values) {
    next.delete(value);
  }
  return next;
}
