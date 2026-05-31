"""
피드백 관리자 스크립트
실행: python server/admin_feedback.py
옵션: python server/admin_feedback.py --export  (CSV 저장)
"""
import sys
import csv
import datetime
import os

sys.path.insert(0, os.path.dirname(__file__))
from db_config import get_db_conn


def fetch_feedback():
    con = get_db_conn()
    cursor = con.cursor()
    cursor.execute("""
        SELECT id, given_grade, correct_grade, reason, text_content, image_path, created_at
        FROM feedback ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    con.close()
    return rows


def print_stats(rows):
    total = len(rows)
    if total == 0:
        print("피드백 데이터 없음")
        return

    # 등급별 오탐/미탐 집계
    mismatch = [r for r in rows if r[1] != r[2]]  # given != correct
    match = total - len(mismatch)

    print(f"\n{'='*40}")
    print(f"  피드백 통계 (총 {total}건)")
    print(f"{'='*40}")
    print(f"  판정 일치:  {match}건 ({match/total*100:.1f}%)")
    print(f"  판정 불일치: {len(mismatch)}건 ({len(mismatch)/total*100:.1f}%)")

    # 불일치 유형별 집계
    if mismatch:
        print(f"\n  [불일치 유형]")
        from collections import Counter
        types = Counter(f"{r[1]} → {r[2]}" for r in mismatch)
        for t, cnt in types.most_common():
            print(f"    {t}: {cnt}건")

    # 최근 5건
    print(f"\n  [최근 피드백 5건]")
    for r in rows[:5]:
        ts = datetime.datetime.fromtimestamp(r[6]).strftime("%m/%d %H:%M") if r[6] else "-"
        text_preview = (r[4] or "")[:30].replace("\n", " ")
        print(f"    [{ts}] 시스템:{r[1]} → 실제:{r[2]}  \"{text_preview}\"")

    print()


def export_csv(rows):
    if not rows:
        print("내보낼 데이터 없음")
        return

    filename = f"feedback_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    out_path = os.path.join(os.path.dirname(__file__), filename)

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "시스템판정", "실제판정", "이유", "문자내용", "이미지경로", "제출시각"])
        for r in rows:
            ts = datetime.datetime.fromtimestamp(r[6]).strftime("%Y-%m-%d %H:%M:%S") if r[6] else ""
            writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5], ts])

    print(f"CSV 저장 완료: {out_path}")


if __name__ == "__main__":
    rows = fetch_feedback()
    print_stats(rows)

    if "--export" in sys.argv:
        export_csv(rows)
    else:
        print("CSV로 내보내려면: python server/admin_feedback.py --export")
