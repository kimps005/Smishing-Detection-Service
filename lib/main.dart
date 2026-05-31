import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'package:share_handler/share_handler.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:share_plus/share_plus.dart';
import 'dart:io';
import 'dart:convert';
import 'dart:async';

const bool _localDev = false; // 로컬 테스트: true / 빌드 배포: false
const String serverUrl = _localDev ? 'http://192.168.0.24:8000' : 'https://api.catchsmishing.com';

void main() {
  runApp(const SmishingApp());
}

class SmishingApp extends StatelessWidget {
  const SmishingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CatchSmishing',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2563EB)),
        useMaterial3: true,
      ),
      home: const MainPage(),
    );
  }
}

// ─────────────────────────────────────────
// 메인 페이지 (상단 탭: 홈 | 리스트)
// ─────────────────────────────────────────
class MainPage extends StatefulWidget {
  const MainPage({super.key});

  @override
  State<MainPage> createState() => _MainPageState();
}

class _MainPageState extends State<MainPage> with SingleTickerProviderStateMixin {
  static _MainPageState? _current;
  late TabController _tabController;

  static void goToFeedback() {
    _current?._tabController.animateTo(2);
  }

  static void goToAnalysis() {
    _current?._tabController.animateTo(1);
  }

  @override
  void initState() {
    super.initState();
    _current = this;
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    if (_current == this) _current = null;
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isTablet = MediaQuery.of(context).size.width >= 600;
    return MediaQuery(
      data: MediaQuery.of(context).copyWith(
        textScaler: isTablet ? const TextScaler.linear(1.2) : TextScaler.noScaling,
      ),
      child: Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        title: Row(
          children: [
            const Text('🛡️', style: TextStyle(fontSize: 26)),
            const SizedBox(width: 6),
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: RichText(
                text: const TextSpan(
                  style: TextStyle(fontSize: 18),
                  children: [
                    TextSpan(text: 'Catch', style: TextStyle(fontWeight: FontWeight.w800, color: Color(0xFF0F172A))),
                    TextSpan(text: 'Smishing', style: TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF2563EB))),
                  ],
                ),
              ),
            ),
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: const Color(0xFF2563EB),
          labelColor: const Color(0xFF2563EB),
          unselectedLabelColor: const Color(0xFF94A3B8),
          dividerColor: const Color(0xFFE2E8F0),
          labelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
          tabs: const [
            Tab(icon: Icon(Icons.home_rounded), text: '홈'),
            Tab(icon: Icon(Icons.search), text: '분석'),
            Tab(icon: Icon(Icons.feedback_outlined), text: '피드백'),
          ],
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFE8F2FE), Color(0xFFF4F8FF), Color(0xFFF0EDFF), Color(0xFFF8FAFF)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: TabBarView(
          controller: _tabController,
          children: const [
            HomePage(),
            AnalysisPage(),
            FeedbackPage(),
          ],
        ),
      ),
    ),
    );
  }
}

// ─────────────────────────────────────────
// 홈 페이지
// ─────────────────────────────────────────
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  static const _types = [
    {'icon': '📦', 'title': '배송 사기', 'color': 0xFFF59E0B,
     'desc': '택배 미수령·주소 오류를 빙자해 개인정보 또는 소액 결제를 유도합니다.',
     'tips': ['공식 앱에서 운송장 번호로 직접 배송 조회', '링크 접속 전 택배사 도메인인지 확인']},
    {'icon': '💳', 'title': '금융 사기', 'color': 0xFFDC2626,
     'desc': '은행·카드사를 사칭해 계좌 인증, 미승인 거래 확인을 명목으로 접속을 유도합니다.',
     'tips': ['은행·카드사는 문자로 링크를 발송하지 않음', '의심 시 카드 뒷면 고객센터로 직접 전화', 'ARS·OTP를 통한 이체 요구 즉시 중단']},
    {'icon': '🏛️', 'title': '공공기관 사칭', 'color': 0xFF7C3AED,
     'desc': '경찰청·검찰·건강보험공단 등을 사칭해 과태료·소환 통보로 링크를 클릭하게 합니다.',
     'tips': ['정부기관은 문자 링크로 벌금·과태료를 고지하지 않음', '정부24·건강보험공단 공식 사이트 직접 접속']},
    {'icon': '🔐', 'title': '계정 탈취', 'color': 0xFFEA580C,
     'desc': '포털·SNS 계정 해킹·정지를 빙자해 비밀번호를 탈취합니다.',
     'tips': ['비밀번호 변경은 반드시 공식 앱에서만', '문자 속 링크로 로그인 금지']},
    {'icon': '📈', 'title': '투자·홍보 유도', 'color': 0xFF0891B2,
     'desc': '고수익 투자 리딩방, 공모주 당첨 등을 미끼로 개인정보나 투자금을 탈취합니다.',
     'tips': ['원금·수익 보장 광고 믿지 말기', '금감원 금융소비자포털에서 등록 여부 확인', '오픈채팅방 투자 제안은 즉시 차단']},
    {'icon': '👤', 'title': '지인 사칭', 'color': 0xFF2563EB,
     'desc': '지인·가족을 사칭해 청첩장·부고를 보내며 APK 설치나 송금을 유도합니다.',
     'tips': ['급한 송금 요청은 반드시 본인 확인 먼저', 'APK 파일 설치 금지']},
  ];

  static const _tips = [
    {'icon': '🚫', 'title': '출처 불명 링크 클릭 금지',
     'desc': '문자·SNS의 단축 URL은 클릭 전 이 앱으로 반드시 확인하세요.'},
    {'icon': '🏦', 'title': '공식 앱/웹사이트 직접 접속',
     'desc': '택배·은행·정부기관은 공식 앱이나 검색을 통해 직접 접속하세요.'},
    {'icon': '🔒', 'title': '개인정보·비밀번호 입력 주의',
     'desc': '문자 링크를 통한 개인정보 입력 요구는 100% 의심하세요.'},
    {'icon': '📞', 'title': '의심 문자 신고',
     'desc': 'KISA 불법스팸대응센터 118 또는 문자 전달로 신고 가능합니다.'},
  ];

  @override
  Widget build(BuildContext context) {
    final bottomPad = MediaQuery.of(context).padding.bottom;
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(20, 16, 20, 16 + bottomPad),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── 히어로 배너 ──
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF2563EB), Color(0xFF4F46E5)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Text('🤖 AI POWERED · KISA 기반',
                    style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
                ),
                const SizedBox(height: 12),
                const Text('스미싱 문자,\nAI로 즉시 판별합니다',
                  style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900, height: 1.3)),
                const SizedBox(height: 8),
                const Text('이미지·텍스트·QR 코드를 업로드하면\nGemini Vision + NLP + URL 보안 분석으로\n위험도를 판정합니다.',
                  style: TextStyle(color: Colors.white70, fontSize: 13, height: 1.6)),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => _MainPageState.goToAnalysis(),
                    icon: const Icon(Icons.search, size: 18),
                    label: const Text('지금 분석하기',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: const Color(0xFF2563EB),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          // ── 스미싱 유형 ──
          const Text('요즘 유행하는 스미싱 유형',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Color(0xFF0F172A))),
          const SizedBox(height: 4),
          const Text('KISA 2024 통계 기반',
            style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
          const SizedBox(height: 12),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: MediaQuery.of(context).size.width >= 600 ? 3 : 2,
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              childAspectRatio: 1.45,
            ),
            itemCount: _types.length,
            itemBuilder: (context, i) => _TypeCard(data: _types[i]),
          ),
          const SizedBox(height: 4),
          // ── 예방 수칙 ──
          const Text('스미싱 피해 예방 수칙',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Color(0xFF0F172A))),
          const SizedBox(height: 12),
          ..._tips.map((t) => Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFBFDBFE).withValues(alpha: 0.5)),
            ),
            child: Row(children: [
              Text(t['icon'] as String,
                style: const TextStyle(fontSize: 26)),
              const SizedBox(width: 12),
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(t['title'] as String,
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: Color(0xFF0F172A))),
                  const SizedBox(height: 2),
                  Text(t['desc'] as String,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF64748B), height: 1.4)),
                ],
              )),
            ]),
          )),
          const SizedBox(height: 4),
          // ── KISA 연락처 ──
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFEFF6FF),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFBFDBFE)),
            ),
            child: const Text(
              '📞 피해 발생 시: KISA 불법스팸대응센터 118  |  경찰청 사이버수사국 182',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: Color(0xFF1D4ED8), fontWeight: FontWeight.w600),
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}

