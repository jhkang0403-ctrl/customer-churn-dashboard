"""
요금제(plan)별 고객 수 및 이탈율 비교 (plotly.express)

data/data_customers.csv를 직접 읽어 재계산한다.
"""
import os

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CUSTOMERS_PATH = os.path.join(DATA_DIR, "data_customers.csv")

HIGHLIGHT_PLAN = "베이직"


def load_plan_summary():
    customers = pd.read_csv(CUSTOMERS_PATH, encoding="utf-8-sig")
    customers["is_churned"] = customers["churn_yn"].str.strip().str.upper() == "Y"

    summary = (
        customers.groupby("plan")
        .agg(고객수=("customer_id", "size"), 이탈고객수=("is_churned", "sum"))
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100
    summary = summary.sort_values("이탈율", ascending=False).reset_index(drop=True)
    return summary


def main():
    summary = load_plan_summary()

    fig = px.bar(
        summary,
        x="plan",
        y="이탈율",
        color="plan",
        color_discrete_map={
            plan: ("#d03b3b" if plan == HIGHLIGHT_PLAN else "#898781")
            for plan in summary["plan"]
        },
        text=summary["이탈율"].map(lambda v: f"{v:.1f}%"),
        custom_data=["고객수", "이탈고객수", "이탈율"],
        title="요금제별 이탈율",
        labels={"이탈율": "이탈율 (%)", "plan": "요금제"},
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
