# ゲスト公開フラグ API（WordPack 単位）

## 概要
- **公開範囲**: WordPack 単位で `guest_public` を管理します。
- **例文の扱い**: 例文は WordPack に紐づくため、WordPack が公開なら例文も公開されます。
- **拡張余地**: 例文単位で公開制御が必要になった場合は `examples` コレクション側へ `guest_public` を追加する設計に拡張可能です。

## 権限
- **更新**: ログイン済みユーザーのみ許可（ゲスト/匿名は拒否）。
- **閲覧（ゲスト）**: `guest_public=true` の WordPack のみ返却。

## API

### 公開フラグ更新
`POST /api/word/packs/{word_pack_id}/guest-public`

**Request**
```json
{
  "guest_public": true
}
```

**Response**
```json
{
  "word_pack_id": "wp:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "guest_public": true
}
```

**メモ**
- 更新後は `word_packs.metadata.guest_public` が保存されます。
- 監査用の構造化ログに `event`, `word_pack_id`, `user_id` を記録します。

### ゲスト閲覧時のフィルタ
`GET /api/word/packs`

- ゲスト閲覧モードの場合は `guest_public=true` の WordPack のみ返却されます。
- `GET /api/word/packs/{word_pack_id}` と `GET /api/word?lemma=...` も同様に非公開の WordPack は 404 で返却されます。
