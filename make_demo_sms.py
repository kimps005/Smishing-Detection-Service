from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


root = Path(__file__).resolve().parent
background = Image.open(root / "backgrounds" / "bg_iPhone.png").convert("RGB")
draw = ImageDraw.Draw(background)
font = ImageFont.truetype(str(root / "fonts" / "AppleSDGothicNeoR.ttf"), 30)
bold = ImageFont.truetype(str(root / "fonts" / "AppleSDGothicNeoB.ttf"), 30)

lines = [
    ("[국민은행] 긴급 보안 안내", bold),
    ("본인이 아니면 즉시 OTP를 입력하세요.", font),
    ("계좌가 잠길 수 있습니다.", font),
    ("인증번호: 123456", font),
    ("24시간 이내 확인 필요", font),
]

x, y = 55, 55
for line, line_font in lines:
    draw.text((x, y), line, fill=(28, 28, 32), font=line_font)
    y += 48

output = root / "demo_sms_for_capture.png"
background.save(output)
print(output)
