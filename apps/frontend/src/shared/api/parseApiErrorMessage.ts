import {
  formatObjectDetail,
  formatValidationDetail,
  getFastApiDetail,
  type FastApiDetailObject,
} from './fastapiDetail';

export const parseApiErrorMessage = (status: number, data: unknown): string => {
  let message = `Request failed: ${status}`;
  const detail = getFastApiDetail(data);
  if (detail !== undefined) {
    if (Array.isArray(detail)) {
      message = formatValidationDetail(detail);
    } else if (detail && typeof detail === 'object') {
      message = formatObjectDetail(detail as FastApiDetailObject);
    } else {
      message = String(detail);
    }
  }
  return message;
};