class _TypeCard extends StatefulWidget {
  final Map<String, Object> data;
  const _TypeCard({required this.data});
  @override
  State<_TypeCard> createState() => _TypeCardState();
}

class _TypeCardState extends State<_TypeCard> {
  bool _flipped = false;

  @override
  Widget build(BuildContext context) {
    final t = widget.data;
    final tips = (t['tips'] as List<Object>).cast<String>();
    return GestureDetector(
      onTap: () => setState(() => _flipped = !_flipped),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: _flipped ? const Color(0xE10F172A) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: _flipped ? const Color(0x4D64748B) : const Color(0xFFD4E4FF)),
          boxShadow: const [BoxShadow(color: Color(0x0A2563EB), blurRadius: 6, offset: Offset(0, 2))],
        ),
        child: _flipped
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${t['icon']} ${t['title']} 예방법',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800,
                    color: Color(0xFFF1F5F9))),
                const SizedBox(height: 8),
                ...tips.map((tip) => Padding(
                  padding: const EdgeInsets.only(bottom: 5),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('→ ', style: TextStyle(fontSize: 11,
                      color: Color(0xFF60A5FA), fontWeight: FontWeight.w700)),
                    Expanded(child: Text(tip,
                      style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8), height: 1.5))),
                  ]),
                )),
              ],
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Text(t['icon'] as String, style: const TextStyle(fontSize: 16)),
                  const SizedBox(width: 6),
                  Expanded(child: Text(t['title'] as String,
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700,
                      color: Color(0xFF0F172A)),
                    overflow: TextOverflow.ellipsis)),
                ]),
                const SizedBox(height: 6),
                Expanded(child: Text(t['desc'] as String,
                  style: const TextStyle(fontSize: 11, color: Color(0xFF64748B), height: 1.45),
                  overflow: TextOverflow.fade)),
              ],
            ),
      ),
    );
  }
}

// ─────────────────────────────────────────
// 분석 페이지 (하단 탭: 이미지 | 텍스트 | QR)
// ─────────────────────────────────────────
class AnalysisPage extends StatefulWidget {
  const AnalysisPage({super.key});

  @override
  State<AnalysisPage> createState() => _AnalysisPageState();
}

class _AnalysisPageState extends State<AnalysisPage> with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;
  int _currentIndex = 0;
  File? _selectedImage;
  bool _isLoading = false;
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _textController = TextEditingController();
  StreamSubscription? _shareSubscription;
  http.Client? _httpClient;


  @override
  void initState() {
    super.initState();
    _initShareHandler();
  }

  Future<void> _initShareHandler() async {
    final handler = ShareHandlerPlatform.instance;
    final initialMedia = await handler.getInitialSharedMedia();
    if (initialMedia != null) {
      _handleSharedMedia(initialMedia);
    }
    _shareSubscription = handler.sharedMediaStream.listen((SharedMedia media) {
      if (!mounted) return;
      _handleSharedMedia(media);
    });
  }

  void _handleSharedMedia(SharedMedia media) {
    // 이미지 공유
    final path = media.attachments?.first?.path;
    if (path != null) {
      setState(() {
        _selectedImage = File(path);
        _currentIndex = 0;
      });
      return;
    }
    // 텍스트 공유 (문자 앱에서 텍스트 선택 후 공유)
    final text = media.content;
    if (text != null && text.trim().isNotEmpty) {
      setState(() {
        _textController.text = text;
        _currentIndex = 1;
      });
    }
  }

  void _cancelAnalysis() {
    _httpClient?.close();
    _httpClient = null;
    setState(() { _isLoading = false; });
  }

  @override
  void dispose() {
    _shareSubscription?.cancel();
    _textController.dispose();
    _httpClient?.close();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final XFile? image = await _picker.pickImage(source: ImageSource.gallery);
    if (image != null) {
      setState(() { _selectedImage = File(image.path); });
    }
  }

  Future<void> _analyzeImage() async {
    if (_selectedImage == null) return;
    _httpClient = http.Client();
    setState(() { _isLoading = true; });
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$serverUrl/analyze'));
      request.files.add(await http.MultipartFile.fromPath('file', _selectedImage!.path));
      var response = await _httpClient!.send(request);
      var responseBody = await response.stream.bytesToString();
      if (response.statusCode != 200) {
        String errMsg = '서버 오류';
        try { errMsg = jsonDecode(responseBody)['detail'] ?? errMsg; } catch (_) {}
        throw Exception(errMsg);
      }
      var result = jsonDecode(responseBody);
      if (mounted) {
        Navigator.push(context, MaterialPageRoute(builder: (context) => ResultPage(result: result)));
      }
    } catch (e) {
      if (mounted && _isLoading) {
        final msg = e.toString().replaceFirst('Exception: ', '');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg.isEmpty ? '서버 연결에 실패했습니다.' : msg)),
        );
      }
    } finally {
      _httpClient = null;
      setState(() { _isLoading = false; });
    }
  }

  Future<void> _analyzeText(String text, {bool isQrScan = false}) async {
    if (text.trim().isEmpty) return;
    _httpClient = http.Client();
    setState(() { _isLoading = true; });
    try {
      final response = await _httpClient!.post(
        Uri.parse('$serverUrl/analyze-text'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': text}),
      );
      if (response.statusCode != 200) {
        String errMsg = '서버 오류';
        try { errMsg = jsonDecode(response.body)['detail'] ?? errMsg; } catch (_) {}
        throw Exception(errMsg);
      }
      final result = jsonDecode(response.body);
      if (mounted) {
        Navigator.push(context, MaterialPageRoute(builder: (context) => ResultPage(result: result, isQrScan: isQrScan)));
      }
    } catch (e) {
      if (mounted && _isLoading) {
        final msg = e.toString().replaceFirst('Exception: ', '');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg.isEmpty ? '서버 연결에 실패했습니다.' : msg)),
        );
      }
    } finally {
      _httpClient = null;
      setState(() { _isLoading = false; });
    }
  }

  Widget _buildImageContent() {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (_selectedImage != null) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(
                  _selectedImage!,
                  key: ValueKey(_selectedImage!.path),
                  height: 250,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
              ),
              const SizedBox(height: 24),
            ] else ...[
              const Icon(Icons.security, size: 100, color: Color(0xFF2563EB)),
              const SizedBox(height: 32),
              const Text('스미싱 문자 탐지', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFF18181B))),
              const SizedBox(height: 12),
              const Text('문자 캡처 이미지를 공유하면\nAI가 스미싱 여부를 분석합니다',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 15, color: Color(0xFF64748B)),
              ),
              const SizedBox(height: 48),
            ],
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed: _isLoading ? null : _pickImage,
                icon: const Icon(Icons.image),
                label: const Text('갤러리에서 이미지 선택', style: TextStyle(fontSize: 16)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2563EB),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
            if (_selectedImage != null) ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton.icon(
                  onPressed: _isLoading ? _cancelAnalysis : _analyzeImage,
                  icon: _isLoading
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Icon(Icons.search),
                  label: Text(_isLoading ? '분석 중단' : 'AI 분석 시작', style: const TextStyle(fontSize: 16)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _isLoading ? const Color(0xFFDC2626) : const Color(0xFF16A34A),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
              if (_isLoading) ...[
                const SizedBox(height: 10),
                const Text('이미지 분석 시 처리 시간이 다소 걸릴 수 있습니다',
                  style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTextContent() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          const Text('문자 내용 붙여넣기',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF18181B)),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _textController,
            maxLines: 8,
            decoration: InputDecoration(
              hintText: '스미싱 의심 문자 내용을 여기에 붙여넣으세요',
              enabled: !_isLoading,
              hintStyle: const TextStyle(color: Color(0xFF94A3B8)),
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0xFFD4E4FF)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0xFFD4E4FF)),
              ),
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton.icon(
              onPressed: _isLoading ? _cancelAnalysis : () => _analyzeText(_textController.text),
              icon: _isLoading
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Icon(Icons.search),
              label: Text(_isLoading ? '분석 중단' : 'AI 분석 시작', style: const TextStyle(fontSize: 16)),
              style: ElevatedButton.styleFrom(
                backgroundColor: _isLoading ? const Color(0xFFDC2626) : const Color(0xFF16A34A),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ),
          if (_isLoading) ...[
            const SizedBox(height: 10),
            const Text('분석 중...',
              style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildQrContent() {
    return QrScanPage(
      onScanned: (String url) => _analyzeText(url, isQrScan: true),
    );
  }

  Widget _buildInputTab(int index, String label) {
    final active = _currentIndex == index;
    return GestureDetector(
      onTap: () => setState(() => _currentIndex = index),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: active ? const Color(0xFF2563EB) : Colors.transparent,
              width: 2,
            ),
          ),
        ),
        child: Text(label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: active ? const Color(0xFF2563EB) : const Color(0xFF64748B),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final pages = [_buildImageContent(), _buildTextContent(), _buildQrContent()];

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('🔍 문자 분석',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: Color(0xFF0F172A))),
                const SizedBox(height: 4),
                const Text('이미지·텍스트·QR 코드를 AI로 즉시 분석합니다',
                  style: TextStyle(fontSize: 13, color: Color(0xFF64748B))),
                const SizedBox(height: 12),
                Row(
                  children: [
                    _buildInputTab(0, '🖼️ 이미지/QR'),
                    _buildInputTab(1, '📝 텍스트'),
                    _buildInputTab(2, '📲 QR 스캔'),
                  ],
                ),
              ],
            ),
          ),
          const Divider(height: 1, thickness: 1, color: Color(0xFFE2E8F0)),
          Expanded(child: pages[_currentIndex]),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────
