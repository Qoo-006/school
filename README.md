# 知能情報科学セミナーⅠ ─ BVH動作解析レポート

工学院大学 情報学部 情報科学科 3年　**平松 瑠希**

mocopi（ソニー製モバイルモーションキャプチャ）で取得した 4 名 × 3 動作（歩く・走る・スキップ）= 12 サンプルの BVH モーションデータを、信号処理の基礎理論（自己相関関数・相互相関関数・連続ウェーブレット変換・動的時間伸縮）を用いて解析したレポート。

---

## 🌐 Web 版レポート

**https://qoo-006.github.io/school/**

GitHub Pages で公開中。デザインは工学院大学のロゴ準拠（navy/yellow/white）で統一。

---

## 📑 結論

> **急いでいる時は、スキップで移動することをお勧めします**

5 つの根拠（速度・リズム・対称性・習得不要・動作の安定）で「スキップは合理的な移動手段」を数値的に示した。

---

## 📁 リポジトリ構成

```
school/
├── index.html                          ← Web 版レポート本体
├── README.md                            ← このファイル
│
├── BVH動作解析_平松.pptx                ← 自動生成版 PPTX（54 枚）
├── BVH動作解析_平松_最終版.pptx          ← 編集後の最終 PPTX（発表用）
│
├── bvh_data/                            ← 入力データ（12 サンプル）
│   ├── Ruki_walk.BVH                    (平松 瑠希 × 歩く)
│   ├── Ruki_run.BVH                     (平松 瑠希 × 走る)
│   ├── Ruki_skip.BVH                    (平松 瑠希 × スキップ)
│   ├── Sora_walking.BVH, Sora_running.BVH, Sora_skip.BVH   (三橋 青空)
│   ├── Shota Walkin.BVH, Sho_run.bvh.BVH, Shota_skip.BVH   (長岡 翔太)
│   └── Nori.walk.BVH, Nori.run.BVH, Nori.skip.BVH          (松田 宣久)
│
├── videos/                              ← 撮影動画（mocopi 同時計測）
│   ├── Ruki_walk.mov, Ruki_run.mov, Ruki_skip.mov
│   ├── Sora_*.mov, Shota_*.mp4, Nori_*.mp4
│   └── ...
│
├── analysis/                            ← 新規解析結果（PNG + JSON）
│   ├── cwt/                             ← 連続ウェーブレット変換
│   │   ├── walk_avg.png / run_avg.png / skip_avg.png    (4 人平均)
│   │   ├── individuals/                                  (12 個人別)
│   │   └── cwt_summary.json
│   └── dtw/                             ← 動的時間伸縮
│       ├── distance_matrix.png          (4×4 距離マトリクス)
│       ├── distance_summary.png         (動作別平均距離)
│       ├── warping_example.png          (DTW 内部可視化)
│       └── dtw_summary.json
│
├── reading_guide/                       ← READING GUIDE 用 注釈付き PNG
│   ├── img_01_root_position.png         (Step 1)
│   ├── img_02_root_vs_foot.png          (Step 2)
│   ├── img_03_left_right.png            (Step 3)
│   ├── img_04_acf.png                   (Step 4)
│   ├── img_05_ccf.png                   (Step 5)
│   └── img_06_score.png                 (Step 6)
│
├── legacy_graphs/                       ← 既存解析グラフ（acf/overview/symmetry × 12）
│   ├── {person}_{motion}_overview.png   (Root位置・加速度・足首回転)
│   ├── {person}_{motion}_acf.png        (自己相関)
│   ├── {person}_{motion}_symmetry.png   (相互相関)
│   ├── chart_cadence.png, chart_speed.png, chart_symmetry.png, chart_efficiency.png
│   └── ext_*.png                        (拡張解析: 左右ACF / 腕足CCF / 減衰 / レーダー)
│
├── assets/                              ← ロゴ
│   ├── kogakuin_logo.png
│   ├── kogakuin_logo_en.svg
│   └── kogakuin_logo_jp.svg
│
└── build_*.py                           ← 解析・スライド生成スクリプト
    ├── build_cwt.py                     ← CWT 解析 → analysis/cwt/
    ├── build_dtw.py                     ← DTW 解析 → analysis/dtw/
    ├── build_cyclogram.py               ← サイクログラム解析（旧、現バージョンでは不使用）
    ├── build_reading_guide.py           ← READING GUIDE 用 PNG 生成
    └── build_pptx.py                    ← HTML 内容を PPTX に変換（python-pptx）
```

---

## 🔬 解析手法

### 既存手法
| # | 手法 | 用途 |
|---|------|------|
| 1 | 自己相関関数 (ACF) | ストライド周期 T の推定 |
| 2 | 歩調・歩数算出 | cadence = 1/T、steps = (duration/T)×2 |
| 3 | 相互相関関数 (CCF) | 左右足首の対称性スコア |

### 新規追加手法
| # | 手法 | 用途 |
|---|------|------|
| 4 | 連続ウェーブレット変換 (CWT) | 時間 × 周波数 2D マップでリズムの揺らぎを可視化 |
| 5 | 動的時間伸縮 (DTW) | 4 人の波形類似度をペアワイズ距離で測定 |

---

## 🚀 再実行方法

```bash
# 1. 依存パッケージのインストール
pip3 install numpy scipy matplotlib pywavelets dtw-python pillow python-pptx

# 2. BVH データ確認
ls bvh_data/

# 3. 各解析スクリプトの実行
python3 build_cwt.py              # → analysis/cwt/
python3 build_dtw.py              # → analysis/dtw/
python3 build_reading_guide.py    # → reading_guide/

# 4. PPTX 生成
python3 build_pptx.py             # → BVH動作解析_平松.pptx
```

---

## 📚 参考文献（抜粋）

[1] 和田成夫: 『よくわかる信号処理 ─ フーリエ解析からウェーブレット変換まで』, 森北出版, 2009.
[2] 中野宏毅, 山本鎭男, 吉田靖夫: 『ウェーブレットによる信号処理と画像処理』, 共立出版, 1999.
[3] 山田昇吾, 高柳英明: "歩きやすさ評価を目的とした歩行加速度特性に関する研究", 日本建築学会技術報告集, 29(72), 999-1004, 2023.
[4] 芥川友彬ほか: "加速度センサを用いた歩行分析の妥当性", 保健医療学雑誌, 6(1), 10-14, 2015.
[5] Minetti, A. E. (1998). The biomechanics of skipping gaits: a third locomotion paradigm? Proc R Soc B, 265(1402), 1227–1235.
[6] Cavagna, G. A., Heglund, N. C. and Taylor, C. R. (1977). Mechanical work in terrestrial locomotion. Am J Physiol, 233(5), R243–R261.
[7] ソニー株式会社: "mocopi モバイルモーションキャプチャー 技術仕様", https://www.sony.jp/mocopi/feature/

---

## 📝 ライセンス

学術目的のレポートです。データ・コードの利用は研究・教育目的に限ります。
工学院大学のロゴ使用については [大学公式規定](https://www.kogakuin.ac.jp/about/kogakuin/logo.html) に準拠。

---

**最終更新**: 2026-05-21
