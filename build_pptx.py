"""HTML レポートの内容を PPTX に変換する。

各セクションを 1 〜 2 枚のスライドに展開。
工学院大学ロゴ準拠の navy/yellow/white パレットで統一。
スライドサイズ 16:9 (13.333" × 7.5")。

出力: /tmp/school/BVH動作解析_平松.pptx
"""
from __future__ import annotations
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from copy import deepcopy

# ===== 色定義（ロゴ準拠） =====
NAVY = RGBColor(0x2C, 0x41, 0x98)
NAVY_LIGHT = RGBColor(0x42, 0x56, 0xAD)
YELLOW = RGBColor(0xFD, 0xD0, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x55, 0x55, 0x55)
DARKGRAY = RGBColor(0x23, 0x18, 0x15)

LOGO_PATH = Path("/tmp/school/assets/kogakuin_logo.png")
RG = Path("/tmp/school/reading_guide")
CWT = Path("/tmp/school/analysis/cwt")
DTW = Path("/tmp/school/analysis/dtw")
OUT = Path("/tmp/school/BVH動作解析_平松.pptx")

# プレゼンテーション設定
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SLIDE_W = prs.slide_width
SLIDE_H = prs.slide_height

BLANK = prs.slide_layouts[6]  # Blank layout


# ===== ヘルパ =====
def add_logo(slide, scale: float = 1.0):
    """工学院大学ロゴを右上に配置（白地カード風）"""
    w = Inches(1.6 * scale)
    h = Inches(0.55 * scale)
    left = SLIDE_W - w - Inches(0.3)
    top = Inches(0.25)
    pic = slide.shapes.add_picture(str(LOGO_PATH), left, top, width=w, height=h)
    return pic


def add_bg(slide, color):
    """スライドの背景色を設定"""
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    bg.line.fill.background()
    # 最背面へ
    spTree = bg._element.getparent()
    spTree.remove(bg._element)
    spTree.insert(2, bg._element)
    return bg


def add_textbox(slide, left, top, width, height, text, *,
                size: int = 18, bold: bool = False, color=DARKGRAY,
                align=PP_ALIGN.LEFT, font: str = "Hiragino Sans"):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0)
    tf.margin_right = Inches(0)
    tf.margin_top = Inches(0)
    tf.margin_bottom = Inches(0)
    tf.text = ""
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    return tb


def add_bullets(slide, left, top, width, height, items: list,
                size: int = 16, color=DARKGRAY, font: str = "Hiragino Sans"):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = f"●  {it}"
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = font
        p.space_after = Pt(6)
    return tb


def add_section_badge(slide, text: str):
    """左上にセクション番号バッジ"""
    w = Inches(2.5)
    h = Inches(0.45)
    left = Inches(0.5)
    top = Inches(0.32)
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, w, h)
    box.fill.solid()
    box.fill.fore_color.rgb = NAVY
    box.line.fill.background()
    tf = box.text_frame
    tf.margin_left = Inches(0.15)
    tf.margin_top = Inches(0.05)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = text
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = "Hiragino Sans"
    return box


def add_title(slide, text: str, top_in: float = 1.0, size: int = 32, color=NAVY):
    return add_textbox(slide, Inches(0.5), Inches(top_in), Inches(12), Inches(0.8),
                       text, size=size, bold=True, color=color)


def add_yellow_underline(slide, top_in: float, width_in: float = 1.5):
    """タイトルの下に黄色のアンダーライン"""
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(top_in),
                                  Inches(width_in), Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = YELLOW
    bar.line.fill.background()
    return bar


def add_image_centered(slide, img_path: Path, top_in: float = 1.9,
                       max_width_in: float = 11.5, max_height_in: float = 5.0):
    """画像を中央配置（最大幅・高さに収まるよう自動スケール）"""
    from PIL import Image
    with Image.open(img_path) as im:
        iw, ih = im.size
    aspect = iw / ih
    if max_width_in / aspect <= max_height_in:
        w = Inches(max_width_in)
        h = Inches(max_width_in / aspect)
    else:
        h = Inches(max_height_in)
        w = Inches(max_height_in * aspect)
    left = (SLIDE_W - w) / 2
    top = Inches(top_in)
    return slide.shapes.add_picture(str(img_path), left, top, width=w, height=h)


