# 付録: OpenAIモデルの比較情報（Responses API）

- 本プロジェクトのバックエンドは Responses API を使用します。推論系の `reasoning`/`text` パラメータはモデルに応じて適用され、未対応エラー時は自動でパラメータを外して再試行します。

## 本プロジェクトで制御できるパラメータ（Responses API）
- gpt-4o-mini / gpt-4.1-mini: `temperature`, `max_output_tokens`（= `.env: LLM_MAX_TOKENS`）
- gpt-5-mini: `reasoning.effort`, `text.verbosity`, `max_output_tokens`（`temperature` は通常無効）

**結論**: gpt-5-mini は推論系（reasoning）モデルで、Responses API で `reasoning`/`text` を利用します。gpt-4.1-mini と gpt-4o-mini は従来どおり `temperature` が有効です。

UI補足: フロントで `gpt-5-mini` を選択した場合は `reasoning.effort`/`text.verbosity` がバックエンドに渡され有効化されます。非推論系では `temperature` が有効です。

---

## モデル別の設定例

### gpt-5-mini（reasoning系：`temperature`は通常無効）
```json
{
  "model": "gpt-5-mini",
  "max_output_tokens": 1600
}
```

### gpt-4.1-mini（従来型テキスト：sampling系が有効）
```json
{
  "model": "gpt-4.1-mini",
  "temperature": 0.45,
  "max_tokens": 1600
}
```

### gpt-4o-mini（高コスパ量産：sampling系が有効）
```json
{
  "model": "gpt-4o-mini",
  "temperature": 0.60,
  "max_tokens": 1600
}
```

---

## 80語×10文タスク向けの微調整ヒント
- 語数の安定化: Responses API の Structured Outputs や JSON スキーマで `minItems=10`/`maxItems=10`、各文 `word_count` を 70–90 などで制約すると安定します（どのモデルでも可）。
- gpt-5-mini を使うときは `temperature` ではなく `reasoning.effort` を段階的に上げ下げして文のまとまり・一貫性を調整（例: `minimal`→高速量産、`low/medium`→表現の精緻化）。

---

## 参考：なぜ `temperature` が「廃止扱い」なのか
- 推論系モデル（o3/o4-mini/GPT-5系）では内部で思考トークンを別勘定し、その振る舞いを `reasoning.effort` 等で制御する設計に移行。多くの推論系で `temperature` は未サポート。
- 非推論モデル（GPT-4.1系・4o系）では `temperature`/`top_p` が引き続きサポートされ、APIリファレンスでも調整指針（どちらか片方を調整）が示されています。

参考リンク:
- [Azure OpenAI reasoning models - GPT-5 series, o3-mini, o1, o1-mini - Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/reasoning)
- [OpenAI API Reference (Responses)](https://platform.openai.com/docs/api-reference/responses-streaming/response/function_call_arguments)
- [OpenAI Cookbook: GPT-4.1 Prompting Guide](https://cookbook.openai.com/examples/gpt4-1_prompting_guide)
- [OpenAI Cookbook: GPT-5 New Params and Tools](https://cookbook.openai.com/examples/gpt-5/gpt-5_new_params_and_tools)
