"""
meal-bbang/Korean_message 데이터셋에서 스미싱(라벨 2) 문자를 가져와
현재 서버 /analyze/text API로 테스트하는 스크립트
"""

import requests
import time
from datasets import load_dataset

API_URL = "http://127.0.0.1:8000/analyze-text"
SAMPLE_SIZE = 80   # 테스트할 샘플 수
OFFSET = 50        # 앞에서 몇 번째부터 시작할지 (0이면 처음부터, 50이면 51번째부터)
DELAY = 5.0        # API 요청 간격 (초) — Gemini free tier 15 RPM 제한 대응

def run_test():
    print("데이터셋 로딩 중...")
    ds = load_dataset("meal-bbang/Korean_message", split="train")
    smishing_data = [row["content"] for row in ds if row["class"] == 2]
    print(f"스미싱 데이터 총 {len(smishing_data)}건 → {OFFSET+1}~{OFFSET+SAMPLE_SIZE}번 테스트")

    sample = smishing_data[OFFSET:OFFSET + SAMPLE_SIZE]

    results = {"Danger": [], "Warning": [], "Safe": [], "Unknown": [], "Error": []}

    for i, text in enumerate(sample, 1):
        try:
            resp = requests.post(API_URL, json={"text": text}, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            grade = data.get("result", {}).get("grade", "Unknown")
            score = data.get("scores", {}).get("final", 0)
            results[grade].append({"text": text[:50], "score": score})
            print(f"[{i:3}/{SAMPLE_SIZE}] {grade:7} (점수: {score:.2f}) | {text[:40]}...")
        except Exception as e:
            results["Error"].append({"text": text[:50], "error": str(e)})
            print(f"[{i:3}/{SAMPLE_SIZE}] ERROR: {e}")

        time.sleep(DELAY)

    if results["Warning"]:
        print("\n[ 주의 판정 (Warning) ]")
        for r in results["Warning"]:
            print(f"  점수 {r['score']:.2f} | {r['text']}")

    print("\n" + "="*55)
    print("[ 최종 결과 요약 ]")
    print(f"  Danger  : {len(results['Danger']):3}건 ({len(results['Danger'])/SAMPLE_SIZE*100:.1f}%)")
    print(f"  Warning : {len(results['Warning']):3}건 ({len(results['Warning'])/SAMPLE_SIZE*100:.1f}%)")
    print(f"  Safe    : {len(results['Safe']):3}건 ({len(results['Safe'])/SAMPLE_SIZE*100:.1f}%)")
    print(f"  Unknown : {len(results['Unknown']):3}건 ({len(results['Unknown'])/SAMPLE_SIZE*100:.1f}%)")
    print(f"  Error   : {len(results['Error']):3}건")
    print(f"  탐지율  : {(len(results['Danger'])+len(results['Warning']))/SAMPLE_SIZE*100:.1f}%  (Danger+Warning)")
    print("="*55)

    if results["Safe"]:
        print("\n[ 미탐 케이스 (Safe로 잘못 판정) ]")
        for r in results["Safe"]:
            print(f"  점수 {r['score']:.2f} | {r['text']}")

if __name__ == "__main__":
    run_test()
