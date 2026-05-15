import { describe, expect, it } from 'vitest';
import { parseAppRoute, routeToPath } from './routes';

describe('dictionary routes', () => {
  it('maps root and lexicon to the lexicon route', () => {
    expect(parseAppRoute('/')).toEqual({ key: 'lexicon' });
    expect(parseAppRoute('/lexicon')).toEqual({ key: 'lexicon' });
  });

  it('round-trips WordPack detail IDs', () => {
    const route = parseAppRoute('/wordpacks/wp%3Atest%3A1');
    expect(route).toEqual({ key: 'wordpackDetail', wordPackId: 'wp:test:1' });
    expect(routeToPath(route)).toBe('/wordpacks/wp%3Atest%3A1');
  });

  it('falls back to lexicon for unknown paths', () => {
    expect(parseAppRoute('/unknown')).toEqual({ key: 'lexicon' });
  });
});

