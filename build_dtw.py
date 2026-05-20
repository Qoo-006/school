"""DTW (動的時間伸縮) で 4 人の波形類似度を測る。

問い: 「どの動作が4人間で最も似ていて、どの動作で個性が出るか」を距離で示す。

出力:
  /tmp/school/analysis/dtw/
    distance_matrix.png         ← 4 人 × 4 人 × 3 動作の距離マトリクス
    distance_summary.png        ← 動作別 4 人平均距離の棒グラフ
    warping_example.png         ← DTW の中身を可視化（教材用）
    dtw_summary.json
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, butter, filtfilt
from dtw import dtw
import sys

sys.path.insert(0, "/tmp/school")
from build_cwt import parse_bvh, FILES, MOTION_JA, NAVY  # type: ignore

BVH_DIR = Path("/tmp/bvh_data")
OUT_DIR = Path("/tmp/school/analysis/dtw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.family"] = ["Hiragino Sans", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

PERSONS = ["Sora", "Shota", "Ruki", "Nori"]


def lowpass(x: np.ndarray, fs: float, cutoff: float = 6.0, order: int = 4) -> np.ndarray:
    nyq = fs / 2
    b, a = butter(order, cutoff / nyq, btype="low")
    return filtfilt(b, a, x)


def extract_normalized_stride(person: str, motion: str, fname: str):
    """1 ストライド分の左足首 Xrot を 200 点にリサンプル + 振幅正規化して返す。"""
    _positions, rotations, fs = parse_bvh(str(BVH_DIR / fname))
    sig = lowpass(rotations["l_foot"][:, 1], fs)
    start = int(2.0 * fs)
    sig = sig[start:]
    peaks, _ = find_peaks(sig, distance=int(0.3 * fs), prominence=3)
    if len(peaks) < 5:
        return None
    mid = len(peaks) // 2
    stride = sig[peaks[mid]:peaks[mid + 1] + 1]
    # 200 点にリサンプル & 振幅正規化（平均 0、標準偏差 1）
    t = np.linspace(0, 1, 200)
    t_orig = np.linspace(0, 1, len(stride))
    stride_resampled = np.interp(t, t_orig, stride)
    stride_norm = (stride_resampled - stride_resampled.mean()) / (stride_resampled.std() + 1e-9)
    return stride_norm


def compute_distance_matrix(strides: dict) -> dict:
    """各動作で 4 × 4 の DTW 距離行列を計算。"""
    result = {}
    for motion in ["walk", "run", "skip"]:
        mat = np.zeros((len(PERSONS), len(PERSONS)))
        for i, pi in enumerate(PERSONS):
            for j, pj in enumerate(PERSONS):
                if i == j:
                    continue
                si = strides.get((pi, motion))
                sj = strides.get((pj, motion))
                if si is None or sj is None:
                    mat[i, j] = np.nan
                    continue
                alignment = dtw(si, sj, keep_internals=False, distance_only=True)
                mat[i, j] = alignment.distance
        result[motion] = mat
    return result


def plot_distance_matrix(result: dict, out_path: Path):
    """3 動作 × 4×4 のヒートマップ。"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    # 共通カラースケール（最大値）
    vmax = max(np.nanmax(mat) for mat in result.values())
    for ax, motion in zip(axes, ["walk", "run", "skip"]):
        mat = result[motion]
        im = ax.imshow(mat, cmap="YlOrRd", vmin=0, vmax=vmax)
        ax.set_xticks(range(len(PERSONS)))
        ax.set_yticks(range(len(PERSONS)))
        ax.set_xticklabels(PERSONS)
        ax.set_yticklabels(PERSONS)
        ax.set_title(f"{MOTION_JA[motion]}（DTW 距離）", color=NAVY, fontsize=13)
        for i in range(len(PERSONS)):
            for j in range(len(PERSONS)):
                v = mat[i, j]
                if not np.isnan(v) and i != j:
                    ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                            color="white" if v > vmax * 0.5 else NAVY, fontsize=11, weight="bold")
        plt.colorbar(im, ax=ax, fraction=0.046)
    plt.suptitle("4 人ペアワイズ DTW 距離 ─ 小さいほど波形が似てる", fontsize=14, color=NAVY, y=1.02)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_average_distance(result: dict, out_path: Path):
    """動作ごとの平均 DTW 距離を棒グラフで比較。"""
    avgs, stds = [], []
    for motion in ["walk", "run", "skip"]:
        mat = result[motion]
        # 上三角だけ抽出
        triu = mat[np.triu_indices_from(mat, k=1)]
        valid = triu[~np.isnan(triu)]
        avgs.append(np.mean(valid))
        stds.append(np.std(valid))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    labels = ["歩く", "走る", "スキップ"]
    colors = ["#4A90E2", "#E07A5F", "#6CC04A"]
    bars = ax.bar(labels, avgs, yerr=stds, capsize=10, color=colors,
                  edgecolor=NAVY, lw=1.5)
    ax.set_ylabel("4 人ペアワイズ DTW 距離（平均 ± 標準偏差）", fontsize=12)
    ax.set_title("動作ごとの「波形のばらつき」 ─ 距離が小さい = 4 人で似てる",
                 color=NAVY, fontsize=13)
    ax.grid(alpha=0.3, axis="y")
    for bar, v in zip(bars, avgs):
        ax.text(bar.get_x() + bar.get_width() / 2, v + max(stds) * 0.2, f"{v:.1f}",
                ha="center", fontsize=13, color=NAVY, weight="bold")
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
    return list(zip(labels, avgs, stds))


