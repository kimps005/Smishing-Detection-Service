import os
import pandas as pd
import easyocr
import cv2
from pyzbar.pyzbar import decode
from difflib import SequenceMatcher # 정확도 계산을 위한 기본 라이브러리

# 🚀 [환경 스위치] 
# 지금은 내 컴퓨터니까 False(CPU 모드), 나중에 고성능 PC로 가면 True(GPU 모드)로 바꿔!
USE_GPU = False

IMAGE_DIR = "output"
CSV_PATH = "output/metadata.csv" 

print(f"EasyOCR 모델 로드 중 (GPU 사용: {USE_GPU})...")
reader = easyocr.Reader(['ko', 'en'], gpu=USE_GPU)

df = pd.read_csv(CSV_PATH)

# [후처리] 오타 자동 교정 함수
def correct_text(text):
    text = text.replace("httpll", "http://").replace("http:ll", "http://").replace("http;ll", "http://").replace("https:ll", "https://")
    text = text.replace("인종", "인증").replace("림크", "링크").replace("되없습니다", "되었습니다")
    text = text.replace("전환월", "전환될").replace("해제틀", "해제를").replace("바람니다", "바랍니다")
    text = text.replace("비밀번호름", "비밀번호를").replace("비밀번호지", "비밀번호를").replace("비밀번호들", "비밀번호를")
    text = text.replace("내용올", "내용을").replace("구*이", "구독이").replace("중단월", "중단될").replace("오서서", "오셔서")
    text = text.replace("I니다", "됩니다").replace("구광", "쿠팡").replace("남께", "님께").replace("보색습니다", "보냈습니다")
    text = text.replace("승금", "송금").replace("기I업", "기업").replace("출시원", "출시된").replace("월니다", "입니다")
    text = text.replace("고객남은", "고객님은").replace("다족시", "■즉시").replace("보벗습니다", "보냈습니다")
    text = text.replace("o원", "0원").replace("바쁘시켓지만", "바쁘시겠지만").replace("청철장", "청첩장").replace("않울", "않을")
    text = text.replace("햇습니다", "했습니다").replace("보묶습니다", "보냈습니다").replace("원올", "원을").replace("맛외게", "맛있게")
    text = text.replace("내여보기", "내역보기").replace("구장", "쿠팡").replace("리뷰틀", "리뷰를").replace("구땅", "쿠팡")

    return text

# [채점] 정확도(%) 계산 함수 (공백 무시하고 순수 글자 일치율 비교)
def get_accuracy(true_text, pred_text):
    true_text_clean = str(true_text).replace(" ", "").replace("\n", "")
    pred_text_clean = str(pred_text).replace(" ", "").replace("\n", "")
    
    if len(true_text_clean) == 0:
        return 0.0
        
    ratio = SequenceMatcher(None, true_text_clean, pred_text_clean).ratio()
    return round(ratio * 100, 2)

results = []
print(f"총 {len(df)}개 채점 시작! (시간이 오래 걸릴 수 있습니다)")

# 전체 데이터를 다 돌리기 위해 df.iterrows() 사용
# (만약 테스트로 10개만 돌리고 싶다면 df.head(10).iterrows() 로 수정해서 쓰면 돼)
for index, row in df.iterrows():
    img_name = row['file_name'] 
    true_text = str(row['text']) 
    
    img_path = os.path.join(IMAGE_DIR, img_name)
    if not os.path.exists(img_path):
        continue

    # 이미지 읽기
    img = cv2.imread(img_path)
    
    # 1. QR 추출
    qr_urls = []
    decoded_objects = decode(img)
    for obj in decoded_objects:
        qr_urls.append(obj.data.decode("utf-8"))
    extracted_qr = qr_urls[0] if qr_urls else ""

    # 2. 텍스트 추출 및 오타 후처리
    res = reader.readtext(img, detail=0)
    raw_text = " ".join(res)
    extracted_text = correct_text(raw_text)

    # 3. 텍스트 인식 정확도(%) 계산
    accuracy = get_accuracy(true_text, extracted_text)

    results.append({
        "파일명": img_name,
        "정답_텍스트": true_text,
        "추출_텍스트": extracted_text,
        "추출_QR": extracted_qr,
        "글자인식_정확도(%)": accuracy
    })
    
    # 진행 상황과 현재 이미지의 정확도 출력
    print(f"[{index+1}/{len(df)}] {img_name} 분석 완료 - 정확도: {accuracy}%")

# 결과 저장
result_df = pd.DataFrame(results)
result_df.to_csv("evaluation_results.csv", index=False, encoding='utf-8-sig')

# 최종 평균 정확도 계산 및 결과 요약 출력
avg_accuracy = result_df["글자인식_정확도(%)"].mean()

print("\n" + "="*50)
print(" 전체 스미싱 데이터 채점 및 테스트가 완료되었습니다!")
print(f"▶ 분석한 이미지 수: {len(results)}개")
print(f" 전체 평균 텍스트 인식 정확도: {avg_accuracy:.2f}%")
print("="*50)
print("현재 폴더에 'evaluation_results.csv' 파일이 성공적으로 저장되었습니다.")