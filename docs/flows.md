# 付録: LangGraph ベースのAI処理フロー

## WordPackFlow（語彙パック生成）
```mermaid
graph TD
    A[Client: POST /api/word/pack] --> B[WordPackFlow];
    B --> C["retrieve(lemma) - OpenAI LLMでJSON生成/解析"];
    C --> D["synthesize(...) - 発音/語義/共起/対比/例文/語源/学習カードを構成"];
    D --> E["examples(generate per category) - Dev/CS/LLM/Business/Common"];
    E --> F["WordPack Response（citations/confidence 付与）"];

    subgraph LangGraph_StateGraph
        G[generate per category]
        G --> G
    end
```

## ArticleImportFlow（文章インポート）
```mermaid
graph TD
    A[Client: POST /api/article/import] --> B[ArticleImportFlow];
    B --> T[Title Subgraph: generate_title];
    T --> TR[Translation Subgraph: generate_translation];
    TR --> EX[Explanation Subgraph: generate_explanation];
    EX --> LM[Lemma Subgraph: generate_lemmas];
    LM --> FL[filter_lemmas: 句優先/機能語除外/記号除外/重複排除];
    FL --> LC[link_or_create: 既存WordPack紐付け/なければ空パック作成];
    LC --> SA[save_article: 記事保存・メタ取得（llm_model/llm_paramsを含む）];
    SA --> R[ArticleDetailResponse];

    subgraph Langfuse Spans
        T --- T1((span: article.title.prompt))
        T --- T2((span: article.title.llm))
        TR --- TR1((span: article.translation.prompt))
        TR --- TR2((span: article.translation.llm))
        EX --- EX1((span: article.explanation.prompt))
        EX --- EX2((span: article.explanation.llm))
        LM --- LM1((span: article.lemmas.prompt))
        LM --- LM2((span: article.lemmas.llm))
        FL --- FL1((span: article.filter_lemmas))
        LC --- LC1((span: article.link_or_create_wordpacks))
        SA --- SA1((span: article.save_article))
    end
```