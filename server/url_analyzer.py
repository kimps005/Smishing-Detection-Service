"""
P_URL 점수 산출 모듈
=====================
스미싱 탐지 시스템의 URL 분석 담당 모듈

기반:
- 김창형, 이병엽 (2025). "KoBERT와 URL 특징 분석을 결합한 하이브리드 딥러닝 기반 스미싱 탐지 모델 연구"
  → 논문 표 4의 URL 10가지 특징 추출
- VirusTotal API: 70+ 보안 엔진 종합 판정 (최종 도착지 기준)
- WHOIS: 도메인 생성일 기반 고위험 판정 (최종 도착지 기준)
- APK 다운로드 유도 검사: 악성 앱 설치 유도 탐지

핵심 기능:
- 단축 URL 최종 도착지 추적 후 조회 (bit.ly → 실제 목적지 분석)

출력: 0~10점 (P_URL)
"""

import re
import requests
from urllib.parse import urlparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import whois  # pip install python-whois

# 피드 인메모리 set (main.py가 서버 시작 및 6시간마다 갱신)
phishingdb_urls: set = set()
urlhaus_urls: set = set()
urlhaus_domains: set = set()

# =============================================================
# 설정 (Constants)
# =============================================================

VIRUSTOTAL_API_KEY = "47a96424ec494365413470dfe76aad4a2bc88dbfd30202803949799d91b95481"

SUSPICIOUS_KEYWORDS = [
    'login', 'secure', 'account', 'update', 'verify',
    'signin', 'confirm', 'password', 'bank', 'auth'
]

URL_SHORTENERS = [
    'bit.ly', 'abit.ly', 'me2.kr', 'me2.do', 'c11.kr', 'tinyurl.com', 'goo.gl',
    't.co', 'is.gd', 'ow.ly', 'buff.ly', 'han.gl', 'vo.la',
    'link24.kr', 'buly.kr', 'rf9.me',
]

SUSPICIOUS_TLDS = [
    '.top', '.xyz', '.club', '.buzz', '.hair',
    '.lol', '.pro', '.tk', '.ml', '.ga', '.cf'
]

APK_INDICATORS = [
    '.apk',
    'download/apk',
    'install.apk',
    'app_install',
    'apk_down',
]

CATEGORY_WEIGHT = {
    "PERSONAL":   1.0,
    "WORK":       1.0,
    "PROMOTION":  1.1,
    "DELIVERY":   1.2,
    "GOVERNMENT": 1.3,
    "FINANCE":    1.4,
    "AUTH":       1.5,
}


# =============================================================
# 0. 유틸: 도메인 추출
# =============================================================