// 리스트 페이지 (위험 문자 탐지 현황)
// ─────────────────────────────────────────
class ListPage extends StatefulWidget {
  const ListPage({super.key});

  @override
  State<ListPage> createState() => _ListPageState();
}

class _ListPageState extends State<ListPage> {

  static const Map<String, String> _categoryNames = {
    'PERSONAL':   '일반 문자',
    'FINANCE':    '금융 사기',
    'DELIVERY':   '배송 사기',
    'GOVERNMENT': '공공기관 사칭',
    'PROMOTION':  '홍보/투자 유도',
    'AUTH':       '계정 탈취',
    'WORK':       '지인 사칭',
  };

  static const Map<String, Color> _categoryColors = {
    'PERSONAL':   Color(0xFF64748B),
    'FINANCE':    Color(0xFFDC2626),
    'DELIVERY':   Color(0xFFF59E0B),
    'GOVERNMENT': Color(0xFF7C3AED),
    'PROMOTION':  Color(0xFF0891B2),
    'AUTH':       Color(0xFFEA580C),
    'WORK':       Color(0xFF2563EB),
  };

  late Future<List<dynamic>> _future;
  final TextEditingController _searchController = TextEditingController();
  String? _selectedCategory;
  String _searchQuery = '';
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _future = _fetchTopUrls();
    _searchController.addListener(() {
      setState(() { _searchQuery = _searchController.text; _currentPage = 0; });
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<List<dynamic>> _fetchTopUrls() async {
    final response = await http.get(Uri.parse('$serverUrl/top-urls?limit=50')).timeout(const Duration(seconds: 5));
    final data = jsonDecode(response.body);
    return data['top_urls'] as List<dynamic>;
  }

  void _refresh() {
    setState(() {
      _future = _fetchTopUrls();
      _currentPage = 0;
    });
  }

  Widget _buildPagination(int totalPages, int currentPage) {
    List<int> visiblePages;
    if (totalPages <= 5) {
      visiblePages = List.generate(totalPages, (i) => i);
    } else {
      final start = (currentPage - 2).clamp(0, totalPages - 5);
      visiblePages = List.generate(5, (i) => start + i);
    }
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        IconButton(
          onPressed: currentPage > 0 ? () => setState(() => _currentPage = currentPage - 1) : null,
          icon: const Icon(Icons.chevron_left),
          iconSize: 20,
          color: const Color(0xFF2563EB),
          disabledColor: const Color(0xFFCBD5E1),
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
        ),
        ...visiblePages.map((pageIdx) => GestureDetector(
          onTap: () => setState(() => _currentPage = pageIdx),
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 3),
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: currentPage == pageIdx ? const Color(0xFF2563EB) : Colors.transparent,
              borderRadius: BorderRadius.circular(6),
            ),
            alignment: Alignment.center,
            child: Text('${pageIdx + 1}',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: currentPage == pageIdx ? Colors.white : const Color(0xFF64748B),
              )),
          ),
        )),
        IconButton(
          onPressed: currentPage < totalPages - 1 ? () => setState(() => _currentPage = currentPage + 1) : null,
          icon: const Icon(Icons.chevron_right),
          iconSize: 20,
          color: const Color(0xFF2563EB),
          disabledColor: const Color(0xFFCBD5E1),
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.transparent,
      child: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: Color(0xFF2563EB)));
          }
          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.wifi_off, size: 64, color: Color(0xFF94A3B8)),
                  const SizedBox(height: 16),
                  const Text('서버에 연결할 수 없습니다', style: TextStyle(fontSize: 16, color: Color(0xFF64748B))),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: _refresh,
                    icon: const Icon(Icons.refresh),
                    label: const Text('다시 시도'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF2563EB),
                      foregroundColor: Colors.white,
                    ),
                  ),
                ],
              ),
            );
          }
          final allUrls = snapshot.data!;
          final urls = allUrls.where((item) {
            final m = item as Map<String, dynamic>;
            final matchSearch = _searchQuery.isEmpty || (m['url'] ?? '').toLowerCase().contains(_searchQuery.toLowerCase().trim());
            final matchCategory = _selectedCategory == null || m['category'] == _selectedCategory;
            return matchSearch && matchCategory;
          }).toList();

          final Map<String, int> catTotals = {};
          for (final item in allUrls) {
            final m = item as Map<String, dynamic>;
            final cat = (m['category'] ?? '') as String;
            catTotals[cat] = (catTotals[cat] ?? 0) + ((m['count'] ?? 0) as int);
          }
          final totalCount = catTotals.values.fold(0, (a, b) => a + b);
          final sortedCats = catTotals.entries.toList()
            ..sort((a, b) => b.value.compareTo(a.value));

          if (allUrls.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.shield, size: 80, color: Color(0xFF94A3B8)),
                  const SizedBox(height: 16),
                  const Text('탐지된 위험 문자가 없습니다', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF64748B))),
                  const SizedBox(height: 8),
                  const Text('위험으로 판단된 문자가 누적되면 표시됩니다', style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
                  const SizedBox(height: 24),
                  IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh, color: Color(0xFF2563EB), size: 32)),
                ],
              ),
            );
          }

          const pageSize = 5;
          final totalPages = (urls.isEmpty ? 1 : (urls.length / pageSize).ceil()).clamp(1, 999);
          final safeCurrentPage = _currentPage.clamp(0, totalPages - 1);
          final pageUrls = urls.skip(safeCurrentPage * pageSize).take(pageSize).toList();

          final bottomPad = MediaQuery.of(context).padding.bottom;
          return SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(16, 16, 16, 24 + bottomPad),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ── 파이 차트 박스 ──
                if (totalCount > 0) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFD4E4FF)),
                      boxShadow: const [BoxShadow(color: Color(0x0A2563EB), blurRadius: 8, offset: Offset(0, 2))],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('탐지된 스미싱 유형 분포',
                          style: TextStyle(fontSize: 13, color: Color(0xFF64748B), fontWeight: FontWeight.w600)),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            CustomPaint(
                              size: const Size(120, 120),
                              painter: _PieChartPainter(
                                sections: sortedCats
                                  .where((e) => e.key.isNotEmpty && e.key != 'PERSONAL' && e.value > 0)
                                  .map((e) => (
                                    value: e.value / totalCount,
                                    color: _categoryColors[e.key] ?? const Color(0xFFDC2626),
                                  )).toList(),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: sortedCats
                                  .where((e) => e.key.isNotEmpty && e.key != 'PERSONAL' && e.value > 0)
                                  .map((e) {
                                    final color = _categoryColors[e.key] ?? const Color(0xFFDC2626);
                                    final name = _categoryNames[e.key] ?? e.key;
                                    final pct = (e.value / totalCount * 100).round();
                                    return Padding(
                                      padding: const EdgeInsets.only(bottom: 5),
                                      child: Row(children: [
                                        Container(width: 9, height: 9,
                                          decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
                                        const SizedBox(width: 6),
                                        Expanded(child: Text(name,
                                          style: const TextStyle(fontSize: 11, color: Color(0xFF374151)),
                                          overflow: TextOverflow.ellipsis)),
                                        Text('$pct%',
                                          style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                                      ]),
                                    );
                                  }).toList(),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                ],

                // ── 검색 + 순위 박스 ──
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFD4E4FF)),
                    boxShadow: const [BoxShadow(color: Color(0x0A2563EB), blurRadius: 8, offset: Offset(0, 2))],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // 검색/필터 행
                      Row(
                        children: [
                          Expanded(
                            flex: 2,
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF8FAFC),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: const Color(0xFFD4E4FF)),
                              ),
                              child: DropdownButton<String>(
                                value: _selectedCategory,
                                isExpanded: true,
                                underline: const SizedBox(),
                                style: const TextStyle(fontSize: 12, color: Color(0xFF18181B)),
                                hint: const Text('카테고리', style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
                                items: _categoryNames.keys.where((k) => k != 'PERSONAL').map((k) => DropdownMenuItem(
                                  value: k,
                                  child: Text(_categoryNames[k] ?? k, overflow: TextOverflow.ellipsis),
                                )).toList(),
                                onChanged: (val) => setState(() { _selectedCategory = val; _currentPage = 0; }),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            flex: 3,
                            child: TextField(
                              controller: _searchController,
                              style: const TextStyle(fontSize: 12),
                              decoration: InputDecoration(
                                hintText: 'URL 검색',
                                hintStyle: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                                prefixIcon: const Icon(Icons.search, size: 18),
                                contentPadding: const EdgeInsets.symmetric(vertical: 10),
                                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFFD4E4FF))),
                                filled: true,
                                fillColor: const Color(0xFFF8FAFC),
                              ),
                            ),
                          ),
                          const SizedBox(width: 6),
                          InkWell(
                            onTap: () {
                              _searchController.clear();
                              setState(() { _selectedCategory = null; _currentPage = 0; });
                            },
                            borderRadius: BorderRadius.circular(8),
                            child: const Padding(
                              padding: EdgeInsets.all(8),
                              child: Icon(Icons.refresh, size: 20, color: Color(0xFF2563EB)),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),

                      // 순위 리스트 (5개씩)
                      if (urls.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 24),
                          child: Center(
                            child: Text('검색 결과가 없습니다', style: TextStyle(color: Color(0xFF94A3B8))),
                          ),
                        )
                      else ...[
                        ...pageUrls.asMap().entries.map((entry) {
                          final index = safeCurrentPage * pageSize + entry.key;
                          final item = entry.value as Map<String, dynamic>;
                          final String url = item['url'] ?? '';
                          final String category = item['category'] ?? '';
                          final int count = item['count'] ?? 0;
                          final Color categoryColor = _categoryColors[category] ?? const Color(0xFFDC2626);
                          final String categoryName = _categoryNames[category] ?? category;
                          final int rank = index + 1;
                          final List<String> medals = ['🥇', '🥈', '🥉'];
                          final bool isTop3 = index < 3;
                          final Color bgColor = index == 0
                              ? const Color(0xFFFFF7ED)
                              : isTop3 ? const Color(0xFFFAFAFA) : Colors.white;
                          final Border border = isTop3
                              ? Border.all(color: categoryColor, width: 2)
                              : Border.all(color: const Color(0xFFD4E4FF));
                          return Container(
                            margin: const EdgeInsets.only(bottom: 10),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: bgColor,
                              borderRadius: BorderRadius.circular(12),
                              border: border,
                            ),
                            child: Row(
                              children: [
                                SizedBox(
                                  width: 40,
                                  child: Center(
                                    child: isTop3
                                        ? Text(medals[index], style: const TextStyle(fontSize: 22))
                                        : Text('$rank위', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Color(0xFF374151))),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(url, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF18181B)), softWrap: true),
                                      const SizedBox(height: 5),
                                      Row(children: [
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: categoryColor.withValues(alpha: 0.1),
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: Text(categoryName, style: TextStyle(fontSize: 10, color: categoryColor, fontWeight: FontWeight.bold)),
                                        ),
                                        const SizedBox(width: 8),
                                        Text('탐지 $count회', style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                                      ]),
                                    ],
                                  ),
                                ),
                                const Icon(Icons.warning_rounded, color: Color(0xFFDC2626), size: 18),
                              ],
                            ),
                          );
                        }),
                        if (totalPages > 1) ...[
                          const SizedBox(height: 4),
                          _buildPagination(totalPages, safeCurrentPage),
                        ],
                      ],
                    ],
                  ),
                ),

                // ── 피드백 활용 + 모델 개선 방향 ──
                const SizedBox(height: 16),
                const _UsageSection(),
                const SizedBox(height: 16),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ─────────────────────────────────────────
