# 付録: OpenAIモデル設定（Responses API）

本プロジェクトで選択できる LLM は `gpt-5.4-mini` と `gpt-5.4-nano` の 2 種だけです。バックエンドは Responses API に対して `max_output_tokens` と、必要に応じて `reasoning` / `text` を送信し、旧世代向けの `temperature`、`max_tokens`、`max_completion_tokens` は使用しません。

JSON 生成を強制したい呼び出しでは、Responses API の `text.format={"type":"json_object"}` を使います。`response_format` は Responses API には送信しません。

## 制御できるパラメータ

- `model`: `gpt-5.4-mini` または `gpt-5.4-nano`
- `reasoning.effort`: `minimal` / `low` / `medium` / `high`
- `text.verbosity`: `low` / `medium` / `high`
- `text.format`: JSON 生成時に内部で `{"type": "json_object"}` を付与
- `max_output_tokens`: `.env` の `LLM_MAX_TOKENS`

## 設定例

```json
{
  "model": "gpt-5.4-mini",
  "reasoning": { "effort": "minimal" },
  "text": { "verbosity": "medium" }
}
```

## 運用メモ

- 通常は `gpt-5.4-mini` を使い、軽量化したい場合に `gpt-5.4-nano` を選びます。
- 出力のまとまりや一貫性は `reasoning.effort`、文量や詳細度は `text.verbosity` で調整します。
- JSON 途中切れが疑われる場合は `LLM_MAX_TOKENS` を増やします。
- モデル側が `reasoning` や `text.verbosity` を拒否した場合、バックエンドは JSON 形式指定だけを残して再試行し、それも拒否された場合はプロンプト内の JSON 指示に委ねて再試行します。
