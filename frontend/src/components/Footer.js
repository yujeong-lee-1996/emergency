// frontend/src/components/Footer.js
import React from 'react';
import './Footer.css';

const Footer = () => {
  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-section">
          <h4>Emergency Detection System</h4>
          <p>AI 기반 실시간 안전 모니터링</p>
        </div>
        <div className="footer-section">
          <h4>연락처</h4>
          <p>긴급상황: 119</p>
          <p>기술지원: support@emergency.ai</p>
        </div>
        <div className="footer-section">
          <h4>시스템 정보</h4>
          <p>Version 1.0.0</p>
          <p>© 2024 Emergency AI Team</p>
        </div>
      </div>
      <div className="footer-bottom">
        <div className="tech-info">
          <span className="tech-badge">AI POWERED</span>
          <span className="tech-badge">REAL-TIME</span>
          <span className="tech-badge">24/7 MONITORING</span>
        </div>
      </div>
    </footer>
  );
};

export default Footer;