def add_finding(slide, label: str, title: str, body: str, top_in: float = 5.6):
    """FINDING 用の navy グラデーション風カード"""
    left = Inches(0.5)
    top = Inches(top_in)
    w = Inches(12.333)
    h = Inches(1.6)
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, h)
    card.fill.solid()
    card.fill.fore_color.rgb = NAVY
    card.line.fill.background()
    card.adjustments[0] = 0.05
    # ラベルバッジ（黄色）
    lb_w = Inches(1.2)
    lb_h = Inches(0.35)
    lb = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left + Inches(0.3),
                                top + Inches(0.2), lb_w, lb_h)
    lb.fill.solid()
    lb.fill.fore_color.rgb = YELLOW
    lb.line.fill.background()
    tf = lb.text_frame
    tf.margin_left = Inches(0.1); tf.margin_top = Inches(0.02)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = label
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = NAVY
    run.font.name = "Hiragino Sans"
    # タイトル
    add_textbox(slide, left + Inches(0.3), top + Inches(0.6),
                w - Inches(0.6), Inches(0.45),
                title, size=17, bold=True, color=WHITE)
    # 本文
    add_textbox(slide, left + Inches(0.3), top + Inches(1.0),
                w - Inches(0.6), Inches(0.55),
                body, size=12, color=WHITE)


def add_footer(slide, number: int, total: int):
    add_textbox(slide, Inches(0.5), SLIDE_H - Inches(0.45),
                Inches(6), Inches(0.3),
                "知能情報科学セミナーⅠ ── 平松瑠希 ── 工学院大学",
                size=9, color=GRAY)
    add_textbox(slide, SLIDE_W - Inches(1.5), SLIDE_H - Inches(0.45),
                Inches(1.0), Inches(0.3),
                f"{number} / {total}",
                size=9, color=GRAY, align=PP_ALIGN.RIGHT)


# ===== スライド生成 =====
def slide_title():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    # 上部の黄色バー
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.25))
    bar.fill.solid(); bar.fill.fore_color.rgb = YELLOW; bar.line.fill.background()
    # 左の縦 navy バー
    nv = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.35), SLIDE_H)
    nv.fill.solid(); nv.fill.fore_color.rgb = NAVY; nv.line.fill.background()
    # ロゴ（大きめ）
    pic = s.shapes.add_picture(str(LOGO_PATH), Inches(0.8), Inches(0.7),
                                width=Inches(3.5), height=Inches(1.2))
    # タイトル
    add_textbox(s, Inches(0.8), Inches(2.5), Inches(12), Inches(0.5),
                "知能情報科学セミナーⅠ", size=18, color=NAVY)
    add_textbox(s, Inches(0.8), Inches(3.0), Inches(12), Inches(1.2),
                "モーションキャプチャによる\n歩行・走行・スキップの定量解析",
                size=40, bold=True, color=NAVY)
    add_yellow_underline(s, 5.0, 2.0)
    add_textbox(s, Inches(0.8), Inches(5.15), Inches(12), Inches(0.45),
                "自己相関 (ACF) ・ 相互相関 (CCF) ・ 連続ウェーブレット変換 (CWT) ・ 動的時間伸縮 (DTW)",
                size=15, color=GRAY)
    add_textbox(s, Inches(0.8), Inches(5.85), Inches(12), Inches(0.4),
                "情報学部 情報科学科 3年", size=14, color=DARKGRAY)
    add_textbox(s, Inches(0.8), Inches(6.25), Inches(12), Inches(0.5),
                "平松 瑠希", size=22, bold=True, color=NAVY)


