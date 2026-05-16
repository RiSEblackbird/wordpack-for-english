export type { ArticleDetailData } from '../../../components/ArticleDetailModal';

export interface ArticleWordPackLink {
  word_pack_id: string;
  lemma: string;
  status: 'existing' | 'created';
  is_empty?: boolean;
}
