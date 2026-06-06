export type LemmaValidationResult = {
  valid: boolean;
  message: string;
  normalizedLemma: string;
};

export const LEMMA_ALLOWED_PATTERN = /^[A-Za-z0-9-' ]+$/;
export const LEMMA_MAX_LENGTH = 64;
export const LEMMA_RULE_MESSAGE = '英数字・半角スペース・ハイフン・アポストロフィのみ（最大64文字）';

export function validateLemmaInput(value: string): LemmaValidationResult {
  const normalizedLemma = value.trim();
  if (!normalizedLemma) {
    return {
      valid: false,
      message: '見出し語を入力してください（英数字・ハイフン・アポストロフィ・半角スペースのみ）',
      normalizedLemma,
    };
  }
  if (normalizedLemma.length > LEMMA_MAX_LENGTH) {
    return {
      valid: false,
      message: `見出し語は最大${LEMMA_MAX_LENGTH}文字までです（英数字・半角スペース・ハイフン・アポストロフィのみ）`,
      normalizedLemma,
    };
  }
  if (!LEMMA_ALLOWED_PATTERN.test(normalizedLemma)) {
    return {
      valid: false,
      message: '英数字と半角スペース、ハイフン、アポストロフィのみ利用できます',
      normalizedLemma,
    };
  }
  return {
    valid: true,
    message: LEMMA_RULE_MESSAGE,
    normalizedLemma,
  };
}