def slide_intro():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "01  INTRODUCTION")
    add_title(s, "背景・目的")
    add_yellow_underline(s, 1.75)
    add_textbox(s, Inches(0.5), Inches(2.0), Inches(12.5), Inches(0.6),
                "本レポートは、知能情報科学セミナーⅠで学んだ", size=15, color=DARKGRAY)
    add_textbox(s, Inches(0.5), Inches(2.4), Inches(12.5), Inches(0.5),
                "FFT に基づく自己相関 (ACF) ・相互相関 (CCF) の理論を実データに適用する実践演習",
                size=15, bold=True, color=NAVY)
    add_textbox(s, Inches(0.5), Inches(3.3), Inches(12), Inches(0.5),
                "研究の問い", size=20, bold=True, color=NAVY)
    add_bullets(s, Inches(0.5), Inches(3.9), Inches(12), Inches(2.5), [
        "「歩く・走る・スキップ」の動作にはどのようなリズム特性があるか？",
        "同じ動作でも個人差・左右差はどう現れるか？",
        "歩き方の癖・腕振りパターンは ACF でどこまで定量化できるか？",
        "そして、最も移動効率の良い動作は何か？",
    ], size=17)


def slide_data():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "02  DATA")
    add_title(s, "計測データ概要")
    add_yellow_underline(s, 1.75)
    add_bullets(s, Inches(0.5), Inches(2.0), Inches(12), Inches(2), [
        "計測機器: mocopi（ソニー製モーションキャプチャ・IMU センサー 6 個）",
        "フォーマット: BVH (BioVision Hierarchy) / 60 Hz サンプリング",
        "被験者: 三橋青空・長岡翔太・平松瑠希・松田宣久 の 4 名",
        "動作: 歩く・走る・スキップ × 4 名 = 計 12 サンプル",
        "記録項目: root の絶対位置 + 25 関節の回転角（うち 6 関節は IMU 実測、19 関節は AI 補完）",
    ], size=16)
    # サマリー BOX
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                              Inches(0.5), Inches(5.6), Inches(12.333), Inches(1.2))
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xF5, 0xF8, 0xFD)
    box.line.color.rgb = NAVY
    add_textbox(s, Inches(0.8), Inches(5.75), Inches(12), Inches(0.4),
                "解析対象信号", size=14, bold=True, color=NAVY)
    add_textbox(s, Inches(0.8), Inches(6.15), Inches(12), Inches(0.6),
                "主：root の鉛直加速度（歩行リズム検出） / 副：左右足首の Xrotation（背屈・底屈 ＝ つま先↑↓）",
                size=13, color=DARKGRAY)


def slide_method():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "03  METHOD")
    add_title(s, "解析手法")
    add_yellow_underline(s, 1.75)
    # 3 つの式を並べる
    cols = [
        ("① ストライド周期 T（ACF）",
         "ACF(τ) = IFFT(|X(f)|²)",
         "ウィーナー＝ヒンチン定理 / 最初の有意ピーク（>0.15）を T と推定"),
        ("② 歩調・歩数",
         "cadence = 1 / T  [Hz]\nsteps = (duration / T) × 2",
         "1 秒あたりのステップ数 / 計測時間内の総歩数"),
        ("③ 左右対称性スコア（CCF）",
         "CCF(τ) = IFFT(X*(f) · Y(f))\nScore = 0.6·RMS比 + 0.3·位相差 + 0.1·CCFピーク",
         "100 点満点の対称性スコア"),
    ]
    col_w = Inches(4.0)
    for i, (title, formula, desc) in enumerate(cols):
        left = Inches(0.5 + i * 4.27)
        # 見出し
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                  left, Inches(2.1), col_w, Inches(4.5))
        box.fill.solid(); box.fill.fore_color.rgb = WHITE
        box.line.color.rgb = NAVY
        add_textbox(s, left + Inches(0.2), Inches(2.3),
                    col_w - Inches(0.4), Inches(0.6),
                    title, size=14, bold=True, color=NAVY)
        # 式
        add_textbox(s, left + Inches(0.2), Inches(3.1),
                    col_w - Inches(0.4), Inches(2.0),
                    formula, size=13, color=DARKGRAY, font="Menlo")
        # 説明
        add_textbox(s, left + Inches(0.2), Inches(5.2),
                    col_w - Inches(0.4), Inches(1.4),
                    desc, size=12, color=GRAY)


