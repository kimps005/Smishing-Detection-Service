import os
import tempfile
os.environ['FLAGS_enable_pir_api'] = '0'
import pandas as pd
import cv2
from paddleocr import PaddleOCR
from pyzbar.pyzbar import decode
from difflib import SequenceMatcher
import re

IMAGE_DIR = "output"
CSV_PATH = "output/metadata.csv"

print("PaddleOCR 모델 로드 중...")
reader = PaddleOCR(use_angle_cls=True, lang='korean')
print("로딩 완료!\n")

df = pd.read_csv(CSV_PATH)


def correct_text(text):
    text = re.sub(r'https?:l\s+', 'https://', text)
    text = re.sub(r'https?://\s+', 'https://', text)
    text = re.sub(r'https?l[I1l]\s*', 'https://', text)
    text = re.sub(r'https?:[I1l]{2}\s*', 'https://', text)
    text = re.sub(r'([a-zA-Z])(com|net|org|kr)(\s|/|$)', r'\1.\2\3', text)
    text = re.sub(r'([a-zA-Z])(cor)(\s|/|$)', r'\1.com\3', text)
    text = re.sub(r'\bwww([a-zA-Z])', r'www.\1', text)
    return text


def run_paddleocr(img):
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp_path = tmp.name
        cv2.imwrite(tmp_path, img)
    try:
        result = reader.predict(tmp_path)
    finally:
        os.remove(tmp_path)

    lines = []
    if result:
        for page in result:
            if not page:
                continue
            if isinstance(page, dict):
                texts = page.get('rec_texts') or page.get('text', [])
                polys = page.get('rec_polys') or page.get('dt_boxes', [])
                for i, text in enumerate(texts):
                    y = polys[i][0][1] if i < len(polys) else i
                    lines.append((y, text))
            else:
                for line in page:
                    try:
                        if isinstance(line[1], (list, tuple)):
                            lines.append((line[0][0][1], line[1][0]))
                        else:
                            lines.append((line[0][0][1], str(line[1])))
                    except Exception:
                        continue
    lines.sort(key=lambda x: x[0])
    return " ".join(text for _, text in lines)


def get_accuracy(true_text, pred_text):
    true_clean = str(true_text).replace(" ", "").replace("\n", "")
    pred_clean = str(pred_text).replace(" ", "").replace("\n", "")
    if len(true_clean) == 0:
        return 0.0
    return round(SequenceMatcher(None, true_clean, pred_clean).ratio() * 100, 2)


results = []
print(f"총 {len(df)}개 채점 시작! (시간이 오래 걸릴 수 있습니다)")

for index, row in df.iterrows():
    img_name = row['file_name']
    true_text = str(row['text'])

    img_path = os.path.join(IMAGE_DIR, img_name)
    if not os.path.exists(img_path):
        continue

    img = cv2.imread(img_path)

    qr_urls = [obj.data.decode("utf-8") for obj in decode(img)]
    extracted_qr = qr_urls[0] if qr_urls else ""

    raw_text = run_paddleocr(img)
    extracted_text = correct_text(raw_text)

    accuracy = get_accuracy(true_text, extracted_text)

    results.append({
        "파일명": img_name,
        "정답_텍스트": true_text,
        "추출_텍스트": extracted_text,
        "추출_QR": extracted_qr,
        "글자인식_정확도(%)": accuracy
    })

    print(f"[{index+1}/{len(df)}] {img_name} 분석 완료 - 정확도: {accuracy}%")

result_df = pd.DataFrame(results)
result_df.to_csv("evaluation_results_paddle.csv", index=False, encoding='utf-8-sig')

avg_accuracy = result_df["글자인식_정확도(%)"].mean()

print("\n" + "=" * 50)
print(" 전체 PaddleOCR 채점이 완료되었습니다!")
print(f"▶ 분석한 이미지 수: {len(results)}개")
print(f"▶ 전체 평균 텍스트 인식 정확도: {avg_accuracy:.2f}%")
print("=" * 50)
print("'evaluation_results_paddle.csv' 파일이 저장되었습니다.")
