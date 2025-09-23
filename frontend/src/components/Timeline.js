// frontend/src/components/Timeline.js
import React from 'react';
import './Timeline.css';

const Timeline = ({ events, currentFrame }) => {
  if (!events || events.length === 0) {
    return (
      <div className="timeline-container">
        <h3>분석 타임라인</h3>
        <div className="timeline-empty">
          <p>아직 분석 데이터가 없습니다.</p>
        </div>
      </div>
    );
  }

  const getStateColor = (state) => {
    switch (state) {
      case 'NORMAL': return '#28a745';
      case 'PRE_FIRE': return '#ffc107';
      case 'SMOKE_DETECTED': return '#fd7e14';
      case 'FIRE_GROWING': return '#dc3545';
      case 'CALL_119': return '#ff3333';
      default: return '#6c757d';
    }
  };

  const getStateText = (state) => {
    switch (state) {
      case 'NORMAL': return '정상';
      case 'PRE_FIRE': return '화재 전조';
      case 'SMOKE_DETECTED': return '연기 감지';
      case 'FIRE_GROWING': return '화재 확산';
      case 'CALL_119': return '119 호출';
      default: return '분석 중';
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className="timeline-container">
      <h3>분석 타임라인</h3>
      <div className="timeline-stats">
        <div className="stat-item">
          <span className="stat-label">총 프레임:</span>
          <span className="stat-value">{events.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">현재 프레임:</span>
          <span className="stat-value">{currentFrame + 1}</span>
        </div>
      </div>

      <div className="timeline">
        <div className="timeline-header">
          <span>시간</span>
          <span>상태</span>
          <span>화재</span>
          <span>연기</span>
        </div>

        <div className="timeline-events">
          {events.slice(-10).map((event, index) => (
            <div
              key={index}
              className={`timeline-event ${index === events.length - 1 ? 'current' : ''}`}
            >
              <div className="event-time">
                {formatTime(event.timestamp)}
              </div>

              <div className="event-state">
                <span
                  className="state-indicator"
                  style={{ backgroundColor: getStateColor(event.state) }}
                >
                  {getStateText(event.state)}
                </span>
              </div>

              <div className="event-score fire">
                {(event.scores.fire * 100).toFixed(1)}%
              </div>

              <div className="event-score smoke">
                {(event.scores.smoke * 100).toFixed(1)}%
              </div>
            </div>
          ))}
        </div>

        {events.length > 10 && (
          <div className="timeline-more">
            <small>최근 10개 이벤트만 표시됩니다.</small>
          </div>
        )}
      </div>

      <div className="timeline-summary">
        <h4>요약 통계</h4>
        <div className="summary-grid">
          <div className="summary-item">
            <span>최대 화재 점수:</span>
            <strong>{Math.max(...events.map(e => e.scores.fire * 100)).toFixed(1)}%</strong>
          </div>
          <div className="summary-item">
            <span>최대 연기 점수:</span>
            <strong>{Math.max(...events.map(e => e.scores.smoke * 100)).toFixed(1)}%</strong>
          </div>
          <div className="summary-item">
            <span>위험 상태 횟수:</span>
            <strong>{events.filter(e => e.state !== 'NORMAL').length}</strong>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Timeline;