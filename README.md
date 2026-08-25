# 授業成果物アーカイブ — 工学院大学 情報学部 情報科学科

**平松 瑠希（J324247）**　授業ごとにフォルダを分けて保管している。

🌐 **https://qoo-006.github.io/school/** — 目次ページ（各成果物へのリンク）

---

## 授業一覧

| 授業 | 成果物 | 種別 | Web版 |
|------|--------|------|-------|
| **情報科学セミナーⅠ**<br>（経営情報システム研究室／三木研） | [BVH動作解析](seminar-1/bvh-motion/) | レポート + 発表PPTX | [→](https://qoo-006.github.io/school/seminar-1/bvh-motion/) |
| | [飲料戦略分析](seminar-1/beverage/) | レポート | [→](https://qoo-006.github.io/school/seminar-1/beverage/) |
| **予測モデリング** | [ベイズ統計 学習ノート](predictive-modeling/bayes/) | 学習ノート | [→](https://qoo-006.github.io/school/predictive-modeling/bayes/) |

---

## 構成

```
school/
├── index.html                  ← 目次ページ（授業ごとのカード）
├── assets/                     ← 工学院ロゴ（目次ページ用）
│
├── seminar-1/                  ← 情報科学セミナーⅠ
│   ├── bvh-motion/             ← BVH動作解析（index.html + データ + 解析スクリプト + PPTX）
│   └── beverage/               ← 飲料戦略分析（単一HTML・自己完結）
│
└── predictive-modeling/        ← 予測モデリング
    └── bayes/                  ← ベイズ統計 学習ノート（単一HTML・自己完結）
```

各成果物フォルダは**自己完結**させる（相対パスがフォルダ内で閉じる）。
`bvh-motion/` が自前の `assets/` を持っているのはそのため。

---

## 新しい授業・成果物を足すとき

1. `{授業スラッグ}/{成果物スラッグ}/` を作る（**スラッグはASCII**。日本語だとURLが percent-encode されて読めなくなる）
2. 成果物一式をその中に入れる。**相対パスはフォルダ内で完結させる**
3. ルートの `index.html` にカードを1枚足す（授業が新規なら `<section class="course">` ごと）
4. この README の授業一覧に行を足す

デザインは工学院大学のロゴ準拠で統一する。

| トークン | 値 |
|---------|-----|
| navy | `#2c4198` |
| navy-light | `#4256ad` |
| yellow | `#fdd000` |
| text / muted | `#1a1a1a` / `#666` |
| フォント | `"Hiragino Sans", "ヒラギノ角ゴシック", "Yu Gothic", sans-serif` |

---

## 関連

成果物の生成は Qoo.000 のスキルで行う。

- `kogakuin-deck` — 授業発表・ゼミ発表のスライド（HTML → 編集可能PPTX）
- `kogakuin-report` — 授業レポート／論文（HTML → PDF・情報処理学会形式に対応）
