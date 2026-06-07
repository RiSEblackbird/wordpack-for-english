export interface ExampleExplanationSections {
  summary: string | null;
  structure: string | null;
  details: string | null;
}

const emptySections: ExampleExplanationSections = {
  summary: null,
  structure: null,
  details: null,
};

const stripNumberPrefix = (value: string) => value.replace(/^\s*\d+\s*[).:：、]\s*/, '').trim();

const stripLabelPrefix = (value: string, labels: string[]) => {
  const numbered = stripNumberPrefix(value);
  for (const label of labels) {
    const pattern = new RegExp(`^${label}\\s*[：:]?\\s*`);
    if (pattern.test(numbered)) return numbered.replace(pattern, '').trim();
  }
  return numbered;
};

const joinParts = (parts: string[]) => {
  const joined = parts.map((part) => part.trim()).filter(Boolean).join('\n\n');
  return joined || null;
};

export const splitExampleExplanation = (value?: string | null): ExampleExplanationSections => {
  const raw = value?.trim();
  if (!raw) return emptySections;

  const paragraphs = raw
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean);
  const summaryParts: string[] = [];
  const structureParts: string[] = [];
  const detailParts: string[] = [];

  paragraphs.forEach((paragraph, index) => {
    const normalized = stripNumberPrefix(paragraph);
    if (/^(品詞分解|文法分解|品詞|語句分解)\s*[：:]/.test(normalized)) {
      detailParts.push(stripLabelPrefix(paragraph, ['品詞分解', '文法分解', '品詞', '語句分解']));
      return;
    }
    if (/^(構文|文構造|文の構造)\s*[：:]/.test(normalized)) {
      structureParts.push(stripLabelPrefix(paragraph, ['構文', '文構造', '文の構造']));
      return;
    }
    if (/^解説\s*[：:]?/.test(normalized)) {
      summaryParts.push(stripLabelPrefix(paragraph, ['解説']));
      return;
    }
    if (paragraphs.length > 1 && index === 0 && /【.+?】|\/.+?【/.test(paragraph)) {
      detailParts.push(paragraph);
      return;
    }
    summaryParts.push(paragraph);
  });

  return {
    summary: joinParts(summaryParts),
    structure: joinParts(structureParts),
    details: joinParts(detailParts),
  };
};
