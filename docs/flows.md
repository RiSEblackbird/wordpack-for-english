# 付録: LangGraph ベースのAI処理フロー

## WordPackFlow（語彙パック生成）
```mermaid
graph TD
    A[Client: POST /api/word/pack] --> B[WordPackFlow];
    B --> C["retrieve(lemma) - OpenAI LLMでJSON生成/解析（RAGは既定で無効）"];
    C --> D["synthesize(...) - 発音/語義/共起/対比/例文/語源/学習カードを構成"];
    D --> E["examples(generate per category) - Dev/CS/LLM/Business/Common"];
    E --> F["WordPack Response（citations/confidence 付与）"];

    subgraph LangGraph_StateGraph
        G[generate(category,count)] --> G
    end
```