def slide_reading_intro():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "READING GUIDE")
    add_title(s, "瑠希・歩くを教材に、グラフの読み方を学ぶ")
    add_yellow_underline(s, 1.95)
    add_textbox(s, Inches(0.5), Inches(2.4), Inches(12.5), Inches(3.5),
                "12 サンプル × 各 3 枚 = 36 枚以上のグラフが続く。\n"
                "いきなり全部見ても何が大事かわかりにくいので、\n"
                "ここでは「瑠希・歩く」を題材に、グラフを 6 ステップで読み解く方法を示す。\n\n"
                "ここで読み方を身につければ、後続の 11 サンプルも同じ要領で読める。",
                size=18, color=DARKGRAY)
    # 6 ステップ目次
    steps = [
        "STEP 1  腰の上下動を見る ─ 歩行リズムの正体",
        "STEP 2  足首のリズムは腰の「半分」 ─ 2 倍周期の謎",
        "STEP 3  左右の足を重ねる ─ 半周期ずれて動く",
        "STEP 4  自己相関（ACF）でリズムを数値化",
        "STEP 5  相互相関（CCF）で左右対称性を数値化",
        "STEP 6  対称性スコアの内訳 ─ 何が個性か",
    ]
    add_bullets(s, Inches(0.5), Inches(5.0), Inches(12.5), Inches(2.5),
                steps, size=13, color=NAVY)


def slide_reading_step(num: int, title: str, img: Path, point: str):
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, f"READING GUIDE  ─  STEP {num}")
    add_title(s, title, top_in=0.95, size=24)
    add_yellow_underline(s, 1.55)
    add_image_centered(s, img, top_in=1.85, max_width_in=11.5, max_height_in=4.4)
    add_finding(s, "POINT", "ここがポイント", point, top_in=6.4)


def slide_cwt_intro():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "★ NEW ANALYSIS ①")
    add_title(s, "連続ウェーブレット変換（CWT）─ 時間軸でリズムの揺らぎを追う", size=24)
    add_yellow_underline(s, 1.65)
    add_textbox(s, Inches(0.5), Inches(2.0), Inches(12.5), Inches(2.5),
                "ACF は「区間全体の平均的リズム」を 1 つの数値に落とすが、区間内でリズムがどう揺らいでいるかは見えない。\n\n"
                "CWT は信号を 時間 × 周波数 の 2 次元マップ（ヒートマップ）に展開する。\n"
                "「いつ・どの周波数が強かったか」が色で可視化される。",
                size=16, color=DARKGRAY)
    # ボックス：手法の中身
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                              Inches(0.5), Inches(4.7), Inches(12.333), Inches(2.0))
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xF5, 0xF8, 0xFD)
    box.line.color.rgb = NAVY
    add_textbox(s, Inches(0.8), Inches(4.85), Inches(12), Inches(0.4),
                "本レポートでの設定", size=14, bold=True, color=NAVY)
    add_bullets(s, Inches(0.8), Inches(5.2), Inches(12), Inches(1.5), [
        "母ウェーブレット: Morlet（時間-周波数のバランスが良い）",
        "入力信号: 腰（root）の鉛直加速度",
        "解析周波数帯: 0.5 〜 5 Hz（歩く 〜 走るまでカバー）",
        "4 人分のパワーマップを時間軸で揃え、正規化 → 平均 → 人類共通のリズム帯を抽出",
    ], size=12)


def slide_cwt_motion(motion_ja: str, img: Path, headline: str, bullets: list):
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "★ NEW ANALYSIS ①  CWT")
    add_title(s, f"CWT - {motion_ja}", top_in=0.95, size=24)
    add_yellow_underline(s, 1.55)
    add_textbox(s, Inches(0.5), Inches(1.6), Inches(12.5), Inches(0.5),
                headline, size=14, bold=True, color=NAVY)
    add_image_centered(s, img, top_in=2.1, max_width_in=11.0, max_height_in=4.0)
    add_bullets(s, Inches(0.5), Inches(6.3), Inches(12.5), Inches(1.0),
                bullets, size=12)


