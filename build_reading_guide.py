"""READING GUIDE 用の注釈付きグラフを生成する（瑠希・歩くを教材として）。

出力: /tmp/school/reading_guide/img_01_*.png 〜 img_06_*.png
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

BVH_PATH = Path("/tmp/Ruki_walk.BVH")
OUT_DIR = Path("/tmp/school/reading_guide")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 日本語フォント
plt.rcParams["font.family"] = ["Hiragino Sans", "Yu Gothic", "Noto Sans CJK JP", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False
# 工学院大学ロゴ準拠の青・黄色基調パレット
NAVY = "#2c4198"          # ロゴ ネイビーブルー
YELLOW = "#fdd000"        # ロゴ イエロー（強調用）
MUSTARD = "#b8860b"       # 黄系をプロット線に使う際の濃い目（白背景で視認性確保）
GRAY = "#666666"          # 補助色
COL_ROOT = NAVY           # 腰
COL_LEFT = NAVY           # 左足（単色 + 線種で区別）
COL_RIGHT = MUSTARD       # 右足
COL_HL = YELLOW           # ハイライト


def parse_bvh(path: str):
    """既存スクリプトと同じ BVH パーサ。"""
    with open(path, "r") as f:
        lines = f.readlines()

    joint_order: list[str] = []
    channel_counts: list[int] = []
    channel_types: list[list[str]] = []
    current_joint: list[str] = []
    in_hierarchy = False
    in_motion = False
    n_frames = 0
    frame_time = 0.02
    motion_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped == "HIERARCHY":
            in_hierarchy = True
            continue
        if stripped == "MOTION":
            in_hierarchy = False
            in_motion = True
            continue
        if in_hierarchy:
            if stripped.startswith("ROOT") or stripped.startswith("JOINT"):
                current_joint.append(stripped.split()[1])
                joint_order.append(stripped.split()[1])
            elif stripped.startswith("End Site"):
                current_joint.append("__end__")
            elif stripped == "}":
                if current_joint:
                    current_joint.pop()
            elif stripped.startswith("CHANNELS"):
                parts = stripped.split()
                count = int(parts[1])
                channel_counts.append(count)
                channel_types.append(parts[2:2 + count])
        if in_motion:
            if stripped.startswith("Frames:"):
                n_frames = int(stripped.split()[1])
            elif stripped.startswith("Frame Time:"):
                frame_time = float(stripped.split()[2])
            elif stripped and not stripped.startswith("Frame"):
                motion_lines.append(stripped)

    fs = 1.0 / frame_time
    data = np.array([list(map(float, l.split())) for l in motion_lines[:n_frames]])
    positions: dict[str, np.ndarray] = {}
    rotations: dict[str, np.ndarray] = {}
    col = 0
    for joint, ccount, ctypes in zip(joint_order, channel_counts, channel_types):
        chunk = data[:, col:col + ccount]
        col += ccount
        pos_idx = [i for i, t in enumerate(ctypes) if "position" in t.lower()]
        rot_idx = [i for i, t in enumerate(ctypes) if "rotation" in t.lower()]
        if pos_idx:
            positions[joint] = chunk[:, pos_idx]
        if rot_idx:
            rotations[joint] = chunk[:, rot_idx]
    return positions, rotations, fs


def acf_fft(x: np.ndarray) -> np.ndarray:
    x = x - x.mean()
    n = len(x)
    nfft = 1 << (2 * n - 1).bit_length()
    X = np.fft.rfft(x, n=nfft)
    r = np.fft.irfft(np.abs(X) ** 2, n=nfft)[:n]
    return r / r[0]


def ccf_fft(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    x = x - x.mean()
    y = y - y.mean()
    n = len(x)
    nfft = 1 << (2 * n - 1).bit_length()
    X = np.fft.rfft(x, n=nfft)
    Y = np.fft.rfft(y, n=nfft)
    full = np.fft.irfft(np.conj(X) * Y, n=nfft)
    # 並べ替えてラグ -n+1 .. n-1 にする
    cc = np.concatenate([full[-(n - 1):], full[:n]])
    norm = np.sqrt(np.sum(x ** 2) * np.sum(y ** 2))
    return cc / norm if norm > 0 else cc


def annotate(ax, xy, text, xytext=(60, 30), color=NAVY, fontsize=11):
    ax.annotate(
        text, xy=xy, xytext=xytext, textcoords="offset points",
        fontsize=fontsize, color="white", weight="bold",
        bbox=dict(boxstyle="round,pad=0.4", fc=color, ec="none", alpha=0.95),
        arrowprops=dict(arrowstyle="->", color=color, lw=2,
                        connectionstyle="arc3,rad=0.2"),
    )


def main() -> None:
    positions, rotations, fs = parse_bvh(str(BVH_PATH))
    n = positions["root"].shape[0]
    t = np.arange(n) / fs
    duration = n / fs
    print(f"フレーム数: {n}, fs: {fs} Hz, duration: {duration:.2f} s")

    root_y = positions["root"][:, 1]
    rot_l = rotations["l_foot"]
    rot_r = rotations["r_foot"]
    sig_l = rot_l[:, 1]  # Xrot
    sig_r = rot_r[:, 1]

    # ===== Story 1: 腰の上下動 (歩行が始まってから 5 秒間) =====
    # 最初の 2 秒（キャリブレーション）を飛ばす
    start = int(2.0 * fs)
    end = int(7.0 * fs)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(t[start:end], root_y[start:end], color=COL_ROOT, lw=2)
    # 最小ピーク間隔 0.35s（半ストライド以下は無視）
    seg = root_y[start:end]
    peaks_rel, _ = find_peaks(seg, distance=int(0.35 * fs), prominence=0.3)
    peaks_abs = peaks_rel + start
    ax.scatter(t[peaks_abs], root_y[peaks_abs], color=COL_HL, s=140, zorder=5,
               edgecolor=NAVY, lw=2, label=f"踵接地ごとのピーク（{len(peaks_abs)}個）")
    ax.set_xlabel("時間 [秒]", fontsize=12)
    ax.set_ylabel("腰のY位置 [cm]", fontsize=12)
    ax.set_title("Step 1 : 腰（Root）が上下に揺れる ─ これが歩行リズムの正体", fontsize=14, color=NAVY, pad=12)
    ax.legend(loc="upper right", fontsize=11)
    ax.grid(alpha=0.3)
    if len(peaks_abs) >= 2:
        # 平均ピーク間隔を計算（first→last の平均）
        avg_gap = (t[peaks_abs[-1]] - t[peaks_abs[0]]) / (len(peaks_abs) - 1)
        p1, p2 = peaks_abs[0], peaks_abs[1]
        y_arrow = min(root_y[p1], root_y[p2]) - 0.4
        ax.annotate(
            "", xy=(t[p2], y_arrow), xytext=(t[p1], y_arrow),
            arrowprops=dict(arrowstyle="<->", color=NAVY, lw=2),
        )
        ax.text((t[p1] + t[p2]) / 2, y_arrow - 0.5,
                f"ピーク同士の平均間隔 ≈ {avg_gap:.2f} s\n（半ストライド = T/2）",
                ha="center", va="top", fontsize=11, color=NAVY,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=NAVY))
    plt.tight_layout()
    plt.savefig(OUT_DIR / "img_01_root_position.png", dpi=130)
    plt.close()

    # ===== Story 2: 左足首の回転角（Root と並べて2倍周期を可視化） =====
    fig, ax = plt.subplots(figsize=(11, 5))
    start = int(2.0 * fs)
    end = int(8.0 * fs)
    # 左軸：Root_Y（ネイビー実線）
    ax.plot(t[start:end], root_y[start:end], color=NAVY, lw=2.5, label="腰（Root）Y位置 ─ 半周期で上下")
    ax.set_xlabel("時間 [秒]", fontsize=12)
    ax.set_ylabel("腰のY位置 [cm]", color=NAVY, fontsize=12)
    ax.tick_params(axis="y", labelcolor=NAVY)
    ax.grid(alpha=0.3)
    # 右軸：左足首 Xrot（濃いマスタード黄色実線）
    ax2 = ax.twinx()
    ax2.plot(t[start:end], sig_l[start:end], color=MUSTARD, lw=2.5, label="左足首 Xrot ─ フル周期で 1 回")
    ax2.set_ylabel("左足首 Xrot [deg]", color=MUSTARD, fontsize=12)
    ax2.tick_params(axis="y", labelcolor=MUSTARD)
    ax.set_title("Step 2 : 左足のリズムは「腰の半分の周期」 ─ Root が 2 回上下する間に左足は 1 回だけ振る",
                 fontsize=13, color=NAVY, pad=12)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=11)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "img_02_root_vs_foot.png", dpi=130)
    plt.close()

    # ===== Story 3: 左右足首が半周期ずれて動く =====
    fig, ax = plt.subplots(figsize=(11, 4.5))
    start = int(2.0 * fs)
    end = int(7.0 * fs)
    ax.plot(t[start:end], sig_l[start:end], color=COL_LEFT, lw=2.2, label="左足首 Xrot")
    ax.plot(t[start:end], sig_r[start:end], color=COL_RIGHT, lw=2.2, label="右足首 Xrot")
    ax.set_xlabel("時間 [秒]", fontsize=12)
    ax.set_ylabel("足首回転角 Xrot [deg]", fontsize=12)
    ax.set_title("Step 3 : 左右が「ちょうど半周期ずれて」交互に動く ─ これが対称な歩行",
                 fontsize=13, color=NAVY, pad=12)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=11)
    # 左右のピークを find_peaks で検出、最初の一組をハイライト
    peaks_l, _ = find_peaks(sig_l[start:end], distance=int(0.5 * fs), prominence=5)
    peaks_r, _ = find_peaks(sig_r[start:end], distance=int(0.5 * fs), prominence=5)
    # アノテーション枠と凡例の場所を空けるために Y 軸範囲を広げる
    y_max = max(sig_l[start:end].max(), sig_r[start:end].max())
    y_min = min(sig_l[start:end].min(), sig_r[start:end].min())
    ax.set_ylim(y_min - 3, y_max + 14)
    if len(peaks_l) >= 1 and len(peaks_r) >= 1:
        lp = peaks_l[0] + start
        rp_candidates = [p + start for p in peaks_r if p + start > lp]
        if rp_candidates:
            rp = rp_candidates[0]
            ax.scatter(t[lp], sig_l[lp], color=COL_LEFT, s=200, zorder=5, edgecolor="white", lw=2.5)
            ax.scatter(t[rp], sig_r[rp], color=COL_RIGHT, s=200, zorder=5, edgecolor="white", lw=2.5)
            y_arrow = max(sig_l[lp], sig_r[rp]) + 3
            ax.annotate(
                "", xy=(t[rp], y_arrow), xytext=(t[lp], y_arrow),
                arrowprops=dict(arrowstyle="<->", color=NAVY, lw=2.5),
            )
            gap = t[rp] - t[lp]
            ax.text((t[lp] + t[rp]) / 2, y_arrow + 1,
                    f"左右ピーク間 ≈ {gap:.2f} s ＝ T/2（半周期）",
                    ha="center", va="bottom", fontsize=11, color=NAVY,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=NAVY))
    plt.tight_layout()
    plt.savefig(OUT_DIR / "img_03_left_right.png", dpi=130)
    plt.close()

    # ===== Story 4: ACF で周期が浮かび上がる =====
    root_vel = np.gradient(root_y, 1.0 / fs)
    root_acc = np.gradient(root_vel, 1.0 / fs) / 100.0  # m/s²
    r_root = acf_fft(root_acc)
    lags = np.arange(len(r_root)) / fs
    # 最初のピーク（lag > 0.2）
    cand = lags > 0.2
    cand_vals = r_root.copy()
    cand_vals[~cand] = -np.inf
    first_peak = int(np.argmax(cand_vals))
    T_root = lags[first_peak]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    mask = lags <= 2.5
    ax.plot(lags[mask], r_root[mask], color=COL_ROOT, lw=2)
    ax.axhline(0, color="gray", lw=0.7)
    ax.axvline(T_root, color=COL_HL, ls="--", lw=2,
               label=f"最初のピーク T = {T_root:.3f} s → 歩調 {1/T_root:.2f} Hz ({60/T_root:.0f} BPM)")
    ax.scatter([T_root], [r_root[first_peak]], color=COL_HL, s=180, zorder=5, edgecolor=NAVY, lw=2)
    ax.set_xlabel("ラグ τ [秒] ─ 信号を何秒ズラして自分自身と比べたか", fontsize=11)
    ax.set_ylabel("自己相関 ACF(τ)", fontsize=12)
    ax.set_title("Step 4 : 自己相関（ACF）でリズムを数値化 ─ T = 0.53 s でピーク",
                 fontsize=13, color=NAVY, pad=12)
    ax.legend(loc="upper right", fontsize=11)
    ax.grid(alpha=0.3)
    ax.text(0.05, 0.05, "ACF が 0.5 を超えるピークが\n2 秒以上残る → 規則的で安定した歩行",
            transform=ax.transAxes, fontsize=10, color=NAVY, va="bottom",
            bbox=dict(boxstyle="round,pad=0.4", fc="#fff7e0", ec=COL_HL))
    plt.tight_layout()
    plt.savefig(OUT_DIR / "img_04_acf.png", dpi=130)
    plt.close()

    # ===== Story 5: CCF で左右対称性 =====
    cc = ccf_fft(sig_l, sig_r)
    nlen = len(sig_l)
    lags_cc = np.arange(-(nlen - 1), nlen) / fs
    peak_idx = int(np.argmax(cc))
    phase_lag = lags_cc[peak_idx]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    mask = np.abs(lags_cc) <= 1.5
    ax.plot(lags_cc[mask], cc[mask], color="#2d4391", lw=2)
    ax.axhline(0, color="gray", lw=0.7)
    ax.axvline(phase_lag, color=COL_HL, ls="--", lw=2.5,
               label=f"ピーク位置 = {phase_lag:.3f} s")
    ax.axvline(T_root, color="green", ls=":", lw=2, label=f"理想 +T/2 = +{T_root:.3f} s")
    ax.axvline(-T_root, color="green", ls=":", lw=2, label=f"理想 −T/2 = −{T_root:.3f} s")
    ax.scatter([phase_lag], [cc[peak_idx]], color=COL_HL, s=180, zorder=5, edgecolor=NAVY, lw=2)
    ax.set_xlabel("ラグ τ [秒] ─ 左信号を何秒ズラすと右と一致するか", fontsize=11)
    ax.set_ylabel("相互相関 CCF(τ)", fontsize=12)
    ax.set_title(f"Step 5 : 左右の相互相関（CCF）─ ピーク {phase_lag:.3f} s が理想 −T/2 とほぼ一致",
                 fontsize=13, color=NAVY, pad=12)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(alpha=0.3)
    ax.text(0.05, 0.05,
            "左を半周期ズラすと右にピッタリ重なる\n→ 完璧な交互ステップの証拠",
            transform=ax.transAxes, fontsize=10, color=NAVY, va="bottom",
            bbox=dict(boxstyle="round,pad=0.4", fc="#e8f4e8", ec="green"))
    plt.tight_layout()
    plt.savefig(OUT_DIR / "img_05_ccf.png", dpi=130)
    plt.close()

    # ===== Story 6: スコア内訳 =====
    rms_l = float(np.sqrt(np.mean(sig_l ** 2)))
    rms_r = float(np.sqrt(np.mean(sig_r ** 2)))
    rms_ratio = min(rms_l, rms_r) / max(rms_l, rms_r)
    phase_score = max(0.0, 1.0 - abs(abs(phase_lag) - T_root) / (T_root / 2))
    ccf_peak = float(cc[peak_idx])
    contrib_rms = 0.6 * rms_ratio
    contrib_phase = 0.3 * phase_score
    contrib_ccf = 0.1 * ccf_peak
    total = (contrib_rms + contrib_phase + contrib_ccf) * 100

    fig, ax = plt.subplots(figsize=(10, 5))
    labels = [
        f"RMS比\n{rms_ratio:.2f} × 60%\n= {contrib_rms*100:.1f}点",
        f"位相差スコア\n{phase_score:.2f} × 30%\n= {contrib_phase*100:.1f}点",
        f"CCFピーク\n{ccf_peak:.2f} × 10%\n= {contrib_ccf*100:.1f}点",
    ]
    values = [contrib_rms * 100, contrib_phase * 100, contrib_ccf * 100]
    colors = ["#4A90E2", "#F39C12", "#27AE60"]
    bars = ax.bar(labels, values, color=colors, edgecolor=NAVY, lw=1.5)
    ax.set_ylim(0, 65)
    ax.set_ylabel("スコア寄与（100点満点）", fontsize=12)
    ax.set_title(f"Step 6 : 対称性スコア = {total:.1f} 点 ─ 内訳を見れば「何が弱点か」がわかる",
                 fontsize=13, color=NAVY, pad=12)
    ax.grid(alpha=0.3, axis="y")
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 1.5, f"{v:.1f}",
                ha="center", fontsize=12, color=NAVY, weight="bold")
    ax.set_ylim(0, 75)
    ax.text(0.5, 0.97,
            f"タイミング（位相差）はほぼ満点 → 左右のリズムは完璧\n"
            f"RMS比 {rms_ratio:.2f} は約 {(1-rms_ratio)*100:.0f}% の左右振幅差 → 歩き方の癖はここ",
            transform=ax.transAxes, ha="center", va="top", fontsize=11, color=NAVY,
            bbox=dict(boxstyle="round,pad=0.5", fc="#fff7e0", ec=COL_HL))
    plt.tight_layout()
    plt.savefig(OUT_DIR / "img_06_score.png", dpi=130)
    plt.close()

    print("✅ 6枚生成完了")
    for p in sorted(OUT_DIR.glob("*.png")):
        print(f"  {p.name} ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
