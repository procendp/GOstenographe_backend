/**
 * Excel Database - Payment API
 * 결제 상태 변경 API 호출
 */

// 결제 상태 변경 API 호출
function changePayment(requestId, paymentStatus) {
    fetch(`/api/requests/${requestId}/change_payment/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            payment_status: paymentStatus
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // UI 업데이트
            const paymentCell = document.querySelector(`[data-request-id="${requestId}"][data-current-payment]`);
            const badge = paymentCell.querySelector('.payment-badge');
            badge.className = `payment-badge payment-${paymentStatus}`;
            badge.textContent = paymentStatus ? '결제 완료' : '미결제';
            // 배경색과 텍스트 색상 직접 설정
            badge.style.background = paymentStatus ? '#dcfce7' : '#fee2e2';
            badge.style.color = paymentStatus ? '#166534' : '#991b1b';
            paymentCell.dataset.currentPayment = paymentStatus;
            
            // 성공 메시지
            showNotification('결제 상태가 변경되었습니다.', 'success');
        } else {
            showNotification(data.error || '결제 상태 변경에 실패했습니다.', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('결제 상태 변경 중 오류가 발생했습니다.', 'error');
    });
}

