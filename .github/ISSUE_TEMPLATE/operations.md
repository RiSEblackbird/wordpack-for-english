---
name: Operations / Production Investigation
about: Cloud Run、Firebase、Firestore、外部API、本番・準本番運用調査
---

# Operations / Production Investigation

## 対象

- サービス: Cloud Run / Firebase Hosting / Firestore / 外部 API / その他
- 環境: production / staging / local / CI
- 発生日時・期間:

## 背景・トリガー

## 現象・影響

- 現象:
- ユーザー影響:
- データ影響:
- セキュリティ影響:

## 確認する証跡

- [ ] Cloud Run logs
- [ ] Firebase Hosting
- [ ] Firestore data / indexes
- [ ] 外部 API status / error
- [ ] CI / deploy logs
- [ ] その他:

## 公開安全性

- [ ] 機密値、認証情報、個人情報、本番ログ原文を Issue に残さない
- [ ] request ID、trace ID、完全な revision 名など、一意に掘れる識別子は必要最小限に丸める
- [ ] 本番ログを確認していない場合は、原因断定せずコード上の仮説として書く

## 調査方針

## 受け入れ条件

- [ ] 観測事実、推測、未確認範囲が分けて書かれている
- [ ] 原因または有力仮説が説明されている
- [ ] 復旧確認または次の最短アクションが明記されている
- [ ] 後続実装が必要なら Issue / PR に分離されている

## 非対象

- N/A

## 完了時に残す証跡

## リスク
