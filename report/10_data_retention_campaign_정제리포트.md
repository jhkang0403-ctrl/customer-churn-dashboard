# data_retention_campaign_raw.csv 정제 리포트

```
원본 행 수: 500
============================================================
[1] 완전 중복 행 제거: 15건 삭제 -> 남은 행 485
[2] 결측치 NULL 표준화: 총 956건 셀 변경
     - discount_pct: 245건 -> NULL
     - response_date: 269건 -> NULL
     - converted_yn: 38건 -> NULL
     - agent_id: 404건 -> NULL
[3] agent_id 표기 정규화(대문자+trim): 4건 변경
[4] 날짜 포맷 ISO(YYYY-MM-DD) 통일:
     - send_date: 485건 변환 성공, 0건 파싱 실패
     - response_date: 216건 변환 성공, 0건 파싱 실패
[5] 라벨 표기 통일 (매핑 테이블):
     - channel: 원본 16종 -> 표준 4종, 377건 값 변경
     - offer_type: 원본 11종 -> 표준 3종, 353건 값 변경
     - responded_yn: 원본 10종 -> 표준 2종, 394건 값 변경
     - converted_yn: 원본 10종 -> 표준 2종, 362건 값 변경
[6] discount_pct 스케일 0~100 정수% 통일:
     - percent_string(57건), number_1_100(102건), fraction_0_1(76건) -> 변환 완료
     - 논리적으로 불가능한 값(150%,150,1.5,-5): 5건 -> NULL 처리
[7] 컬럼 간 논리적 모순 보정:
     - (a) responded_yn=FALSE인데 response_date 존재 -> TRUE로 보정: 7건
     - (b) responded_yn=TRUE인데 response_date 없음 -> 그대로 유지(정책상 정상): 7건
     - (c) response_date < send_date -> response_date NULL 처리: 2건
[8] 참조무결성 처리:
     - customer_id가 C001~C500 밖 -> 행 삭제: 3건 -> 남은 행 482
     - agent_id가 AG01~AG20 밖(예: AG21) -> 그대로 유지: 1건 (삭제 안 함)
============================================================
최종 행 수: 482 (원본 500행 대비 18건 감소)
저장 완료: C:\Users\jhkan\OneDrive\바탕 화면\AI_insight\EDATA_7\customer_churn_dashboard\customer-churn-dashboard\data\data_retention_campaign_clean.csv
```
