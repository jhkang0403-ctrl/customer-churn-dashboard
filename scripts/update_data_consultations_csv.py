"""data_clean_상담이력.csv의 2025-01·02월분을 data_consultations.csv에 이어붙인다.

data_consultations.csv 스키마: consult_id, customer_id, consult_date, channel, category,
duration_min, status, is_recontact(Y/N 텍스트), agent_id (2024-01~2024-12, 1320행).

BigQuery consultations 테이블 적재(load_consultations_2025.py)와 같은 소스·같은 consult_id
채번(CON1321~)을 사용해 두 저장소가 서로 어긋나지 않게 한다. is_recontact은 이 CSV의 기존
표기 관례(Y/N 텍스트)에 맞춰 저장한다(정제본의 True/False 불리언과 다름).

이미 2025-01/02가 포함되어 있으면 중복 추가를 막기 위해 중단한다(재실행 안전).
"""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CLEAN_PATH = DATA_DIR / "data_clean_상담이력.csv"
CONSULTATIONS_PATH = DATA_DIR / "data_consultations.csv"
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
    existing = pd.read_csv(CONSULTATIONS_PATH, encoding="utf-8-sig")

    already_present = existing["consult_date"].str.slice(0, 7).isin(TARGET_MONTHS).sum()
    if already_present > 0:
        raise SystemExit(f"{TARGET_MONTHS} 데이터가 이미 {already_present}건 존재합니다. 중복 추가를 막기 위해 중단합니다.")

    max_num = existing["consult_id"].str.replace("CON", "", regex=False).astype(int).max()

    new_df = pd.read_csv(CLEAN_PATH, encoding="utf-8-sig")
    new_df = new_df[new_df["월"].isin(TARGET_MONTHS)].reset_index(drop=True)
    new_df = new_df.rename(columns=COLUMN_MAP)
    new_df["is_recontact"] = new_df["is_recontact"].map({True: "Y", False: "N"})
    new_df["consult_id"] = [f"CON{max_num + i + 1:04d}" for i in range(len(new_df))]
    new_df = new_df[OUTPUT_COLUMNS]

    combined = pd.concat([existing, new_df], ignore_index=True)
    combined.to_csv(CONSULTATIONS_PATH, index=False, encoding="utf-8-sig")

    print(f"기존 {len(existing)}건 + 신규 {len(new_df)}건 = {len(combined)}건")
    print(f"신규 consult_id 범위: {new_df['consult_id'].iloc[0]} ~ {new_df['consult_id'].iloc[-1]}")
    print(f"저장 경로: {CONSULTATIONS_PATH}")


if __name__ == "__main__":
    main()
