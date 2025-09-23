// frontend/src/components/Header.js
import React from 'react';
import './Header.css';

const Header = ({ user, onLogout }) => {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="brand-section">
          <div className="emergency-badge">
            <span className="badge-icon">🚨</span>
            <span className="badge-text">EMERGENCY</span>
          </div>
          <h1 className="main-title">안전 감지 자동화 119</h1>
          <p className="subtitle">AI 기반 실시간 화재 및 연기 감지 시스템</p>
        </div>
        <div className="status-indicators">
          <div className="system-status online">
            <span className="status-dot"></span>
            <span>시스템 정상</span>
          </div>
          {user && (
            <div className="user-info">
              <span className="user-name">👤 {user.username}</span>
              <span className="user-role">({user.role})</span>
              <button className="logout-button" onClick={onLogout}>
                로그아웃
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;