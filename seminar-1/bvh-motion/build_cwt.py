"""連続ウェーブレット変換（CWT）で 4 人 × 3 動作 = 12 サンプルを解析する。

出力:
  /tmp/school/analysis/cwt/
    walk_avg.png  / run_avg.png  / skip_avg.png   ← 4人平均ヒートマップ
    individuals/{person}_{motion}_cwt.png        ← 個人別12枚
    cwt_summary.json                              ← データサマリー（sections.json統合用）
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
import pywt

BVH_DIR = Path("/tmp/bvh_data")
OUT_DIR = Path("/tmp/school/analysis/cwt")
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "individuals").mkdir(exist_ok=True)

plt.rcParams["font.family"] = ["Hiragino Sans", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False
NAVY = "#1a2b6b"

# 解析対象: (person, motion, filename, color)
FILES = [
    ("Sora",  "walk", "Sora_walking.BVH",  "#4A90E2"),
    ("Sora",  "run",  "Sora_running.BVH",  "#4A90E2"),
    ("Sora",  "skip", "Sora_skip.BVH",     "#4A90E2"),
    ("Shota", "walk", "Shota Walkin.BVH",  "#E07A5F"),
    ("Shota", "run",  "Sho_run.bvh.BVH",   "#E07A5F"),
    ("Shota", "skip", "Shota_skip.BVH",    "#E07A5F"),
    ("Ruki",  "walk", "Ruki_walk.BVH",     "#6CC04A"),
    ("Ruki",  "run",  "Ruki_run.BVH",      "#6CC04A"),
    ("Ruki",  "skip", "Ruki_skip.BVH",     "#6CC04A"),
    ("Nori",  "walk", "Nori.walk.BVH",     "#9B59B6"),
    ("Nori",  "run",  "Nori.run.BVH",      "#9B59B6"),
    ("Nori",  "skip", "Nori.skip.BVH",     "#9B59B6"),
]

MOTION_JA = {"walk": "歩く", "run": "走る", "skip": "スキップ"}


def parse_bvh(path: str):
    """既存スクリプトと同じパーサ。"""
    with open(path, "r") as f:
        lines = f.readlines()
    joint_order, channel_counts, channel_types = [], [], []
    current_joint, motion_lines = [], []
    in_hierarchy = in_motion = False
    n_frames, frame_time = 0, 0.02
    for line in lines:
        s = line.strip()
        if s == "HIERARCHY":
            in_hierarchy = True
            continue
        if s == "MOTION":
            in_hierarchy, in_motion = False, True
            continue
        if in_hierarchy:
            if s.startswith("ROOT") or s.startswith("JOINT"):
                current_joint.append(s.split()[1])
                joint_order.append(s.split()[1])
            elif s.startswith("End Site"):
                current_joint.append("__end__")
            elif s == "}":
                if current_joint:
                    current_joint.pop()
            elif s.startswith("CHANNELS"):
                parts = s.split()
                count = int(parts[1])
                channel_counts.append(count)
                channel_types.append(parts[2:2 + count])
        if in_motion:
            if s.startswith("Frames:"):
                n_frames = int(s.split()[1])
            elif s.startswith("Frame Time:"):
                frame_time = float(s.split()[2])
            elif s and not s.startswith("Frame"):
                motion_lines.append(s)
    fs = 1.0 / frame_time
    data = np.array([list(map(float, l.split())) for l in motion_lines[:n_frames]])
    positions, rotations = {}, {}
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


def compute_cwt(signal: np.ndarray, fs: float, freqs: np.ndarray):
    """Morlet ウェーブレットで CWT を計算し、|coef|² (power) を返す。"""
    scales = pywt.central_frequency("morl") * fs / freqs
    coef, _ = pywt.cwt(signal, scales, "morl", sampling_period=1.0 / fs)
    power = np.abs(coef) ** 2
    # 各時刻で正規化（時間方向の優位周波数を見やすく）
    power_norm = power / (power.max(axis=0, keepdims=True) + 1e-12)
    return power, power_norm


def analyze_sample(person: str, motion: str, fname: str):
    """1サンプル分の CWT を計算してメタデータを返す。"""
    positions, _rotations, fs = parse_bvh(str(BVH_DIR / fname))
    root_y = positions["root"][:, 1]
    # 鉛直加速度（既存スクリプトと同じ）
    vel = np.gradient(root_y, 1.0 / fs)
    acc = np.gradient(vel, 1.0 / fs) / 100.0  # cm/s² → m/s²
    # キャリブレーション 2 秒を除外
    start = int(2.0 * fs)
    sig = acc[start:]
    t = np.arange(len(sig)) / fs
    # 解析対象周波数: 0.5 〜 5 Hz （歩・走・スキップを全部カバー）
    freqs = np.linspace(0.5, 5.0, 80)
    power, power_norm = compute_cwt(sig, fs, freqs)
    # 優位周波数の時間変化
    dominant_freq = freqs[np.argmax(power, axis=0)]
    return {
        "person": person,
        "motion": motion,
        "fs": fs,
        "t": t,
        "freqs": freqs,
        "power": power,
        "power_norm": power_norm,
        "dominant_freq": dominant_freq,
        "duration": t[-1] if len(t) else 0,
    }


def plot_individual(result, color, out_path):
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), gridspec_kw={"height_ratios": [3, 1]})
    ax = axes[0]
    extent = [result["t"][0], result["t"][-1], result["freqs"][0], result["freqs"][-1]]
    im = ax.imshow(result["power_norm"], extent=extent, aspect="auto",
                   origin="lower", cmap="magma", interpolation="bilinear", vmin=0, vmax=1)
    ax.plot(result["t"], result["dominant_freq"], color="cyan", lw=1.5, alpha=0.85,
            label="優位周波数")
    ax.set_xlabel("時間 [秒]")
    ax.set_ylabel("周波数 [Hz]")
    ax.set_title(f"{result['person']} ・ {MOTION_JA[result['motion']]}  ─ CWT パワー（正規化）",
                 color=NAVY, fontsize=13)
    ax.legend(loc="upper right", fontsize=10)
    plt.colorbar(im, ax=ax, label="正規化パワー")

    # 下段：優位周波数の時系列
    ax2 = axes[1]
    ax2.plot(result["t"], result["dominant_freq"], color=color, lw=2)
    ax2.axhline(np.median(result["dominant_freq"]), color=NAVY, ls="--", lw=1,
                label=f"中央値 {np.median(result['dominant_freq']):.2f} Hz")
    ax2.set_xlabel("時間 [秒]")
    ax2.set_ylabel("優位周波数 [Hz]")
    ax2.set_ylim(0.5, 5.0)
    ax2.grid(alpha=0.3)
    ax2.legend(loc="upper right", fontsize=10)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()


def plot_motion_average(motion: str, results: list, out_path: Path):
    """4 人分の CWT パワーを共通の時間グリッドにリサンプルして平均、その上に個人線を重ねる。"""
    # 共通グリッド：4 人の最短時間 × 200 サンプルに揃える
    min_dur = min(r["duration"] for r in results)
    t_grid = np.linspace(0, min_dur, 200)
    freqs = results[0]["freqs"]
    powers_resampled = []
    dom_resampled = []
    for r in results:
        # 各時刻における power（全周波数）を時間軸方向に補間
        p = np.empty((len(freqs), len(t_grid)))
        for i in range(len(freqs)):
            p[i] = np.interp(t_grid, r["t"], r["power_norm"][i])
        powers_resampled.append(p)
        dom_resampled.append(np.interp(t_grid, r["t"], r["dominant_freq"]))
    avg_power = np.mean(powers_resampled, axis=0)
    avg_dom = np.mean(dom_resampled, axis=0)

    fig, axes = plt.subplots(2, 1, figsize=(12, 7.5), gridspec_kw={"height_ratios": [3, 1.2]})
    ax = axes[0]
    extent = [t_grid[0], t_grid[-1], freqs[0], freqs[-1]]
    im = ax.imshow(avg_power, extent=extent, aspect="auto", origin="lower",
                   cmap="magma", interpolation="bilinear", vmin=0, vmax=1)
    ax.plot(t_grid, avg_dom, color="cyan", lw=2.2, label="4人平均 優位周波数")
    ax.set_xlabel("時間 [秒]")
    ax.set_ylabel("周波数 [Hz]")
    ax.set_title(f"【4人平均】{MOTION_JA[motion]} の CWT パワー  ─ 人類共通のリズム帯",
                 color=NAVY, fontsize=14)
    ax.legend(loc="upper right", fontsize=10)
    plt.colorbar(im, ax=ax, label="正規化パワー（4人平均）")

    # 下段：個人別の優位周波数を全部重ねる
    ax2 = axes[1]
    for r, dom in zip(results, dom_resampled):
        ax2.plot(t_grid, dom, lw=1.5, alpha=0.7, label=r["person"])
    ax2.plot(t_grid, avg_dom, color=NAVY, lw=3, label="4人平均")
    ax2.set_xlabel("時間 [秒]")
    ax2.set_ylabel("優位周波数 [Hz]")
    ax2.set_ylim(0.5, 5.0)
    ax2.grid(alpha=0.3)
    ax2.legend(loc="upper right", fontsize=9, ncol=5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
    return {
        "median_dominant": float(np.median(avg_dom)),
        "std_across_individuals": float(np.std([np.median(d) for d in dom_resampled])),
        "min_dur": float(min_dur),
    }


def main():
    print("=" * 60)
    print("CWT 解析 開始")
    print("=" * 60)
    all_results = []
    for person, motion, fname, color in FILES:
        print(f"  分析中: {person} - {motion} ({fname})")
        r = analyze_sample(person, motion, fname)
        all_results.append((r, color))
        out = OUT_DIR / "individuals" / f"{person}_{motion}_cwt.png"
        plot_individual(r, color, out)

    # 動作別 4 人平均
    summary = {}
    for motion in ["walk", "run", "skip"]:
        results = [r for r, _c in all_results if r["motion"] == motion]
        out = OUT_DIR / f"{motion}_avg.png"
        s = plot_motion_average(motion, results, out)
        s["individuals"] = {
            r["person"]: float(np.median(r["dominant_freq"]))
            for r in results
        }
        summary[motion] = s
        print(f"  ✓ 4人平均 ({motion}): 優位周波数中央値={s['median_dominant']:.2f} Hz, "
              f"個人差σ={s['std_across_individuals']:.2f} Hz")

    with open(OUT_DIR / "cwt_summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("\n出力先:", OUT_DIR)


if __name__ == "__main__":
    main()
