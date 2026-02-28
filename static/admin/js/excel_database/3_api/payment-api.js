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
            // UI 업데이트 - 동일 Order의 모든 Request 행에 반영
            const paymentCell = document.querySelector(`[data-request-id="${requestId}"][data-current-payment]`);
            const row = paymentCell ? paymentCell.closest('tr') : null;
            const orderId = row ? row.dataset.orderId : null;

            const updateBadge = (cell) => {
                if (!cell) return;
                const badge = cell.querySelector('.payment-badge');
                if (badge) {
                    badge.className = `payment-badge payment-${paymentStatus}`;
                    badge.textContent = paymentStatus ? '결제 완료' : '미결제';
                    badge.style.background = paymentStatus ? '#dcfce7' : '#fee2e2';
                    badge.style.color = paymentStatus ? '#166534' : '#991b1b';
                }
                cell.dataset.currentPayment = paymentStatus;
            };

            if (orderId) {
                document.querySelectorAll(`tr[data-order-id="${orderId}"]`).forEach(r => {
                    const cell = r.querySelector('.payment-cell[data-current-payment]');
                    updateBadge(cell);
                });
            } else {
                updateBadge(paymentCell);
            }

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

