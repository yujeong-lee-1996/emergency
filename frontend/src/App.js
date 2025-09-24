// frontend/src/App.js
import React, { useState, useRef, useEffect } from 'react';
import Header from './components/Header';
import Footer from './components/Footer';
import VideoUpload from './components/VideoUpload';
import VideoPlayer from './components/VideoPlayer';
import Timeline from './components/Timeline';
import StateIndicator from './components/StateIndicator';
import AlertLog from './components/AlertLog';
import Login from './components/Login';
import './App.css';

// 디버그 모드 설정
const DEBUG = false; // false로 설정하면 console 로그가 거의 출력되지 않음

function App() {
  const [user, setUser] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [currentData, setCurrentData] = useState({
    scores: { fire: 0, smoke: 0, hazard: 0 },
    detections: { fire: [], smoke: [], person: [] },
    state: 'NORMAL',
    timestamp: null,
    videoMeta: { width: 640, height: 480 }
  });
  const [events, setEvents] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [isPaused, setIsPaused] = useState(false);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    // 로그인 상태 확인
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    setUser(null);
    // 로그아웃 시 모든 상태 초기화
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setJobId(null);
    setVideoUrl(null);
    setCurrentData({
      scores: { fire: 0, smoke: 0, hazard: 0 },
      detections: { fire: [], smoke: [], person: [] },
      state: 'NORMAL',
      timestamp: null,
      videoMeta: { width: 640, height: 480 }
    });
    setEvents([]);
    setIsProcessing(false);
    setError(null);
  };

  const startSSEConnection = (id) => {
    // 기존 연결이 있으면 먼저 닫기
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const directUrl = `http://localhost:8000/events?job_id=${id}`;

    const eventSource = new EventSource(directUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = (event) => {
      if (DEBUG) console.log('SSE 연결 성공');
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'tick') {

          setCurrentData({
            scores: data.scores,
            rawData: data,  // 원본 데이터 저장
            state: data.state,
            timestamp: data.t,
            videoMeta: { width: data.img_w || 640, height: data.img_h || 480 }
          });


          // 이벤트 히스토리에 추가
          setEvents(prev => [...prev, {
            timestamp: data.t,
            state: data.state,
            scores: data.scores,
            frame: prev.length
          }]);

        } else if (data.type === 'end') {
          if (DEBUG) console.log('영상 분석 완료');
          setIsProcessing(false);
          // SSE 연결 정상 종료
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }
        } else if (data.type === 'error') {
          if (DEBUG) console.error('처리 오류:', data.error);
          setError(data.error);
          setIsProcessing(false);
        } else if (data.type === 'heartbeat') {
          // 연결 유지 확인 - 조용히 처리
          if (DEBUG) console.log('서버 연결 유지 확인');
        }
      } catch (err) {
        if (DEBUG) console.error('SSE 이벤트 파싱 오류:', err);
      }
    };

    eventSource.onerror = (event) => {
      console.log('SSE 연결 상태:', eventSource.readyState);

      // readyState가 2(CLOSED)인 경우는 정상 종료일 수 있음
      if (eventSource.readyState === 2) {
        if (DEBUG) console.log('SSE 연결 정상 종료');
        return;
      }

      // 실제 에러인 경우만 에러 표시
      if (eventSource.readyState === 0) {
        console.error('SSE 연결 오류 발생');
        setError('서버 연결이 끊어졌습니다. 재분석을 시도해주세요.');
        setIsProcessing(false);

        // 연결 정리
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      }
    };
  };

  const handleUploadSuccess = (result) => {
    if (DEBUG) console.log('업로드 성공:', result.job_id);

    setJobId(result.job_id);
    setVideoUrl(`http://localhost:8000${result.video_url}`);
    setIsProcessing(true);
    setError(null);
    setEvents([]);

    // SSE 연결 시작
    startSSEConnection(result.job_id);
  };

  const handleUploadError = (errorMessage) => {
    setError(`업로드 실패: ${errorMessage}`);
    setIsProcessing(false);
  };

  const handleReset = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setJobId(null);
    setVideoUrl(null);
    setCurrentData({
      scores: { fire: 0, smoke: 0, hazard: 0 },
      detections: { fire: [], smoke: [], person: [] },
      state: 'NORMAL',
      timestamp: null
    });
    setEvents([]);
    setIsProcessing(false);
    setError(null);
  };

  const handleRestart = async () => {
    if (!jobId) {
      setError('분석할 영상이 없습니다.');
      return;
    }

    try {
      if (DEBUG) console.log('재분석 시작:', jobId);

      // API 상태 먼저 확인
      try {
        const testResponse = await fetch('http://localhost:8000/test');
        console.log('백엔드 상태 확인:', testResponse.status);
        if (testResponse.ok) {
          const testData = await testResponse.json();
          console.log('사용 가능한 jobs:', testData.jobs);
        }
      } catch (testError) {
        console.error('백엔드 연결 테스트 실패:', testError);
      }

      const response = await fetch(`http://localhost:8000/jobs/${jobId}/restart`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.text();
        console.error('재분석 API 응답:', response.status, errorData);
        console.error('요청 URL:', `http://localhost:8000/jobs/${jobId}/restart`);
        throw new Error(`HTTP ${response.status}: ${errorData}`);
      }

      const result = await response.json();
      if (DEBUG) console.log('재분석 응답:', result);

      // 기존 연결 완전 정리
      if (eventSourceRef.current) {
        console.log('기존 SSE 연결 정리 중...');
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // 상태 초기화
      setCurrentData({
        scores: { fire: 0, smoke: 0, hazard: 0 },
        detections: { fire: [], smoke: [], person: [] },
        state: 'NORMAL',
        timestamp: null,
        videoMeta: { width: 640, height: 480 }
      });
      setEvents([]);
      setIsProcessing(true);
      setError(null);

      // 영상을 처음부터 재생하도록 설정
      const videoElement = document.querySelector('video');
      if (videoElement) {
        videoElement.currentTime = 0;
        videoElement.play().catch(console.error);
      }

      // 잠시 대기 후 새 SSE 연결 시작 (더 안전하게)
      setTimeout(() => {
        console.log('새 SSE 연결 시작...');
        startSSEConnection(jobId);
      }, 1000);

    } catch (error) {
      console.error('재분석 오류:', error);
      console.error('에러 상세:', error.stack);

      if (error.message.includes('404')) {
        setError('재분석 실패: 백엔드 서버를 재시작해주세요. (python main.py)');
      } else {
        setError(`재분석 실패: ${error.message}`);
      }
      setIsProcessing(false);
    }
  };

  // 영상 재생/일시정지 제어
  const handleVideoPlayPause = async (isPlaying) => {
    if (!jobId) return;

    try {
      const response = await fetch(`http://localhost:8000/jobs/${jobId}/control`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ cmd: isPlaying ? 'resume' : 'pause' })
      });

      if (response.ok) {
        setIsPaused(!isPlaying);
        if (DEBUG) console.log(`분석 ${isPlaying ? '재개' : '일시정지'}`);
      }
    } catch (error) {
      if (DEBUG) console.error('영상 제어 오류:', error);
    }
  };

  // 로그인하지 않은 경우 로그인 화면 표시
  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="App">
      <Header user={user} onLogout={handleLogout} />

      <main className="main-content">
        <div className="container">
          {error && (
            <div className="error-banner">
              <div className="error-content">
                <span className="error-icon">⚠️</span>
                <span className="error-text">{error}</span>
                <button
                  className="error-close"
                  onClick={() => setError(null)}
                >
                  ✕
                </button>
              </div>
            </div>
          )}

          {!jobId ? (
            <VideoUpload
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
              isProcessing={isProcessing}
            />
          ) : (
            <div className="analysis-dashboard">
              <div className="dashboard-header">
                <button onClick={handleReset} className="reset-button">
                  🔄 새 분석 시작
                </button>
                <button onClick={handleRestart} className="restart-button" disabled={!jobId || isProcessing}>
                  🔁 재분석
                </button>
                {isProcessing && (
                  <div className="processing-status">
                    <div className="processing-spinner"></div>
                    <span>분석 진행 중...</span>
                  </div>
                )}
              </div>

              {videoUrl && (
                <div className="video-dashboard-container">
                  <div className="video-section">
                    <VideoPlayer
                      jobId={jobId}
                      videoUrl={videoUrl}
                      currentFrame={events.length}
                      scores={currentData.scores}
                      rawData={currentData.rawData}
                      currentState={currentData.state}
                      timestamp={currentData.timestamp}
                      currentData={currentData}
                      onPlayPauseChange={handleVideoPlayPause}
                      onVideoReplay={handleRestart}
                    />
                  </div>

                  <div className="right-panel">
                    <StateIndicator
                      currentState={currentData.state}
                      scores={currentData.scores}
                      jobId={jobId}
                      timestamp={currentData.timestamp}
                    />

                    <AlertLog
                      currentState={currentData.state}
                      scores={currentData.scores}
                      timestamp={currentData.timestamp}
                    />
                  </div>
                </div>
              )}

              {events.length > 0 && (
                <Timeline
                  events={events}
                  currentFrame={events.length - 1}
                />
              )}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default App;