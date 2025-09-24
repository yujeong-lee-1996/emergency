# backend/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import json
import uuid
import asyncio
import time
import cv2
from datetime import datetime
from typing import Dict, Any, AsyncGenerator
from pydantic import BaseModel
from ultralytics import YOLO
from email_notifier import EmailNotifier

# 경로 설정
ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "media"
UPLOADS = MEDIA / "uploads"
RUNS = MEDIA / "runs"

for p in (UPLOADS, RUNS):
    p.mkdir(parents=True, exist_ok=True)

# 모델 로드
def load_model() -> YOLO:
    # 절대 경로로 모델 파일 찾기
    model_paths = [
        ROOT / "backend" / "models" / "vision" / "best_nano_111.pt",
        ROOT / "models" / "vision" / "best_nano_111.pt",
        Path("./models/vision/best_nano_111.pt"),
        Path("./backend/models/vision/best_nano_111.pt")
    ]

    for model_path in model_paths:
        if model_path.exists():
            print(f"[model] Using: {model_path}")
            return YOLO(str(model_path))

    print(f"[model] Using default: yolo11n.pt")
    return YOLO('yolo11n.pt')

MODEL = load_model()
EMAIL_NOTIFIER = EmailNotifier()

# 모델 클래스 정보 출력
try:
    print(f"[model] 클래스 이름: {MODEL.names}")
    print(f"[model] 총 클래스 수: {len(MODEL.names) if MODEL.names else 'Unknown'}")
except Exception as e:
    print(f"[model] 클래스 정보 조회 실패: {e}")

# 화재/연기 감지를 위한 클래스 ID 매핑
FIRE_CLASS_IDS = []
SMOKE_CLASS_IDS = []

if MODEL.names:
    for class_id, class_name in MODEL.names.items():
        name_lower = class_name.lower()
        if 'fire' in name_lower or 'flame' in name_lower or 'burn' in name_lower:
            FIRE_CLASS_IDS.append(class_id)
            print(f"[model] Fire 클래스 발견: {class_id} = {class_name}")
        elif 'smoke' in name_lower or 'vapor' in name_lower:
            SMOKE_CLASS_IDS.append(class_id)
            print(f"[model] Smoke 클래스 발견: {class_id} = {class_name}")

print(f"[model] Fire 클래스 IDs: {FIRE_CLASS_IDS}")
print(f"[model] Smoke 클래스 IDs: {SMOKE_CLASS_IDS}")

# 기본값 설정 (클래스가 발견되지 않으면)
if not FIRE_CLASS_IDS:
    FIRE_CLASS_IDS = [0]  # 기본적으로 0번을 Fire로 가정
    print("[model] Fire 클래스를 찾지 못해 기본값 [0] 사용")

if not SMOKE_CLASS_IDS:
    SMOKE_CLASS_IDS = [1]  # 기본적으로 1번을 Smoke로 가정
    print("[model] Smoke 클래스를 찾지 못해 기본값 [1] 사용")

# 로깅 설정
DEBUG_MODE = False  # False로 설정하면 로그가 거의 출력되지 않음
QUIET_MODE = True   # True로 설정하면 거의 모든 로그 숨김

# 규칙 설정
RULES = {
    "imgsz": 416,
    "conf": 0.15,  # 더 낮은 임계값으로 설정 (더 많은 감지)
    "iou": 0.20,   # IoU 임계값도 약간 높여서 중복 제거
    "max_det": 20, # 최대 감지 수 증가
    "fps_target": 5,
    "ema_alpha": 0.4,
    "weights": {"s_smoke": 0.6, "s_fire": 0.8, "growth": 0.4},
    "thresholds": {
        "pre_fire": {"smoke": 0.10, "fire": 0.08},      # 매우 민감하게
        "smoke_detected": {"smoke": 0.25},               # 낮은 임계치
        "fire_growing": {"fire": 0.30, "hazard": 0.35}, # 낮은 임계치
        "call_119": {"hazard": 0.45},                    # 매우 낮은 임계치
    },
}

