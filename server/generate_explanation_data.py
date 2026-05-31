"""
Gemini 교사 모델로 설명 포함 파인튜닝 데이터 생성
- 정상: 7 카테고리 × 400개 = 2800개
- 스미싱: meal-bbang/Korean_message (class==2) 2800개
- 출력: exaone_finetune_with_explanation.jsonl
"""

from google import genai
from datasets import load_dataset
import json
import random
import time
import re
import os

API_KEY = "AIzaSyCa2GnI1dhBrVQTBRdKaF02XcDVWJoxiKs"
OUTPUT_FILE = "exaone_finetune_with_explanation.jsonl"
NORMAL_FILES = [
    r"C:\Users\asd\Downloads\normal_messages_mine.jsonl",
    r"C:\Users\asd\Desktop\vscode\normal_messages_friend.jsonl",
]
NORMAL_CATEGORIES = ["PERSONAL", "FINANCE", "DELIVERY", "GOVERNMENT", "PROMOTION", "AUTH", "WORK"]
SAMPLES_PER_CATEGORY = 400
BATCH_SIZE = 30
SEED = 42

INSTRUCTION = "다음 문자 메시지가 스미싱인지 분석하고, 판정 이유와 위험도를 설명해주세요."

MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

PROMPT_TEMPLATE = """다음 {n}개의 한국어 문자 메시지를 각각 분석해주세요.
각 메시지의 정답 레이블이 주어져 있습니다. 해당 레이블에 맞는 구체적인 분석을 제공해주세요.

{messages}

JSON 배열만 출력하세요 (다른 설명 없이):
[{{"판정": "스미싱" 또는 "정상", "위험도": "높음" 또는 "중간" 또는 "낮음", "이유": "2~3문장 한국어 설명"}}, ...]"""


def count_existing():
    if not os.path.exists(OUTPUT_FILE):
        return 0
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def load_normal_samples():
    category_pools = {cat: [] for cat in NORMAL_CATEGORIES}
    for file_path in NORMAL_FILES:
        if not os.path.exists(file_path):
            print(f"  파일 없음 (건너뜀): {file_path}")
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    label = obj.get("label", "")
                    text = obj.get("text", "").strip()
                    if label in category_pools and text:
                        category_pools[label].append(text)
                except Exception:
                    pass

    samples = []
    random.seed(SEED)
    for cat in NORMAL_CATEGORIES:
        pool = list(set(category_pools[cat]))  # 중복 제거
        if len(pool) < SAMPLES_PER_CATEGORY:
            print(f"  경고: {cat} 풀={len(pool)}개 (목표 {SAMPLES_PER_CATEGORY}개)")
        selected = random.sample(pool, min(SAMPLES_PER_CATEGORY, len(pool)))
        for text in selected:
            samples.append({"text": text, "label": "정상", "category": cat})
    return samples


def load_smishing_samples():
    print("스미싱 데이터 로딩 중 (HuggingFace)...")
    ds = load_dataset("meal-bbang/Korean_message", split="train")
    texts = []
    for row in ds:
        if row["class"] == 2:
            text = row["content"].strip()
            if text:
                texts.append(text)
    print(f"  스미싱 원본: {len(texts)}개")

    random.seed(SEED)
    random.shuffle(texts)
    target = SAMPLES_PER_CATEGORY * 7  # 2800개
    selected = texts[:target]

    samples = []
    for text in selected:
        samples.append({"text": text, "label": "스미싱", "category": "SMISHING"})
    return samples


def parse_response(text):
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("["):
                text = part
                break
    return json.loads(text)


def format_prompt(batch):
    lines = []
    for i, item in enumerate(batch, 1):
        lines.append(f"[{i}] 레이블: {item['label']}\n문자: {item['text']}")
    return PROMPT_TEMPLATE.format(n=len(batch), messages="\n\n".join(lines))


def is_daily_limit(err_str):
    return "GenerateRequestsPerDayPerProjectPerModel" in err_str


def main():
    client = genai.Client(api_key=API_KEY)
    model_idx = 0
    current_model = MODELS[model_idx]

    # 데이터 준비
    print("=== 데이터 로딩 ===")
    normal_samples = load_normal_samples()
    print(f"정상 샘플: {len(normal_samples)}개")
    smishing_samples = load_smishing_samples()
    print(f"스미싱 샘플: {len(smishing_samples)}개")

    all_samples = normal_samples + smishing_samples
    all_samples.sort(key=lambda x: (x["category"], x["text"]))  # 재현성 보장
    random.seed(SEED)
    random.shuffle(all_samples)

    count_done = count_existing()
    total = len(all_samples)
    print(f"\n기존 처리: {count_done}개 / 전체: {total}개")

    if count_done >= total:
        print("이미 완료!")
        return

    remaining = all_samples[count_done:]
    print(f"남은 처리: {len(remaining)}개")
    print(f"사용 모델: {current_model}")
    print(f"예상 요청 수: {(len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE}회\n")

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        i = 0
        while i < len(remaining):
            batch = remaining[i:i + BATCH_SIZE]
            try:
                prompt = format_prompt(batch)
                response = client.models.generate_content(model=current_model, contents=prompt)
                results = parse_response(response.text)

                written = 0
                for j, item in enumerate(batch):
                    if j >= len(results):
                        break
                    res = results[j]
                    판정 = res.get("판정", item["label"])
                    위험도 = res.get("위험도", "중간")
                    이유 = res.get("이유", "")
                    output_text = f"판정: {판정}\n위험도: {위험도}\n이유: {이유}"
                    record = {
                        "instruction": INSTRUCTION,
                        "input": item["text"],
                        "output": output_text,
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    written += 1

                f.flush()
                i += written
                print(f"  진행: {count_done + i}/{total} ({(count_done + i) / total * 100:.1f}%)", end="\r")
                time.sleep(7)

            except Exception as e:
                err_str = str(e)
                print(f"\n  에러: {err_str[:250]}")

                if is_daily_limit(err_str):
                    model_idx += 1
                    if model_idx >= len(MODELS):
                        print("  모든 모델 일일 한도 초과. 내일 재실행하세요.")
                        break
                    current_model = MODELS[model_idx]
                    print(f"  모델 전환 → {current_model}")
                else:
                    m = re.search(r"'retryDelay': '(\d+)s'", err_str)
                    wait = int(m.group(1)) + 5 if m else 45
                    print(f"  {wait}초 후 재시도...")
                    time.sleep(wait)

    final = count_existing()
    print(f"\n=== 완료 ===")
    print(f"  총계: {final}개")
    print(f"  저장: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
