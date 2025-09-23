#!/usr/bin/env python3
"""
빠른 화재 감지 테스트 스크립트
"""
import sys
import os
sys.path.append('backend')

from backend.detectors.vision import FireDetector
import cv2
import asyncio

async def test_fire_detection():
    print("🔥 화재 감지 시스템 테스트 시작...")

    try:
        # FireDetector 초기화
        detector = FireDetector()
        print("✅ FireDetector 초기화 성공")

        # 업로드된 비디오 파일 확인
        video_files = [
            "D:/emergency/backend/media/uploads/077d6393-ef97-43de-89de-140089a65b2d_fire2.mp4",
            "D:/emergency/backend/media/uploads/2a575fb3-c6fa-4aed-b72d-638597fbf647_fire1.mp4",
        ]

        for video_file in video_files:
            if os.path.exists(video_file):
                print(f"📹 테스트 비디오: {os.path.basename(video_file)}")

                # 비디오 정보 확인
                cap = cv2.VideoCapture(video_file)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration = frame_count / fps if fps > 0 else 0
                    print(f"  - FPS: {fps}, 총 프레임: {frame_count}, 길이: {duration:.1f}초")

                    # 첫 5 프레임만 테스트
                    test_frames = 0
                    max_test_frames = 5

                    async for frame_data in detector.process_video(video_file):
                        test_frames += 1
                        scores = frame_data['scores']
                        boxes = frame_data['boxes']

                        print(f"  프레임 {frame_data['frame_number']:03d}: "
                              f"화재={scores['fire']:.3f}, 연기={scores['smoke']:.3f} | "
                              f"박스: 화재={len(boxes['fire'])}개, 연기={len(boxes['smoke'])}개")

                        # 감지된 박스가 있으면 상세 정보 출력
                        if len(boxes['fire']) > 0:
                            for i, box in enumerate(boxes['fire']):
                                print(f"    🔥 화재 박스 #{i+1}: {box['class_name']} "
                                      f"(confidence: {box['confidence']:.2f})")

                        if len(boxes['smoke']) > 0:
                            for i, box in enumerate(boxes['smoke']):
                                print(f"    💨 연기 박스 #{i+1}: {box['class_name']} "
                                      f"(confidence: {box['confidence']:.2f})")

                        if test_frames >= max_test_frames:
                            print(f"  ✅ {max_test_frames}프레임 테스트 완료")
                            break

                    cap.release()
                    print("")
                    break  # 첫 번째 비디오만 테스트
                else:
                    print(f"  ❌ 비디오를 열 수 없음: {video_file}")
            else:
                print(f"  ❌ 파일이 존재하지 않음: {video_file}")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fire_detection())