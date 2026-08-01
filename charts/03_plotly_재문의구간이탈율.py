"""
고객별 재문의(is_recontact=Y) 횟수 구간(0회 / 1회 / 2회 이상)별 이탈율 비교 (plotly.express)

data/data_consultations.csv, data/data_customers.csv를 직접 읽어 재계산한다.
"""
import os
import sys

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

sys.path.insert(0, BASE_DIR)
import common as c

CONSULTATIONS_PATH = os.path.join(DATA_DIR, "data_consultations.csv")
CUSTOMERS_PATH = os.path.join(DATA_DIR, "data_customers.csv")

HIGHLIGHT_BUCKET = "2회 이상"


def bucketize(count: int) -> str:
    if count == 0:
        return "0회"
    if count == 1:
        return "1회"
    return "2회 이상"


def load_bucket_summary():
    consultations = pd.read_csv(CONSULTATIONS_PATH, encoding="utf-8-sig")
    customers = pd.read_csv(CUSTOMERS_PATH, encoding="utf-8-sig")
    customers["is_churned"] = customers["churn_yn"].str.strip().str.upper() == "Y"

    recontact_counts = (
        consultations[consultations["is_recontact"].str.strip().str.upper() == "Y"]
        .groupby("customer_id")
        .size()
    )

    customers["recontact_count"] = (
        customers["customer_id"].map(recontact_counts).fillna(0).astype(int)
    )
    customers["recontact_bucket"] = customers["recontact_count"].apply(bucketize)

    bucket_order = ["0회", "1회", "2회 이상"]
    summary = (
        customers.groupby("recontact_bucket")
        .agg(고객수=("customer_id", "size"), 이탈고객수=("is_churned", "sum"))
        .reindex(bucket_order)
        .fillna(0)
        .astype({"고객수": int, "이탈고객수": int})
        .reset_index()
        .rename(columns={"recontact_bucket": "재문의구간"})
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100

    overall_rate = customers["is_churned"].mean() * 100

    return summary, overall_rate


def main():
    summary, overall_rate = load_bucket_summary()

    fig = px.bar(
        summary,
        x="재문의구간",
        y="이탈율",
        color="재문의구간",
        color_discrete_map={
            "0회": c.COLOR_NEUTRAL,
            "1회": c.COLOR_NEUTRAL,
            "2회 이상": c.COLOR_CRITICAL,
        },
        text=summary["이탈율"].map(lambda v: f"{v:.1f}%"),
        custom_data=["고객수", "이탈고객수", "이탈율"],
        title="재문의 횟수 구간별 이탈율",
        labels={"이탈율": "이탈율 (%)", "재문의구간": "재문의 횟수"},
        category_orders={"재문의구간": ["0회", "1회", "2회 이상"]},
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

    fig.add_hline(y=overall_rate, line_dash="dash", line_color="#0b0b0b")
    fig.add_annotation(
        x=0.5,
        y=overall_rate,
        xref="x",
        yref="y",
        xanchor="left",
        yanchor="bottom",
        text=f"전체 평균 이탈율 {overall_rate:.1f}%",
        showarrow=False,
        bgcolor="rgba(252,252,251,0.85)",
        font=dict(color="#0b0b0b"),
    )

    fig.update_layout(**c.CHART_LAYOUT)
    fig.update_layout(showlegend=False, yaxis_ticksuffix="%")

    if os.environ.get("CHART_HEADLESS"):
        out_path = os.path.join(BASE_DIR, "charts", "output", "03_재문의구간이탈율.png")
        fig.write_image(out_path, width=1000, height=600, scale=2)
        print(f"저장: {out_path}")
    else:
        fig.show()


if __name__ == "__main__":
    main()
