### DB ER 図（Mermaid）

以下は Firestore 移行前の SQLite 実装に基づく主要テーブルとリレーションのER図です。現行の Firestore コレクション設計を把握するための参考資料として残しています。

```mermaid
erDiagram
    lemmas    ||--o{ word_packs        : labels
    word_packs ||--o{ word_pack_examples : has
    articles   ||--o{ article_word_packs : links
    word_packs ||--o{ article_word_packs : linked_by

    lemmas {
        TEXT id PK
        TEXT label
        TEXT sense_title
        TEXT llm_model
        TEXT llm_params
        TEXT created_at
    }

    word_packs {
        TEXT id PK
        TEXT lemma_id FK
        TEXT data
        TEXT created_at
        TEXT updated_at
        INTEGER checked_only_count
        INTEGER learned_count
    }

    word_pack_examples {
        INTEGER id PK
        TEXT word_pack_id FK
        TEXT category
        INTEGER position
        TEXT en
        TEXT ja
        TEXT grammar_ja
        TEXT llm_model
        TEXT llm_params
        TEXT created_at
    }

    articles {
        TEXT id PK
        TEXT title_en
        TEXT body_en
        TEXT body_ja
        TEXT notes_ja
        TEXT llm_model
        TEXT llm_params
        TEXT generation_category
        TEXT created_at
        TEXT updated_at
        TEXT generation_started_at
        TEXT generation_completed_at
        INTEGER generation_duration_ms
    }

    article_word_packs {
        TEXT article_id FK
        TEXT word_pack_id FK
        TEXT lemma
        TEXT status
        TEXT created_at
    }
```

補足:
- `word_pack_examples.word_pack_id` は `word_packs.id` を参照（ON DELETE CASCADE）。
- `word_packs.lemma_id` は `lemmas.id` を参照（ON DELETE CASCADE）。
- `article_word_packs.article_id` は `articles.id` を参照（ON DELETE CASCADE）。
- `article_word_packs.word_pack_id` は `word_packs.id` を参照（ON DELETE CASCADE）。
- `article_word_packs` の主キーは `(article_id, word_pack_id)` の複合主キー。
- インデックス（実装由来）
  - `idx_lemmas_label_ci(lower(label))`
  - `idx_word_packs_lemma_id(lemma_id)`, `idx_word_packs_created_at(created_at)`
  - `idx_wpex_pack(word_pack_id)`, `idx_wpex_pack_cat_pos(word_pack_id, category, position)`
  - `idx_articles_created_at(created_at)`, `idx_articles_title(title_en)`
  - `idx_article_wps_article(article_id)`, `idx_article_wps_lemma(lemma)`

データ由来の値の例:
- `word_pack_examples.category`: {"Dev","CS","LLM","Business","Common"}
- `article_word_packs.status`: {"existing","created"}


