# 🚨 안전 감지 자동화 119 (웹 업로드형)

실시간 화재 감지 및 자동 알림 시스템입니다. 업로드된 영상을 분석하여 **전조 → 연기/초기화염 → 화재확대 → 119 호출** 단계를 실시간으로 표시하고, 위험 상황 시 자동 알림을 발송합니다.

## 🎯 주요 기능

- **실시간 영상 분석**: YOLO 기반 화재/연기 감지
- **단계별 상태 추적**: 5단계 화재 진행 상황 모니터링
- **자동 알림 시스템**: Slack/Email 긴급 알림 발송
- **웹 인터페이스**: 업로드, 실시간 모니터링, 타임라인, 점수 그래프
- **고도화된 필터링**: ROI, 색상 게이팅, Person 억제 기능

## 🏗️ 시스템 아키텍처

```
├── backend/                 # FastAPI 서버
│   ├── main.py             # API 엔드포인트
│   ├── detectors/
│   │   └── vision.py       # YOLO 화재/연기 감지
│   ├── state_machine.py    # 상태 전이 로직
│   ├── utils.py           # 알림 발송 유틸리티
│   └── test_system.py     # 시스템 테스트
├── frontend/               # React 웹 인터페이스
│   └── src/
│       ├── App.js         # 메인 앱
│       └── components/    # UI 컴포넌트
├── rules/                 # 엔진 규칙 정의
├── models/vision/         # AI 모델 저장소
└── media/                 # 업로드/스냅샷 저장
```

## 🚀 설치 및 실행

### 1. 의존성 설치

#### Backend (Python)
```bash
cd backend
pip install -r requirements.txt
```

#### Frontend (Node.js)
```bash
cd frontend
npm install
```

### 2. 환경 설정

`.env` 파일에서 설정을 확인하고 필요시 수정:

```bash
# 파일 경로
UPLOAD_PATH=./media/uploads
SNAPSHOT_PATH=./media/snap
PROCESSING_FPS=3

# 알림 설정 (선택사항)
SLACK_WEBHOOK_URL=your_slack_webhook_url
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_password
ALERT_EMAIL=alert@example.com

# 모델 설정
MODEL_PATH=./models/vision/yolov5s.pt
CONFIDENCE_THRESHOLD=0.25
```

### 3. 서버 실행

#### Backend 실행
```bash
cd backend
python main.py
```
서버가 http://localhost:8000 에서 실행됩니다.

#### Frontend 실행
```bash
cd frontend
npm start
```
웹 인터페이스가 http://localhost:3000 에서 실행됩니다.

## 📖 사용 방법

### 1. 영상 업로드
- 웹 인터페이스에서 MP4, AVI, MOV 파일 업로드 (최대 100MB)
- 드래그 & 드롭 또는 파일 선택으로 업로드

### 2. 실시간 모니터링
- 업로드 후 자동으로 분석 시작
- 실시간 상태 표시 및 점수 업데이트
- 타임라인과 그래프로 진행 상황 확인

### 3. 알림 수신
- CALL_119 상태 진입 시 자동 알림 발송
- 브라우저 알림 + Slack/Email (설정 시)

## 🔧 상태 및 임계치

### 상태 전이 단계
1. **NORMAL** (정상) - 평상시 상태
2. **PRE_FIRE** (전조) - 화재 전조 현상 감지
3. **SMOKE_DETECTED** (연기 감지) - 연기 확인
4. **FIRE_GROWING** (화재 확산) - 화재 진행 중
5. **CALL_119** (긴급 호출) - 즉시 신고 필요

### 기본 임계치
- 화재 점수: 25% (전조), 60% (확산)
- 연기 점수: 30% (감지), 50% (확인)
- 위험도: 85% (119 호출)

임계치는 `backend/thresholds.json`에서 조정 가능합니다.

## 🧪 테스트

시스템 기능 검증을 위한 자동화된 테스트:

```bash
cd backend
python test_system.py
```

테스트는 다음 시나리오를 포함합니다:
- 화재 진행 시나리오 (정상 → 119 호출)
- 오탐 방지 테스트 (Person 억제)
- 정상 활동 테스트

## 📊 API 엔드포인트

### POST /upload/video
영상 파일 업로드 및 분석 시작
```json
{
  "job_id": "uuid-string",
  "status": "queued"
}
```

### GET /events?job_id={id}
실시간 SSE 스트림 (0.2초 간격)
```json
{
  "type": "frame",
  "timestamp": "2024-01-01T00:00:00",
  "state": "SMOKE_DETECTED",
  "scores": {"fire": 0.45, "smoke": 0.62, "hazard": 0.53},
  "boxes": {...},
  "snapshot": "path/to/snapshot.jpg"
}
```

### GET /report/{job_id}
분석 완료 후 상세 리포트
```json
{
  "job_id": "uuid",
  "state_history": [...],
  "alerts_sent": [...],
  "summary": {...}
}
```

## ⚙️ 고급 설정

### ROI (관심 영역) 설정
`thresholds.json`에서 분석할 영역 지정:
```json
{
  "roi": {
    "enabled": true,
    "coordinates": [0.2, 0.2, 0.8, 0.8]
  }
}
```

### Person 억제 기능
사람과 겹치는 화재 감지 억제:
```json
{
  "person_suppression": {
    "enabled": true,
    "iou_threshold": 0.5,
    "fire_ratio_threshold": 0.20
  }
}
```

### HSV 색상 필터링
불색 조건에 맞지 않는 감지 제거:
```json
{
  "hsv_filter": {
    "enabled": true,
    "h_range": [0, 60],
    "s_min": 0.5,
    "v_min": 0.5,
    "min_fire_ratio": 0.08
  }
}
```

## 🔍 문제 해결

### 모델 로딩 실패
- `models/vision/` 디렉토리에 YOLO 모델 파일 확인
- 인터넷 연결 시 자동으로 YOLOv8n 다운로드

### SSE 연결 끊김
- 브라우저 새로고침 후 재연결
- 방화벽/프록시 설정 확인

### 알림 발송 실패
- `.env` 파일의 Slack/SMTP 설정 확인
- 네트워크 연결 및 인증 정보 검증

## 📝 개발 참고사항

### 성능 최적화
- 기본 처리 속도: 2-5 FPS
- EMA 평활화로 노이즈 감소 (α=0.4)
- 연속 프레임 조건으로 오탐 방지

### 확장 가능성
- 커스텀 모델 교체 가능
- 추가 알림 채널 구현
- 다중 카메라 지원

## 📄 라이선스

이 프로젝트는 방어적 보안 목적으로만 사용되어야 합니다.

---

🚨 **중요**: 실제 화재 상황에서는 즉시 119에 신고하고 대피하세요. 이 시스템은 보조 도구로만 사용하시기 바랍니다.