/**
 * Excel Database - Helper Functions
 * 유틸리티 헬퍼 함수들
 */

// 셀 값 가져오기 (테이블 정렬용)
function getCellValue(cell, column) {
    if (column === 'status') {
        const badge = cell.querySelector('.status-badge');
        return badge ? badge.textContent.trim() : '';
    } else if (column === 'payment_status') {
        const badge = cell.querySelector('.payment-badge');
        return badge ? badge.textContent.trim() : '';
    } else {
        let text = cell.textContent.trim();
        if (text === '-' || text === '') return '';
        return text;
    }
}

// 파일 다운로드
function downloadFile(s3Key, originalName) {
    console.log(`파일 다운로드 시도: ${s3Key} (${originalName})`);
    
    // 새로운 단순한 다운로드 엔드포인트 사용
    const downloadUrl = `/api/download-file/?file_key=${encodeURIComponent(s3Key)}`;
    
    // 직접 새 창에서 다운로드 (브라우저가 자동으로 다운로드 처리)
    window.open(downloadUrl, '_blank');
}

// 미디어 파일 길이 추출
function getMediaDuration(file) {
    return new Promise((resolve) => {
        const isAudio = file.type && file.type.startsWith('audio/');
        const isVideo = file.type && file.type.startsWith('video/');
        
        if (!isAudio && !isVideo) {
            resolve('00:00:00');
            return;
        }
        
        const media = isAudio ? new Audio() : document.createElement('video');
        const objectUrl = URL.createObjectURL(file);
        
        media.preload = 'metadata';
        
        media.onloadedmetadata = () => {
            URL.revokeObjectURL(objectUrl);
            const duration = media.duration;
            if (isNaN(duration) || !isFinite(duration)) {
                resolve('00:00:00');
                return;
            }
            const hours = Math.floor(duration / 3600);
            const minutes = Math.floor((duration % 3600) / 60);
            const seconds = Math.floor(duration % 60);
            const formatted = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            resolve(formatted);
        };
        
        media.onerror = () => {
            URL.revokeObjectURL(objectUrl);
            resolve('00:00:00');
        };
        
        media.src = objectUrl;
    });
}

// 편집 취소 (레거시 함수 - 현재 미사용)
function cancelEdit(container, editor, valueSpan) {
    editor.remove();
    valueSpan.style.display = '';
    container.querySelector('.edit-btn').style.display = '';
}

