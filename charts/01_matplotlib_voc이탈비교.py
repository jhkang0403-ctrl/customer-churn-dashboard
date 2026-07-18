"""
전체 고객 이탈율 vs 해지관련 부정 VOC 이력 있는 고객 이탈율 비교 막대그래프

data/data_voc.csv, data/data_customers.csv를 직접 읽어 재계산한다.
"""
import csv
import os

import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

VOC_PATH = os.path.join(DATA_DIR, "data_voc.csv")
CUSTOMERS_PATH = os.path.join(DATA_DIR, "data_customers.csv")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "01_matplotlib_voc이탈비교.png")

TARGET_CATEGORY = "해지관련"
TARGET_SENTIMENT = "부정"


def load_churn_rates():
    with open(VOC_PATH, encoding="utf-8-sig") as f:
        voc_rows = list(csv.DictReader(f))

    with open(CUSTOMERS_PATH, encoding="utf-8-sig") as f:
        customers = list(csv.DictReader(f))

    customer_map = {c["customer_id"]: c for c in customers}

    target_ids = {
        r["customer_id"]
        for r in voc_rows
        if r["category"] == TARGET_CATEGORY and r["sentiment"] == TARGET_SENTIMENT
    }
    target_customers = [customer_map[cid] for cid in target_ids if cid in customer_map]

    total_all = len(customers)
    churned_all = sum(1 for c in customers if c["churn_yn"].strip().upper() == "Y")
    rate_all = churned_all / total_all * 100

    total_target = len(target_customers)
    churned_target = sum(1 for c in target_customers if c["churn_yn"].strip().upper() == "Y")
    rate_target = (churned_target / total_target * 100) if total_target else 0

    return rate_all, rate_target


def main():
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    rate_all, rate_target = load_churn_rates()

    labels = ["전체 고객", "해지관련 부정 VOC 이력 있음"]
    values = [rate_all, rate_target]
    colors = ["#898781", "#d03b3b"]  # 첫 막대: 무채색(기준), 두 번째 막대: 강조 빨강(critical)

    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(labels, values, color=colors, width=0.5)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.6,
            f"{value:.1f}%",
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
        )

    ax.set_ylabel("이탈율 (%)")
    ax.set_title("전체 고객 vs 해지관련 부정 VOC 이력 고객 이탈율 비교")
    ax.set_ylim(0, max(values) * 1.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    print(f"saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
