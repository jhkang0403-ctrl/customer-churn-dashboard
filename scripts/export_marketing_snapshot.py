"""'채널 효율' 페이지가 배포 환경(BigQuery 인증 정보 없음)에서 쓸 수 있도록
marketing_spend 테이블을 그대로 data/marketing_spend_snapshot.csv로 저장한다.
"""
import os

from google.cloud import bigquery

BQ_PROJECT_ID = "project-6342726b-6c19-4847-844"
BQ_DATASET = "project1_day1"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

MARKETING_SPEND_QUERY = f"""
    SELECT *
    FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.marketing_spend`
    ORDER BY month, channel
"""


def main() -> None:
    client = bigquery.Client(project=BQ_PROJECT_ID)

    df = client.query(MARKETING_SPEND_QUERY).to_dataframe()
    path = os.path.join(DATA_DIR, "marketing_spend_snapshot.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {path} ({len(df)}행)")


if __name__ == "__main__":
    main()
