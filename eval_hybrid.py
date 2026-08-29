import os
import tempfile
os.environ['FLAGS_enable_pir_api'] = '0'
import pandas as pd
import cv2
import easyocr
from paddleocr import PaddleOCR
from pyzbar.pyzbar import decode
from difflib import SequenceMatcher
import re

IMAGE_DIR = "output"
SAMPLE_CSV = "output/metadata.csv"

URL_RE = re.compile(
    r"http[s]?://\S+"
    r"|http[s]?:ll\S+"
    r"|http[s]?:[/\\]{1,2}\S+"
    r"|(?<!\w)[a-zA-Z0-9][-a-zA-Z0-9.]*\.(?:com|net|org|kr)(?:/\S*)?"
)


def correct_text(text):
    text = re.sub(r'https?:l\s+', 'https://', text)
    text = re.sub(r'https?://\s+', 'https://', text)
    text = re.sub(r'https?l[I1l]\s*', 'https://', text)
    text = re.sub(r'https?:[I1l]{2}\s*', 'https://', text)
    text = re.sub(r'ht\s+tp(s?)://', r'http\1://', text)
    text = re.sub(r'https?\s*:\s*//\s*', 'https://', text)
    text = re.sub(r'https?:/\s+/', 'https://', text)
    text = re.sub(r'(https?:)[Il1\[]{1,2}', r'\1//', text)
    text = re.sub(r'(https?://)([Il1])(/)', r'\1/\3', text)
    text = re.sub(r'(https?://[^\s]*\w)\[(\w)', r'\1.\2', text)
    text = re.sub(r'(https?://[^\s]*\w)\](\w)', r'\1.\2', text)
    text = re.sub(r'([a-zA-Z])(com|net|org|kr)(\s|/|$)', r'\1.\2\3', text)
    text = re.sub(r'([a-zA-Z])(cor)(\s|/|$)', r'\1.com\3', text)
    text = re.sub(r'\bwww([a-zA-Z])', r'www.\1', text)
    text = re.sub(r'\b[/\\|]{1,3}[A-Za-z0-9]{0,3}[/\\|]{1,3}\b', ' ', text)
    text = re.sub(r'(?<!\S)[^\w가-힣\s]{2,}(?!\S)', ' ', text)
    text = re.sub(r'\[[^\w가-힣]{1,5}\]', '', text)
    text = re.sub(r' {2,}', ' ', text).strip()
    return text


_URL_START = re.compile(r'^https?://')
_MSG_HEADER = re.compile(r'^\[|^[가-힣]')


def _reorder_url_blocks(lines):
    if len(lines) < 2:
        return lines
    url_front = []
    i = 0
    while i < len(lines) and _URL_START.search(lines[i][1]):
        url_front.append(lines[i])
        i += 1
    rest = lines[i:]
    if url_front and rest and _MSG_HEADER.search(rest[0][1]):
        return rest + url_front
    return lines


def run_easyocr(img, reader):
    """EasyOCR로 텍스트 추출 (한글 위주)"""
    result = reader.readtext(img)
    # result: [(bbox, text, confidence), ...]
    # bbox: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    lines = []
    for (bbox, text, conf) in result:
        y = bbox[0][1]  # 좌상단 y좌표
        lines.append((y, text))
    lines.sort(key=lambda x: x[0])
    lines = _reorder_url_blocks(lines)
    return " ".join(text for _, text in lines)


def run_paddleocr_url_only(img, reader):
    """PaddleOCR로 URL만 추출"""
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
    raw = " ".join(text for _, text in lines)
    raw = correct_text(raw)
    # URL만 추출해서 반환
    urls = URL_RE.findall(raw)
    return urls


def merge_texts(easy_text, paddle_urls):
    """EasyOCR 텍스트 + PaddleOCR에서만 잡힌 URL 합산"""
    easy_urls = set(URL_RE.findall(easy_text))
    extra_urls = [u for u in paddle_urls if u not in easy_urls]
    if extra_urls:
        return easy_text + " " + " ".join(extra_urls)
    return easy_text


def get_accuracy(true_text, pred_text):
    true_clean = str(true_text).replace(" ", "").replace("\n", "")
    pred_clean = str(pred_text).replace(" ", "").replace("\n", "")
    if len(true_clean) == 0:
        return 0.0
    return round(SequenceMatcher(None, true_clean, pred_clean).ratio() * 100, 2)


def extract_qr(img):
    qr_urls = [obj.data.decode("utf-8") for obj in decode(img)]
    return qr_urls[0] if qr_urls else ""


OUTPUT_CSV = "evaluation_results_hybrid.csv"

