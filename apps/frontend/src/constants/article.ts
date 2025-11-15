/**
 * 文章インポートに利用する文字数上限を一元管理する定数。
 * バックエンド (ArticleImportRequest.max_length) と同期する運用のため、
 * UI層ではこの値のみを参照して制御を行う。
 */
export const ARTICLE_IMPORT_TEXT_MAX_LENGTH = 4000;
