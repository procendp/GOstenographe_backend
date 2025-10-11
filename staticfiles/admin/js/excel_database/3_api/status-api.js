/**
 * Excel Database - Status API
 * 상태 변경 API 호출
 */

// 상태 변경 API 호출 - 알림 발송 제거
function changeStatus(requestId, newStatus, reason = '', statusType = 'request') {
    // API 엔드포인트 결정
    const endpoint = statusType === 'order' ? 
        `/api/requests/${requestId}/change_order_status/` : 
        `/api/requests/${requestId}/change_status/`;
    
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            status: newStatus,
            reason: reason,
            skip_notification: true  // 알림 발송 스킵
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // UI 업데이트 - status-cell 클래스로 찾기
            const statusCell = document.querySelector(`.status-cell[data-request-id="${requestId}"]`);
            if (!statusCell) {
                console.error('Cell not found for UI update:', requestId);
                showNotification('상태가 변경되었지만 UI 업데이트에 실패했습니다. 페이지를 새로고침하세요.', 'warning');
                return;
            }
            
            const badge = statusCell.querySelector('.status-badge');
            if (!badge) {
                console.error('Badge not found in cell');
                showNotification('상태가 변경되었지만 UI 업데이트에 실패했습니다. 페이지를 새로고침하세요.', 'warning');
                return;
            }
            
            // 상태 타입에 따라 적절한 상태 정보 선택
            const statusInfo = statusType === 'order' ? orderStatusInfo : requestStatusInfo;
            
            // 상태 정보가 있는지 확인
            if (!statusInfo[newStatus]) {
                console.error('Status info not found for:', newStatus);
                showNotification('상태가 변경되었지만 상태 정보를 찾을 수 없습니다.', 'warning');
                return;
            }
            
            badge.className = `status-badge status-${newStatus}`;
            badge.textContent = statusInfo[newStatus].name;
            // 배경색과 텍스트 색상 직접 설정
            badge.style.background = statusInfo[newStatus].color;
            badge.style.color = statusInfo[newStatus].textColor;
            statusCell.dataset.currentStatus = newStatus;
            
            // 성공 메시지 (알림 발송 메시지는 제거)
            showNotification('상태가 변경되었습니다.', 'success');
        } else {
            showNotification(data.error || '상태 변경에 실패했습니다.', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('상태 변경 중 오류가 발생했습니다.', 'error');
    });
}

