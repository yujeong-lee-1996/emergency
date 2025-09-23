# backend/app.py
"""
업로드한 동영상을 YOLO로 분석해 실시간처럼 SSE로 점수/상태/바운딩박스를 스트리밍합니다.
- 외부 thresholds.json 없이 코드 내 RULES 로직만 사용
- 프레임 샘플링(stride = round(src_fps / RULES['fps_target']))
- EMA로 score를 안정화하고 hazard 계산 → 상태머신 (NORMAL→PRE_FIRE→SMOKE_DETECTED→FIRE_GROWING→CALL_119)
- 비디오 재생과 싱크: '벽시계 기준'으로 프레임 타임을 맞추고, 늦으면 grab()으로 프레임 스킵
- 제어 API: /jobs/{job_id}/control (pause/resume/stop)
- 프론트에 그릴 수 있도록 매 tick 에 바운딩박스(xyxy, cls, conf)와 원본 프레임 해상도(img_w, img_h) 포함
"""

import asyncio, json, time, uuid
from pathlib import Path
from typing import AsyncGenerator, Dict, Any

import cv2
from fastapi import FastAPI, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ultralytics import YOLO

# ---------- 경로/모델 설정 ----------
ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "media"
UPLOADS = MEDIA / "uploads"
RUNS = MEDIA / "runs"
MODELS_DIR = ROOT / "models"  # 폴더 검색용

# 명시 모델(있으면 우선)
EXPLICIT_MODEL = Path(
    r"D:\deep2st\test\Real-Time-Smoke-Fire-Detection-YOLO11\models\best_nano_111.pt"
)

for p in (UPLOADS, RUNS, MODELS_DIR):
    p.mkdir(parents=True, exist_ok=True)


def load_model() -> YOLO:
    """EXPLICIT_MODEL → models/*.onnx → models/*.pt 순으로 모델 로드"""
    if EXPLICIT_MODEL.exists():
        print(f"[model] Using explicit: {EXPLICIT_MODEL}")
        return YOLO(str(EXPLICIT_MODEL))
    onnx = next(MODELS_DIR.glob("*.onnx"), None)
    if onnx:
        print(f"[model] Using ONNX: {onnx}")
        return YOLO(str(onnx))
    pt = next(MODELS_DIR.glob("*.pt"), None)
    if pt:
        print(f"[model] Using PT: {pt}")
        return YOLO(str(pt))
    raise RuntimeError("모델 가중치를 찾지 못했습니다. EXPLICIT_MODEL 또는 models/ 확인.")


MODEL = load_model()

# ---------- 규칙/하이퍼파라미터 (내장) ----------
RULES = {
    # 추론 하이퍼파라미터(속도/정확도 트레이드오프)
    "imgsz": 416,        # 320~640 권장(CPU면 낮추면 빨라짐)
    "conf": 0.30,
    "iou": 0.10,
    "max_det": 10,

    # 프레임 샘플링: target FPS로 낮춰 처리 (실시간 페이싱의 핵심)
    "fps_target": 5,     # 25fps 원본이면 5프레임마다 1번 추론

    # 점수 안정화
    "ema_alpha": 0.4,    # 0.3~0.5 범위 권장

    # hazard 가중치
    "weights": {"s_smoke": 0.6, "s_fire": 0.8, "growth": 0.4},

    # 상태 임계치
    "thresholds": {
        "pre_fire":       {"smoke": 0.30, "fire": 0.25},
        "smoke_detected": {"smoke": 0.50},
        "fire_growing":   {"fire": 0.60, "hazard": 0.70},
        "call_119":       {"hazard": 0.85},
    },
}

# ---------- FastAPI 기본 설정 ----------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# 작업 관리
JOBS: Dict[str, Dict[str, Any]] = {}            # job_id -> { path, done, err }
EVENT_QUEUES: Dict[str, asyncio.Queue] = {}     # job_id -> SSE queue
JOB_FLAGS: Dict[str, Dict[str, Any]] = {}       # job_id -> {'paused':bool, 'stop':bool}


# ---------- 유틸 ----------
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
    q = EVENT_QUEUES[job_id]
    await q.put({"type": "hello", "job_id": job_id})
    while True:
        item = await q.get()
        yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n".encode("utf-8")
        if item.get("type") in ("end", "error"):
            break


# ---------- API ----------
@app.post("/upload")
async def upload_video(file: UploadFile, background_tasks: BackgroundTasks):
    """동영상 업로드 → 비동기 분석 시작 → job_id 반환"""
    job_id = uuid.uuid4().hex[:12]
    dest = UPLOADS / f"{job_id}.mp4"
    with open(dest, "wb") as f:
        while True:
            chunk = await file.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)

    JOBS[job_id] = {"path": str(dest), "done": False, "err": None}
    EVENT_QUEUES[job_id] = asyncio.Queue(maxsize=100)
    JOB_FLAGS[job_id] = {"paused": False, "stop": False}

    background_tasks.add_task(process_video_job, job_id, dest)
    return {"job_id": job_id, "video_url": f"/media/{dest.name}"}


@app.get("/events")
async def events(job_id: str):
    """SSE 스트림 엔드포인트"""
    if job_id not in EVENT_QUEUES:
        raise HTTPException(404, "unknown job_id")
    return StreamingResponse(sse_gen(job_id), media_type="text/event-stream")


@app.get("/media/{name}")
async def media(name: str):
    """업로드된 원본 영상 재생용 엔드포인트"""
    p = UPLOADS / name
    if not p.exists():
        raise HTTPException(404)
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


# ---------- 핵심 워커 ----------
async def process_video_job(job_id: str, path: Path):
    """
    - stride = round(src_fps / fps_target) 만큼 프레임을 건너뛰며 추론
    - EMA로 fire/smoke 점수 산출 → hazard 계산
    - 상태 결정 후 매 tick 이벤트에 box/점수/상태/시간을 push
    - pause 동안 타임라인 보정(start_wall += pause_duration) → 싱크 유지
    - 뒤처지면 grab()으로 프레임 스킵
    """
    q = EVENT_QUEUES[job_id]
    flags = JOB_FLAGS[job_id]
    try:
        fps, w, h, _ = video_meta(path)
        stride = max(1, round(fps / RULES["fps_target"]))
        alpha = RULES["ema_alpha"]
        w_smoke = RULES["weights"]["s_smoke"]
        w_fire = RULES["weights"]["s_fire"]
        w_growth = RULES["weights"]["growth"]

        cap = cv2.VideoCapture(str(path))
        start_wall = time.monotonic()  # '영상 t'와 매칭할 기준 시각
        frame_idx = -1
        S_ema = F_ema = prev_S = prev_F = 0.0
        state = "NORMAL"
        pause_started = None

        # 한 프레임 재생 간격(원본 FPS 기준)
        interval = 1.0 / fps if fps > 0 else 0.04

        while True:
            # 강제 중지
            if flags.get("stop"):
                break

            # 일시정지 처리 (resume 시 벽시계 보정으로 싱크 유지)
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

            # 프레임 샘플링(속도↑)
            if frame_idx % stride != 0:
                continue

            # --- YOLO 추론 ---
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
            if res.boxes is not None and res.boxes.cls is not None:
                xyxy = res.boxes.xyxy.cpu().tolist()
                clss = res.boxes.cls.cpu().int().tolist()
                confs = res.boxes.conf.cpu().tolist()
                for (x1, y1, x2, y2), c, cf in zip(xyxy, clss, confs):
                    if c in (0, 1):  # 0:Fire, 1:Smoke
                        boxes_out.append(
                            {
                                "x1": x1,
                                "y1": y1,
                                "x2": x2,
                                "y2": y2,
                                "cls": int(c),
                                "conf": round(float(cf), 3),
                            }
                        )
                        if c == 0:
                            fire_raw = max(fire_raw, float(cf))
                        if c == 1:
                            smoke_raw = max(smoke_raw, float(cf))

            # EMA & hazard
            F_ema = alpha * fire_raw + (1 - alpha) * F_ema
            S_ema = alpha * smoke_raw + (1 - alpha) * S_ema
            growth = max(0.0, S_ema - prev_S) + max(0.0, F_ema - prev_F)
            H = max(w_smoke * S_ema, w_fire * F_ema) + w_growth * growth
            prev_S, prev_F = S_ema, F_ema

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
            await q.put(
                {
                    "type": "tick",
                    "job_id": job_id,
                    "t": t_video,
                    "state": state,
                    "scores": {
                        "fire": round(F_ema, 3),
                        "smoke": round(S_ema, 3),
                        "hazard": round(H, 3),
                    },
                    "img_w": w,
                    "img_h": h,
                    "boxes": boxes_out,
                }
            )

            # 재생 속도 맞추기(늦으면 grab()으로 따라잡기)
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
        await q.put({"type": "end", "job_id": job_id})
        JOBS[job_id]["done"] = True

    except Exception as e:
        JOBS[job_id]["err"] = str(e)
        await q.put({"type": "error", "job_id": job_id, "error": str(e)})
    finally:
        JOB_FLAGS.pop(job_id, None)


# ---------- 정적 서빙 ----------
app.mount("/ui", StaticFiles(directory=str(ROOT / "frontend"), html=True), name="ui")


@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")
