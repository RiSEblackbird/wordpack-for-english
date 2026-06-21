export interface ExampleExplanationSections {
  summary: string | null;
  structure: string | null;
  details: string | null;
}

export interface ExampleTranslationPair {
  index: number;
  en: string;
  ja: string;
}

const emptySections: ExampleExplanationSections = {
  summary: null,
  structure: null,
  details: null,
};

const normalizeInlineText = (value: string) => value.replace(/\s+/g, ' ').trim();

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

const partBreakdownPattern =
  /\/\s*[^/]+?【|【[^】]*(?:名詞|名|動詞|動|形容詞|形|副詞|副|前置詞|接続詞|主語|主|述語|目的語|目的|補語|修飾|従属節|前置詞句)[^】]*】|(?:名詞|動詞|形容詞|副詞|前置詞|接続詞|主語|述語|目的語)[/＝=]/;

const looksLikePartBreakdown = (value: string) => partBreakdownPattern.test(value);

const splitDetailAndSummary = (value: string) => {
  const trimmed = value.trim();
  const marker = /[。.!?]\s*(?=(文の核|この文|ここでは|全体として|意味として|文全体|ポイント|要点))/u.exec(trimmed);
  if (!marker || marker.index < 0) {
    return { detail: trimmed, summary: null };
  }
  const boundary = marker.index + 1;
  const detail = trimmed.slice(0, boundary).trim();
  const summary = trimmed.slice(boundary).trim();
  return {
    detail: detail || null,
    summary: summary || null,
  };
};

const pushBreakdownWithOptionalSummary = (value: string, detailParts: string[], summaryParts: string[]) => {
  const lines = value
    .split(/\n+/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (lines.length > 1) {
    const detailLines = lines.filter(looksLikePartBreakdown);
    const summaryLines = lines.filter((line) => !looksLikePartBreakdown(line));
    if (detailLines.length > 0) {
      detailParts.push(detailLines.join('\n'));
      summaryParts.push(...summaryLines);
      return;
    }
  }

  const separated = splitDetailAndSummary(value);
  if (separated.detail) detailParts.push(separated.detail);
  if (separated.summary) summaryParts.push(separated.summary);
};

const splitEnglishSentences = (value: string) => {
  const normalized = normalizeInlineText(value);
  if (!normalized) return [];
  const periodPlaceholder = '\uE000';
  const protectedText = normalized
    .replace(/\b(?:[A-Za-z]\.){2,}/g, (match) => match.replace(/\./g, periodPlaceholder))
    .replace(/\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc|No)\./gi, (match) =>
      match.replace(/\./g, periodPlaceholder),
    )
    .replace(/\b(?:Node|Next|React|Vue)\.js\b/gi, (match) => match.replace(/\./g, periodPlaceholder))
    .replace(/(\d)\.(?=\d)/g, `$1${periodPlaceholder}`);
  const parts = protectedText.match(/[^.!?]+[.!?]+["')\]]*|[^.!?]+$/g) ?? [protectedText];
  return parts
    .map((part) => part.replace(/\uE000/g, '.').trim())
    .filter(Boolean);
};

const splitJapaneseSentences = (value: string) => {
  const normalized = normalizeInlineText(value);
  if (!normalized) return [];
  const parts = normalized.match(/[^。！？]+[。！？]+|[^。！？]+$/g) ?? [normalized];
  return parts.map((part) => part.trim()).filter(Boolean);
};

export const buildExampleTranslationPairs = (en: string, ja: string): ExampleTranslationPair[] => {
  const enSentences = splitEnglishSentences(en);
  const jaSentences = splitJapaneseSentences(ja);

  if (enSentences.length > 0 && enSentences.length === jaSentences.length) {
    return enSentences.map((sentence, index) => ({
      index: index + 1,
      en: sentence,
      ja: jaSentences[index],
    }));
  }

  return [
    {
      index: 1,
      en: normalizeInlineText(en),
      ja: normalizeInlineText(ja),
    },
  ];
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
      pushBreakdownWithOptionalSummary(
        stripLabelPrefix(paragraph, ['品詞分解', '文法分解', '品詞', '語句分解']),
        detailParts,
        summaryParts,
      );
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
    if ((paragraphs.length > 1 || index === 0) && looksLikePartBreakdown(paragraph)) {
      pushBreakdownWithOptionalSummary(paragraph, detailParts, summaryParts);
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
