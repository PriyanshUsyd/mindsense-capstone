# CLAUDE.md — MindSense / DATA5702

Statistical Analysis Lead (Moe Tanaka) の作業リポジトリ。git 管理外。

## 文書と実装の同期規則

`analysis/` 配下のコードを変更した場合、同じセッション内で以下の文書に反映すること。
変更だけして文書を残すのは禁止。

- `analysis/preregistration.md`
- `Week5_Statistical_Analysis_Deliverable.md`

反映が難しい場合は、変更内容を下記「未反映の変更」セクションに追記して、
次のセッションに引き継ぐこと。

## 未反映の変更

（コードを変更したが文書に反映できなかった項目をここに追記する。
反映が済んだら該当行を削除する。日付・対象ファイル・変更内容を書くこと。）

現在なし。

## 確定済みの決定事項（変更には Statistical Analysis Lead の承認が必要）

- 品質ゲート **12h**
- 比較窓 **`[-14, -1]`**、baseline 窓 **`[-42, -15]`** / **`[-70, -15]`**
- 変換順序 **`log(mean)`**。**`mean(log)` は使用禁止**
- recency 窓は **14日に統一**、`RECENCY_WINDOW_DAYS` は**廃止**
- cohort-level family = **213**、**BH-FDR が報告値**、Holm は感度分析
- user-facing は **2値**（`evidence_available` / `no_claim`）
- cold-start は**評価機会ごと**、**State C は永続しない**

## セッション開始時の確認

このリポジトリは複数のセッションから作業されている。
作業開始前に `analysis/` 配下の更新時刻を確認し、文書より新しいコードがないか
確認すること。

```bash
find analysis -type f -not -path "*__pycache__*" -printf "%T+  %p\n" | sort | tail -20
ls -l --time-style=full-iso analysis/preregistration.md Week5_Statistical_Analysis_Deliverable.md
```

文書の更新時刻より新しいコードがあれば、それが未反映の変更である可能性が高い。
