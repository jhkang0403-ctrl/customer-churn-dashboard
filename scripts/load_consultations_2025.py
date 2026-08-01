"""data_clean_상담이력.csv의 2025-01·02월분을 BigQuery consultations 테이블에 추가 적재한다.

consultations 테이블 스키마: consult_id, customer_id, consult_date, channel, category,
duration_min, status, is_recontact, agent_id (2024-01~2024-12, 1320행 존재).

정제본의 "소속"(팀)·"월" 컬럼은 테이블 스키마에 없으므로 적재 시 제외한다.
consult_id는 기존 최대값(CON1320) 이후를 이어서 순번을 부여한다.

이미 2025-01/02 데이터가 테이블에 있으면 중복 적재를 막기 위해 중단한다(재실행 안전).
"""
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_PATH = BASE_DIR / "data" / "data_clean_상담이력.csv"

PROJECT_ID = "project-6342726b-6c19-4847-844"
DATASET = "project1_day1"
TABLE = "consultations"
TABLE_REF = f"{PROJECT_ID}.{DATASET}.{TABLE}"
TARGET_MONTHS = ["2025-01", "2025-02"]

COLUMN_MAP = {
    "상담원": "agent_id",
    "상담일": "consult_date",
    "고객ID": "customer_id",
    "채널": "channel",
    "문의유형": "category",
    "상담시간": "duration_min",
    "처리결과": "status",
    "재문의여부": "is_recontact",
}
OUTPUT_COLUMNS = [
    "consult_id", "customer_id", "consult_date", "channel",
    "category", "duration_min", "status", "is_recontact", "agent_id",
]


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)

    existing = list(
        client.query(
            f"SELECT COUNT(*) AS n FROM `{TABLE_REF}` "
            "WHERE FORMAT_DATE('%Y-%m', consult_date) IN UNNEST(@months)",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ArrayQueryParameter("months", "STRING", TARGET_MONTHS)]
            ),
        ).result()
    )[0]["n"]
    if existing > 0:
        raise SystemExit(
            f"{TARGET_MONTHS} 데이터가 이미 {existing}건 존재합니다. 중복 적재를 막기 위해 중단합니다."
        )

    max_id = list(client.query(f"SELECT MAX(consult_id) AS max_id FROM `{TABLE_REF}`").result())[0]["max_id"]
    max_num = int(max_id.replace("CON", ""))

    df = pd.read_csv(CLEAN_PATH, encoding="utf-8-sig")
    df = df[df["월"].isin(TARGET_MONTHS)].reset_index(drop=True)
    df = df.rename(columns=COLUMN_MAP)
    df["consult_date"] = pd.to_datetime(df["consult_date"]).dt.date
    df["is_recontact"] = df["is_recontact"].astype(bool)
    df["consult_id"] = [f"CON{max_num + i + 1:04d}" for i in range(len(df))]
    df = df[OUTPUT_COLUMNS]

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    job = client.load_table_from_dataframe(df, TABLE_REF, job_config=job_config)
    job.result()

    print(f"적재 완료: {len(df)}건 (consult_id {df['consult_id'].iloc[0]} ~ {df['consult_id'].iloc[-1]})")

    verify = list(
        client.query(
            f"SELECT FORMAT_DATE('%Y-%m', consult_date) AS month, COUNT(*) AS n "
            f"FROM `{TABLE_REF}` WHERE FORMAT_DATE('%Y-%m', consult_date) IN UNNEST(@months) "
            "GROUP BY month ORDER BY month",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ArrayQueryParameter("months", "STRING", TARGET_MONTHS)]
            ),
        ).result()
    )
    for row in verify:
        print(f"  검증: {row['month']} -> {row['n']}건")


if __name__ == "__main__":
    main()