app = FastAPI(title="Safety Detection 119", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 글로벌 상태
JOBS: Dict[str, Dict[str, Any]] = {}
EVENT_QUEUES: Dict[str, asyncio.Queue] = {}
JOB_FLAGS: Dict[str, Dict[str, Any]] = {}

# 유틸 함수
def video_meta(path: Path):
    """영상 메타데이터(fps, w, h, frame_count) 추출"""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    return fps, w, h, n

async def sse_gen(job_id: str) -> AsyncGenerator[bytes, None]:
    """SSE 스트림 제너레이터"""
    try:
        q = EVENT_QUEUES[job_id]
        await q.put({"type": "hello", "job_id": job_id})
        while True:
            try:
                item = await asyncio.wait_for(q.get(), timeout=30.0)  # 30초 타임아웃
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n".encode("utf-8")
                if item.get("type") in ("end", "error"):
                    break
            except asyncio.TimeoutError:
                # 연결 유지를 위한 heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat', 'job_id': job_id})}\n\n".encode("utf-8")
    except Exception as e:
        print(f"❌ SSE 스트림 오류: {job_id} - {e}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n".encode("utf-8")

@app.post("/upload")
async def upload_video(file: UploadFile, background_tasks: BackgroundTasks):
    """동영상 업로드 → 비동기 분석 시작 → job_id 반환"""
    if DEBUG_MODE:
        print(f"📹 비디오 업로드 시작: {file.filename}")

    # 파일 타입 검증
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="Video file required")

    job_id = uuid.uuid4().hex[:12]
    dest = UPLOADS / f"{job_id}.mp4"

    try:
        # 업로드 디렉토리 확실히 생성
        UPLOADS.mkdir(parents=True, exist_ok=True)

        # 파일 저장
        content = await file.read()
        with open(dest, "wb") as f:
            f.write(content)

        # 파일이 실제로 저장되었는지 확인
        if not dest.exists() or dest.stat().st_size == 0:
            raise RuntimeError(f"File save failed: {dest}")

        if not QUIET_MODE:
            print(f"✅ 저장완료: {job_id} ({dest.stat().st_size} bytes)")

        JOBS[job_id] = {"path": str(dest), "done": False, "err": None}
        EVENT_QUEUES[job_id] = asyncio.Queue(maxsize=100)
        JOB_FLAGS[job_id] = {"paused": False, "stop": False}

        background_tasks.add_task(process_video_job, job_id, dest)
        return {"job_id": job_id, "video_url": f"/media/uploads/{dest.name}"}

    except Exception as e:
        if not QUIET_MODE:
            print(f"❌ 업로드실패: {e}")
        if dest.exists():
            dest.unlink()  # 실패 시 파일 삭제
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/events")
async def events(job_id: str):
    """SSE 스트림 엔드포인트"""
    if job_id not in EVENT_QUEUES:
        raise HTTPException(404, "unknown job_id")
    return StreamingResponse(sse_gen(job_id), media_type="text/event-stream")

@app.get("/media/uploads/{name}")
async def media_uploads(name: str):
    """업로드된 원본 영상 재생용 엔드포인트"""
    p = UPLOADS / name
    if not p.exists():
        raise HTTPException(404, f"File not found: {name}")
    return FileResponse(str(p), media_type="video/mp4")

@app.get("/media/{name}")
async def media(name: str):
    """미디어 파일 일반 엔드포인트"""
    p = UPLOADS / name
    if not p.exists():
        raise HTTPException(404, f"File not found: {name}")
    return FileResponse(str(p), media_type="video/mp4")

class Ctrl(BaseModel):
    cmd: str  # 'pause' | 'resume' | 'stop'

@app.post("/jobs/{job_id}/control")
async def control(job_id: str, c: Ctrl):
    """분석 제어: 일시정지/재개/중지"""
    if job_id not in JOB_FLAGS:
        raise HTTPException(404, "unknown job_id")
    if c.cmd == "pause":
        JOB_FLAGS[job_id]["paused"] = True
    elif c.cmd == "resume":
        JOB_FLAGS[job_id]["paused"] = False
    elif c.cmd == "stop":
        JOB_FLAGS[job_id]["stop"] = True
    else:
        raise HTTPException(400, "cmd must be pause|resume|stop")
    return {"ok": True, "flags": JOB_FLAGS[job_id]}

@app.get("/test")
async def test_endpoint():
    """테스트 엔드포인트"""
    return {"message": "API is working", "jobs": list(JOBS.keys())}

class EmailRequest(BaseModel):
    job_id: str
    scores: dict
    timestamp: float = None

@app.post("/send-emergency-email")
async def send_emergency_email(request: EmailRequest):
    """119 호출 버튼 클릭 시 긴급 이메일 발송"""
    try:
        print(f"🚨 EMERGENCY EMAIL REQUEST: {request.job_id}")

        success = EMAIL_NOTIFIER.send_emergency_alert(
            job_id=request.job_id,
            scores=request.scores,
            timestamp=request.timestamp
        )

        if success:
            return {"success": True, "message": "긴급 알림 이메일이 발송되었습니다."}
        else:
            raise HTTPException(status_code=500, detail="이메일 발송에 실패했습니다.")

    except Exception as e:
        print(f"❌ 이메일 발송 API 오류: {e}")
        raise HTTPException(status_code=500, detail=f"이메일 발송 실패: {str(e)}")

@app.post("/jobs/{job_id}/restart")
async def restart_analysis(job_id: str, background_tasks: BackgroundTasks):
    """기존 영상 재분석"""
    print(f"🔄 재분석 요청 수신: {job_id}")
    print(f"🗃️ 현재 등록된 JOBS: {list(JOBS.keys())}")

    if job_id not in JOBS:
        print(f"❌ Job ID {job_id}를 찾을 수 없음")
        available_jobs = list(JOBS.keys())
        raise HTTPException(404, f"Job {job_id} not found. Available jobs: {available_jobs}")

    video_path = Path(JOBS[job_id]["path"])
    print(f"📁 비디오 파일 경로: {video_path}")

    if not video_path.exists():
        print(f"❌ 비디오 파일이 존재하지 않음: {video_path}")
        raise HTTPException(404, f"Video file not found: {video_path}")

    # 기존 작업 정리
    if job_id in JOB_FLAGS:
        JOB_FLAGS[job_id]["stop"] = True
        print(f"🛑 기존 작업 중지 플래그 설정")

    # 잠시 대기 (기존 작업이 완전히 종료되도록)
    await asyncio.sleep(0.2)

    if job_id in EVENT_QUEUES:
        del EVENT_QUEUES[job_id]
        print(f"🗑️ 기존 이벤트 큐 삭제")

    # 새로운 분석 시작
    EVENT_QUEUES[job_id] = asyncio.Queue(maxsize=100)
    JOB_FLAGS[job_id] = {"paused": False, "stop": False}
    JOBS[job_id]["done"] = False
    JOBS[job_id]["err"] = None

    print(f"🚀 새로운 분석 작업 시작")
    background_tasks.add_task(process_video_job, job_id, video_path)
    return {"ok": True, "message": "Analysis restarted", "job_id": job_id}

async def process_video_job(job_id: str, path: Path):
    """
    - stride = round(src_fps / fps_target) 만큼 프레임을 건너뛰며 추론
    - EMA로 fire/smoke 점수 산출 → hazard 계산
    - 상태 결정 후 매 tick 이벤트에 box/점수/상태/시간을 push
    - pause 동안 타임라인 보정(start_wall += pause_duration) → 싱크 유지
    """
    if DEBUG_MODE:
        print(f"🎬 비디오 분석 시작: {job_id}")
    q = EVENT_QUEUES[job_id]
    flags = JOB_FLAGS[job_id]
    try:
        fps, w, h, _ = video_meta(path)
        if DEBUG_MODE:
            print(f"📊 비디오 메타: {w}x{h}, {fps:.1f}fps")

        stride = max(1, round(fps / RULES["fps_target"]))
        alpha = RULES["ema_alpha"]
        w_smoke = RULES["weights"]["s_smoke"]
        w_fire = RULES["weights"]["s_fire"]
        w_growth = RULES["weights"]["growth"]

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {path}")

        start_wall = time.monotonic()
        frame_idx = -1
        S_ema = F_ema = prev_S = prev_F = 0.0
        state = "NORMAL"
        last_state = "NORMAL"
        pause_started = None
        processed_frames = 0

        interval = 1.0 / fps if fps > 0 else 0.04

        while True:
            if flags.get("stop"):
                break

            if flags.get("paused"):
                if pause_started is None:
                    pause_started = time.monotonic()
                await asyncio.sleep(0.05)
                continue
            elif pause_started is not None:
                start_wall += (time.monotonic() - pause_started)
                pause_started = None

            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1

            if frame_idx % stride != 0:
                continue

            processed_frames += 1

            # YOLO 추론
            res = MODEL.predict(
                source=frame,
                imgsz=RULES["imgsz"],
                conf=RULES["conf"],
                iou=RULES["iou"],
                device="cpu",
                max_det=RULES["max_det"],
                verbose=False,
            )[0]

            # 최대 점수 및 박스 수집
            fire_raw, smoke_raw = 0.0, 0.0
            boxes_out = []

            # 총 감지된 객체 수 로그
            total_detections = len(res.boxes.xyxy) if res.boxes is not None else 0
            if total_detections > 0:
                print(f"🔍 프레임 {processed_frames}: YOLO가 {total_detections}개 객체 감지")
            elif processed_frames % 30 == 0:  # 30프레임마다 감지 없음 로그
                print(f"🔍 프레임 {processed_frames}: YOLO 감지 없음")

            if res.boxes is not None and len(res.boxes.xyxy) > 0:
                xyxy = res.boxes.xyxy.cpu().tolist()
                clss = res.boxes.cls.cpu().int().tolist()
                confs = res.boxes.conf.cpu().tolist()

                # 모델 클래스 이름 확인
                class_names = res.names if hasattr(res, 'names') else {}

                # 감지된 클래스 출력 (첫 10프레임만)
                if processed_frames <= 10:
                    detected_classes = [(c, class_names.get(c, f"class_{c}"), cf) for c, cf in zip(clss, confs)]
                    if detected_classes:
                        print(f"🎯 프레임 {processed_frames} 감지 클래스: {detected_classes}")

                for (x1, y1, x2, y2), c, cf in zip(xyxy, clss, confs):
                    class_name = class_names.get(c, f"class_{c}")

                    # 동적 클래스 매핑 사용
                    is_fire = c in FIRE_CLASS_IDS
                    is_smoke = c in SMOKE_CLASS_IDS

                    # 모든 감지된 객체를 boxes_out에 추가
                    if is_fire or is_smoke:
                        box_data = {
                            "x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2),
                            "cls": int(c), "conf": round(float(cf), 3),
                            "label": "fire" if is_fire else "smoke" if is_smoke else class_name
                        }
                        boxes_out.append(box_data)

                        if is_fire:
                            fire_raw = max(fire_raw, float(cf))
                            # 모든 화재 감지 로그 (신뢰도 관계없이)
                            print(f"🔥 FIRE 감지! 클래스: {c}({class_name}), 신뢰도: {cf:.3f}, 위치: ({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})")

                        if is_smoke:
                            smoke_raw = max(smoke_raw, float(cf))
                            # 모든 연기 감지 로그 (신뢰도 관계없이)
                            print(f"💨 SMOKE 감지! 클래스: {c}({class_name}), 신뢰도: {cf:.3f}, 위치: ({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})")
                    else:
                        # 화재/연기가 아닌 다른 객체 (매우 높은 신뢰도만)
                        if cf > 0.8 and processed_frames % 50 == 0:
                            print(f"🎯 기타 객체: {c}({class_name}), 신뢰도: {cf:.3f}")

            # 감지 로깅 (모든 감지 결과)
            if len(boxes_out) > 0:
                print(f"📊 프레임 {processed_frames}: {len(boxes_out)}개 감지, Fire: {fire_raw:.3f} (EMA: {F_ema:.3f}), Smoke: {smoke_raw:.3f} (EMA: {S_ema:.3f})")
            elif processed_frames % 20 == 0:  # 20프레임마다 감지 없음 로그
                print(f"⚪ 프레임 {processed_frames}: 감지 없음, Fire EMA: {F_ema:.3f}, Smoke EMA: {S_ema:.3f}")

            # EMA & hazard
            F_ema = alpha * fire_raw + (1 - alpha) * F_ema
            S_ema = alpha * smoke_raw + (1 - alpha) * S_ema
            growth = max(0.0, S_ema - prev_S) + max(0.0, F_ema - prev_F)
            H = max(w_smoke * S_ema, w_fire * F_ema) + w_growth * growth
            prev_S, prev_F = S_ema, F_ema

            # 박스 데이터에 EMA 점수 추가 (필터링 없이 모든 YOLO 감지 결과 표시)
            for box in boxes_out:
                if box["cls"] == 0:  # Fire
                    box["ema_score"] = round(F_ema, 3)
                else:  # Smoke
                    box["ema_score"] = round(S_ema, 3)

            # 상태 결정
            th = RULES["thresholds"]
            if H > th["call_119"]["hazard"]:
                state = "CALL_119"
            elif (F_ema > th["fire_growing"]["fire"]) or (H > th["fire_growing"]["hazard"]):
                state = "FIRE_GROWING"
            elif S_ema > th["smoke_detected"]["smoke"]:
                state = "SMOKE_DETECTED"
            elif (S_ema > th["pre_fire"]["smoke"]) or (F_ema > th["pre_fire"]["fire"]):
                state = "PRE_FIRE"
            else:
                state = "NORMAL"

            # 이벤트 push (SSE)
            t_video = frame_idx / fps

            # 상태 변화 추적만 (이메일은 버튼 클릭 시 별도 API로 발송)
            last_state = state
            event_data = {
                "type": "tick",
                "job_id": job_id,
                "t": t_video,
                "state": state,
                "scores": {
                    "fire": round(F_ema, 3),
                    "smoke": round(S_ema, 3),
                    "hazard": round(H, 3),
                },
                "raw_scores": {
                    "fire": round(fire_raw, 3),
                    "smoke": round(smoke_raw, 3),
                },
                "img_w": w,
                "img_h": h,
                "boxes": boxes_out,
            }

            # SSE 데이터 확인 (상태 변화나 높은 점수일 때만)
            # 중요한 이벤트만 로그
            if not DEBUG_MODE and state == "CALL_119":
                print(f"🚨 EMERGENCY: {job_id} - {state}")
            elif DEBUG_MODE and state != "NORMAL":
                print(f"📤 {state}: fire={F_ema:.2f}, smoke={S_ema:.2f}, hazard={H:.2f}")

            await q.put(event_data)

            # 재생 속도 맞추기
            due = start_wall + t_video
            now = time.monotonic()
            if due - now > 0:
                await asyncio.sleep(due - now)
            else:
                lag = now - due
                behind_frames = int(lag / interval)
                for _ in range(max(0, behind_frames)):
                    cap.grab()
                    frame_idx += 1

        cap.release()
        print(f"✅ 분석 완료: {job_id}")
        if DEBUG_MODE:
            print(f"   처리 프레임: {processed_frames}")
        await q.put({"type": "end", "job_id": job_id})
        JOBS[job_id]["done"] = True

    except Exception as e:
        print(f"❌ 분석 오류: {job_id}")
        if DEBUG_MODE:
            print(f"   에러: {e}")
            import traceback
            traceback.print_exc()
        JOBS[job_id]["err"] = str(e)
        await q.put({"type": "error", "job_id": job_id, "error": str(e)})
    finally:
        JOB_FLAGS.pop(job_id, None)

# 정적 파일 서빙
app.mount("/media", StaticFiles(directory=str(MEDIA)), name="media")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)