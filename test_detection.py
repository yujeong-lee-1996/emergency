#!/usr/bin/env python3
"""
테스트용 화재 감지 스크립트
"""
import cv2
import numpy as np
from backend.detectors.vision import FireDetector

def test_image_detection():
    """간단한 이미지로 감지 테스트"""
    print("=== 화재 감지 테스트 ===")

    # 탐지기 초기화
    detector = FireDetector()

    # 웹캠에서 한 프레임 캡처하여 테스트
    cap = cv2.VideoCapture(0)  # 웹캠
    if cap.isOpened():
        ret, test_image = cap.read()
        cap.release()
        if ret:
            print("웹캠에서 프레임 캡처 성공")
        else:
            # 웹캠 실패 시 테스트 이미지 생성
            test_image = np.ones((480, 640, 3), dtype=np.uint8) * 127  # 회색 배경
            # 다양한 형태로 그려서 객체처럼 보이게
            cv2.circle(test_image, (320, 240), 50, (0, 255, 0), -1)  # 녹색 원
            cv2.rectangle(test_image, (100, 100), (200, 200), (255, 0, 0), -1)  # 파란색 사각형
            print("테스트 패턴 이미지 생성")
    else:
        # 웹캠 실패 시 테스트 이미지 생성
        test_image = np.ones((480, 640, 3), dtype=np.uint8) * 127  # 회색 배경
        cv2.circle(test_image, (320, 240), 50, (0, 255, 0), -1)  # 녹색 원
        cv2.rectangle(test_image, (100, 100), (200, 200), (255, 0, 0), -1)  # 파란색 사각형
        print("웹캠 사용 불가, 테스트 패턴 이미지 생성")

    # 이미지 저장해서 확인
    cv2.imwrite("test_frame.jpg", test_image)

    print(f"테스트 이미지 크기: {test_image.shape}")

    # 감지 실행
    try:
        result = detector.infer(test_image)
        print(f"\n=== 감지 결과 ===")
        print(f"Fire 점수: {result['fire_score']:.3f}")
        print(f"Smoke 점수: {result['smoke_score']:.3f}")
        print(f"Fire 박스 개수: {len(result['fire_boxes'])}")
        print(f"Smoke 박스 개수: {len(result['smoke_boxes'])}")
        print(f"Person 박스 개수: {len(result['person_boxes'])}")

        # 박스 상세 정보
        for i, box in enumerate(result['fire_boxes']):
            print(f"Fire 박스 {i+1}: {box['class_name']} ({box['confidence']:.3f})")

        for i, box in enumerate(result['smoke_boxes']):
            print(f"Smoke 박스 {i+1}: {box['class_name']} ({box['confidence']:.3f})")

    except Exception as e:
        print(f"감지 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_image_detection()