import 'vitest';
import type { AxeResults } from 'axe-core';

/**
 * a11y テストで使用する `toHaveNoViolations` matcher の型定義。
 *
 * - 実体（matcher の登録）は `vitest.setup.ts` の `expect.extend(...)` が担う。
 * - ここでは TypeScript の型チェックで matcher が解決できることのみを保証する。
 */
declare module 'vitest' {
  interface Assertion<T = any> {
    toHaveNoViolations(this: Assertion<AxeResults>): T;
  }

  interface AsymmetricMatchersContaining {
    toHaveNoViolations(): unknown;
  }
}
