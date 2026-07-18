"""
전체 고객 이탈율 vs 해지관련 부정 VOC 이력 있는 고객 이탈율 비교 막대그래프 (plotly.express)

data/data_voc.csv, data/data_customers.csv를 직접 읽어 재계산한다.
"""
import os

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

VOC_PATH = os.path.join(DATA_DIR, "data_voc.csv")
CUSTOMERS_PATH = os.path.join(DATA_DIR, "data_customers.csv")

TARGET_CATEGORY = "해지관련"
TARGET_SENTIMENT = "부정"


def load_churn_summary():
    voc = pd.read_csv(VOC_PATH, encoding="utf-8-sig")
    customers = pd.read_csv(CUSTOMERS_PATH, encoding="utf-8-sig")
    customers["is_churned"] = customers["churn_yn"].str.strip().str.upper() == "Y"

    target_ids = voc.loc[
        (voc["category"] == TARGET_CATEGORY) & (voc["sentiment"] == TARGET_SENTIMENT),
        "customer_id",
    ].unique()
    target_customers = customers[customers["customer_id"].isin(target_ids)]

    def summarize(df):
        total = len(df)
        churned = int(df["is_churned"].sum())
        rate = (churned / total * 100) if total else 0
        return total, churned, rate

    all_total, all_churned, all_rate = summarize(customers)
    target_total, target_churned, target_rate = summarize(target_customers)

    return pd.DataFrame(
        {
            "구분": ["전체 고객", "해지관련 부정 VOC 이력 있음"],
            "고객수": [all_total, target_total],
            "이탈고객수": [all_churned, target_churned],
            "이탈율": [all_rate, target_rate],
        }
    )


def main():
    summary = load_churn_summary()

    fig = px.bar(
        summary,
        x="구분",
        y="이탈율",
        color="구분",
        color_discrete_map={
            "전체 고객": "#898781",
            "해지관련 부정 VOC 이력 있음": "#d03b3b",
        },
        text=summary["이탈율"].map(lambda v: f"{v:.1f}%"),
        custom_data=["고객수", "이탈고객수", "이탈율"],
        title="전체 고객 vs 해지관련 부정 VOC 이력 고객 이탈율 비교",
        labels={"이탈율": "이탈율 (%)"},
    )

    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>"
            "이탈율: %{customdata[2]:.1f}%"
            "<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=False, yaxis_ticksuffix="%")

    fig.show()


if __name__ == "__main__":
    main()
