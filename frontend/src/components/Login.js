import React, { useState } from 'react';
import './Login.css';

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    // 간단한 하드코딩된 인증 (실제 프로덕션에서는 백엔드 API 사용)
    if (username === 'admin' && password === 'safety119') {
      localStorage.setItem('user', JSON.stringify({ username: 'admin', role: 'admin' }));
      onLogin({ username: 'admin', role: 'admin' });
    } else if (username === 'operator' && password === 'fire2024') {
      localStorage.setItem('user', JSON.stringify({ username: 'operator', role: 'operator' }));
      onLogin({ username: 'operator', role: 'operator' });
    } else {
      setError('아이디 또는 비밀번호가 잘못되었습니다.');
    }

    setIsLoading(false);
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h1>🚨 EMERGENCY</h1>
          <p>안전 감지 자동화 119</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">아이디</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              placeholder="사용자 ID를 입력하세요"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">비밀번호</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="비밀번호를 입력하세요"
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button
            type="submit"
            className="login-button"
            disabled={isLoading}
          >
            {isLoading ? '로그인 중...' : '로그인'}
          </button>
        </form>

        <div className="login-info">
          <h3>데모 계정</h3>
          <p><strong>관리자:</strong> admin / safety119</p>
          <p><strong>운영자:</strong> operator / fire2024</p>
        </div>
      </div>
    </div>
  );
};

export default Login;