def plot_warping_example(strides: dict, out_path: Path):
    """DTW がどう動くかを 1 ペアの例で教材的に可視化。"""
    si = strides.get(("Ruki", "walk"))
    sj = strides.get(("Nori", "walk"))
    if si is None or sj is None:
        return
    alignment = dtw(si, sj, keep_internals=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    # 左：2 つの波形 + DTW で対応付けられた点同士を線で結ぶ
    ax = axes[0]
    ax.plot(si + 3, color="#6CC04A", lw=2, label="Ruki 歩く（上にオフセット）")
    ax.plot(sj - 3, color="#9B59B6", lw=2, label="Nori 歩く（下にオフセット）")
    # 対応関係を一部だけ描く
    idx1, idx2 = alignment.index1, alignment.index2
    step = max(1, len(idx1) // 30)
    for k in range(0, len(idx1), step):
        ax.plot([idx1[k], idx2[k]], [si[idx1[k]] + 3, sj[idx2[k]] - 3],
                color="gray", lw=0.6, alpha=0.6)
    ax.set_xlabel("時間（1 ストライド = 200 サンプル）", fontsize=11)
    ax.set_ylabel("Xrot（正規化）", fontsize=11)
    ax.set_title(f"DTW 対応付け例： Ruki ⇔ Nori（歩く）　距離 = {alignment.distance:.2f}",
                 color=NAVY, fontsize=12)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(alpha=0.3)
    # 右：累積コスト行列
    ax2 = axes[1]
    cost = alignment.costMatrix
    im = ax2.imshow(cost.T, cmap="viridis", origin="lower", aspect="auto")
    ax2.plot(alignment.index1, alignment.index2, color="red", lw=2, label="最適パス")
    ax2.set_xlabel("Ruki 時間 [サンプル]", fontsize=11)
    ax2.set_ylabel("Nori 時間 [サンプル]", fontsize=11)
    ax2.set_title("DTW 累積コスト行列 ─ 赤線が「最も似た対応関係」", color=NAVY, fontsize=12)
    ax2.legend(loc="lower right", fontsize=10)
    plt.colorbar(im, ax=ax2, label="累積コスト")
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()


def main():
    print("=" * 60)
    print("DTW 解析 開始")
    print("=" * 60)
    strides = {}
    for person, motion, fname, _color in FILES:
        s = extract_normalized_stride(person, motion, fname)
        if s is None:
            print(f"  ⚠ {person} {motion}: ストライド抽出失敗")
            continue
        strides[(person, motion)] = s
        print(f"  ✓ {person} {motion} 抽出")

    result = compute_distance_matrix(strides)

    plot_distance_matrix(result, OUT_DIR / "distance_matrix.png")
    avgs = plot_average_distance(result, OUT_DIR / "distance_summary.png")
    plot_warping_example(strides, OUT_DIR / "warping_example.png")

    summary = {"by_motion": {}}
    for label, avg, std in avgs:
        motion_key = {"歩く": "walk", "走る": "run", "スキップ": "skip"}[label]
        summary["by_motion"][motion_key] = {
            "label_ja": label,
            "avg_pairwise_distance": float(avg),
            "std_pairwise_distance": float(std),
        }
        print(f"  {label}: 平均距離 {avg:.2f} ± {std:.2f}")

    with open(OUT_DIR / "dtw_summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("\n出力先:", OUT_DIR)


if __name__ == "__main__":
    main()
