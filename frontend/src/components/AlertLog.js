// frontend/src/components/AlertLog.js
import React, { useState, useEffect } from 'react';
import './AlertLog.css';

const AlertLog = ({ currentState, scores, timestamp }) => {
  const [logs, setLogs] = useState([]);
  const [lastState, setLastState] = useState('NORMAL');

  useEffect(() => {
    // 상태가 변경되었을 때만 로그 추가
    if (currentState !== lastState && currentState !== 'NORMAL') {
      const newLog = {
        id: Date.now(),
        timestamp: new Date(),
        state: currentState,
        scores: { ...scores },
        videoTime: timestamp || 0
      };

      setLogs(prev => [newLog, ...prev.slice(0, 49)]); // 최대 50개 로그 유지
    }

    setLastState(currentState);
  }, [currentState, scores, timestamp, lastState]);

  const getStateInfo = (state) => {
    switch (state) {
      case 'PRE_FIRE':
        return {
          icon: '🟡',
          text: '화재 전조',
          color: '#ffc107',
          priority: 'warning'
        };
      case 'SMOKE_DETECTED':
        return {
          icon: '🟠',
          text: '연기 감지',
          color: '#fd7e14',
          priority: 'caution'
        };
      case 'FIRE_GROWING':
        return {
          icon: '🔴',
          text: '화재 확산',
          color: '#dc3545',
          priority: 'danger'
        };
      case 'CALL_119':
        return {
          icon: '🚨',
          text: '119 호출',
          color: '#ff3333',
          priority: 'emergency'
        };
      default:
        return {
          icon: '⚪',
          text: '알 수 없음',
          color: '#6c757d',
          priority: 'neutral'
        };
    }
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatVideoTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const clearLogs = () => {
    setLogs([]);
  };

  return (
    <div className="alert-log-container">
      <div className="alert-log-header">
        <div className="log-title">
          <span className="log-icon">📋</span>
          <h3>알람 로그</h3>
        </div>
        <div className="log-controls">
          <span className="log-count">{logs.length}개</span>
          {logs.length > 0 && (
            <button
              className="clear-btn"
              onClick={clearLogs}
              title="로그 초기화"
            >
              🗑️
            </button>
          )}
        </div>
      </div>

      <div className="alert-log-content">
        {logs.length === 0 ? (
          <div className="no-logs">
            <span className="no-logs-icon">📝</span>
            <p>아직 알람이 없습니다</p>
          </div>
        ) : (
          <div className="log-list">
            {logs.map((log) => {
              const stateInfo = getStateInfo(log.state);
              return (
                <div
                  key={log.id}
                  className={`log-item ${stateInfo.priority}`}
                >
                  <div className="log-icon">
                    <span>{stateInfo.icon}</span>
                  </div>

                  <div className="log-content">
                    <div className="log-main">
                      <span className="log-state">{stateInfo.text}</span>
                      <span className="log-time">
                        {formatTime(log.timestamp)} (영상 {formatVideoTime(log.videoTime)})
                      </span>
                    </div>

                    <div className="log-scores">
                      <span className="log-score fire">
                        🔥 {(log.scores.fire * 100).toFixed(1)}%
                      </span>
                      <span className="log-score smoke">
                        💨 {(log.scores.smoke * 100).toFixed(1)}%
                      </span>
                      <span className="log-score hazard">
                        ⚠️ {(log.scores.hazard * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertLog;