# create_test_video.py
import cv2
import numpy as np
import os

def create_simple_test_video():
    """간단한 테스트 비디오 생성"""
    os.makedirs("./media/uploads", exist_ok=True)
    video_path = "./media/uploads/fire2.mp4"

    # 비디오 설정
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 10
    duration = 20  # 20초
    width, height = 640, 480

    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    print(f"테스트 비디오 생성 중: {video_path}")

    for frame_num in range(fps * duration):
        # 기본 배경 (어두운 회색)
        frame = np.full((height, width, 3), (50, 50, 50), dtype=np.uint8)

        # 시간 진행에 따른 화재 시뮬레이션
        progress = frame_num / (fps * duration)

        if progress > 0.2:  # 20% 지점부터 화재 시작
            # 화재 영역 크기 증가
            fire_intensity = min((progress - 0.2) * 2, 1.0)
            fire_size = int(50 + fire_intensity * 100)

            # 화재 색상 (주황-빨강)
            center_x, center_y = width // 2, height // 2

            # 불규칙한 화재 모양
            for i in range(5):
                offset_x = np.random.randint(-30, 31)
                offset_y = np.random.randint(-30, 31)
                radius = int(fire_size * (0.5 + np.random.random() * 0.5))

                # 불색 (BGR)
                color = (0, int(100 + 155 * fire_intensity), int(200 + 55 * fire_intensity))
                cv2.circle(frame, (center_x + offset_x, center_y + offset_y), radius, color, -1)

        if progress > 0.4:  # 40% 지점부터 연기 추가
            # 연기 영역
            smoke_intensity = min((progress - 0.4) * 1.5, 1.0)
            smoke_color = int(100 + 50 * smoke_intensity)

            # 연기 영역 (상단)
            smoke_area = frame[50:200, 150:500]
            smoke_overlay = np.full_like(smoke_area, (smoke_color, smoke_color, smoke_color))
            cv2.addWeighted(smoke_area, 1-smoke_intensity*0.6, smoke_overlay, smoke_intensity*0.6, 0, smoke_area)

        # 프레임 정보 표시
        cv2.putText(frame, f"Frame: {frame_num:03d} Progress: {progress:.2f}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        out.write(frame)

    out.release()
    print(f"테스트 비디오 생성 완료: {video_path}")
    return video_path

if __name__ == "__main__":
    create_simple_test_video()