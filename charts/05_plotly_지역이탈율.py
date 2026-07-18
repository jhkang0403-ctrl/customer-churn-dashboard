"""
지역(region)별 고객 수 및 이탈율 비교 (plotly.express)

data/data_customers.csv를 직접 읽어 재계산한다.
"""
import os

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CUSTOMERS_PATH = os.path.join(DATA_DIR, "data_customers.csv")

HIGHLIGHT_REGIONS = {"부산", "대구"}
CAPTION_REGION = "인천"


def load_region_summary():
    customers = pd.read_csv(CUSTOMERS_PATH, encoding="utf-8-sig")
    customers["is_churned"] = customers["churn_yn"].str.strip().str.upper() == "Y"

    summary = (
        customers.groupby("region")
        .agg(고객수=("customer_id", "size"), 이탈고객수=("is_churned", "sum"))
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100
    summary = summary.sort_values("이탈율", ascending=False).reset_index(drop=True)
    return summary


def main():
    summary = load_region_summary()

    caption_row = summary[summary["region"] == CAPTION_REGION].iloc[0]
    caption_text = (
        f"※ {CAPTION_REGION}은 표본이 {int(caption_row['고객수'])}건이지만 "
        f"이탈 {int(caption_row['이탈고객수'])}건뿐입니다."
    )

    fig = px.bar(
        summary,
        x="region",
        y="이탈율",
        color="region",
        color_discrete_map={
            region: ("#d03b3b" if region in HIGHLIGHT_REGIONS else "#898781")
            for region in summary["region"]
        },
        text=summary["이탈율"].map(lambda v: f"{v:.1f}%"),
        custom_data=["고객수", "이탈고객수", "이탈율"],
        title="지역별 이탈율",
        labels={"이탈율": "이탈율 (%)", "region": "지역"},
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
    fig.update_layout(
        showlegend=False,
        yaxis_ticksuffix="%",
        margin=dict(b=140),
    )
    fig.add_annotation(
        x=0,
        y=-0.3,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        text=caption_text,
        showarrow=False,
        font=dict(size=12, color="#52514e"),
    )

    fig.show()


if __name__ == "__main__":
    main()