def extract_domain(url):
    """URL에서 도메인만 추출 (www, m 등 제거)"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        elif netloc.startswith('m.'):
            netloc = netloc[2:]
        return netloc
    except Exception:
        return ""


# =============================================================
# 1. 최종 도착지 추적 (★ 핵심 추가 기능)
# =============================================================

def resolve_url(url, timeout=5):
    """
    단축 URL의 실제 최종 도착지 추적
    
    예: http://vo.la/kr_3930 → 실제 리다이렉트된 최종 URL
    
    Args:
        url (str): 원본 URL
        timeout (int): 요청 타임아웃 (초)
    
    Returns:
        dict: {
            'original_url': str,     # 원본 URL
            'final_url': str,        # 최종 도착지 URL
            'final_domain': str,     # 최종 도착지 도메인
            'is_shortener': bool,    # 원본이 단축 URL이었는지
            'content_type': str,     # 응답 Content-Type 헤더
            'error': str or None,    # 에러 메시지 (실패 시)
        }
    """
    result = {
        'original_url': url,
        'final_url': url,
        'final_domain': extract_domain(url),
        'is_shortener': False,
        'content_type': '',
        'error': None,
    }

    # 원본 도메인이 단축 URL 서비스인지 체크
    original_domain = extract_domain(url)
    result['is_shortener'] = any(
        original_domain == short or original_domain.endswith('.' + short)
        for short in URL_SHORTENERS
    )

    request_url = url if url.startswith(('http://', 'https://')) else 'http://' + url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.head(
            request_url,
            headers=headers,
            allow_redirects=True,
            timeout=timeout
        )
        # HEAD에 리다이렉트 없이 그대로 반환한 경우 GET으로 재시도
        if response.url == request_url:
            get_response = requests.get(
                request_url,
                headers=headers,
                allow_redirects=True,
                timeout=timeout,
                stream=True,
            )
            get_response.close()
            response = get_response
        result['final_url'] = response.url
        result['final_domain'] = extract_domain(response.url)
        result['content_type'] = response.headers.get('Content-Type', '')
    except requests.exceptions.ConnectionError:
        result['error'] = "도메인에 연결할 수 없습니다"
    except requests.exceptions.Timeout:
        result['error'] = "연결 시간 초과"
    except requests.exceptions.RequestException as e:
        result['error'] = f"URL 접속 실패: {str(e)[:50]}"
    except Exception as e:
        result['error'] = f"알 수 없는 오류: {str(e)[:50]}"

    return result


# =============================================================
# 2. 논문 표 4 기반 URL 10가지 특징 추출 (원본 URL 기준)
# =============================================================

def extract_url_features(url):
    """논문 표 4 기반 10가지 특징 추출 (원본 URL 기준)"""
    if not url:
        return {key: 0 for key in [
            'url_length', 'domain_length', 'path_length', 'subdomain_count',
            'special_char_count', 'digit_ratio', 'has_ip', 'has_suspicious_keyword',
            'is_shortener', 'has_suspicious_tld'
        ]}
    
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        path = parsed.path
    except Exception:
        return {key: 0 for key in [
            'url_length', 'domain_length', 'path_length', 'subdomain_count',
            'special_char_count', 'digit_ratio', 'has_ip', 'has_suspicious_keyword',
            'is_shortener', 'has_suspicious_tld'
        ]}
    
    features = {
        'url_length': len(url),
        'domain_length': len(netloc),
        'path_length': len(path),
        'subdomain_count': netloc.count('.'),
        'special_char_count': len(re.findall(r'[-_=?&]', url)),
        'digit_ratio': sum(c.isdigit() for c in url) / len(url) if len(url) > 0 else 0,
        'has_ip': 1 if re.match(r'^\d+\.\d+\.\d+\.\d+', netloc) else 0,
        'has_suspicious_keyword': 1 if any(kw in url.lower() for kw in SUSPICIOUS_KEYWORDS) else 0,
        'is_shortener': 1 if any(
            netloc == short or netloc.endswith('.' + short)
            for short in URL_SHORTENERS
        ) else 0,
        'has_suspicious_tld': 1 if any(tld in netloc for tld in SUSPICIOUS_TLDS) else 0,
    }
    
    return features


def score_url_features(features):
    """10가지 특징 → 0~10 점수"""
    score = 0
    
    if features['url_length'] > 75:
        score += 1.5
    elif features['url_length'] > 50:
        score += 0.8
    
    if features['domain_length'] > 30:
        score += 1.0
    
    if features['path_length'] > 50:
        score += 0.8
    
    if features['subdomain_count'] >= 4:
        score += 1.5
    elif features['subdomain_count'] == 3:
        score += 0.8
    
    if features['special_char_count'] >= 10:
        score += 1.0
    elif features['special_char_count'] >= 5:
        score += 0.5
    
    if features['digit_ratio'] > 0.3:
        score += 1.2
    elif features['digit_ratio'] > 0.15:
        score += 0.6
    
    if features['has_ip'] == 1:
        score += 2.0
    
    if features['has_suspicious_keyword'] == 1:
        score += 1.5
    
    if features['is_shortener'] == 1:
        score += 2.0
    
    if features['has_suspicious_tld'] == 1:
        score += 2.0
    
    return min(score, 10.0)


# =============================================================
# 3. VirusTotal 악성 판정 (★ 도메인 기반으로 변경)
# =============================================================

def check_virustotal(domain):
    """
    VirusTotal API로 도메인 또는 IP의 악성 여부 조회

    - 도메인: GET /domains/{domain}
    - IP 주소: GET /ip_addresses/{ip}  ← IP 전용 엔드포인트 분기 추가

    Args:
        domain (str): 조회할 도메인 또는 IP (예: "coupang.com", "122.155.197.69")

    Returns:
        dict: {
            'is_malicious': bool,
            'positive_count': int,
            'total_count': int,
            'score': float,
            'domain': str,
        }
    """
    result = {
        'is_malicious': False,
        'positive_count': 0,
        'total_count': 0,
        'harmless_count': 0,
        'score': 0.0,
        'domain': domain,
    }

    if not domain:
        return result

    is_ip = bool(re.match(r'^\d+\.\d+\.\d+\.\d+$', domain))

    try:
        headers = {'x-apikey': VIRUSTOTAL_API_KEY, 'accept': 'application/json'}

        if is_ip:
            vt_url = f'https://www.virustotal.com/api/v3/ip_addresses/{domain}'
        else:
            vt_url = f'https://www.virustotal.com/api/v3/domains/{domain}'

        response = requests.get(vt_url, headers=headers, timeout=10)

        if response.status_code == 404:
            return result

        if response.status_code != 200:
            print(f"[VirusTotal] API 오류 (상태 코드: {response.status_code})")
            return result

        stats = response.json()['data']['attributes']['last_analysis_stats']

        malicious = stats.get('malicious', 0)
        suspicious = stats.get('suspicious', 0)
        harmless = stats.get('harmless', 0)

        positive = malicious + suspicious
        total = malicious + suspicious + harmless + stats.get('undetected', 0)

        result['positive_count'] = positive
        result['total_count'] = total
        result['harmless_count'] = harmless
        result['is_malicious'] = positive > 0

        # 점수 산정 (탐지 비율 기반)
        if total > 0:
            ratio = positive / total
            if ratio > 0.1:
                result['score'] = 10.0
            elif ratio > 0.05:
                result['score'] = 8.0
            elif ratio > 0.02:
                result['score'] = 6.0
            elif positive > 0:
                result['score'] = 4.0
            else:
                result['score'] = 0.0

    except requests.exceptions.Timeout:
        print("[VirusTotal] 요청 시간 초과")
    except Exception as e:
        print(f"[VirusTotal] 오류: {e}")

    return result


# =============================================================
# 4. WHOIS 도메인 생성일 검사 (★ 도메인 직접 입력)
# =============================================================

def check_whois_age(domain):
    """
    WHOIS로 도메인 생성일 조회 → 신생 도메인 여부 판단
    
    ★ 변경: URL 입력 → 도메인 입력 방식
    
    Args:
        domain (str): 조회할 도메인 (예: "coupang.com")
    
    Returns:
        dict
    """
    result = {
        'creation_date': None,
        'age_days': -1,
        'is_new': False,
        'score': 0.0,
        'domain': domain,
    }
    
    if not domain:
        return result
    
    # IP 주소는 WHOIS 조회 안 함
    if re.match(r'^\d+\.\d+\.\d+\.\d+', domain):
        return result
    
    try:
        w = whois.whois(domain)
        creation_date = w.creation_date
        
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        
        if creation_date is None:
            return result
        
        if hasattr(creation_date, 'tzinfo') and creation_date.tzinfo is not None:
            creation_date = creation_date.replace(tzinfo=None)
        
        result['creation_date'] = creation_date
        age = (datetime.now() - creation_date).days
        result['age_days'] = age
        
        if age < 30:
            result['is_new'] = True
            result['score'] = 5.0
        elif age < 90:
            result['score'] = 3.5
        elif age < 180:
            result['score'] = 2.5
        elif age < 365:
            result['score'] = 1.5
        else:
            result['score'] = 0.0
    
    except Exception as e:
        error_msg = str(e)[:80]
        print(f"[WHOIS] {domain}: {error_msg}")
    
    return result


# =============================================================
# 5. APK 다운로드 유도 검사 (최종 URL 기준)
# =============================================================

def check_apk_download(url, content_type=''):
    """URL이 APK 파일 다운로드를 유도하는지 검사 (최종 URL 기준)"""
    result = {
        'is_apk': False,
        'matched_pattern': '',
        'score': 0.0
    }

    if not url:
        return result

    url_lower = url.lower()

    # URL 문자열 패턴 검사
    for pattern in APK_INDICATORS:
        if pattern in url_lower:
            result['is_apk'] = True
            result['matched_pattern'] = pattern
            result['score'] = 10.0
            return result

    # Content-Type 헤더 검사 (resolve_url에서 HEAD 요청으로 받아온 값)
    if content_type and 'android.package-archive' in content_type.lower():
        result['is_apk'] = True
        result['matched_pattern'] = 'Content-Type: APK'
        result['score'] = 10.0

    return result


# =============================================================
# 6. 위협 인텔리전스 피드 조회 (OpenPhish + URLhaus)
# =============================================================

def _strip_query(url: str) -> str:
    """쿼리 파라미터·fragment 제거한 URL 반환 (피드 매칭용)"""
    try:
        p = urlparse(url)
        return p._replace(query='', fragment='').geturl()
    except Exception:
        return url


def check_threat_feeds(url: str, final_url: str, final_domain: str) -> dict:
    """
    OpenPhish / URLhaus 피드에 URL 또는 도메인이 등재됐는지 조회 (인메모리 set 기반)
    - exact URL 매칭: 원본 URL + 최종 도착지 URL 둘 다 확인
    - 쿼리 파라미터 제거 URL 매칭: 피해자별 추적 파라미터 무시
    - domain 매칭: 최종 도착지 도메인 기준 (URLhaus, 단축 서비스 제외)
    """
    result = {'is_feed_hit': False, 'source': '', 'matched': '', 'score': 0.0}

    urls_to_check = {url, final_url} - {''}
    if not urls_to_check and not final_domain:
        return result

    # 쿼리 파라미터 제거 URL 추가 (단축 URL은 경로 자체가 식별자라 변화 없음)
    stripped = {_strip_query(u) for u in urls_to_check} - {''}
    urls_to_check_extended = urls_to_check | stripped

    # Phishing.Database: exact + 쿼리 제거 URL 매칭
    for u in urls_to_check_extended:
        if u in phishingdb_urls:
            result.update({'is_feed_hit': True, 'source': 'Phishing.Database', 'matched': u, 'score': 10.0})
            return result

    # URLhaus: exact + 쿼리 제거 URL 매칭
    for u in urls_to_check_extended:
        if u in urlhaus_urls:
            result.update({'is_feed_hit': True, 'source': 'URLhaus (URL)', 'matched': u, 'score': 10.0})
            return result

    # URLhaus: domain 매칭 (최종 도착지 기준, 단축 URL 서비스 제외)
    is_shortener_domain = any(
        final_domain == s or final_domain.endswith('.' + s)
        for s in URL_SHORTENERS
    )
    if final_domain and final_domain in urlhaus_domains and not is_shortener_domain:
        result.update({'is_feed_hit': True, 'source': 'URLhaus (domain)', 'matched': final_domain, 'score': 9.0})

    return result


# =============================================================
# 7. 단일 URL 분석 (P_URL 계산) ★ 최종 도착지 추적 흐름
# =============================================================

def calculate_p_url(url):
    """
    단일 URL의 P_URL 점수 산출

    흐름:
    1. 최종 도착지 추적 (resolve_url)
    2. 위협 인텔리전스 피드 조회 (OpenPhish + URLhaus)
    3. 단축 URL이면 최종 목적지로 특징 분석, is_shortener만 원본 기준
    4. 최종 도메인으로 VirusTotal 조회
    5. 최종 도메인으로 WHOIS 조회
    6. 최종 URL로 APK 검사
    7. 점수 결합
    """
    if not url:
        return {
            'p_url': 0.0,
            'feed_hit': False,
            'details': {'message': 'URL 없음'}
        }

    # Step 1: 최종 도착지 추적 ★ 핵심
    resolved = resolve_url(url)
    final_domain = resolved['final_domain']
    final_url = resolved['final_url']

    # Step 2: 위협 인텔리전스 피드 조회
    feed_result = check_threat_feeds(url, final_url, final_domain)

    # Step 3: 특징 분석 - 리다이렉트 발생했으면 최종 URL로, is_shortener만 원본 기준
    is_shortener = resolved['is_shortener']
    analysis_url = final_url if final_url and final_url != url else url
    features = extract_url_features(analysis_url)
    features['is_shortener'] = 1 if is_shortener else 0
    features_score = score_url_features(features)

    # Step 4+5: VirusTotal · WHOIS 병렬 실행
    _whois_default = {'creation_date': None, 'age_days': -1, 'is_new': False, 'score': 0.0, 'domain': final_domain}
    with ThreadPoolExecutor(max_workers=2) as executor:
        vt_future    = executor.submit(check_virustotal, final_domain)
        whois_future = executor.submit(check_whois_age,  final_domain)
        try:
            virustotal = vt_future.result(timeout=12)
        except Exception:
            virustotal = {'is_malicious': False, 'positive_count': 0, 'total_count': 0, 'harmless_count': 0, 'score': 0.0, 'domain': final_domain}
        try:
            whois_result = whois_future.result(timeout=8)
        except Exception:
            whois_result = _whois_default

    vt_found = virustotal['total_count'] > 0
    vt_confirmed_safe = virustotal['positive_count'] == 0 and virustotal['harmless_count'] > 0

    # VT 안전 확인 시 url_length · is_shortener 점수 제거
    # (네이버 검색 URL처럼 정상 서비스가 길고 서브도메인이 많은 경우 오탐 방지)
    if vt_confirmed_safe:
        suppressed = dict(features)
        suppressed['url_length'] = 0
        suppressed['is_shortener'] = 0
        features_score = score_url_features(suppressed)

    # VT 안전 확인 시 WHOIS 신생 도메인 패널티 80% 경감
    # (보안 엔진이 이미 안전 확인한 도메인은 나이가 어려도 신뢰)
    whois_score_effective = whois_result['score'] * 0.2 if vt_confirmed_safe else whois_result['score']

    # Step 6: 최종 URL로 APK 검사 (Content-Type도 함께 확인)
    content_type = resolved.get('content_type', '')
    apk_result = check_apk_download(final_url, content_type)

    # Step 7: 점수 결합 (피드 히트 시 최고 우선순위)
    weighted_avg = (
        feed_result['score']     * 0.30 +
        virustotal['score']      * 0.25 +
        features_score           * 0.20 +
        whois_score_effective    * 0.15 +
        apk_result['score']      * 0.10
    )

    max_score = max(
        feed_result['score'],
        virustotal['score'],
        features_score,
        whois_score_effective,
        apk_result['score']
    )

    p_url = max_score * 0.6 + weighted_avg * 0.4
    p_url = min(max(p_url, 0.0), 10.0)

    # 위험 근거
    danger_reasons = []
    if feed_result['is_feed_hit']:
        danger_reasons.append("피싱 데이터베이스에 등재된 URL입니다")
    if virustotal['is_malicious']:
        malicious = virustotal['positive_count']
        danger_reasons.append("보안 엔진에서 악성 URL로 판정되었습니다" if malicious > 0
                              else "보안 엔진에서 의심 URL로 판정되었습니다")
    if apk_result['is_apk']:
        danger_reasons.append("공식 스마트스토어가 아닌 APK 파일로 설치 유도하는 링크입니다")
    if resolved['is_shortener'] and not vt_confirmed_safe:
        danger_reasons.append("실제 목적지를 숨기는 단축 URL을 사용하였습니다")
    if features['has_ip']:
        danger_reasons.append("도메인 없이 IP 주소를 직접 사용하였습니다")
    if features['has_suspicious_tld']:
        danger_reasons.append("피싱에 자주 쓰이는 의심 도메인 확장자를 사용하였습니다")
    if whois_result['age_days'] >= 0:
        age = whois_result['age_days']
        if age < 365:
            danger_reasons.append(f"생성된 지 {age}일 된 도메인입니다")

    # 안전 근거 (Safe일 때만 표시용)
    safe_reasons = []
    if resolved['is_shortener'] and vt_confirmed_safe:
        safe_reasons.append("단축 URL을 사용하였으나, 최종 도착지가 안전한 것으로 확인되었습니다")
    if vt_confirmed_safe:
        safe_reasons.append("보안 엔진 검사 결과 위협이 발견되지 않았습니다")
    if not feed_result['is_feed_hit']:
        safe_reasons.append("피싱 데이터베이스에 등재되지 않은 URL입니다")
    if whois_result['age_days'] >= 365:
        age_days = whois_result['age_days']
        years = age_days // 365
        months = (age_days % 365) // 30
        if years > 0:
            age_str = f"{years}년" + (f" {months}개월" if months > 0 else "")
        else:
            age_str = f"{months}개월"
        safe_reasons.append(f"생성된 지 {age_str} 된 도메인입니다")

    return {
        'p_url': round(p_url, 2),
        'feed_hit': feed_result['is_feed_hit'],
        'vt_found': vt_found,
        'vt_confirmed_safe': vt_confirmed_safe,
        'reasons': danger_reasons,
        'safe_reasons': safe_reasons,
        'details': {
            'original_url': url,
            'final_url': final_url,
            'final_domain': final_domain,
            'resolve': resolved,
            'feed_result': feed_result,
            'feed_score': round(feed_result['score'], 2),
            'features_score': round(features_score, 2),
            'virustotal_score': round(virustotal['score'], 2),
            'whois_score': round(whois_result['score'], 2),
            'apk_score': round(apk_result['score'], 2),
            'weighted_avg': round(weighted_avg, 2),
            'max_score': round(max_score, 2),
            'features': features,
            'virustotal': virustotal,
            'whois': whois_result,
            'apk': apk_result,
        }
    }


# =============================================================
# 7. 다중 URL 분석 (main.py 진입점)
# =============================================================

def analyze_urls(urls, category=None, text=None):
    """
    여러 URL을 받아 가장 위험한 점수를 P_URL로 반환
    
    Args:
        urls (list): 분석할 URL 리스트
        category (str): 카테고리명 (예: "FINANCE")
        text (str): 텍스트 (향후 확장용)
    
    Returns:
        dict
    """
    if not urls or len(urls) == 0:
        return {
            'p_url': 0.0,
            'p_url_raw': 0.0,
            'feed_hit': False,
            'category': category or 'UNKNOWN',
            'category_weight': 1.0,
            'url_count': 0,
            'analyzed_urls': [],
            'message': 'URL이 없습니다.'
        }
    
    # 중복 URL 제거 (같은 단축 URL이 QR과 텍스트에서 중복 추출되는 경우 방지)
    seen = set()
    unique_urls = []
    for url in urls:
        normalized = url.lower().rstrip('/').replace('http://', '').replace('https://', '')
        # 단축 URL 특성상 path까지 보고 구분
        if normalized not in seen:
            seen.add(normalized)
            unique_urls.append(url)
    
    # 모든 URL 분석
    analyzed = []
    max_score = -1.0
    any_feed_hit = False
    best_result = None

    for url in unique_urls:
        result = calculate_p_url(url)
        analyzed.append(result)
        if result['p_url'] >= max_score:
            max_score = result['p_url']
            best_result = result
        if result.get('feed_hit', False):
            any_feed_hit = True

    # 카테고리 가중치 적용
    weight = CATEGORY_WEIGHT.get(category, 1.0)
    p_url_final = min(max_score * weight, 10.0)

    # 정부 기관 문자 + URL = 스미싱 확정 플래그
    # 근거: 정부·공공기관은 공식 문자에 URL을 포함하지 않음
    government_url_override = (category == "GOVERNMENT" and len(unique_urls) > 0)

    # 가장 위험한 URL의 reasons 사용
    url_reasons = best_result.get('reasons', []) if best_result else []
    url_safe_reasons = best_result.get('safe_reasons', []) if best_result else []

    return {
        'p_url': round(p_url_final, 2),
        'p_url_raw': round(max_score, 2),
        'feed_hit': any_feed_hit,
        'vt_found': best_result.get('vt_found', False) if best_result else False,
        'vt_confirmed_safe': best_result.get('vt_confirmed_safe', False) if best_result else False,
        'category': category or 'UNKNOWN',
        'category_weight': weight,
        'url_count': len(unique_urls),
        'analyzed_urls': analyzed,
        'government_url_override': government_url_override,
        'url_reasons': url_reasons,
        'url_safe_reasons': url_safe_reasons,
    }
