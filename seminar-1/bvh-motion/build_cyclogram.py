"""サイクログラム解析：左右足首の Xrot を XY 平面にプロット。

歩行/走行/スキップそれぞれで「軌跡の形が指紋になる」かを 4 人重ねて検証する。

出力:
  /tmp/school/analysis/cyclogram/
    walk_avg.png / run_avg.png / skip_avg.png  ← 4人重ね（平均軌跡を太線）
    individuals/{person}_{motion}_cyc.png      ← 個人別 12 枚
    cyclogram_summary.json
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from scipy.signal import find_peaks, butter, filtfilt, correlate
import sys

sys.path.insert(0, "/tmp/school")
from build_cwt import parse_bvh, FILES, MOTION_JA, NAVY  # type: ignore

BVH_DIR = Path("/tmp/bvh_data")
OUT_DIR = Path("/tmp/school/analysis/cyclogram")
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "individuals").mkdir(exist_ok=True)

plt.rcParams["font.family"] = ["Hiragino Sans", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


def lowpass(x: np.ndarray, fs: float, cutoff: float = 6.0, order: int = 4) -> np.ndarray:
    """ゼロ位相 Butterworth ローパス（既存スクリプトと同じカットオフ）。"""
    nyq = fs / 2
    b, a = butter(order, cutoff / nyq, btype="low")
    return filtfilt(b, a, x)


def extract_stride(person: str, motion: str, fname: str):
    """1 サンプルから「ローパスかけた」左右足首 Xrot を返す。

    Returns:
        seg_5: (sig_l_5, sig_r_5)  ← 個人別表示用の 5 周期
        seg_1: (sig_l_1, sig_r_1)  ← 4 人平均用の 1 周期
        fs
    """
    positions, rotations, fs = parse_bvh(str(BVH_DIR / fname))
    sig_l = lowpass(rotations["l_foot"][:, 1], fs)  # Xrot, ローパス済み
    sig_r = lowpass(rotations["r_foot"][:, 1], fs)
    start = int(2.0 * fs)
    sig_l = sig_l[start:]
    sig_r = sig_r[start:]
    # 左足ピーク検出
    peaks, _ = find_peaks(sig_l, distance=int(0.3 * fs), prominence=3)
    if len(peaks) < 6:
        return None, None, None
    # 5 周期分（個人表示用）
    seg_l_5 = sig_l[peaks[0]:peaks[5] + 1]
    seg_r_5 = sig_r[peaks[0]:peaks[5] + 1]
    # 1 周期分（平均用、中央寄りの安定したやつ）
    mid = len(peaks) // 2
    seg_l_1 = sig_l[peaks[mid]:peaks[mid + 1] + 1]
    seg_r_1 = sig_r[peaks[mid]:peaks[mid + 1] + 1]
    return (seg_l_5, seg_r_5), (seg_l_1, seg_r_1), fs


def resample_loop(x: np.ndarray, y: np.ndarray, n: int = 400):
    """軌跡を共通の点数 n にリサンプル（後で平均しやすくする）。"""
    t_orig = np.linspace(0, 1, len(x))
    t_new = np.linspace(0, 1, n)
    return np.interp(t_new, t_orig, x), np.interp(t_new, t_orig, y)


def plot_individual_cyclogram(person: str, motion: str, color, sig_l, sig_r, out_path):
    """1 サンプルのサイクログラム（時間でグラデーション）。"""
    fig, ax = plt.subplots(figsize=(8, 7))
    points = np.array([sig_l, sig_r]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap="viridis", linewidths=2)
    lc.set_array(np.linspace(0, 1, len(segments)))
    ax.add_collection(lc)
    ax.scatter(sig_l[0], sig_r[0], color="lime", s=120, zorder=5, edgecolor="black", lw=1.5, label="開始")
    ax.scatter(sig_l[-1], sig_r[-1], color="red", s=120, zorder=5, edgecolor="black", lw=1.5, label="終了")
    ax.plot([sig_l.min(), sig_l.max()], [sig_l.min(), sig_l.max()],
            color="gray", ls="--", lw=0.8, label="左右対称線 y=x")
    span = max(abs(sig_l).max(), abs(sig_r).max()) + 5
    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_aspect("equal")
    ax.set_xlabel("左足首 Xrot [deg]", fontsize=11)
    ax.set_ylabel("右足首 Xrot [deg]", fontsize=11)
    ax.set_title(f"{person}・{MOTION_JA[motion]}  ─ サイクログラム（5 周期分）",
                 color=NAVY, fontsize=13)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()


def align_phase(ref_x: np.ndarray, x: np.ndarray, y: np.ndarray):
    """ref_x との相互相関が最大になるよう x, y を巡回シフトする。"""
    c = correlate(ref_x, x, mode="full")
    shift = c.argmax() - (len(x) - 1)
    return np.roll(x, shift), np.roll(y, shift)


def plot_motion_overlay(motion: str, samples: list, out_path: Path):
    """4 人分のサイクログラムを位相揃えて重ねて、平均軌跡を太線で描く。"""
    fig, ax = plt.subplots(figsize=(9, 8.5))
    resampled_xs, resampled_ys = [], []
    # 全員を最初に共通グリッドにリサンプル & 正規化
    for person, color, seg_l, seg_r in samples:
        scale = max(np.abs(seg_l).max(), np.abs(seg_r).max())
        nl = seg_l / scale if scale > 0 else seg_l
        nr = seg_r / scale if scale > 0 else seg_r
        rl, rr = resample_loop(nl, nr, n=400)
        resampled_xs.append(rl)
        resampled_ys.append(rr)
    # 位相を最初の被験者に揃える
    ref = resampled_xs[0]
    aligned_xs = [resampled_xs[0]]
    aligned_ys = [resampled_ys[0]]
    for i in range(1, len(resampled_xs)):
        ax_, ay_ = align_phase(ref, resampled_xs[i], resampled_ys[i])
        aligned_xs.append(ax_)
        aligned_ys.append(ay_)
    # 個人別を薄く重ねる
    for (person, color, _sl, _sr), ax_, ay_ in zip(samples, aligned_xs, aligned_ys):
        ax.plot(ax_, ay_, color=color, alpha=0.5, lw=1.8, label=person)
    avg_x = np.mean(aligned_xs, axis=0)
    avg_y = np.mean(aligned_ys, axis=0)
    resampled_xs, resampled_ys = aligned_xs, aligned_ys  # 後の相関計算用
    # 平均を時間グラデーションで太く
    points = np.array([avg_x, avg_y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap="magma", linewidths=4.5)
    lc.set_array(np.linspace(0, 1, len(segments)))
    ax.add_collection(lc)
    ax.plot([-1.2, 1.2], [-1.2, 1.2], color="gray", ls="--", lw=0.8, label="左右対称線")
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect("equal")
    ax.set_xlabel("左足首 Xrot（個人最大値で正規化）", fontsize=11)
    ax.set_ylabel("右足首 Xrot（個人最大値で正規化）", fontsize=11)
    ax.set_title(f"【4人重ね】{MOTION_JA[motion]} のサイクログラム\n"
                 f"─ 太い軌跡が 4 人平均（時間でグラデーション）",
                 color=NAVY, fontsize=13)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=10)
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
    # 形状の類似度（4人ペアごとの相関）
    correlations = []
    for i in range(len(resampled_xs)):
        for j in range(i + 1, len(resampled_xs)):
            cxx = float(np.corrcoef(resampled_xs[i], resampled_xs[j])[0, 1])
            cyy = float(np.corrcoef(resampled_ys[i], resampled_ys[j])[0, 1])
            correlations.append((cxx + cyy) / 2)
    return {
        "n_individuals": len(samples),
        "avg_pairwise_correlation": float(np.mean(correlations)),
        "min_correlation": float(min(correlations)) if correlations else None,
    }


def main():
    print("=" * 60)
    print("サイクログラム解析 開始")
    print("=" * 60)
    motion_data: dict[str, list] = {"walk": [], "run": [], "skip": []}
    for person, motion, fname, color in FILES:
        print(f"  分析中: {person} - {motion}")
        seg_5, seg_1, _fs = extract_stride(person, motion, fname)
        if seg_5 is None:
            print(f"    ⚠ ピーク不足、スキップ")
            continue
        out = OUT_DIR / "individuals" / f"{person}_{motion}_cyc.png"
        plot_individual_cyclogram(person, motion, color, seg_5[0], seg_5[1], out)
        motion_data[motion].append((person, color, seg_1[0], seg_1[1]))

    summary = {}
    for motion in ["walk", "run", "skip"]:
        out = OUT_DIR / f"{motion}_avg.png"
        s = plot_motion_overlay(motion, motion_data[motion], out)
        summary[motion] = s
        print(f"  ✓ 4人重ね ({motion}): 形状相関 平均={s['avg_pairwise_correlation']:.3f}, "
              f"最小={s['min_correlation']:.3f}")

    with open(OUT_DIR / "cyclogram_summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("\n出力先:", OUT_DIR)


if __name__ == "__main__":
    main()
