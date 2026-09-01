"""
meal-bbang/Korean_message 데이터셋에서 정상 문자(라벨 0)를 가져와
오탐(Safe → Warning/Danger) 여부를 확인하는 스크립트
"""

import requests
import time
try:
    from datasets import load_dataset
except ImportError:  # 선택적 테스트 의존성
    load_dataset = None

API_URL = "http://127.0.0.1:8000/analyze-text"
SAMPLE_SIZE = 50   # 테스트할 샘플 수
DELAY = 5.0        # API 요청 간격 (초) — Gemini free tier 15 RPM 제한 대응

def run_test():
    if load_dataset is None:
        raise RuntimeError("datasets가 필요합니다. `pip install -r requirements.txt`를 실행해주세요.")
    print("데이터셋 로딩 중...")
    ds = load_dataset("meal-bbang/Korean_message", split="train")
    normal_data = [row["content"] for row in ds if row["class"] != 2]
    print(f"정상 문자 데이터 총 {len(normal_data)}건 → {SAMPLE_SIZE}건 샘플 테스트")

    sample = normal_data[:SAMPLE_SIZE]

    results = {"Danger": [], "Warning": [], "Safe": [], "Unknown": [], "Error": []}

    for i, text in enumerate(sample, 1):
        try:
            resp = requests.post(API_URL, json={"text": text}, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            grade = data.get("result", {}).get("grade", "Unknown")
            score = data.get("scores", {}).get("final", 0)
            results[grade].append({"text": text[:80], "score": score})
            print(f"[{i:3}/{SAMPLE_SIZE}] {grade:7} (점수: {score:.2f}) | {text[:40]}...")
        except Exception as e:
            results["Error"].append({"text": text[:80], "error": str(e)})
            print(f"[{i:3}/{SAMPLE_SIZE}] ERROR: {e}")

        time.sleep(DELAY)

    print("\n" + "="*55)
    print("[ 최종 결과 요약 ]")
    print(f"  Danger  : {len(results['Danger']):3}건 ({len(results['Danger'])/SAMPLE_SIZE*100:.1f}%)")
    print(f"  Warning : {len(results['Warning']):3}건 ({len(results['Warning'])/SAMPLE_SIZE*100:.1f}%)")
    print(f"  Safe    : {len(results['Safe']):3}건 ({len(results['Safe'])/SAMPLE_SIZE*100:.1f}%)")
    print(f"  Unknown : {len(results['Unknown']):3}건 ({len(results['Unknown'])/SAMPLE_SIZE*100:.1f}%)")
    print(f"  Error   : {len(results['Error']):3}건")
    print(f"  오탐률  : {(len(results['Danger'])+len(results['Warning']))/SAMPLE_SIZE*100:.1f}%  (정상인데 Warning/Danger)")
    print("="*55)

    if results["Danger"] or results["Warning"]:
        print("\n[ 오탐 케이스 (정상인데 Warning/Danger 판정) ]")
        for r in results["Danger"] + results["Warning"]:
            print(f"  점수 {r['score']:.2f} | {r['text']}")

if __name__ == "__main__":
    run_test()
