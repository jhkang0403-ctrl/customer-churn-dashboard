"""
가입기간(tenure_months) vs 평균 데이터 사용량(data_gb) 산점도, 이탈 여부 색상 구분 (plotly.express)

data/data_customers.csv, data/data_usage_history.csv를 직접 읽어 재계산한다.
"""
import os

import pandas as pd
import plotly.express as px

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

CUSTOMERS_PATH = os.path.join(DATA_DIR, "data_customers.csv")
USAGE_PATH = os.path.join(DATA_DIR, "data_usage_history.csv")

REFERENCE_DATE = pd.Timestamp("2024-12-31")


def load_scatter_data():
    customers = pd.read_csv(CUSTOMERS_PATH, encoding="utf-8-sig")
    usage = pd.read_csv(USAGE_PATH, encoding="utf-8-sig")

    customers["join_date"] = pd.to_datetime(customers["join_date"])
    customers["tenure_months"] = (
        (REFERENCE_DATE.year - customers["join_date"].dt.year) * 12
        + (REFERENCE_DATE.month - customers["join_date"].dt.month)
    )

    avg_usage = usage.groupby("customer_id")["data_gb"].mean().rename("avg_data_gb")

    merged = customers.merge(avg_usage, on="customer_id", how="left")
    merged["이탈여부"] = merged["churn_yn"].str.strip().str.upper().map({"Y": "이탈", "N": "유지"})

    return merged


def main():
    df = load_scatter_data()

    fig = px.scatter(
        df,
        x="tenure_months",
        y="avg_data_gb",
        color="이탈여부",
        color_discrete_map={"유지": "#898781", "이탈": "#d03b3b"},
        custom_data=["customer_id", "tenure_months", "avg_data_gb", "이탈여부"],
        title="가입기간 대비 평균 데이터 사용량 (이탈 여부별)",
        labels={"tenure_months": "가입기간 (개월)", "avg_data_gb": "평균 데이터 사용량 (GB)"},
    )

    fig.update_traces(
        marker=dict(size=9, opacity=0.75, line=dict(width=0.5, color="white")),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "가입기간: %{customdata[1]}개월<br>"
            "평균 데이터 사용량: %{customdata[2]:.1f}GB<br>"
            "이탈 여부: %{customdata[3]}"
            "<extra></extra>"
        ),
    )
    fig.update_layout(legend_title_text="이탈 여부")

    fig.show()


if __name__ == "__main__":
    main()
