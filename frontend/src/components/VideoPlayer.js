// frontend/src/components/VideoPlayer.js
import React, { useRef, useEffect, useState, useCallback } from 'react';
import './VideoPlayer.css';

const VideoPlayer = ({
  jobId,
  videoUrl,
  currentFrame = 0,
  scores = { fire: 0, smoke: 0, hazard: 0 },
  rawData = null,
  currentState = 'NORMAL',
  timestamp = null,
  currentData = null,
  onPlayPauseChange = () => {},
  onVideoReplay = () => {}
}) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [needsManualPlay, setNeedsManualPlay] = useState(false);

  // 영상 메타데이터 로드 및 자동 재생 처리
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
      // 메타데이터 로드 후 즉시 자동 재생 시도
      console.log('🎬 비디오 메타데이터 로드 완료, 자동 재생 시도');
      video.play().catch(error => {
        console.error('자동 재생 실패:', error);
        console.log('📌 사용자가 수동으로 재생 버튼을 눌러야 합니다');
        setNeedsManualPlay(true);
      });
    };

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };

    const handlePlay = () => {
      setIsPlaying(true);
      setNeedsManualPlay(false);
      onPlayPauseChange(true);

      // 영상이 처음부터 재생되는 경우 자동 재분석 트리거
      if (video.currentTime <= 1) {
        console.log('🎬 영상 처음부터 재생 - 자동 재분석 시작');
        onVideoReplay();
      }
    };
    const handlePause = () => {
      setIsPlaying(false);
      onPlayPauseChange(false);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      console.log('🏁 영상 재생 완료');
    };

    const handleSeeked = () => {
      console.log('⏭️ 영상 시간 변경:', video.currentTime);
    };

    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('ended', handleEnded);
    video.addEventListener('seeked', handleSeeked);

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('ended', handleEnded);
      video.removeEventListener('seeked', handleSeeked);
    };
  }, [videoUrl, onPlayPauseChange]);

  // letterbox 보정을 적용한 박스 그리기 함수
  const fitCanvasToVideo = useCallback(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    canvas.width = video.clientWidth;
    canvas.height = video.clientHeight;
  }, []);

  // HTML 테스트와 완전히 동일한 drawBoxes 함수
  const drawBoxes = useCallback((data) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;

    if (!canvas || !video || !data) return;

    const ctx = canvas.getContext('2d');

    // 캔버스를 비디오 크기에 맞춤
    canvas.width = video.clientWidth;
    canvas.height = video.clientHeight;

    const vw = data.img_w;
    const vh = data.img_h;
    const cw = canvas.width;
    const ch = canvas.height;

    console.log(`🎨 drawBoxes - 영상크기: ${vw}x${vh}, 캔버스: ${cw}x${ch}, 박스수: ${data.boxes ? data.boxes.length : 0}`);

    if (!data.boxes || data.boxes.length === 0) {
      ctx.clearRect(0, 0, cw, ch);
      return;
    }

    // letterbox 보정 계산 (HTML 테스트와 동일)
    const scale = Math.min(cw/vw, ch/vh);
    const dw = vw*scale;
    const dh = vh*scale;
    const ox = (cw - dw) / 2;
    const oy = (ch - dh) / 2;

    console.log(`📐 scale=${scale}, offset=(${ox}, ${oy})`);

    // 캔버스 초기화
    ctx.clearRect(0, 0, cw, ch);
    ctx.lineWidth = 2;
    ctx.font = '12px ui-monospace, monospace';

    // 박스 그리기 (HTML 테스트와 완전히 동일)
    data.boxes.forEach((b, index) => {
      console.log(`📦 박스 ${index}:`, b);

      const x1 = ox + b.x1*scale;
      const y1 = oy + b.y1*scale;
      const x2 = ox + b.x2*scale;
      const y2 = oy + b.y2*scale;

      // 색상 결정 (HTML 테스트와 동일)
      ctx.strokeStyle = b.cls===0 ? '#ef4444' : '#f59e0b'; // Fire/Smoke
      ctx.strokeRect(x1, y1, x2-x1, y2-y1);

      // 라벨 그리기 - EMA 점수만 표시
      const emaScore = b.cls === 0 ? data.scores.fire : data.scores.smoke;
      const label = `${b.cls===0?'Fire':'Smoke'} ${emaScore.toFixed(2)}`;
      const tw = ctx.measureText(label).width + 8;
      ctx.fillStyle = 'rgba(0,0,0,0.6)';
      ctx.fillRect(x1, y1-16, tw, 14);
      ctx.fillStyle = '#fff';
      ctx.fillText(label, x1+4, y1-4);

      console.log(`✅ 박스 ${index} 그리기 완료: ${label}`);
    });

    console.log(`🎨 총 ${data.boxes.length}개 박스 그리기 완료`);

  }, []);

  // 프레임 업데이트 시 캔버스 다시 그리기 (HTML 테스트와 동일)
  useEffect(() => {
    if (rawData && rawData.boxes && rawData.boxes.length > 0) {
      drawBoxes(rawData);
    } else {
      // 박스가 없으면 캔버스 클리어
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
  }, [rawData, drawBoxes]);

  // 윈도우 리사이즈 시 캔버스 업데이트 (HTML 테스트와 동일)
  useEffect(() => {
    const handleResize = () => {
      fitCanvasToVideo();
      if (rawData) {
        setTimeout(() => drawBoxes(rawData), 100);
      }
    };

    const video = videoRef.current;

    window.addEventListener('resize', handleResize);
    if (video) {
      video.addEventListener('loadedmetadata', fitCanvasToVideo);
    }

    return () => {
      window.removeEventListener('resize', handleResize);
      if (video) {
        video.removeEventListener('loadedmetadata', fitCanvasToVideo);
      }
    };
  }, [rawData, drawBoxes, fitCanvasToVideo]);

  const getStateColor = (state) => {
    switch (state) {
      case 'NORMAL': return '#00ff00';
      case 'PRE_FIRE': return '#ffff00';
      case 'SMOKE_DETECTED': return '#ff8800';
      case 'FIRE_GROWING': return '#ff4400';
      case 'CALL_119': return '#ff0000';
      default: return '#888888';
    }
  };

  const getStateText = (state) => {
    switch (state) {
      case 'NORMAL': return '🟢 정상';
      case 'PRE_FIRE': return '🟡 화재 전조';
      case 'SMOKE_DETECTED': return '🟠 연기 감지';
      case 'FIRE_GROWING': return '🔴 화재 확산';
      case 'CALL_119': return '🚨 119 호출';
      default: return '⚪ 분석 중...';
    }
  };

  const togglePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play();
    }
  };

  const handleSeek = (e) => {
    const video = videoRef.current;
    if (!video) return;

    const progressBar = e.currentTarget;
    const rect = progressBar.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    video.currentTime = pos * video.duration;
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
    }
  };

  const handleSpeedChange = (e) => {
    const newRate = parseFloat(e.target.value);
    setPlaybackRate(newRate);
    if (videoRef.current) {
      videoRef.current.playbackRate = newRate;
    }
  };

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  // 상태별 CSS 클래스 매핑
  const getStateClass = (state) => {
    switch (state) {
      case 'NORMAL': return 'state-normal';
      case 'PRE_FIRE': return 'state-prefire';
      case 'SMOKE_DETECTED': return 'state-smoke';
      case 'FIRE_GROWING': return 'state-fire';
      case 'CALL_119': return 'state-emergency';
      default: return 'state-normal';
    }
  };

  const isFireDetected = currentState === 'FIRE_GROWING' || currentState === 'CALL_119';

  return (
    <div className={`video-player ${getStateClass(currentState)}`}>
      {needsManualPlay && (
        <div className="manual-play-notice">
          <div className="notice-content">
            <span>🎬</span>
            <p>분석과 동기화를 위해 재생 버튼을 눌러주세요</p>
            <button
              onClick={() => {
                const video = videoRef.current;
                if (video) video.play();
              }}
              className="play-now-btn"
            >
              ▶️ 재생 시작
            </button>
          </div>
        </div>
      )}

      <div className={`video-container ${isFireDetected ? 'fire-detected' : ''}`}>
        <video
          ref={videoRef}
          src={videoUrl}
          className="video-element"
          onLoadedData={() => {
            fitCanvasToVideo();
            if (rawData) drawBoxes(rawData);
          }}
        />
        <canvas
          ref={canvasRef}
          className="detection-overlay"
        />
      </div>

      <div className="video-controls">
        <button
          className="play-pause-btn"
          onClick={togglePlayPause}
        >
          {isPlaying ? '⏸️' : '▶️'}
        </button>

        <div className="time-display">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>

        <div
          className="progress-bar"
          onClick={handleSeek}
        >
          <div
            className="progress-filled"
            style={{ width: `${(currentTime / duration) * 100}%` }}
          />
        </div>

        <div className="control-group">
          <label>속도:</label>
          <select value={playbackRate} onChange={handleSpeedChange}>
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="1.5">1.5x</option>
            <option value="2">2x</option>
          </select>
        </div>

        <div className="control-group">
          <label>볼륨:</label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={volume}
            onChange={handleVolumeChange}
            className="volume-slider"
          />
        </div>
      </div>

      {timestamp && (
        <div className="sync-info">
          <small>분석 시간: {new Date().toLocaleTimeString()}</small>
        </div>
      )}
    </div>
  );
};

export default VideoPlayer;