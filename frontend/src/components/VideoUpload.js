// frontend/src/components/VideoUpload.js
import React, { useState, useRef } from 'react';
import './VideoUpload.css';

const VideoUpload = ({ onUploadSuccess, onUploadError, isProcessing }) => {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFile = (file) => {
    // 파일 타입 검증
    if (!file.type.startsWith('video/')) {
      onUploadError('비디오 파일만 업로드 가능합니다.');
      return;
    }

    // 파일 크기 검증 (100MB 제한)
    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
      onUploadError('파일 크기는 100MB 이하여야 합니다.');
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      onUploadError('파일을 선택해주세요.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // HTML 테스트와 동일하게 직접 localhost:8000으로 업로드
      console.log('🔥 업로드 시작 - 직접 localhost:8000 연결');
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      onUploadSuccess(result);
    } catch (error) {
      console.error('Upload error:', error);
      onUploadError(`업로드 실패: ${error.message}`);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="upload-container">
      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !selectedFile && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          disabled={isProcessing}
        />

        {!selectedFile ? (
          <div className="upload-prompt">
            <div className="upload-icon">📹</div>
            <h3>비디오 파일을 업로드하세요</h3>
            <p>드래그 앤 드롭하거나 클릭하여 파일을 선택하세요</p>
            <div className="upload-specs">
              <span>지원 형식: MP4, AVI, MOV, WMV</span>
              <span>최대 크기: 100MB</span>
            </div>
          </div>
        ) : (
          <div className="file-selected">
            <div className="file-icon">🎬</div>
            <div className="file-info">
              <h4>{selectedFile.name}</h4>
              <p>크기: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
              <p>타입: {selectedFile.type}</p>
            </div>
          </div>
        )}
      </div>

      {selectedFile && (
        <div className="upload-actions">
          <button
            className="btn-upload"
            onClick={handleUpload}
            disabled={isProcessing}
          >
            {isProcessing ? (
              <>
                <span className="spinner"></span>
                분석 중...
              </>
            ) : (
              '🔍 화재 감지 시작'
            )}
          </button>
          <button
            className="btn-reset"
            onClick={handleReset}
            disabled={isProcessing}
          >
            다시 선택
          </button>
        </div>
      )}

      <div className="upload-guidelines">
        <h4>📋 업로드 가이드라인</h4>
        <ul>
          <li>화재 또는 연기가 포함된 영상을 업로드하세요</li>
          <li>화면이 선명하고 흔들림이 적은 영상이 더 정확합니다</li>
          <li>실내 또는 실외 환경 모두 지원됩니다</li>
          <li>분석 시간은 영상 길이에 따라 다릅니다</li>
        </ul>
      </div>
    </div>
  );
};

export default VideoUpload;