// 피드백 페이지
// ─────────────────────────────────────────
class FeedbackPage extends StatefulWidget {
  const FeedbackPage({super.key});

  @override
  State<FeedbackPage> createState() => _FeedbackPageState();
}

class _FeedbackPageState extends State<FeedbackPage> with SingleTickerProviderStateMixin {
  static const Map<String, String> _gradeLabels = {
    'Danger': '🚨 위험',
    'Warning': '⚠️ 주의',
    'Safe': '✅ 안전',
  };

  late TabController _subTabController;
  bool _isImageMode = false;
  File? _selectedImage;
  final TextEditingController _textController = TextEditingController();
  final TextEditingController _reasonController = TextEditingController();
  String _givenGrade = 'Danger';
  String _correctGrade = 'Safe';
  bool _submitted = false;
  bool _isLoading = false;
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _subTabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _subTabController.dispose();
    _textController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final XFile? image = await _picker.pickImage(source: ImageSource.gallery);
    if (image != null) setState(() => _selectedImage = File(image.path));
  }

  Future<void> _submit() async {
    final hasText = _textController.text.trim().isNotEmpty;
    final hasImage = _selectedImage != null;
    if (!hasText && !hasImage) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('문자 내용 또는 이미지를 입력해주세요.')),
      );
      return;
    }
    setState(() => _isLoading = true);
    try {
      final request = http.MultipartRequest('POST', Uri.parse('$serverUrl/feedback'));
      request.fields['given_grade'] = _givenGrade;
      request.fields['correct_grade'] = _correctGrade;
      request.fields['reason'] = _reasonController.text;
      request.fields['text_content'] = hasText ? _textController.text.trim() : '[이미지 첨부 피드백]';
      if (hasImage) {
        request.files.add(await http.MultipartFile.fromPath('image', _selectedImage!.path));
      }
      await request.send();
      setState(() { _submitted = true; _isLoading = false; });
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('제출에 실패했습니다. 서버 연결을 확인해주세요.')),
        );
      }
      setState(() => _isLoading = false);
    }
  }

  void _reset() {
    setState(() {
      _submitted = false;
      _textController.clear();
      _reasonController.clear();
      _selectedImage = null;
      _givenGrade = 'Danger';
      _correctGrade = 'Safe';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            boxShadow: [BoxShadow(color: Color(0x0A2563EB), blurRadius: 4, offset: Offset(0, 2))],
          ),
          child: TabBar(
            controller: _subTabController,
            labelColor: const Color(0xFF2563EB),
            unselectedLabelColor: const Color(0xFF64748B),
            indicatorColor: const Color(0xFF2563EB),
            dividerColor: const Color(0xFFE2E8F0),
            labelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
            unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
            tabs: const [Tab(text: '피드백하기'), Tab(text: '탐지 현황')],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _subTabController,
            children: [_buildFeedbackContent(), const ListPage()],
          ),
        ),
      ],
    );
  }

  Widget _buildFeedbackContent() {
    if (_submitted) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle, color: Color(0xFF16A34A), size: 72),
            const SizedBox(height: 16),
            const Text('피드백이 제출됐습니다. 감사합니다!',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF18181B))),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _reset,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF2563EB),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('새 피드백 보내기'),
            ),
          ],
        ),
      );
    }

    final bottomPad = MediaQuery.of(context).padding.bottom;
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(24, 24, 24, 24 + bottomPad),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          const Text('💬 피드백 보내기',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: Color(0xFF18181B))),
          const SizedBox(height: 4),
          const Text('탐지 결과가 잘못됐거나 개선이 필요하다면 알려주세요.',
            style: TextStyle(fontSize: 13, color: Color(0xFF64748B))),
          const SizedBox(height: 20),
          // 입력 방식 토글
          Row(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() { _isImageMode = false; _selectedImage = null; }),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    decoration: BoxDecoration(
                      color: !_isImageMode ? const Color(0xFF2563EB) : Colors.white,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF2563EB)),
                    ),
                    child: Text('📝 텍스트', textAlign: TextAlign.center,
                      style: TextStyle(fontWeight: FontWeight.bold,
                        color: !_isImageMode ? Colors.white : const Color(0xFF2563EB))),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() { _isImageMode = true; _textController.clear(); }),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    decoration: BoxDecoration(
                      color: _isImageMode ? const Color(0xFF2563EB) : Colors.white,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF2563EB)),
                    ),
                    child: Text('🖼️ 이미지', textAlign: TextAlign.center,
                      style: TextStyle(fontWeight: FontWeight.bold,
                        color: _isImageMode ? Colors.white : const Color(0xFF2563EB))),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // 텍스트 또는 이미지 입력
          if (!_isImageMode)
            TextField(
              controller: _textController,
              maxLines: 5,
              decoration: InputDecoration(
                hintText: '분석된 문자 내용을 입력해주세요.',
                hintStyle: const TextStyle(color: Color(0xFF94A3B8)),
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: Color(0xFFD4E4FF))),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: Color(0xFFD4E4FF))),
              ),
            )
          else
            Column(
              children: [
                if (_selectedImage != null)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(_selectedImage!, height: 180, width: double.infinity, fit: BoxFit.cover),
                  ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _pickImage,
                    icon: const Icon(Icons.image),
                    label: Text(_selectedImage == null ? '이미지 선택' : '이미지 변경'),
                    style: OutlinedButton.styleFrom(
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
              ],
            ),
          const SizedBox(height: 16),
          // 판정 선택
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('시스템 판정', style: TextStyle(fontSize: 13, color: Color(0xFF64748B))),
                    const SizedBox(height: 4),
                    DropdownButtonFormField<String>(
                      initialValue: _givenGrade,
                      decoration: InputDecoration(
                        filled: true, fillColor: Colors.white,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: Color(0xFFD4E4FF))),
                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: Color(0xFFD4E4FF))),
                      ),
                      items: _gradeLabels.entries.map((e) =>
                        DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
                      onChanged: (v) => setState(() => _givenGrade = v!),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('실제 판정', style: TextStyle(fontSize: 13, color: Color(0xFF64748B))),
                    const SizedBox(height: 4),
                    DropdownButtonFormField<String>(
                      initialValue: _correctGrade,
                      decoration: InputDecoration(
                        filled: true, fillColor: Colors.white,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: Color(0xFFD4E4FF))),
                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10),
                          borderSide: const BorderSide(color: Color(0xFFD4E4FF))),
                      ),
                      items: _gradeLabels.entries.map((e) =>
                        DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
                      onChanged: (v) => setState(() => _correctGrade = v!),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _reasonController,
            maxLines: 3,
            decoration: InputDecoration(
              hintText: '이유를 입력해주세요 (선택)',
              hintStyle: const TextStyle(color: Color(0xFF94A3B8)),
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0xFFD4E4FF))),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0xFFD4E4FF))),
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton(
              onPressed: _isLoading ? null : _submit,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF2563EB),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: _isLoading
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Text('피드백 제출', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
          ),
          const SizedBox(height: 28),
          const _UsageSection(),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────