sample_df = pd.read_csv(SAMPLE_CSV)
print(f"총 {len(sample_df)}장 하이브리드(EasyOCR+PaddleOCR) 평가 시작")

print("EasyOCR 로드 중...")
easy_reader = easyocr.Reader(['ko', 'en'], gpu=False)
print("PaddleOCR 로드 중...")
paddle_reader = PaddleOCR(use_angle_cls=True, lang='korean', det_db_thresh=0.2, det_db_box_thresh=0.5)
print("로드 완료!\n")

results = []
for i, row in sample_df.iterrows():
    img_path = os.path.join(IMAGE_DIR, row['file_name'])
    if not os.path.exists(img_path):
        continue
    img = cv2.imread(img_path)
    true_text = str(row['text'])

    qr = extract_qr(img)

    # EasyOCR: 한글 텍스트
    easy_raw = run_easyocr(img, easy_reader)
    easy_corrected = correct_text(easy_raw)
    easy_corrected = re.sub(r'(https?://\S+)\s+(com|net|org|co\.kr|kr)(\s|/|$)', r'\1.\2\3', easy_corrected)
    easy_corrected = re.sub(r'(https?://\S+\.(com|net|org|co\.kr|kr))\s+(\[?[A-Za-z0-9_\-]+)', lambda m: m.group(1) + '/' + m.group(3).lstrip('['), easy_corrected)
    easy_corrected = re.sub(r'(https?://\S+)\s+(/\S+)', r'\1\2', easy_corrected)

    # PaddleOCR: URL 보완
    paddle_urls = run_paddleocr_url_only(img, paddle_reader)

    # 합산
    extracted = merge_texts(easy_corrected, paddle_urls)
    acc = get_accuracy(true_text, extracted)

    results.append({
        "파일명": row['file_name'],
        "정답_텍스트": true_text,
        "추출_텍스트": extracted,
        "추출_QR": qr,
        "글자인식_정확도(%)": acc
    })
    print(f"[Hybrid {len(results)}/{len(sample_df)}] {row['file_name']} - {acc}%")

all_df = pd.DataFrame(results)

has_url_mask = all_df['정답_텍스트'].apply(lambda t: bool(URL_RE.search(str(t))))
has_url  = all_df[has_url_mask]
no_url   = all_df[~has_url_mask]
url_success = has_url.apply(lambda r: bool(URL_RE.search(str(r['추출_텍스트']))) or str(r['추출_QR']) not in ['', 'nan'], axis=1).sum()

avg        = all_df["글자인식_정확도(%)"].mean()
avg_url    = has_url["글자인식_정확도(%)"].mean() if len(has_url) > 0 else 0
avg_no_url = no_url["글자인식_정확도(%)"].mean()  if len(no_url)  > 0 else 0

print(f"\n=== 전체 결과 ({len(all_df)}장) ===")
print(f"전체 평균 정확도       : {avg:.2f}%")
print(f"URL 포함 이미지 정확도 : {avg_url:.2f}% ({len(has_url)}장)")
print(f"URL 없는 이미지 정확도 : {avg_no_url:.2f}% ({len(no_url)}장)")
print(f"URL 추출 성공률        : {url_success}/{len(has_url)} ({url_success/len(has_url)*100:.1f}%)")

summary = pd.DataFrame([
    {'파일명': '=== 요약 ===', '정답_텍스트': '', '추출_텍스트': '', '추출_QR': '', '글자인식_정확도(%)': ''},
    {'파일명': '전체 평균 정확도',        '정답_텍스트': f'{len(all_df)}장',    '추출_텍스트': '', '추출_QR': '', '글자인식_정확도(%)': f'{avg:.2f}%'},
    {'파일명': 'URL 포함 이미지 정확도',  '정답_텍스트': f'{len(has_url)}장',   '추출_텍스트': '', '추출_QR': '', '글자인식_정확도(%)': f'{avg_url:.2f}%'},
    {'파일명': 'URL 없는 이미지 정확도',  '정답_텍스트': f'{len(no_url)}장',    '추출_텍스트': '', '추출_QR': '', '글자인식_정확도(%)': f'{avg_no_url:.2f}%'},
    {'파일명': 'URL 추출 성공률',         '정답_텍스트': f'{url_success}/{len(has_url)}', '추출_텍스트': '', '추출_QR': '', '글자인식_정확도(%)': f'{url_success/len(has_url)*100:.1f}%'},
])
pd.concat([all_df, summary], ignore_index=True).to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
print(f"저장 완료: {OUTPUT_CSV} ({len(all_df)}장)")