def slide_cwt_finding():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "★ NEW ANALYSIS ①  FINDING")
    add_title(s, "人間は速くなるほど「同じリズム」に収束する", size=26)
    add_yellow_underline(s, 1.75)
    # 数表
    headers = ["動作", "4 人平均 優位周波数", "個人差 σ", "解釈"]
    rows = [
        ["歩く", "1.90 Hz (114 BPM)", "±0.32 Hz", "個人差 大"],
        ["走る", "3.06 Hz (184 BPM)", "±0.11 Hz", "5 秒後にロックオン"],
        ["スキップ", "2.18 Hz (131 BPM)", "±0.08 Hz", "個人差 最小"],
    ]
    table = s.shapes.add_table(rows=4, cols=4,
                                left=Inches(0.7), top=Inches(2.3),
                                width=Inches(12), height=Inches(2.4)).table
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.color.rgb = WHITE
                r.font.bold = True
                r.font.size = Pt(14)
                r.font.name = "Hiragino Sans"
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            cell = table.cell(i, j)
            cell.text = v
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.color.rgb = DARKGRAY
                    r.font.size = Pt(13)
                    r.font.name = "Hiragino Sans"
    add_finding(s, "解釈", "動作スピードが上がるほど個人差が縮む",
                "物理的に最も効率の良いリズムが動作ごとに 1 つ存在し、人間は無意識にそこに収束する。"
                "歩行は『日常の動き』ゆえに個性が許容されるが、走るやスキップでは身体最適化が優先される。",
                top_in=5.4)


def slide_dtw_intro():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "★ NEW ANALYSIS ②")
    add_title(s, "動的時間伸縮（DTW）─ 波形そのものの距離を測る", size=26)
    add_yellow_underline(s, 1.75)
    add_textbox(s, Inches(0.5), Inches(2.1), Inches(12.5), Inches(2.5),
                "ACF が「自分自身の周期」、CWT が「時間 × 周波数」を見るのに対し、\n"
                "DTW は「2 つの波形の形そのもの」を比較する。\n\n"
                "時間軸を伸び縮みさせて最も似た対応関係を探し、距離をスカラ値で出す。\n"
                "「誰と誰がどれくらい似てるか」を 4×4 マトリクスで一望できる。",
                size=16, color=DARKGRAY)
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                              Inches(0.5), Inches(5.0), Inches(12.333), Inches(1.7))
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xF5, 0xF8, 0xFD)
    box.line.color.rgb = NAVY
    add_textbox(s, Inches(0.8), Inches(5.15), Inches(12), Inches(0.4),
                "本レポートでの設定", size=14, bold=True, color=NAVY)
    add_bullets(s, Inches(0.8), Inches(5.5), Inches(12), Inches(1.2), [
        "各人の左足首 Xrot から 1 ストライド分を抽出 → 200 サンプルにリサンプル + 振幅正規化",
        "4 人 × 4 人 = 6 ペアで DTW 距離を計算 → 動作別マトリクス",
    ], size=12)


def slide_dtw_image(title: str, img: Path, bullets: list, note: str = ""):
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "★ NEW ANALYSIS ②  DTW")
    add_title(s, title, top_in=0.95, size=22)
    add_yellow_underline(s, 1.55)
    add_image_centered(s, img, top_in=1.85, max_width_in=11.0, max_height_in=4.3)
    add_bullets(s, Inches(0.5), Inches(6.3), Inches(12.5), Inches(0.9),
                bullets, size=12)


def slide_dtw_finding():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "★ NEW ANALYSIS ②  FINDING")
    add_title(s, "2 手法とも同じ結論", size=28)
    add_yellow_underline(s, 1.85)
    add_textbox(s, Inches(0.5), Inches(2.1), Inches(12.5), Inches(0.6),
                "スキップは人類共通、歩くは個性、走るには外れ値あり",
                size=22, bold=True, color=NAVY)
    add_textbox(s, Inches(0.5), Inches(3.0), Inches(12.5), Inches(2.5),
                "CWT（周波数のばらつき）と DTW（波形距離のばらつき）の\n"
                "2 つの数学的に独立した手法が、ともに「スキップが最も 4 人で揃う」\n"
                "「歩くは個人差が大きい」という同じ結論を出した。\n\n"
                "これは偶然ではなく、動作の自由度（スキップ < 走る ≈ 歩く）を\n"
                "2 通りに測ったと解釈できる。",
                size=15, color=DARKGRAY)
    add_finding(s, "DISCOVERY",
                "Sora ⇔ Nori（走る）の DTW 距離が 216 と異常値",
                "他のペアは 23〜82 の範囲だが、このペアだけ突出。"
                "リズムは同じ 3 Hz でも、波形そのものの形が大きく違う ─ 動画を見直す価値あり。",
                top_in=5.6)