// 파이 차트 Painter
// ─────────────────────────────────────────
class _PieChartPainter extends CustomPainter {
  final List<({double value, Color color})> sections;
  const _PieChartPainter({required this.sections});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    double startAngle = -3.14159 / 2;
    for (final s in sections) {
      final sweepAngle = s.value * 2 * 3.14159;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle, sweepAngle, true,
        Paint()..color = s.color..style = PaintingStyle.fill,
      );
      startAngle += sweepAngle;
    }
    canvas.drawCircle(center, radius * 0.52,
      Paint()..color = Colors.white..style = PaintingStyle.fill);
  }

  @override
  bool shouldRepaint(_PieChartPainter old) => old.sections != sections;
}

// ─────────────────────────────────────────
// 피드백 활용 섹션 (공통)
// ─────────────────────────────────────────
class _UsageSection extends StatelessWidget {
  const _UsageSection();

  static const _usageItems = [
    ('📌 전체 분석 결과 누적 수집', '안전·주의·위험 모든 판정을 항목별 점수(P_NLP, P_URL, P_Gemini 등)와 함께 저장해 판정 패턴을 분석합니다.'),
    ('📌 키워드 가중치 조정', '오탐·미탐 패턴을 분석해 NLP 위험 키워드의 가중치를 조정합니다.'),
    ('📌 Gemini 프롬프트 개선', '오탐·미탐 사례를 분석해 AI 문맥 분석 프롬프트의 판단 기준을 지속적으로 개선합니다.'),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('수집된 피드백, 어떻게 활용되나요?',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Color(0xFF0F172A))),
        const SizedBox(height: 8),
        ..._usageItems.map((item) => Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFD4E4FF)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(item.$1, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: Color(0xFF18181B))),
              const SizedBox(height: 4),
              Text(item.$2, style: const TextStyle(fontSize: 12, color: Color(0xFF374151), height: 1.6)),
            ],
          ),
        )),
        const SizedBox(height: 16),
        const Text('모델 개선 방향',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Color(0xFF0F172A))),
        const SizedBox(height: 8),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFF0FDF4),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF86EFAC)),
          ),
          child: const Text(
            '✅  누적 데이터 기반 오탐·미탐 패턴 분석 — 전체 판정 데이터를 활용해 판단 오류 유형을 파악합니다\n'
            '✅  분류 모델 정확도 향상 — 수집된 데이터로 학습 데이터를 지속 확보해 모델을 개선합니다\n'
            '✅  판단 임계값 조정 — 피드백 패턴을 반영해 안전·주의·위험 기준을 정밀하게 조정합니다',
            style: TextStyle(fontSize: 12, color: Color(0xFF166534), height: 1.9),
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────
// QR 스캔 페이지
// ─────────────────────────────────────────
class QrScanPage extends StatefulWidget {
  final Function(String) onScanned;
  const QrScanPage({super.key, required this.onScanned});

  @override
  State<QrScanPage> createState() => _QrScanPageState();
}

class _QrScanPageState extends State<QrScanPage> {
  final MobileScannerController _scannerController = MobileScannerController();
  bool _scanned = false;

  @override
  void dispose() {
    _scannerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        MobileScanner(
          controller: _scannerController,
          onDetect: (capture) {
            if (_scanned) return;
            final barcode = capture.barcodes.firstOrNull;
            final url = barcode?.rawValue;
            if (url != null) {
              setState(() { _scanned = true; });
              _scannerController.stop();
              widget.onScanned(url);
            }
          },
        ),
        if (_scanned)
          Container(
            color: Colors.black54,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const CircularProgressIndicator(color: Colors.white, strokeWidth: 3),
                  const SizedBox(height: 20),
                  const Text('분석 중...', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: () {
                      setState(() { _scanned = false; });
                      _scannerController.start();
                    },
                    style: TextButton.styleFrom(foregroundColor: Colors.white70),
                    child: const Text('다시 스캔하기'),
                  ),
                ],
              ),
            ),
          ),
        if (!_scanned)
          Align(
            alignment: const Alignment(0, -0.2),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 250,
                  height: 250,
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.white, width: 2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(20)),
                  child: const Text('QR 코드를 사각형 안에 맞춰주세요',
                    style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────
// 결과 페이지
// ─────────────────────────────────────────
class ResultPage extends StatelessWidget {
  final Map<String, dynamic> result;
  final bool isQrScan;

  const ResultPage({super.key, required this.result, this.isQrScan = false});

  static const Map<String, String> _categoryNames = {
    'PERSONAL':   '일반 문자',
    'FINANCE':    '금융 사기',
    'DELIVERY':   '배송 사기',
    'GOVERNMENT': '공공기관 사칭',
    'PROMOTION':  '홍보/투자 유도',
    'AUTH':       '계정 탈취',
    'WORK':       '지인 사칭',
  };
  static const Map<String, String> _categoryNamesSafe = {
    'PERSONAL':   '일반 문자',
    'FINANCE':    '금융 문자',
    'DELIVERY':   '배송 문자',
    'GOVERNMENT': '공공기관 문자',
    'PROMOTION':  '홍보/투자 문자',
    'AUTH':       '계정 문자',
    'WORK':       '지인 문자',
  };

  // 위험도 레벨 결정
  String _riskLevel(String? grade) {
    switch (grade) {
      case 'Danger': return 'danger';
      case 'Warning': return 'caution';
      case 'Safe': return 'safe';
      default: return 'pending';
    }
  }

  String _buildShareText(String riskLabel, String categoryLabel, String? grade, List<dynamic> textReasons, List<dynamic> urlReasons) {
    final buf = StringBuffer();
    buf.writeln('[스미싱 탐지 결과]');
    buf.writeln('판정: $riskLabel ($categoryLabel)');
    if (textReasons.isNotEmpty) {
      buf.writeln('\n[탐지 근거]');
      for (final r in textReasons) { buf.writeln('• $r'); }
    }
    if (urlReasons.isNotEmpty) {
      if (textReasons.isEmpty) buf.writeln('\n[탐지 근거]');
      for (final r in urlReasons) { buf.writeln('• $r'); }
    }
    if (grade == 'Danger') {
      buf.writeln('\n의심 문자는 KISA 불법스팸대응센터(118)에 신고하세요.');
    }
    buf.write('\n- 스미싱 탐지 앱으로 분석됨');
    return buf.toString();
  }

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic>? categoryMap = result['category'] is Map
        ? result['category'] as Map<String, dynamic>
        : null;
    final String? category = categoryMap?['category'] as String?;
    final Map<String, dynamic>? resultMap = result['result'] is Map
        ? result['result'] as Map<String, dynamic>
        : null;
    final String? grade = resultMap?['grade'] as String?;
    final Map<String, dynamic>? nlpAnalysis = result['nlp_analysis'] as Map<String, dynamic>?;
    final List<dynamic> riskKeywords = nlpAnalysis?['risk_keywords'] ?? [];
    final List<dynamic> textReasons = result['text_reasons'] ?? [];
    final List<dynamic> urlReasons = result['url_reasons'] ?? [];
    final int? rank = result['rank'] != null ? result['rank'] as int : null;
    final bool lowConfidence = result['low_confidence_warning'] == true;
    final String extractedText = result['extracted_text'] as String? ?? '';
    final List<dynamic> textUrls = result['text_urls'] ?? [];
    final List<dynamic> qrUrls = result['qr_urls'] ?? [];
    final bool isUrlOnly = extractedText.trim().isEmpty && (textUrls.isNotEmpty || qrUrls.isNotEmpty) && !isQrScan;
    final Map<String, dynamic> vlmAnalysis = (result['vlm_analysis'] as Map<String, dynamic>?) ?? {};
    final bool vlmSuccess = vlmAnalysis['success'] == true;
    final List<dynamic> vlmSignals = vlmAnalysis['visual_signals'] ?? [];
    final String vlmReason = vlmAnalysis['reason'] as String? ?? '';
    final Map<String, dynamic> geminiTextAnalysis = (result['gemini_text_analysis'] as Map<String, dynamic>?) ?? {};
    final bool geminiTextSuccess = geminiTextAnalysis['success'] == true;
    final String geminiTextReason = geminiTextAnalysis['reason'] as String? ?? '';
    final String riskLevel = category == 'UNKNOWN' ? 'unknown' : _riskLevel(grade);

    // AI 종합 분석 카드용 변수
    final Map<String, dynamic> urlAnalysis = (result['url_analysis'] as Map<String, dynamic>?) ?? {};
    final double pUrl = ((result['scores']?['p_url'] ?? 0) as num).toDouble();
    final bool hasUrl = urlAnalysis.isNotEmpty;
    final bool vtSafe = urlAnalysis['vt_confirmed_safe'] == true;
    final double pGemini = ((result['scores']?['p_gemini'] ?? 0) as num).toDouble();
    final bool geminiHigh = geminiTextSuccess && pGemini >= 5.0;
    final bool hasK = riskKeywords.isNotEmpty;
    final bool hasU = hasUrl;
    final bool hasUr = pUrl > 2.0;

    String buildSummary() {
      if (grade == 'Danger') {
        if (geminiTextSuccess && vlmSuccess && hasUr) return 'AI 문맥·시각 분석에서 스미싱 패턴이 감지되었고, URL이 악성으로 확인되어 위험으로 판정되었습니다.';
        if (geminiTextSuccess && hasUr)              return 'AI 문맥 분석에서 스미싱 패턴이 감지되었고, URL이 악성으로 확인되어 위험으로 판정되었습니다.';
        if (vlmSuccess && hasUr)                     return '이미지에서 시각적 위협 신호가 감지되었고, URL이 악성으로 확인되어 위험으로 판정되었습니다.';
        if (hasUr)                                   return 'URL 보안 분석에서 악성으로 확인되어 위험으로 판정되었습니다.';
        if (geminiTextSuccess && vlmSuccess)         return 'AI 문맥·시각 분석에서 스미싱 패턴이 감지되어 위험으로 판정되었습니다.';
        if (geminiTextSuccess)                       return 'AI 문맥 분석에서 스미싱 패턴이 강하게 감지되어 위험으로 판정되었습니다.';
        return '복합적인 위험 신호가 감지되어 위험으로 판정되었습니다.';
      }
      if (grade == 'Warning') {
        if (geminiTextSuccess && vlmSuccess && hasUr) return 'AI 문맥·시각 분석에서 의심 요소가 발견되었고, URL에서도 위험 신호가 감지되어 주의로 판정되었습니다.';
        if (geminiTextSuccess && hasUr)               return 'AI 문맥 분석에서 의심 요소가 발견되었고, URL에서 일부 위험 신호가 감지되어 주의로 판정되었습니다.';
        if (geminiTextSuccess && hasK)                return 'AI 문맥 분석과 키워드 패턴에서 의심 요소가 발견되어 주의로 판정되었습니다.';
        if (geminiTextSuccess)                        return 'AI 문맥 분석에서 일부 의심 요소가 발견되어 주의로 판정되었습니다.';
        if (hasK && hasUr)                            return '스미싱 패턴 키워드가 탐지되었고, URL에서도 의심 신호가 발견되어 주의로 판정되었습니다.';
        if (hasUr)                                    return 'URL 분석에서 일부 위험 신호가 감지되어 주의로 판정되었습니다.';
        if (hasK)                                     return '스미싱에서 자주 사용되는 키워드 패턴이 감지되어 주의로 판정되었습니다.';
        return '복합적인 의심 신호가 감지되어 주의로 판정되었습니다.';
      }
      if (grade == 'Safe') {
        if (geminiHigh && vtSafe)  return 'AI 문맥 분석에서 일부 의심 요소가 감지되었으나, 다수의 보안 엔진에서 URL을 안전한 사이트로 확인하여 최종 안전으로 판정되었습니다.';
        if (geminiHigh && hasU)    return 'AI 문맥 분석에서 의심 요소가 감지되었으나, URL이 알려진 위험 사이트가 아닌 것으로 확인되어 최종 안전으로 판정되었습니다.';
        if (geminiTextSuccess && hasK && hasUr) return '키워드와 URL에서 일부 의심 요소가 발견되었으나, URL이 알려진 위험 사이트가 아닌 것으로 확인되어 안전으로 판정되었습니다.';
        if (geminiTextSuccess && hasK)          return '일부 키워드가 탐지되었으나, 핵심 위험 패턴이 발견되지 않아 안전으로 판정되었습니다.';
        if (geminiTextSuccess && hasU)          return 'AI 문맥 분석과 URL 분석 모두에서 위험 요소가 발견되지 않아 안전으로 판정되었습니다.';
        if (geminiTextSuccess)                  return 'AI 문맥 분석에서 위험 요소가 발견되지 않아 안전으로 판정되었습니다.';
        if (hasK)                               return '일부 키워드가 탐지되었으나, 스미싱 핵심 패턴이 발견되지 않아 안전으로 판정되었습니다.';
        return '위험 패턴 및 악성 URL이 감지되지 않아 안전으로 판정되었습니다.';
      }
      return '';
    }

    final Color resultColor;
    final IconData resultIcon;
    final String riskLabel;

    switch (riskLevel) {
      case 'danger':
        resultColor = const Color(0xFFDC2626);
        resultIcon = Icons.warning_rounded;
        riskLabel = '위험';
        break;
      case 'caution':
        resultColor = const Color(0xFFF59E0B);
        resultIcon = Icons.error_outline;
        riskLabel = '주의';
        break;
      case 'safe':
        resultColor = const Color(0xFF16A34A);
        resultIcon = Icons.check_circle;
        riskLabel = '안전';
        break;
      case 'unknown':
        resultColor = const Color(0xFF6B7280);
        resultIcon = Icons.close;
        riskLabel = '분석 불가';
        break;
      default:
        resultColor = const Color(0xFF94A3B8);
        resultIcon = Icons.hourglass_empty;
        riskLabel = '분석 대기 중';
    }

    final Map<String, String> nameMap = grade == 'Safe' ? _categoryNamesSafe : _categoryNames;
    final String categoryLabel = (category == null)
        ? '분석에 실패했습니다. 다시 시도해주세요.'
        : (category == 'UNKNOWN' ? '' : (nameMap[category] ?? category));

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: const Color(0xFFEEF5FF),
        appBar: AppBar(
          backgroundColor: Colors.white,
          elevation: 1,
          shadowColor: const Color(0x1A000000),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back, color: Color(0xFF1E293B)),
            onPressed: () => Navigator.pop(context),
          ),
          title: const Text('분석 결과', style: TextStyle(color: Color(0xFF1E293B), fontWeight: FontWeight.bold)),
          actions: const [],
          bottom: const TabBar(
            labelColor: Color(0xFF2563EB),
            unselectedLabelColor: Color(0xFF94A3B8),
            indicatorColor: Color(0xFF2563EB),
            tabs: [
              Tab(text: '결과 요약'),
              Tab(text: '탐지 근거'),
            ],
          ),
        ),
        body: Column(
          children: [
            Expanded(
              child: TabBarView(
                children: [
                  // ── 탭 1: 결과 요약 ──
                  SingleChildScrollView(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      children: [
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 24),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [resultColor, Color.lerp(resultColor, Colors.black, 0.15)!],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [BoxShadow(color: resultColor.withValues(alpha: 0.4), blurRadius: 24, offset: const Offset(0, 8))],
                          ),
                          child: Column(
                            children: [
                              Icon(resultIcon, color: Colors.white, size: 52),
                              const SizedBox(height: 12),
                              Text(riskLabel,
                                style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
                              const SizedBox(height: 4),
                              if (categoryLabel.isNotEmpty)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.25),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: Text(categoryLabel,
                                  style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                              ),
                              if (resultMap?['message'] != null && (resultMap!['message'] as String).isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Text(resultMap['message'] as String,
                                  style: const TextStyle(color: Colors.white70, fontSize: 13)),
                              ],
                            ],
                          ),
                        ),
                        const SizedBox(height: 12),
                        if (isQrScan || isUrlOnly || lowConfidence)
                          Container(
                            width: double.infinity,
                            margin: const EdgeInsets.only(bottom: 12),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFEFCE8),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: const Color(0xFFFBBF24)),
                            ),
                            child: Text(
                              isQrScan
                                  ? '📱 QR 분석은 URL 분석 결과를 기반으로 판정됩니다.'
                                  : isUrlOnly
                                      ? '🔗 텍스트가 없어 URL 분석으로 판정되었습니다.'
                                      : '⚠️ AI 분석 신호가 미약합니다. 명확한 위험 패턴이 감지되지 않았습니다. 의심스럽다면 발신 번호를 검색하거나 해당 기관에 직접 문의하세요.',
                              style: const TextStyle(fontSize: 13, color: Color(0xFF92400E), height: 1.5),
                            ),
                          ),
                        if (riskLevel != 'unknown') ...[
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: resultColor.withValues(alpha: 0.07),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: resultColor.withValues(alpha: 0.25)),
                              boxShadow: [BoxShadow(color: resultColor.withValues(alpha: 0.08), blurRadius: 8, offset: const Offset(0, 2))],
                            ),
                            child: Text(
                              riskLevel == 'danger'
                                  ? '링크를 절대 클릭하지 마세요. 발신자를 차단하고 KISA 불법스팸대응센터(118)에 신고하세요.'
                                  : riskLevel == 'caution'
                                      ? '링크 대신 공식 앱·웹사이트를 직접 검색해서 확인하세요. 개인정보나 금융정보는 절대 입력하지 마세요.'
                                      : '정상 문자로 판정되었습니다. 그래도 출처가 불분명한 문자라면 발신자 혹은 공식 웹사이트를 직접 확인해보세요.',
                              style: TextStyle(fontSize: 14, color: resultColor, height: 1.5),
                            ),
                          ),
                          const SizedBox(height: 12),
                        ],
                        if (riskLevel == 'danger' || rank != null) ...[
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFD4E4FF)),
                              boxShadow: const [BoxShadow(color: Color(0x0A2563EB), blurRadius: 8, offset: Offset(0, 2))],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('위험 문자 탐지 현황', style: TextStyle(fontSize: 14, color: Color(0xFF64748B))),
                                const SizedBox(height: 8),
                                Text(
                                  rank != null ? '탐지 순위 $rank위' : '탐지 순위 목록에 없음',
                                  style: TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.bold,
                                    color: rank != null ? const Color(0xFFDC2626) : const Color(0xFF64748B),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                        ],
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          height: 48,
                          child: ElevatedButton.icon(
                            onPressed: () => Share.share(_buildShareText(riskLabel, categoryLabel, grade, textReasons, urlReasons)),
                            icon: const Icon(Icons.share, size: 18),
                            label: const Text('결과 공유하기', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF3D9DF3),
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFFD4E4FF)),
                            boxShadow: const [BoxShadow(color: Color(0x0A2563EB), blurRadius: 8, offset: Offset(0, 2))],
                          ),
                          child: Row(
                            children: [
                              const Expanded(
                                child: Text('결과가 잘못되었다면?', style: TextStyle(fontSize: 14, color: Color(0xFF64748B))),
                              ),
                              ElevatedButton.icon(
                                onPressed: () {
                                  Navigator.pop(context);
                                  _MainPageState.goToFeedback();
                                },
                                icon: const Icon(Icons.feedback_outlined, size: 16),
                                label: const Text('피드백하러 가기'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF2563EB),
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],
                    ),
                  ),

                  // ── 탭 2: 탐지 근거 ──
                  SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(24.0, 24.0, 24.0, 48.0),
                    child: Column(
                      children: [
                        // ── AI 종합 분석 카드 ──
                        Builder(builder: (context) {
                          final String summary = buildSummary();
                          if (summary.isEmpty) return const SizedBox.shrink();
                          final Color sColor = grade == 'Danger'
                              ? const Color(0xFFDC2626)
                              : grade == 'Warning'
                                  ? const Color(0xFFF97316)
                                  : const Color(0xFF16A34A);
                          final String sIcon = grade == 'Danger' ? '🚨' : grade == 'Warning' ? '⚠️' : '✅';
                          return Column(children: [
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: sColor.withValues(alpha: 0.05),
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: sColor.withValues(alpha: 0.35), width: 1.5),
                                boxShadow: [BoxShadow(color: sColor.withValues(alpha: 0.1), blurRadius: 10, offset: const Offset(0, 3))],
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('$sIcon AI 종합 분석',
                                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: sColor)),
                                  const SizedBox(height: 8),
                                  Text(summary, style: const TextStyle(fontSize: 14, color: Color(0xFF1E293B), height: 1.6)),
                                ],
                              ),
                            ),
                            const SizedBox(height: 12),
                          ]);
                        }),

                        // Gemini 실패 경고
                        if (!geminiTextSuccess && !vlmSuccess) ...[
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFFFBEB),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.5)),
                            ),
                            child: Text(
                              isQrScan
                                ? '📱 QR 분석은 URL 분석 결과를 기반으로 판정됩니다.'
                                : '⚠️ AI 문맥 분석을 일시적으로 이용할 수 없어 NLP 및 URL 분석 결과만 반영되었습니다.',
                              style: const TextStyle(fontSize: 13, color: Color(0xFF92400E)),
                            ),
                          ),
                          const SizedBox(height: 12),
                        ],

                        // Gemini 문맥 분석 섹션
                        if (geminiTextSuccess && geminiTextReason.isNotEmpty) ...[
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFD4E4FF)),
                              boxShadow: const [BoxShadow(color: Color(0x0A2563EB), blurRadius: 8, offset: Offset(0, 2))],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Text('AI 문맥 분석', style: TextStyle(fontSize: 14, color: Color(0xFF64748B))),
                                    const SizedBox(width: 8),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF0EA5E9).withValues(alpha: 0.1),
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: const Text('Gemini', style: TextStyle(fontSize: 11, color: Color(0xFF0EA5E9))),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(geminiTextReason, style: const TextStyle(fontSize: 13, color: Color(0xFF374151))),
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                        ],

                        // VLM 시각 분석 섹션
                        if (vlmSuccess && vlmSignals.isNotEmpty) ...[
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFD4E4FF)),
                              boxShadow: const [BoxShadow(color: Color(0x0A2563EB), blurRadius: 8, offset: Offset(0, 2))],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Text('AI 시각 분석', style: TextStyle(fontSize: 14, color: Color(0xFF64748B))),
                                    const SizedBox(width: 8),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF7C3AED).withValues(alpha: 0.1),
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: const Text('Gemini Vision', style: TextStyle(fontSize: 11, color: Color(0xFF7C3AED))),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 12),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: vlmSignals.map((s) => Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF7C3AED).withValues(alpha: 0.08),
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(color: const Color(0xFF7C3AED).withValues(alpha: 0.3)),
                                    ),
                                    child: Text(s.toString(), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF7C3AED))),
                                  )).toList(),
                                ),
                                if (vlmReason.isNotEmpty) ...[
                                  const SizedBox(height: 8),
                                  Text(vlmReason, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                                ],
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                        ],
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: const Color(0xFFD4E4FF)),
                            boxShadow: const [BoxShadow(color: Color(0x0A2563EB), blurRadius: 8, offset: Offset(0, 2))],
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('탐지된 위험 키워드', style: TextStyle(fontSize: 14, color: Color(0xFF64748B))),
                              const SizedBox(height: 12),
                              if (riskKeywords.isNotEmpty)
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: riskKeywords.map((kw) {
                                    final Map<String, dynamic> k = kw as Map<String, dynamic>;
                                    final String type = k['type'] ?? '';
                                    final Color chipColor = switch (type) {
                                      'urgency'          => const Color(0xFFDC2626),
                                      'threat'           => const Color(0xFFEA580C),
                                      'action'           => const Color(0xFFF59E0B),
                                      'category_pattern' => const Color(0xFF7C3AED),
                                      _                  => const Color(0xFF64748B),
                                    };
                                    final String typeLabel = switch (type) {
                                      'urgency'          => '긴박감',
                                      'threat'           => '위협',
                                      'action'           => '행동유도',
                                      'category_pattern' => '유형패턴',
                                      _                  => type,
                                    };
                                    return Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                      decoration: BoxDecoration(
                                        color: chipColor.withValues(alpha: 0.1),
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: chipColor.withValues(alpha: 0.3)),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Text(k['keyword'] ?? '', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: chipColor)),
                                          const SizedBox(width: 6),
                                          Text('[$typeLabel]', style: TextStyle(fontSize: 11, color: chipColor.withValues(alpha: 0.8))),
                                        ],
                                      ),
                                    );
                                  }).toList(),
                                )
                              else
                                const Text('감지된 키워드 없음', style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8))),
                            ],
                          ),
                        ),
                        const SizedBox(height: 12),
                        if (textReasons.isNotEmpty || urlReasons.isNotEmpty) ...[
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFD4E4FF)),
                              boxShadow: const [BoxShadow(color: Color(0x0A2563EB), blurRadius: 8, offset: Offset(0, 2))],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (textReasons.isNotEmpty) ...[
                                  const Text('문자 내용 탐지 근거', style: TextStyle(fontSize: 14, color: Color(0xFF64748B))),
                                  const SizedBox(height: 8),
                                  ...textReasons.map((r) => Padding(
                                    padding: const EdgeInsets.only(bottom: 4),
                                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                      const Text('• ', style: TextStyle(fontSize: 13, color: Color(0xFF475569))),
                                      Expanded(child: Text(r.toString(), style: const TextStyle(fontSize: 13, color: Color(0xFF475569)))),
                                    ]),
                                  )),
                                ],
                                if (textReasons.isNotEmpty && urlReasons.isNotEmpty) const Divider(height: 24),
                                if (urlReasons.isNotEmpty) ...[
                                  const Text('URL 탐지 근거', style: TextStyle(fontSize: 14, color: Color(0xFF64748B))),
                                  const SizedBox(height: 8),
                                  ...urlReasons.map((r) => Padding(
                                    padding: const EdgeInsets.only(bottom: 4),
                                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                      const Text('• ', style: TextStyle(fontSize: 13, color: Color(0xFF475569))),
                                      Expanded(child: Text(r.toString(), style: const TextStyle(fontSize: 13, color: Color(0xFF475569)))),
                                    ]),
                                  )),
                                ],
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                        ],
                        if (riskKeywords.isEmpty && textReasons.isEmpty && urlReasons.isEmpty)
                          const Padding(
                            padding: EdgeInsets.all(24),
                            child: Text('탐지된 근거가 없습니다.', style: TextStyle(fontSize: 14, color: Color(0xFF94A3B8))),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

          ],
        ),
      ),
    );
  }

}
