"""
개인 문자 HTML 파일을 파싱하여 스미싱 탐지 API로 테스트
"""

import sys
import re
import requests
import time
import argparse
import os
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

API_URL = "http://127.0.0.1:8000/analyze-text"
DELAY = 5.0  # Gemini free tier 15 RPM 제한 대응

SAMPLE_SIZE = None  # None이면 전체, 숫자 입력 시 앞에서 N개만


def parse_messages(filepath: str) -> list[str]:
    with open(filepath, "rb") as f:
        raw = f.read().decode("utf-8", errors="replace")

    # HTML 구분자 <br><br>-<br><br> 로 먼저 분리 (내용 내 '-'와 구별)
    parts = re.split(r"<br><br>-<br><br>", raw)

    messages = []
    for part in parts:
        # HTML 태그 제거
        text = re.sub(r"<br\s*/?>", "\n", part, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
        text = text.strip()
        if text:
            messages.append(text)

    return messages


def run_test(html_file: Path, sample_size: int | None = SAMPLE_SIZE):
    print("파일 파싱 중...")
    if not html_file.is_file():
        raise FileNotFoundError(f"HTML 파일을 찾을 수 없습니다: {html_file}")
    messages = parse_messages(str(html_file))
    print(f"총 {len(messages)}개 메시지 발견")

    sample = messages if sample_size is None else messages[:sample_size]
    total = len(sample)
    print(f"→ {total}개 테스트 시작 (예상 소요: {total * DELAY / 60:.1f}분)\n")

    results = {"Danger": [], "Warning": [], "Safe": [], "Unknown": [], "Error": []}
    for i, text in enumerate(sample, 1):
        try:
            resp = requests.post(API_URL, json={"text": text}, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            grade = data.get("result", {}).get("grade", "Unknown")
            score = data.get("scores", {}).get("final", 0)
            results[grade].append({"text": text[:80], "score": score})
            marker = "!!" if grade in ("Danger", "Warning") else "  "
            line = f"[{i:3}/{total}] {marker} {grade:7} (점수: {score:.2f}) | {text[:50].replace(chr(10), ' ')}..."
        except Exception as e:
            results["Error"].append({"text": text[:80], "error": str(e)})
            line = f"[{i:3}/{total}] ERROR: {e}"

        print(line)

        # 진행 상황 즉시 파일에 추가 (중간에 꺼져도 기록 남음)
        with open("test_my_messages_result.txt", "a", encoding="utf-8") as f:
            f.write(line + "\n")

        time.sleep(DELAY)

    # 최종 요약 파일 저장
    with open("test_my_messages_result.txt", "a", encoding="utf-8") as f:
        f.write(f"\nDanger : {len(results['Danger'])}건\n")
        f.write(f"Warning: {len(results['Warning'])}건\n")
        f.write(f"Safe   : {len(results['Safe'])}건\n")
        f.write(f"Error  : {len(results['Error'])}건\n")
        if results["Danger"] or results["Warning"]:
            f.write("\n[ 주의/위험 판정 ]\n")
            for r in results["Danger"] + results["Warning"]:
                f.write(f"  {r['score']:.2f} | {r['text']}\n")

    print("\n" + "=" * 55)
    print("[ 최종 결과 요약 ]")
    print(f"  Danger  : {len(results['Danger']):3}건")
    print(f"  Warning : {len(results['Warning']):3}건")
    print(f"  Safe    : {len(results['Safe']):3}건")
    print(f"  Unknown : {len(results['Unknown']):3}건")
    print(f"  Error   : {len(results['Error']):3}건")
    print("=" * 55)
    print("결과 파일: test_my_messages_result.txt")

    if results["Danger"] or results["Warning"]:
        print("\n[ 주의/위험 판정 메시지 ]")
        for r in results["Danger"] + results["Warning"]:
            print(f"  {r['score']:.2f} | {r['text']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="개인 문자 HTML 파일 API 테스트")
    parser.add_argument(
        "--html",
        default=os.getenv("MESSAGES_HTML_FILE"),
        help="분석할 HTML 파일 경로 (MESSAGES_HTML_FILE로도 설정 가능)",
    )
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    args = parser.parse_args()
    if not args.html:
        parser.error("--html 경로 또는 MESSAGES_HTML_FILE 환경변수가 필요합니다.")
    run_test(Path(args.html), args.sample_size)