def slide_references():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, WHITE)
    add_logo(s)
    add_section_badge(s, "REFERENCES")
    add_title(s, "参考文献", size=28)
    add_yellow_underline(s, 1.85)
    refs = [
        ("分析", "[1] Cooley, J. W. and Tukey, J. W. (1965). An Algorithm for the Machine Calculation of Complex Fourier Series. Mathematics of Computation, 19(90), 297–301."),
        ("分析", "[2] Sakoe, H. and Chiba, S. (1978). Dynamic Programming Algorithm Optimization for Spoken Word Recognition. IEEE TASSP, 26(1), 43–49."),
        ("分析", "[3] Mallat, S. G. (1989). A Theory for Multiresolution Signal Decomposition. IEEE PAMI, 11(7), 674–693."),
        ("分析", "[4] Torrence, C. and Compo, G. P. (1998). A Practical Guide to Wavelet Analysis. BAMS, 79(1), 61–78."),
        ("歩行", "[5] Cavagna, G. A., Heglund, N. C. and Taylor, C. R. (1977). Mechanical work in terrestrial locomotion. Am J Physiol, 233(5), R243–R261."),
        ("歩行", "[6] Alexander, R. McN. (1989). Optimization and gaits in the locomotion of vertebrates. Physiol Rev, 69(4), 1199–1227."),
        ("歩行", "[7] Hreljac, A. (1995). Determinants of the gait transition speed during human locomotion. J Biomech, 28(6), 669–677."),
        ("歩行", "[8] Minetti, A. E. (1998). The biomechanics of skipping gaits: a third locomotion paradigm? Proc R Soc B, 265(1402), 1227–1235."),
        ("歩行", "[9] Pavei, G. et al. (2015). Skipping vs. running as the bipedal gait of choice in hypogravity. J Appl Physiol, 119(1), 93–100."),
    ]
    tb = s.shapes.add_textbox(Inches(0.5), Inches(2.1), Inches(12.5), Inches(5))
    tf = tb.text_frame; tf.word_wrap = True
    for i, (cat, ref) in enumerate(refs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(3)
        # カテゴリバッジ
        run = p.add_run()
        run.text = f"[{cat}] "
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = NAVY if cat == "分析" else RGBColor(0x2C, 0x8C, 0x4F)
        run.font.name = "Hiragino Sans"
        # 本文
        run = p.add_run()
        run.text = ref
        run.font.size = Pt(11)
        run.font.color.rgb = DARKGRAY
        run.font.name = "Hiragino Sans"


def slide_closing():
    s = prs.slides.add_slide(BLANK)
    add_bg(s, NAVY)
    # 黄色バー
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(0.25))
    bar.fill.solid(); bar.fill.fore_color.rgb = YELLOW; bar.line.fill.background()
    # ロゴ（白枠付き）
    pic = s.shapes.add_picture(str(LOGO_PATH), Inches(5.4), Inches(1.0),
                                width=Inches(2.5), height=Inches(0.85))
    add_textbox(s, Inches(0.5), Inches(3.0), Inches(12.5), Inches(1.5),
                "ご清聴ありがとうございました",
                size=44, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_textbox(s, Inches(0.5), Inches(4.7), Inches(12.5), Inches(0.5),
                "知能情報科学セミナーⅠ ─ BVH動作解析レポート",
                size=18, color=YELLOW, align=PP_ALIGN.CENTER)
    add_textbox(s, Inches(0.5), Inches(5.4), Inches(12.5), Inches(0.5),
                "情報学部 情報科学科  ─  平松 瑠希",
                size=16, color=WHITE, align=PP_ALIGN.CENTER)


# ===== ビルド =====
def main():
    slide_title()
    slide_intro()
    slide_data()
    slide_method()

    slide_reading_intro()
    slide_reading_step(1, "腰の上下動を見る ─ 歩行リズムの正体",
                       RG / "img_01_root_position.png",
                       "ピーク間隔の平均 ≈ 0.56 s ＝ 半ストライド（T/2）。腰は 1 ストライドの間に 2 回上下する。")
    slide_reading_step(2, "足首のリズムは腰の「半分」 ─ 2 倍周期の謎",
                       RG / "img_02_root_vs_foot.png",
                       "左足は 1 ストライドに 1 回しか動かないが、腰は 2 回上下する。だから足首の周期 1.05 s ≈ 腰の周期 0.53 s × 2。")
    slide_reading_step(3, "左右の足を重ねる ─ 半周期ずれて動く",
                       RG / "img_03_left_right.png",
                       "左右ピーク間 ≈ 0.58 s ＝ T/2。これが「交互ステップ」の数学的定義。")
    slide_reading_step(4, "ACF でリズムを数値化",
                       RG / "img_04_acf.png",
                       "τ = 0.53 s でピーク → ストライド周期 T。歩調 1.87 Hz ＝ 112 BPM。2 秒以上ピークが残る = 規則的で安定。")
    slide_reading_step(5, "CCF で左右対称性を数値化",
                       RG / "img_05_ccf.png",
                       "ピーク位置 -0.517 s ≈ 理想 -T/2 = -0.533 s。差わずか 0.016 s ─ 完璧な交互ステップ。")
    slide_reading_step(6, "対称性スコアの内訳 ─ 「何が個性か」を読む",
                       RG / "img_06_score.png",
                       "84.3 点。タイミングはほぼ満点、RMS 比 0.81 で 19% の左右振幅差 → これが歩き方の癖。")

    slide_cwt_intro()
    slide_cwt_motion("歩く", CWT / "walk_avg.png",
                     "1.90 Hz（114 BPM）、個人差 σ = 0.32 Hz ─ 最も個性が出る",
                     ["1.5〜2.2 Hz の幅で 4 人がばらつく",
                      "歩行は日常動作ゆえに個性が許容される"])
    slide_cwt_motion("走る", CWT / "run_avg.png",
                     "3.06 Hz（184 BPM）、個人差 σ = 0.11 Hz ─ 5 秒後にロックオン",
                     ["0〜5 秒は加速期、5 秒以降に 3 Hz の明るい横帯",
                      "4 人とも同タイミングで同周波数に収束 ─ 人類共通リズム"])
    slide_cwt_motion("スキップ", CWT / "skip_avg.png",
                     "2.18 Hz、個人差 σ = 0.08 Hz ─ 全動作中最小",
                     ["複数の周波数帯（基本リズム + 高調波）が共存",
                      "「ステップ + ホップ」の複合動作だが優位周波数は最も揃う"])
    slide_cwt_finding()

    slide_dtw_intro()
    slide_dtw_image("4 人ペアワイズ DTW 距離マトリクス",
                    DTW / "distance_matrix.png",
                    ["色が薄い（黄）ほど波形が似ている、濃い（赤）ほど違う",
                     "走るの Sora ⇔ Nori だけ 216.3 と異常値 ─ 他は 23〜82"])
    slide_dtw_image("動作ごとの平均距離 ─ 「ばらつき」で比較",
                    DTW / "distance_summary.png",
                    ["歩く 30.5 ± 14.5 / 走る 78.2 ± 65.7 / スキップ 35.3 ± 6.4",
                     "標準偏差の小ささ = 4 人がどれだけ揃っているか ─ スキップが最小"])
    slide_dtw_image("DTW の中身 ─ Ruki ⇔ Nori（歩く）の例",
                    DTW / "warping_example.png",
                    ["左：2 人の波形と DTW が対応付けた点同士をグレー線で結ぶ",
                     "右：累積コスト行列。赤線が「最も似た対応関係」のパス"])
    slide_dtw_finding()

    slide_references()
    slide_closing()

    # ページ番号フッタ
    total = len(prs.slides)
    for i, s in enumerate(prs.slides, start=1):
        add_footer(s, i, total)

    prs.save(str(OUT))
    print(f"✅ PPTX 生成完了: {OUT}")
    print(f"   スライド数: {total}")


if __name__ == "__main__":
    main()
