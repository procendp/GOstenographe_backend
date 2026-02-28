// 파일 탭 관련 변수들
let activeFileTabIndex = 0;
let fileTabsData = [];


// 상태 정보 정의
// Order 상태 정보
const orderStatusInfo = {
    'received': { name: '접수됨', color: '#f0f9ff', textColor: '#0c4a6e' },
    'payment_completed': { name: '결제완료', color: '#fef3c7', textColor: '#92400e' },
    'sent': { name: '발송완료', color: '#dcfce7', textColor: '#166534' },
    'impossible': { name: '작업불가', color: '#fce7f3', textColor: '#9f1239' },
    'cancelled': { name: '취소됨', color: '#fee2e2', textColor: '#991b1b' },
    'refunded': { name: '환불완료', color: '#f3f4f6', textColor: '#374151' }
};

// Request 상태 정보
const requestStatusInfo = {
    'received': { name: '접수됨', color: '#f0f9ff', textColor: '#0c4a6e' },
    'in_progress': { name: '작업중', color: '#dbeafe', textColor: '#1e40af' },
    'work_completed': { name: '작업완료', color: '#e0e7ff', textColor: '#3730a3' },
    'sent': { name: '발송완료', color: '#dcfce7', textColor: '#166534' },
    'impossible': { name: '작업불가', color: '#fce7f3', textColor: '#9f1239' },
    'cancelled': { name: '취소됨', color: '#fee2e2', textColor: '#991b1b' }
};

// 상태 전환 규칙
const allowedTransitions = {
    'received': ['payment_completed', 'impossible', 'cancelled'],
    'payment_completed': ['in_progress', 'cancelled'],
    'in_progress': ['work_completed', 'impossible'],
    'work_completed': ['sent'],
    'sent': [],
    'impossible': ['cancelled', 'refunded'],
    'cancelled': ['refunded'],
    'refunded': []
};

// 상태 변경 함수
function editStatus(requestId, initialStatus, statusType = 'request') {
    console.log('[DEBUG] editStatus called:', requestId, initialStatus, statusType);
    
    // 모든 상태 셀 확인 (디버깅)
    const allStatusCells = document.querySelectorAll('.status-cell');
    console.log('[DEBUG] Total status cells found:', allStatusCells.length);
    allStatusCells.forEach(c => {
        console.log('[DEBUG] Cell data-request-id:', c.getAttribute('data-request-id'));
    });
    
    // 상태 셀 찾기
    const statusCell = document.querySelector(`.status-cell[data-request-id="${requestId}"]`);
    console.log('[DEBUG] Looking for requestId:', requestId);
    console.log('[DEBUG] Found cell:', statusCell);
    const container = statusCell ? statusCell.querySelector('.status-container') : null;
    console.log('[DEBUG] Found container:', container);
    
    if (!statusCell || !container) {
        console.error('[ERROR] Cell or container not found for request ID:', requestId);
        return;
    }
    
    // 현재 상태를 셀의 data attribute에서 동적으로 가져오기
    const currentStatus = statusCell.dataset.currentStatus || initialStatus;
    console.log('[DEBUG] Current status:', currentStatus);
    
    // 이미 드롭다운이 열려있으면 닫기
    const existingDropdown = container.querySelector('.status-dropdown');
    if (existingDropdown) {
        existingDropdown.remove();
        return;
    }

    // 다른 열린 드롭다운 닫기
    document.querySelectorAll('.status-dropdown').forEach(d => d.remove());
    
    // 드롭다운 생성
    const dropdown = document.createElement('div');
    dropdown.className = 'status-dropdown';
    
    // 버튼의 위치 계산
    const buttonRect = container.querySelector('.status-edit-btn').getBoundingClientRect();
    dropdown.style.left = buttonRect.left + 'px';
    dropdown.style.top = (buttonRect.bottom + 4) + 'px';
    
    // 상태 타입에 따라 적절한 상태 정보 선택
    const statusInfo = statusType === 'order' ? orderStatusInfo : requestStatusInfo;
    console.log('[DEBUG] Status type:', statusType, 'StatusInfo:', statusInfo);
    
    // 허용된 상태만 표시
    for (const [key, info] of Object.entries(statusInfo)) {
        const item = document.createElement('div');
        item.className = 'status-dropdown-item';
        
        const isAllowed = true; // 모든 상태 선택 가능
        
        const dot = document.createElement('span');
        dot.className = 'status-dot';
        dot.style.background = info.color;
        dot.style.border = `2px solid ${info.textColor}`;
        
        const text = document.createElement('span');
        text.textContent = info.name;
        if (key === currentStatus) {
            text.innerHTML += ' (현재)';
            text.style.fontWeight = '600';
        }
        
        item.appendChild(dot);
        item.appendChild(text);
        
        if (isAllowed) {
            item.onclick = () => {
                // 상태 변경 (알림 없음) - 상태 타입 전달
                changeStatus(requestId, key, '', statusType);
                dropdown.remove();
            };
        }
        
        dropdown.appendChild(item);
    }
    
    // 드롭다운을 body에 추가 (셀 밖으로 나오도록)
    document.body.appendChild(dropdown);
    
    // 외부 클릭시 닫기
    setTimeout(() => {
        document.addEventListener('click', function closeStatusDropdown(e) {
            if (!container.contains(e.target)) {
                dropdown.remove();
                document.removeEventListener('click', closeStatusDropdown);
            }
        });
    }, 100);
}

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

// 결제 상태 변경 함수
function editPayment(requestId, currentPayment) {
    const paymentCell = document.querySelector(`[data-request-id="${requestId}"][data-current-payment]`);
    const container = paymentCell.querySelector('.payment-container');
    
    // 현재 결제 상태를 셀의 data attribute에서 동적으로 가져오기
    const currentPaymentStatus = paymentCell.dataset.currentPayment === 'True';
    
    // 이미 드롭다운이 열려있으면 닫기
    const existingDropdown = container.querySelector('.payment-dropdown');
    if (existingDropdown) {
        existingDropdown.remove();
        return;
    }

    // 다른 열린 드롭다운 닫기
    document.querySelectorAll('.payment-dropdown').forEach(d => d.remove());
    document.querySelectorAll('.status-dropdown').forEach(d => d.remove());
    
    // 드롭다운 생성
    const dropdown = document.createElement('div');
    dropdown.className = 'payment-dropdown';
    
    // 버튼의 위치 계산
    const buttonRect = container.querySelector('.payment-edit-btn').getBoundingClientRect();
    dropdown.style.left = buttonRect.left + 'px';
    dropdown.style.top = (buttonRect.bottom + 4) + 'px';
    
    // 결제 상태 옵션
    const paymentOptions = [
        { value: false, name: '미결제', color: '#fee2e2', textColor: '#991b1b' },
        { value: true, name: '결제 완료', color: '#dcfce7', textColor: '#166534' }
    ];
    
    // 모든 결제 상태 표시
    for (const option of paymentOptions) {
        const item = document.createElement('div');
        item.className = 'payment-dropdown-item';
        
        const dot = document.createElement('span');
        dot.className = 'status-dot';
        dot.style.background = option.color;
        dot.style.border = `2px solid ${option.textColor}`;
        
        const text = document.createElement('span');
        text.textContent = option.name;
        if (option.value === currentPaymentStatus) {
            text.innerHTML += ' (현재)';
            text.style.fontWeight = '600';
        }
        
        item.appendChild(dot);
        item.appendChild(text);
        
        item.onclick = () => {
            changePayment(requestId, option.value);
            dropdown.remove();
        };
        
        dropdown.appendChild(item);
    }
    
    // 드롭다운을 body에 추가 (셀 밖으로 나오도록)
    document.body.appendChild(dropdown);
    
    // 외부 클릭시 닫기
    setTimeout(() => {
        document.addEventListener('click', function closePaymentDropdown(e) {
            if (!container.contains(e.target)) {
                dropdown.remove();
                document.removeEventListener('click', closePaymentDropdown);
            }
        });
    }, 100);
}

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

// CSRF 토큰 가져오기
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 알림 표시
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 6px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// 파일 다운로드 함수
function downloadFile(s3Key, originalName) {
    console.log(`파일 다운로드 시도: ${s3Key} (${originalName})`);
    
    // 새로운 단순한 다운로드 엔드포인트 사용
    const downloadUrl = `/api/download-file/?file_key=${encodeURIComponent(s3Key)}`;
    
    // 직접 새 창에서 다운로드 (브라우저가 자동으로 다운로드 처리)
    window.open(downloadUrl, '_blank');
}

// 테이블 정렬 기능
let currentSort = { column: null, direction: null };

function sortTable(column) {
    const table = document.getElementById('excel-table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr')).filter(row => row.querySelectorAll('td').length > 1);
    
    // 정렬 방향 결정
    let direction = 'asc';
    if (currentSort.column === column) {
        direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    }
    
    // 헤더 스타일 업데이트
    document.querySelectorAll('.sortable-th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    const currentTh = document.querySelector(`[data-sort="${column}"]`);
    currentTh.classList.add(`sort-${direction}`);
    
    // Order ID List (셀 병합)인지 확인
    const hasMergedCells = tbody.querySelector('.merged-cell');
    
    if (hasMergedCells) {
        // Order ID List: 그룹 기준으로 정렬
        sortOrderIDList(tbody, rows, column, direction);
    } else {
        // Request ID List: 일반 행 정렬
        sortRegularTable(tbody, rows, column, direction);
    }
    
    // 현재 정렬 상태 저장
    currentSort = { column, direction };
}

function sortOrderIDList(tbody, rows, column, direction) {
    // Order ID별로 그룹화
    const groups = new Map();
    
    rows.forEach(row => {
        const rowOrderId = row.getAttribute('data-order-id');
        if (!groups.has(rowOrderId)) {
            groups.set(rowOrderId, []);
        }
        groups.get(rowOrderId).push(row);
    });
    
    // 컬럼 인덱스 찾기
    const headers = Array.from(tbody.closest('table').querySelectorAll('th'));
    const columnIndex = headers.findIndex(th => th.getAttribute('data-sort') === column);
    
    if (columnIndex === -1) return;
    
    // 각 그룹의 첫 번째 행(대표값)으로 그룹들을 정렬
    const sortedGroups = Array.from(groups.entries()).sort(([orderIdA, rowsA], [orderIdB, rowsB]) => {
        const firstRowA = rowsA[0];
        const firstRowB = rowsB[0];
        
        const sortCellA = firstRowA.cells[columnIndex];
        const sortCellB = firstRowB.cells[columnIndex];
        
        let valueA = getCellValue(sortCellA, column);
        let valueB = getCellValue(sortCellB, column);
        
        // 정렬 비교
        let comparison = 0;
        if (column === 'order_id' || column === 'estimated_price' || column === 'payment_amount') {
            // 숫자 정렬
            valueA = parseFloat(valueA) || 0;
            valueB = parseFloat(valueB) || 0;
            comparison = valueA - valueB;
        } else if (column === 'payment_status') {
            // 결제 여부 정렬
            const statusA = valueA === '결제 완료' ? 1 : 0;
            const statusB = valueB === '결제 완료' ? 1 : 0;
            comparison = statusA - statusB;
        } else {
            // 문자열 정렬
            comparison = valueA.localeCompare(valueB, 'ko');
        }
        
        return direction === 'asc' ? comparison : -comparison;
    });
    
    // 정렬된 그룹들을 tbody에 다시 추가
    let groupIndex = 0;
    sortedGroups.forEach(([orderId, groupRows]) => {
        const evenOdd = groupIndex % 2 === 0 ? 'even' : 'odd';
        groupRows.forEach(row => {
            // 행 색상 클래스 업데이트
            row.className = row.className.replace(/order-group-(even|odd)/, `order-group-${evenOdd}`);
            tbody.appendChild(row);
        });
        groupIndex++;
    });
}

function sortRegularTable(tbody, rows, column, direction) {
    // 컬럼 인덱스 찾기
    const headers = Array.from(tbody.closest('table').querySelectorAll('th'));
    const columnIndex = headers.findIndex(th => th.getAttribute('data-sort') === column);
    
    if (columnIndex === -1) return;
    
    // 일반적인 행 정렬
    rows.sort((a, b) => {
        const sortCellA = a.cells[columnIndex];
        const sortCellB = b.cells[columnIndex];
        
        let valueA = getCellValue(sortCellA, column);
        let valueB = getCellValue(sortCellB, column);
        
        // 정렬 비교
        let comparison = 0;
        if (column === 'order_id' || column === 'estimated_price' || column === 'payment_amount') {
            // 숫자 정렬
            valueA = parseFloat(valueA) || 0;
            valueB = parseFloat(valueB) || 0;
            comparison = valueA - valueB;
        } else if (column === 'payment_status') {
            // 결제 여부 정렬
            const statusA = valueA === '결제 완료' ? 1 : 0;
            const statusB = valueB === '결제 완료' ? 1 : 0;
            comparison = statusA - statusB;
        } else {
            // 문자열 정렬
            comparison = valueA.localeCompare(valueB, 'ko');
        }
        
        return direction === 'asc' ? comparison : -comparison;
    });
    
    // 정렬된 행을 다시 추가
    rows.forEach(row => tbody.appendChild(row));
}

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

// 컬럼 리사이징 기능
document.addEventListener('DOMContentLoaded', function() {
    const table = document.getElementById('excel-table');
    let isResizing = false;
    let currentTh = null;
    let startX = 0;
    let startWidth = 0;

    // 컬럼의 최대 콘텐츠 너비 계산 함수
    function getMaxContentWidth(columnIndex) {
        const table = document.getElementById('excel-table');
        const rows = table.querySelectorAll('tr');
        let maxWidth = 0;
        
        // 헤더 너비 계산
        const headerTh = rows[0].cells[columnIndex];
        if (headerTh) {
            const headerContent = headerTh.querySelector('.th-content');
            if (headerContent) {
                const tempSpan = document.createElement('span');
                tempSpan.style.cssText = 'position: absolute; visibility: hidden; white-space: nowrap; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;';
                tempSpan.textContent = headerContent.textContent.trim();
                document.body.appendChild(tempSpan);
                maxWidth = Math.max(maxWidth, tempSpan.offsetWidth + 40); // 패딩과 정렬 아이콘 공간 추가
                document.body.removeChild(tempSpan);
            }
        }
        
        // 첨부파일 컬럼인지 확인
        const isAttachmentColumn = headerTh && headerTh.textContent.includes('첨부 파일');            // 데이터 셀 너비 계산
        for (let i = 1; i < rows.length; i++) {
            const measureCell = rows[i].cells[columnIndex];
            if (measureCell) {
                // 셀의 실제 콘텐츠 가져오기
                let content = '';
                const statusBadge = measureCell.querySelector('.status-badge');
                const paymentBadge = measureCell.querySelector('.payment-badge');
                const editableValue = measureCell.querySelector('.editable-value');
                
                if (statusBadge) {
                    content = statusBadge.textContent.trim();
                } else if (paymentBadge) {
                    content = paymentBadge.textContent.trim();
                } else if (editableValue) {
                    content = editableValue.textContent.trim();
                } else {
                    content = measureCell.textContent.trim();
                }
                
                // 임시 요소로 너비 측정
                const tempSpan = document.createElement('span');
                tempSpan.style.cssText = 'position: absolute; visibility: hidden; white-space: nowrap; font-size: 13px;';
                tempSpan.textContent = content;
                document.body.appendChild(tempSpan);
                
                // 상태/결제 컬럼은 버튼 공간도 고려
                let additionalWidth = 32; // 기본 패딩
                if (statusBadge || paymentBadge) {
                    additionalWidth = 60; // 뱃지 패딩 + 편집 버튼 공간
                }
                
                maxWidth = Math.max(maxWidth, tempSpan.offsetWidth + additionalWidth);
                document.body.removeChild(tempSpan);
            }
        }
        
        return Math.min(maxWidth + 10, 500); // 최대 500px로 제한
    }

    // 모든 리사이즈 핸들에 이벤트 리스너 추가
    const resizeHandles = table.querySelectorAll('.resize-handle');
    
    resizeHandles.forEach(handle => {
        // 더블클릭 이벤트 추가
        handle.addEventListener('dblclick', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const th = this.parentElement;
            const columnIndex = Array.from(th.parentElement.children).indexOf(th);
            const optimalWidth = getMaxContentWidth(columnIndex);
            
            // 애니메이션 효과로 리사이즈
            th.style.transition = 'width 0.2s ease';
            th.style.width = optimalWidth + 'px';
            th.style.minWidth = optimalWidth + 'px';
            
            setTimeout(() => {
                th.style.transition = '';
            }, 200);
        });
        
        // 기존 드래그 리사이즈 기능
        handle.addEventListener('mousedown', function(e) {
            isResizing = true;
            currentTh = this.parentElement;
            startX = e.pageX;
            startWidth = currentTh.offsetWidth;
            this.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            e.preventDefault();
        });
    });

    document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        
        const width = startWidth + (e.pageX - startX);
        if (width > 50) { // 최소 너비 50px
            currentTh.style.width = width + 'px';
            currentTh.style.minWidth = width + 'px';
        }
    });

    document.addEventListener('mouseup', function() {
        if (isResizing) {
            isResizing = false;
            currentTh = null;
            document.body.style.cursor = 'default';
            document.querySelectorAll('.resize-handle.resizing').forEach(handle => {
                handle.classList.remove('resizing');
            });
        }
    });

    // 정렬 가능한 헤더에 클릭 이벤트 추가
    const sortableHeaders = table.querySelectorAll('.sortable-th');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function(e) {
            // 리사이즈 핸들 클릭이 아닌 경우에만 정렬
            if (!e.target.classList.contains('resize-handle')) {
                const column = this.getAttribute('data-sort');
                if (column) {
                    sortTable(column);
                }
            }
        });
    });
});

// 병합된 셀 호버 효과
document.addEventListener('DOMContentLoaded', function() {
    const mergedCells = document.querySelectorAll('.merged-cell');
    
    mergedCells.forEach(cell => {
        cell.addEventListener('mouseenter', function(e) {
            const row = this.closest('tr');
            if (row) {
                const hoverOrderId = row.getAttribute('data-order-id');
                if (hoverOrderId) {
                    const relatedRows = document.querySelectorAll(`tr[data-order-id="${hoverOrderId}"]`);
                    relatedRows.forEach(relatedRow => {
                        relatedRow.classList.add('merged-row-hover');
                    });
                }
            }
        });
        
        cell.addEventListener('mouseleave', function(e) {
            const row = this.closest('tr');
            if (row) {
                const hoverOrderId = row.getAttribute('data-order-id');
                if (hoverOrderId) {
                    const relatedRows = document.querySelectorAll(`tr[data-order-id="${hoverOrderId}"]`);
                    relatedRows.forEach(relatedRow => {
                        relatedRow.classList.remove('merged-row-hover');
                    });
                }
            }
        });
    });
});

// 파일명 표시는 이제 템플릿에서 직접 처리 (transcript_file.original_name)

// 파일 선택 창 직접 열기
function openFileDialog(requestId, fieldName) {
    // 숨겨진 파일 입력 요소 생성
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.style.display = 'none';
    fileInput.accept = '.pdf,.doc,.docx,.txt';
    
    // 파일 선택 이벤트
    fileInput.onchange = function() {
        if (this.files.length > 0) {
            uploadTranscriptFile(requestId, fieldName, this.files[0]);
        }
        // 사용 후 요소 제거
        document.body.removeChild(fileInput);
    };
    
    // body에 추가 후 클릭
    document.body.appendChild(fileInput);
    fileInput.click();
}

// 필드 편집 함수
// 필드 편집 모달 관련 변수
let currentEditRequestId = null;
let currentEditFieldName = null;
let currentEditFieldType = null;

function closeFieldEditModal() {
    document.getElementById('fieldEditModal').style.display = 'none';
    currentEditRequestId = null;
    currentEditFieldName = null;
    currentEditFieldType = null;
}

function openFieldEditModal(requestId, fieldName, fieldType, currentValue, fieldLabel) {
    currentEditRequestId = requestId;
    currentEditFieldName = fieldName;
    currentEditFieldType = fieldType;

    const fieldEditModal = document.getElementById('fieldEditModal');
    const input = document.getElementById('fieldEditInput');
    const title = document.getElementById('fieldEditModalTitle');
    const label = document.getElementById('fieldEditLabel');

    // 모달 설정
    title.textContent = fieldLabel + ' 편집';
    label.textContent = fieldLabel;
    input.value = currentValue;
    input.type = fieldType === 'number' ? 'number' : 'text';

    if (fieldType === 'number') {
        input.min = '0';
        input.step = '1';

        // 음수 입력 방지 (키보드 입력 차단)
        input.addEventListener('keydown', function(e) {
            // 마이너스 키(-) 입력 차단
            if (e.key === '-' || e.key === 'Subtract') {
                e.preventDefault();
                return false;
            }
        });

        // 붙여넣기 시 음수 방지
        input.addEventListener('paste', function(e) {
            setTimeout(() => {
                const val = parseInt(input.value);
                if (isNaN(val) || val < 0) {
                    input.value = '';
                }
            }, 10);
        });
    } else {
        input.removeAttribute('min');
        input.removeAttribute('step');
    }

    // 저장 버튼 이벤트
    const saveBtn = document.getElementById('fieldEditSaveBtn');
    saveBtn.onclick = () => saveFieldFromModal();

    // Enter 키 이벤트
    input.onkeydown = (e) => {
        if (e.key === 'Enter') {
            saveFieldFromModal();
        } else if (e.key === 'Escape') {
            closeFieldEditModal();
        }
    };

    // 모달 표시 및 포커스
    fieldEditModal.style.display = 'flex';
    setTimeout(() => input.focus(), 100);
}

function saveFieldFromModal() {
    const input = document.getElementById('fieldEditInput');
    let value = input.value;

    // 숫자 필드인 경우 음수 방지
    if (input.type === 'number') {
        const numValue = parseInt(value);
        if (isNaN(numValue) || numValue < 0) {
            alert('결제 금액은 0 이상의 숫자만 입력 가능합니다.');
            return;
        }
        value = numValue.toString();
    }

    // 값 저장
    saveFieldValue(currentEditRequestId, currentEditFieldName, value);

    // 모달 닫기
    closeFieldEditModal();
}

function saveFieldValue(requestId, fieldName, value) {
    fetch(`/api/requests/${requestId}/`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            [fieldName]: value || null
        })
    })
    .then(response => response.json())
    .then(data => {
        // UI 업데이트
        const editableCell = document.querySelector(`[data-request-id="${requestId}"][data-field="${fieldName}"]`);
        if (editableCell) {
            const valueSpan = editableCell.querySelector('.editable-value');
            if (valueSpan) {
                if (fieldName === 'payment_amount' || fieldName === 'refund_amount') {
                    valueSpan.textContent = value ? `${Number(value).toLocaleString()}원` : '-';
                } else {
                    valueSpan.textContent = value || '-';
                }
            }

            // 하이라이트 제거 (값이 입력된 경우)
            if (value) {
                editableCell.style.backgroundColor = '';
            }
        }

        showNotification('저장되었습니다.', 'success');
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('저장 중 오류가 발생했습니다.', 'error');
    });
}

function editField(requestId, fieldName, fieldType) {
    const editableCell = document.querySelector(`[data-request-id="${requestId}"][data-field="${fieldName}"]`);
    const container = editableCell.querySelector('.editable-container');
    const valueSpan = container.querySelector('.editable-value');

    let currentValue = valueSpan.textContent === '-' ? '' : valueSpan.textContent.trim();

    // 숫자 필드의 경우 '원' 제거
    if (fieldType === 'number' && currentValue.endsWith('원')) {
        currentValue = currentValue.replace(/[^0-9]/g, '');
    }

    // 필드 라벨 결정
    const fieldLabels = {
        'payment_amount': '결제 금액',
        'refund_amount': '환불 금액',
        'price_change_reason': '금액 변경 사유',
        'cancel_reason': '취소 사유',
        'notes': '메모'
    };

    const fieldLabel = fieldLabels[fieldName] || '값';

    // 모달 열기
    openFieldEditModal(requestId, fieldName, fieldType, currentValue, fieldLabel);
}

function saveField(requestId, fieldName, value, container, editor, valueSpan) {
    const data = {};
    data[fieldName] = fieldName.includes('amount') ? (value ? parseInt(value) : null) : value;
    
    fetch(`/api/requests/${requestId}/update_field/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            valueSpan.textContent = value || '-';
            showNotification('수정되었습니다.', 'success');
            cancelEdit(container, editor, valueSpan);
        } else {
            showNotification(data.error || '수정에 실패했습니다.', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('수정 중 오류가 발생했습니다.', 'error');
    });
}

function uploadTranscriptFile(requestId, fieldName, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('field_name', fieldName);
    
    fetch(`/api/requests/${requestId}/upload_transcript/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const editableCell = document.querySelector(`[data-request-id="${requestId}"][data-field="${fieldName}"]`);
            if (editableCell) {
                const valueSpan = editableCell.querySelector('.editable-value');
                if (valueSpan) {
                    valueSpan.textContent = data.original_name || file.name;
                }
            }
            showNotification('파일이 업로드되었습니다.', 'success');
        } else {
            showNotification(data.error || '파일 업로드에 실패했습니다.', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('파일 업로드 중 오류가 발생했습니다.', 'error');
    });
}

function cancelEdit(container, editor, valueSpan) {
    editor.remove();
    valueSpan.style.display = '';
    container.querySelector('.edit-btn').style.display = '';
}

// 전체 선택/해제 함수
function toggleAllCheckboxes() {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const rowCheckboxes = document.querySelectorAll('.row-checkbox');
    
    rowCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    
    updateSelectAllState();
    updateDetailViewButtonVisibility();
}

// 개별 체크박스 토글 함수
function toggleCheckbox(cell) {
    const checkbox = cell.querySelector('.row-checkbox');
    checkbox.checked = !checkbox.checked;
    updateSelectAllState();
    updateDetailViewButtonVisibility();
}

// 상세 보기 버튼 표시/숨김
function updateDetailViewButtonVisibility() {
    const btn = document.getElementById('detailViewBtn');
    if (!btn) return;
    const checked = document.querySelectorAll('.row-checkbox:checked');
    btn.style.display = checked.length > 0 ? 'inline-flex' : 'none';
}

// 선택된 request_id 목록 수집
function getSelectedRequestIds() {
    const checked = document.querySelectorAll('.row-checkbox:checked');
    const requestIds = [];
    checked.forEach(cb => {
        const reqIds = cb.getAttribute('data-request-ids');
        const rid = cb.getAttribute('data-request-id');
        if (reqIds) reqIds.split(',').forEach(id => { if (id.trim()) requestIds.push(id.trim()); });
        else if (rid) requestIds.push(rid);
    });
    return requestIds;
}

// 상세 보기 모달 열기
async function openDetailModal() {
    const requestIds = getSelectedRequestIds();
    if (!requestIds || requestIds.length === 0) {
        showNotification('선택된 항목이 없습니다.', 'error');
        return;
    }
    const config = window.DETAIL_VIEW_CONFIG || {};
    const hideRequestId = config.hide_request_id || false;
    const hideOrderId = config.hide_order_id || false;

    const checked = document.querySelectorAll('.row-checkbox:checked');
    const orderSet = new Set();
    checked.forEach(cb => {
        let oid = cb.getAttribute('data-order-id');
        if (!oid) {
            const row = cb.closest('tr');
            oid = row ? row.getAttribute('data-order-id') : null;
        }
        if (oid) orderSet.add(oid);
    });
    if (orderSet.size > 10) {
        showNotification('최대 10개 주문까지 확인할 수 있습니다.', 'error');
        return;
    }

    const contentEl = document.getElementById('detailViewContent');
    const modalEl = document.getElementById('detailViewModal');
    contentEl.innerHTML = '<p style="color:#6b7280;">불러오는 중...</p>';
    modalEl.style.display = 'flex';

    try {
        const res = await fetch('/api/requests/bulk_detail/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ request_ids: requestIds })
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || '조회 실패');
        }
        if (data.truncated) {
            showNotification('10개 주문까지만 표시됩니다.', 'info');
        }
        contentEl.innerHTML = renderDetailViewContent(data.requests || [], hideRequestId, hideOrderId);
    } catch (err) {
        contentEl.innerHTML = '<p style="color:#dc2626;">' + (err.message || '조회 중 오류가 발생했습니다.') + '</p>';
    }
}

function closeDetailModal() {
    document.getElementById('detailViewModal').style.display = 'none';
}

function formatDate(val) {
    if (!val) return '-';
    if (typeof val === 'string' && val.length >= 19) return val.substr(0, 19).replace('T', ' ');
    return val;
}

function escapeHtml(str) {
    if (str == null || str === '') return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML.replace(/\n/g, '<br>');
}

function renderDetailViewContent(requests, hideRequestId, hideOrderId) {
    const cols = [];
    if (!hideOrderId) cols.push({ key: 'order_id', label: 'Order ID' });
    if (!hideRequestId) cols.push({ key: 'request_id', label: 'Request ID' });
    const statusMap = { received: '접수됨', in_progress: '작업중', work_completed: '작업완료', sent: '발송완료', impossible: '작업불가', cancelled: '취소됨' };
    const orderStatusMap = { received: '접수됨', payment_completed: '결제완료', sent: '발송완료', impossible: '작업불가', cancelled: '취소됨', refunded: '환불완료' };
    cols.push(
        { key: 'status', label: '상태 (Request)', fn: r => r.status ? (statusMap[r.status] || r.status) : '-' },
        { key: 'order_status', label: 'Order 상태', fn: r => r.order_status ? (orderStatusMap[r.order_status] || r.order_status) : '-' },
        { key: 'files', label: '첨부 파일', fn: r => (r.files && r.files.length) ? r.files.map(f => f.original_name || f.file).join(', ') : '-' },
        { key: 'recording_type', label: '녹취 타입' },
        { key: 'partial_range', label: '부분 녹취 구간' },
        { key: 'total_duration', label: '총 길이' },
        { key: 'speaker_count', label: '화자수' },
        { key: 'speaker_names', label: '화자 이름' },
        { key: 'recording_location', label: '녹음 종류' },
        { key: 'recording_date', label: '녹음 일시', fn: r => formatDate(r.recording_date) },
        { key: 'additional_info', label: '상세 정보 (고객)' },
        { key: 'draft_format', label: '열람파일 형식' },
        { key: 'final_option', label: '최종본 옵션', fn: r => ({ file: '파일', file_usb: '파일+등기우편', file_usb_cd: '파일+등기우편+CD', file_usb_post: '파일+등기우편+USB' }[r.final_option] || r.final_option || '-') },
        { key: 'name', label: '주문자' },
        { key: 'phone', label: '연락처' },
        { key: 'email', label: '이메일' },
        { key: 'address', label: '주소' },
        { key: 'estimated_price', label: '예상 견적', fn: r => r.estimated_price != null ? Number(r.estimated_price).toLocaleString() + '원' : '-' },
        { key: 'payment_status', label: '결제 여부', fn: r => r.payment_status ? 'Y' : 'N' },
        { key: 'payment_amount', label: '결제 금액', fn: r => r.payment_amount != null ? Number(r.payment_amount).toLocaleString() + '원' : '-' },
        { key: 'price_change_reason', label: '결제금액 변동 사유' },
        { key: 'refund_amount', label: '환불 금액', fn: r => r.refund_amount != null ? Number(r.refund_amount).toLocaleString() + '원' : '-' },
        { key: 'cancel_reason', label: '취소 사유' },
        { key: 'transcript_file', label: '속기록', fn: r => r.transcript_file_name || (r.transcript_file && r.transcript_file.original_name ? r.transcript_file.original_name : null) || '-' },
        { key: 'notes', label: '메모 (관리자)' }
    );

    let html = '';
    requests.forEach((r, idx) => {
        html += '<div style="border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 16px; overflow: hidden;">';
        html += '<div style="background: #f9fafb; padding: 12px 16px; font-weight: 600; color: #374151;">';
        html += '요청 ' + (idx + 1) + (r.request_id ? ' - ' + r.request_id : '');
        html += '</div><div style="padding: 16px;">';
        cols.forEach(c => {
            let val = '-';
            if (c.fn) val = c.fn(r);
            else if (r[c.key] !== undefined && r[c.key] !== null && r[c.key] !== '') val = String(r[c.key]);
            const valStr = (val === '-' || val === null || val === undefined) ? '-' : escapeHtml(String(val));
            html += '<div style="display: flex; margin-bottom: 10px; font-size: 13px;">';
            html += '<span style="min-width: 160px; color:#6b7280;">' + escapeHtml(c.label) + ':</span>';
            html += '<span style="flex:1; word-break: break-all; white-space: pre-wrap;">' + valStr + '</span></div>';
        });
        html += '</div></div>';
    });
    return html || '<p style="color:#6b7280;">표시할 데이터가 없습니다.</p>';
}

// 전체 선택 체크박스 상태 업데이트
function updateSelectAllState() {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const rowCheckboxes = document.querySelectorAll('.row-checkbox');
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    
    if (checkedBoxes.length === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (checkedBoxes.length === rowCheckboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

// 체크박스 상태 변경 이벤트 리스너
document.addEventListener('DOMContentLoaded', function() {
    // 개별 체크박스 변경 감지
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('row-checkbox')) {
            updateSelectAllState();
            updateDetailViewButtonVisibility();
        }
    });
    
    // 초기 상태 설정
    updateSelectAllState();
    updateDetailViewButtonVisibility();
});

// 견적 및 입금 안내 발송
// 모달 관련 전역 변수
let pendingSendData = null;

function closeDuplicateModal() {
    document.getElementById('duplicateSendModal').style.display = 'none';
    pendingSendData = null;
}

function confirmDuplicateSend() {
    if (pendingSendData) {
        // 프로세스 1: Order ID 기반 (견적/결제)
        if (pendingSendData.endpoint && pendingSendData.orderIds) {
            executeSend(pendingSendData.endpoint, pendingSendData.orderIds, pendingSendData.successMessage);
        }
        // 프로세스 2: Request ID 기반 (초안/최종안)
        else if (pendingSendData.requestIds) {
            if (pendingSendData.isFinalDraft) {
                executeSendFinalDraft(pendingSendData.requestIds);
            } else {
                executeSendDraft(pendingSendData.requestIds);
            }
        }
        closeDuplicateModal();
    }
}

function executeSend(endpoint, orderIds, successMessage) {
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            order_ids: orderIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message || successMessage, 'success');
            if (data.errors && data.errors.length > 0) {
                data.errors.forEach(error => {
                    showNotification(error, 'error');
                });
            }
            // 페이지 새로고침하여 업데이트된 상태 반영
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showNotification(data.error || '발송에 실패했습니다.', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('발송 중 오류가 발생했습니다.', 'error');
    });
}

// 견적 검증 모달 관련 변수
let quotationOrderIds = [];
let validOrderIds = [];
let paymentCompletionOrderIds = [];
let validPaymentCompletionOrderIds = [];

function closeQuotationValidationModal() {
    document.getElementById('quotationValidationModal').style.display = 'none';
    quotationOrderIds = [];
    validOrderIds = [];
}

function confirmQuotationSend() {
    // validOrderIds를 사용하기 전에 복사
    const orderIdsToSend = [...validOrderIds];

    // 모달 닫기
    closeQuotationValidationModal();

    // 중복 발송 이력 확인
    fetch('/api/send/check-history/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            order_ids: orderIdsToSend,
            email_type: 'quotation_guide'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.has_duplicate) {
            showDuplicateModal(data.duplicate_history, '/api/send/quotation-guide/', orderIdsToSend, '견적 및 입금 안내');
        } else {
            executeSend('/api/send/quotation-guide/', orderIdsToSend, '견적 및 입금 안내를 발송했습니다.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('발송 이력 확인 중 오류가 발생했습니다.', 'error');
    });
}

function sendOnlyValidOrders() {
    if (validOrderIds.length === 0) {
        showNotification('발송 가능한 주문이 없습니다.', 'error');
        return;
    }

    // 문제있는 주문 체크 해제
    document.querySelectorAll('.row-checkbox:checked').forEach(checkbox => {
        const orderId = checkbox.getAttribute('data-order-id');
        if (!validOrderIds.includes(orderId)) {
            checkbox.checked = false;
        }
    });

    confirmQuotationSend();
}

function highlightProblemOrders(invalidResults) {
    console.log('Highlighting problem orders:', invalidResults);

    // 모든 셀의 하이라이트 제거
    document.querySelectorAll('.excel-cell').forEach(cell => {
        cell.style.backgroundColor = '';
        cell.style.border = '';
    });
    document.querySelectorAll('tr[data-order-id]').forEach(row => {
        row.style.borderLeft = '';
    });

    // 문제있는 주문의 셀들을 하이라이트
    invalidResults.forEach(result => {
        const row = document.querySelector(`tr[data-order-id="${result.order_id}"]`);
        console.log(`Looking for order ${result.order_id}:`, row);

        if (row) {
            // 에러별로 해당 셀 하이라이트
            result.errors.forEach(error => {
                if (error.includes('결제 금액')) {
                    // 결제 금액 셀 찾기
                    const paymentCell = row.querySelector('td[data-field="payment_amount"]');
                    if (paymentCell) {
                        paymentCell.style.backgroundColor = '#ffb3b3';  // 중간 톤 빨간색 (더 진하게)
                        paymentCell.style.transition = 'all 0.3s';
                        console.log(`Highlighted payment_amount cell for order ${result.order_id}`);
                    }
                }

                if (error.includes('이메일')) {
                    // 이메일 셀 찾기 (Order ID List에는 없을 수 있음)
                    const emailCell = row.querySelector('td[data-field="email"]');
                    if (emailCell) {
                        emailCell.style.backgroundColor = '#ffb3b3';  // 중간 톤 빨간색 (더 진하게)
                        emailCell.style.transition = 'all 0.3s';
                        console.log(`Highlighted email cell for order ${result.order_id}`);
                    }
                }
            });

            // 왼쪽 테두리로 행 전체 표시
            row.style.borderLeft = '4px solid #dc2626';
            console.log(`Highlighted row for order ${result.order_id}`);
        } else {
            console.warn(`Row not found for order ${result.order_id}`);
        }
    });

    // 잠시 후 스크롤 (DOM 업데이트 대기)
    setTimeout(() => {
        const firstInvalidRow = document.querySelector(`tr[data-order-id="${invalidResults[0].order_id}"]`);
        if (firstInvalidRow) {
            firstInvalidRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            console.log('Scrolled to first invalid row');
        }
    }, 100);

    // 알림 표시
    showNotification(`${invalidResults.length}개 주문에 필수 항목이 누락되었습니다. 빨간색으로 표시된 셀을 확인해주세요.`, 'error');
}

// 주문서 삭제 기능
let deleteOrderIds = [];

async function deleteSelected() {
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');

    if (checkedBoxes.length === 0) {
        showNotification('선택된 주문이 없습니다.', 'error');
        return;
    }

    // Order ID 수집 (중복 제거)
    const orderIdsSet = new Set();
    checkedBoxes.forEach(checkbox => {
        const checkedOrderId = checkbox.getAttribute('data-order-id');
        if (checkedOrderId) {
            orderIdsSet.add(checkedOrderId);
        }
    });

    deleteOrderIds = Array.from(orderIdsSet);

    // 실제 파일 개수를 서버에서 가져오기
    try {
        const response = await fetch(`/api/database/get-order-file-counts/?order_ids=${deleteOrderIds.join(',')}`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '파일 개수 조회 실패');
        }
        
        const fileCounts = data.file_counts;
        const fileLists = data.file_lists;
        
        // 모달에 삭제할 주문 목록 표시
        const content = document.getElementById('deleteConfirmContent');
        let html = `<div style="margin-bottom: 16px;">
            <p style="color: #374151; font-weight: 500; margin-bottom: 12px;">다음 ${deleteOrderIds.length}개 주문이 삭제됩니다:</p>
            <div style="max-height: 400px; overflow-y: auto;">`;

        deleteOrderIds.forEach(orderId => {
            // Order ID에 해당하는 Request 정보 찾기
            const firstRow = document.querySelector(`.row-checkbox[data-order-id="${orderId}"]`).closest('tr');
            const nameCell = firstRow.querySelector('td:nth-child(4)');  // 주문자명
            const emailCell = firstRow.querySelector('td:nth-child(5)');  // 이메일
            const name = nameCell ? nameCell.textContent.trim() : '-';
            const email = emailCell ? emailCell.textContent.trim() : '-';

            // 서버에서 가져온 실제 파일 개수와 파일 목록 사용
            const fileCount = fileCounts[orderId] || 0;
            const files = fileLists[orderId] || [];

            html += `
                <div style="background-color: #f9fafb; padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 3px solid #dc2626;">
                    <p style="color: #111827; font-weight: 500; margin: 0 0 4px 0;">Order ID: ${orderId}</p>
                    <p style="color: #6b7280; font-size: 14px; margin: 0 0 8px 0;">주문자: ${name} (${email})</p>
                    <p style="color: #dc2626; font-size: 14px; margin: 0 0 8px 0; font-weight: 500;">파일 개수: ${fileCount}개</p>
            `;

            // 파일 목록 표시
            if (files.length > 0) {
                html += `<div style="margin-top: 8px; padding: 8px; background-color: #fee2e2; border-radius: 6px;">
                    <p style="color: #991b1b; font-size: 12px; font-weight: 500; margin: 0 0 6px 0;">삭제될 파일 목록:</p>`;
                
                files.forEach(file => {
                    const typeColor = file.type === '속기록' ? '#dc2626' : '#7c2d12';
                    const typeIcon = file.type === '속기록' ? '📝' : '📎';
                    html += `<p style="color: ${typeColor}; font-size: 11px; margin: 2px 0; padding-left: 12px;">
                        ${typeIcon} ${file.name}
                    </p>`;
                });
                
                html += `</div>`;
            }

            html += `</div>`;
        });

        html += `</div></div>`;
        content.innerHTML = html;

        // 모달 열기
        document.getElementById('deleteConfirmModal').style.display = 'flex';
        
    } catch (error) {
        console.error('파일 개수 조회 오류:', error);
        showNotification('파일 개수 조회 중 오류가 발생했습니다.', 'error');
    }
}

function closeDeleteConfirmModal() {
    document.getElementById('deleteConfirmModal').style.display = 'none';
    deleteOrderIds = [];
}

async function confirmDelete() {
    const btn = document.getElementById('confirmDeleteBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '삭제 중...';

    try {
        const response = await fetch('/api/database/delete-orders/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ order_ids: deleteOrderIds })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showNotification(data.message, 'success');
            closeDeleteConfirmModal();
            // 페이지 새로고침
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showNotification(data.error || '삭제 실패', 'error');
            if (data.errors && data.errors.length > 0) {
                console.error('삭제 오류:', data.errors);
            }
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    } catch (error) {
        console.error('삭제 중 오류:', error);
        showNotification('삭제 중 오류가 발생했습니다.', 'error');
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// 주문서 추가 모달 기능
let uploadedFilesData = [];

async function openAddModal() {
    // 폼 초기화 (ID 설정 전에 먼저)
    document.getElementById('addOrderForm').reset();
    uploadedFilesData = [];
    document.getElementById('uploadedFiles').innerHTML = '';
    document.getElementById('uploadStatusContainer').style.display = 'none';
    document.getElementById('uploadStatusContainer').innerHTML = '';
    document.getElementById('fileUploadProgress').style.display = 'none';
    
    // 파일 탭 관련 데이터 초기화
    fileTabsData = [];
    activeFileTabIndex = 0;
    
    // 파일 탭 컨테이너 숨김
    const fileTabsContainer = document.getElementById('fileTabsContainer');
    if (fileTabsContainer) {
        fileTabsContainer.style.display = 'none';
        document.getElementById('fileTabs').innerHTML = '';
        document.getElementById('fileSettingsPanel').innerHTML = '';
    }
    // Order ID와 Request ID 생성
    try {
        const response = await fetch('/api/database/generate-db-order-id/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('orderIdInput').value = data.order_id;
            document.getElementById('requestIdInput').value = data.request_id;
        }
    } catch (error) {
        console.error('ID 생성 오류:', error);
    }


    // 초기 상태 설정

    // 모달 열기
    document.getElementById('addOrderModal').style.display = 'flex';
}

async function closeAddModal() {
    document.getElementById('addOrderModal').style.display = 'none';
    
    // 모든 데이터 초기화
    uploadedFilesData = [];
    fileTabsData = [];
    activeFileTabIndex = 0;
    
    // 파일 탭 컨테이너 숨김 및 초기화
    const fileTabsContainer = document.getElementById('fileTabsContainer');
    if (fileTabsContainer) {
        fileTabsContainer.style.display = 'none';
        document.getElementById('fileTabs').innerHTML = '';
        document.getElementById('fileSettingsPanel').innerHTML = '';
    }
    
    // 업로드된 파일 목록 초기화
    document.getElementById('uploadedFiles').innerHTML = '';
    document.getElementById('uploadStatusContainer').style.display = 'none';
    document.getElementById('uploadStatusContainer').innerHTML = '';
    document.getElementById('fileUploadProgress').style.display = 'none';
}
async function confirmCloseAddModal() {
    console.log(`[CLOSE MODAL] confirmCloseAddModal 호출`);
    console.log(`[CLOSE MODAL] uploadedFilesData.length: ${uploadedFilesData.length}`);
    
    // 업로드된 파일이 있다면 삭제 확인
    if (uploadedFilesData.length > 0) {
        const confirmed = confirm(`업로드한 ${uploadedFilesData.length}개 파일이 DB에서 삭제됩니다.\n정말 취소하시겠습니까?`);
        if (!confirmed) {
            return;
        }
        
        try {
            const fileKeys = uploadedFilesData.map(file => file.file_key);
            console.log(`[CLOSE MODAL] 삭제할 파일 키:`, fileKeys);
            const response = await fetch('/api/database/delete-uploaded-files/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    file_keys: fileKeys
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('업로드된 파일 삭제 완료:', result.message);
            } else {
                console.error('파일 삭제 실패');
            }
        } catch (error) {
            console.error('파일 삭제 중 오류:', error);
        }
    }
    
    closeAddModal();
}

// 파일 업로드 처리 (Presigned URL 방식)
document.getElementById('fileInput').addEventListener('change', async function(e) {
    const files = Array.from(e.target.files);

    if (files.length === 0) return;


    // 3GB 제한 검증
    const maxSize = 3 * 1024 * 1024 * 1024;  // 3GB
    for (const file of files) {
        if (file.size > maxSize) {
            showNotification(`파일 "${file.name}"이(가) 3GB를 초과합니다.`, 'error');
            e.target.value = '';
            return;
        }
    }

    const progressContainer = document.getElementById('fileUploadProgress');
    const uploadedFilesContainer = document.getElementById('uploadedFiles');
    progressContainer.style.display = 'block';
    progressContainer.innerHTML = '';

    const saveBtn = document.getElementById('saveOrderBtn');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '업로드 중...';

    // 병렬 업로드
    try {
        const uploadPromises = files.map((file, index) => uploadOrderFile(file, index, progressContainer));
        const results = await Promise.all(uploadPromises);

        // 기존 파일들과 새로 업로드된 파일들 합치기 (누적)
        const newUploadedFiles = results.filter(r => r.success);
        
        // duration 정보를 파일 객체에 추가
        newUploadedFiles.forEach((fileData, index) => {
            const originalFile = files[index];
            if (originalFile && fileData.duration) {
                fileData.duration = fileData.duration; // duration 정보 유지
                console.log(`[DEBUG] duration 정보 연결 - 파일: ${fileData.original_name}, duration: ${fileData.duration}`);
            }
        });
        
        uploadedFilesData = uploadedFilesData.concat(newUploadedFiles);

        // 업로드된 파일 목록 표시 (누적 방식)
        if (uploadedFilesData.length > 0) {
            uploadStatusContainer.style.display = 'block'; uploadStatusContainer.innerHTML = '<p style="font-size: 14px; font-weight: 500; color: #059669; margin-bottom: 8px;">✓ 업로드 완료:</p>';
            uploadedFilesData.forEach(file => {
                uploadStatusContainer.style.display = 'block'; uploadStatusContainer.innerHTML += `<p style="font-size: 13px; color: #6b7280; margin: 4px 0;">• ${file.original_name} (${(file.file_size / (1024 * 1024)).toFixed(2)} MB)</p>`;
            });
        }

        progressContainer.style.display = 'none';
        saveBtn.disabled = false;
        saveBtn.innerHTML = '저장';

        showNotification(`${uploadedFilesData.length}개 파일 업로드 완료`, 'success');

        // 파일 탭 생성 (전체 누적 파일 전달)
        console.log(`[DEBUG] createFileSettingsTabs 호출 전 uploadedFilesData:`, uploadedFilesData);
        await createFileSettingsTabs(uploadedFilesData);
    } catch (error) {
        console.error('파일 업로드 오류:', error);
        showNotification('파일 업로드 중 오류가 발생했습니다.', 'error');
        saveBtn.disabled = false;
        saveBtn.innerHTML = '저장';
    }
});

async function uploadOrderFile(file, index, progressContainer) {
    console.log(`[DEBUG] uploadFile 시작 - index: ${index}, 파일명: ${file.name}`);
    
    // 미디어 파일인 경우 길이 미리 추출
    let duration = '00:00:00';
    if (file.type && (file.type.startsWith('audio/') || file.type.startsWith('video/'))) {
        console.log(`[DEBUG] 미디어 파일 감지: ${file.name}, 타입: ${file.type}`);
        try {
            duration = await getMediaDuration(file);
            console.log(`[DEBUG] 미디어 길이 추출 완료: ${duration}`);
        } catch (error) {
            console.error(`[DEBUG] 미디어 길이 추출 실패:`, error);
            duration = '00:00:00';
        }
    }
    
    // 프로그레스 바 생성
    const progressDiv = document.createElement('div');
    progressDiv.style.marginBottom = '12px';
    progressDiv.innerHTML = `
        <p style="font-size: 13px; color: #374151; margin-bottom: 4px;">${file.name} ${duration !== '00:00:00' ? `(${duration})` : ''}</p>
        <div style="background-color: #e5e7eb; border-radius: 9999px; height: 8px; overflow: hidden;">
            <div id="progress-${index}" style="background-color: #059669; height: 100%; width: 0%; transition: width 0.3s;"></div>
        </div>
    `;
    progressContainer.appendChild(progressDiv);

    try {
        // 1. Presigned URL 요청
        const customerName = document.getElementById('nameInput').value || 'Unknown';
        const customerEmail = document.getElementById('emailInput').value || 'unknown@example.com';
        const emailId = customerEmail.split('@')[0];

        
        const presignedResponse = await fetch('/api/s3/presigned-url/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                file_name: file.name,
                file_type: file.type,
                file_size: file.size,
                customer_name: customerName,
                customer_email: customerEmail
            })
        });

        
        if (!presignedResponse.ok) {
            throw new Error('Presigned URL 생성 실패');
        }

        const presignedData = await presignedResponse.json();
        
        
        
        const progressBar = document.getElementById(`progress-${index}`);
        progressBar.style.width = '30%';

        // 2. S3에 파일 업로드
        const formData = new FormData();
        Object.entries(presignedData.presigned_post.fields).forEach(([key, value]) => {
            formData.append(key, value);
        });
        formData.append('file', file);

        
        const uploadResponse = await fetch(presignedData.presigned_post.url, {
            method: 'POST',
            body: formData
        });

        
        if (!uploadResponse.ok) {
            const errorText = await uploadResponse.text();
            console.error(`[DEBUG ${index}] S3 응답 에러:`, errorText);
            throw new Error(`S3 업로드 실패: ${uploadResponse.status}`);
        }

        progressBar.style.width = '100%';
        

        return {
            success: true,
            file_key: presignedData.file_name,
            original_name: file.name,
            file_type: file.type,
            file_size: file.size,
            duration: duration  // 미디어 길이 정보 추가
        };
    } catch (error) {
        console.error(`[DEBUG ${index}] ❌ 파일 "${file.name}" 업로드 실패:`, error);
        return {
            success: false,
            error: error.message
        };
    }
}

async function saveOrder() {


    // 폼 검증
    const name = document.getElementById('nameInput').value.trim();
    const email = document.getElementById('emailInput').value.trim();
    const phone = document.getElementById('phoneInput').value.trim();

    const errors = [];

    // 1. 주문자명 검증
    if (!name) {
        errors.push('주문자명을 입력해주세요.');
    }

    // 2. 연락처 검증 (10-11자리 숫자)
    if (!phone) {
        errors.push('연락처를 입력해주세요.');
    } else {
        const phoneDigits = phone.replace(/[^\d]/g, '');
        if (phoneDigits.length < 10 || phoneDigits.length > 11) {
            errors.push('연락처는 10~11자리 숫자여야 합니다.');
        }
    }

    // 3. 이메일 검증
    if (!email) {
        errors.push('이메일을 입력해주세요.');
    } else {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            errors.push('올바른 이메일 형식이 아닙니다.');
        }
    }

    // 4. 파일 업로드 검증
    if (!fileTabsData || fileTabsData.length === 0) {
        errors.push('최소 1개 이상의 파일을 업로드해주세요.');
    }

    // 5. 파일별 설정 검증
    if (fileTabsData && fileTabsData.length > 0) {
        for (let i = 0; i < fileTabsData.length; i++) {
            const fileData = fileTabsData[i];
            const fileNum = i + 1;

            // 녹취 타입 검증
            if (!fileData.recordingType || (fileData.recordingType !== '전체' && fileData.recordingType !== '부분')) {
                errors.push(`파일 ${fileNum}: 녹취 타입을 선택해주세요.`);
            }

            // 녹음 종류 검증
            if (!fileData.recordingLocation || (fileData.recordingLocation !== '통화' && fileData.recordingLocation !== '현장')) {
                errors.push(`파일 ${fileNum}: 녹음 종류를 선택해주세요.`);
            }

            // 부분 녹취 선택 시 구간 검증
            if (fileData.recordingType === '부분') {
                const partialRange = fileData.partialRange?.trim();
                if (!partialRange) {
                    errors.push(`파일 ${fileNum}: 부분 녹취 구간을 입력해주세요.`);
                } else {
                    // 형식 검증
                    const validation = validatePartialRange(partialRange);
                    if (!validation.valid) {
                        errors.push(`파일 ${fileNum}: ${validation.error}`);
                    }
                }
            }

            // 화자수 검증
            const speakerCount = parseInt(fileData.speakerCount);
            if (!speakerCount || speakerCount < 1 || speakerCount > 10) {
                errors.push(`파일 ${fileNum}: 화자수는 1~10명 사이여야 합니다.`);
            }
        }
    }

    // 에러가 있으면 알림 표시 후 중단
    if (errors.length > 0) {
        const errorMessage = errors.join('\n');
        showNotification(errorMessage, 'error');
        return;
    }

    const saveBtn = document.getElementById('saveOrderBtn');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '저장 중...';

    try {
        const filesData = getFileSettingsData();

        console.log('[DEBUG] saveOrder - filesData:', filesData);
        console.log('[DEBUG] saveOrder - fileTabsData:', fileTabsData);

        const formData = {
            name: name,
            email: email,
            phone: phone,
            address: document.getElementById('addressInput').value.trim(),
            draft_format: document.getElementById('draftFormatInput').value,
            final_option: document.getElementById('finalOptionInput').value,
            payment_status: document.getElementById('paymentStatusInput').checked,
            payment_amount: document.getElementById('paymentAmountInput').value ? Math.max(0, parseInt(document.getElementById('paymentAmountInput').value)) : null,
            notes: document.getElementById('notesInput').value.trim(),
            files_data: filesData
        };

        console.log('[DEBUG] saveOrder - formData:', JSON.stringify(formData, null, 2));

        const response = await fetch('/api/database/create-db-order/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        console.log('[DEBUG] saveOrder - response status:', response.status);
        console.log('[DEBUG] saveOrder - response data:', data);

        if (response.ok && data.success) {
            showNotification(data.message, 'success');
            closeAddModal();
            // 페이지 새로고침
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            console.error('[ERROR] saveOrder failed:', data);
            showNotification(data.error || '저장 실패', 'error');
            saveBtn.disabled = false;
            saveBtn.innerHTML = '저장';
        }
    } catch (error) {
        console.error('저장 중 오류:', error);
        showNotification('저장 중 오류가 발생했습니다.', 'error');
        saveBtn.disabled = false;
        saveBtn.innerHTML = '저장';
    }
}

function sendQuotationGuide() {
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    console.log('Checked boxes:', checkedBoxes);
    console.log('Checked boxes length:', checkedBoxes.length);

    if (checkedBoxes.length === 0) {
        showNotification('선택된 주문이 없습니다.', 'error');
        return;
    }

    const orderIds = Array.from(checkedBoxes).map(checkbox => {
        const orderId = checkbox.getAttribute('data-order-id');
        console.log('Checkbox:', checkbox, 'Order ID:', orderId);
        return orderId;
    }).filter(id => id);  // null/undefined 제거

    console.log('Order IDs to send:', orderIds);
    quotationOrderIds = orderIds;

    // 검증 API 호출
    fetch('/api/send/validate-quotation/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            order_ids: orderIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        // 검증 모달 표시
        showQuotationValidationModal(data);
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('검증 중 오류가 발생했습니다.', 'error');
    });
}

// 결제 완료 안내 검증 모달
function closePaymentCompletionValidationModal() {
    document.getElementById('paymentCompletionValidationModal').style.display = 'none';
    paymentCompletionOrderIds = [];
    validPaymentCompletionOrderIds = [];
}

function confirmPaymentCompletionSend() {
    // validPaymentCompletionOrderIds를 사용하기 전에 복사
    const orderIdsToSend = [...validPaymentCompletionOrderIds];

    // 모달 닫기
    closePaymentCompletionValidationModal();

    // 중복 발송 이력 확인
    fetch('/api/send/check-history/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            order_ids: orderIdsToSend,
            email_type: 'payment_completion_guide'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.has_duplicate) {
            showDuplicateModal(data.duplicate_history, '/api/send/payment-completion-guide/', orderIdsToSend, '결제 완료 안내');
        } else {
            executeSend('/api/send/payment-completion-guide/', orderIdsToSend, '결제 완료 안내를 발송했습니다.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('발송 이력 확인 중 오류가 발생했습니다.', 'error');
    });
}

function sendOnlyValidPaymentCompletionOrders() {
    if (validPaymentCompletionOrderIds.length === 0) {
        showNotification('발송 가능한 주문이 없습니다.', 'error');
        return;
    }

    // 문제있는 주문 체크 해제
    document.querySelectorAll('.row-checkbox:checked').forEach(checkbox => {
        const orderId = checkbox.getAttribute('data-order-id');
        if (!validPaymentCompletionOrderIds.includes(orderId)) {
            checkbox.checked = false;
        }
    });

    confirmPaymentCompletionSend();
}

function showPaymentCompletionValidationModal(validationData) {
    const modal = document.getElementById('paymentCompletionValidationModal');
    const content = document.getElementById('paymentCompletionValidationContent');
    const buttonsContainer = document.getElementById('paymentCompletionValidationButtons');

    // 유효한 주문들과 무효한 주문들 분리
    const validResults = validationData.results.filter(r => r.valid);
    const invalidResults = validationData.results.filter(r => !r.valid);

    validPaymentCompletionOrderIds = validResults.map(r => r.order_id);

    // 컨텐츠 생성
    let html = `<p style="margin-bottom: 16px; color: #6b7280;">다음 ${validationData.results.length}개 주문에 이메일을 발송합니다:</p>`;

    html += '<div style="max-height: 400px; overflow-y: auto;">';

    // 유효한 주문들
    validResults.forEach(result => {
        html += `
            <div style="padding: 12px; margin-bottom: 12px; background-color: #eff6ff; border: 1px solid #93c5fd; border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <span style="color: #2563eb; font-size: 18px;">✓</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #1e40af; margin-bottom: 4px;">Order ${result.order_id} (${result.customer_name})</div>
                        <div style="font-size: 14px; color: #1e40af;">
                            <div>• 결제 금액: ${result.payment_amount ? Number(result.payment_amount).toLocaleString() + '원' : '-'}</div>
                            <div>• 이메일: ${result.email}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    // 무효한 주문들
    invalidResults.forEach(result => {
        html += `
            <div style="padding: 12px; margin-bottom: 12px; background-color: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <span style="color: #dc2626; font-size: 18px;">✗</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #991b1b; margin-bottom: 4px;">Order ${result.order_id} (${result.customer_name || '정보 없음'})</div>
                        <div style="font-size: 14px; color: #b91c1c;">
                            <div>• 결제 금액: ${result.payment_amount ? Number(result.payment_amount).toLocaleString() + '원' : '<span style="color: #dc2626; font-weight: 600;">미입력 ← 필수 항목</span>'}</div>
                            <div>• 이메일: ${result.email || '<span style="color: #dc2626; font-weight: 600;">미입력 ← 필수 항목</span>'}</div>
        `;

        if (result.errors.length > 0) {
            html += '<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #fca5a5;">';
            result.errors.forEach(error => {
                html += `<div style="color: #dc2626;">⚠️ ${error}</div>`;
            });
            html += '</div>';
        }

        html += `
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';

    // 요약 메시지
    if (invalidResults.length > 0) {
        html += `<div style="margin-top: 16px; padding: 12px; background-color: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; color: #92400e;">
            <strong>총 ${validationData.results.length}개 주문 중 ${invalidResults.length}개에 문제가 있습니다.</strong>
        </div>`;
    }

    content.innerHTML = html;

    // 버튼 생성
    let buttonsHtml = `
        <button onclick="closePaymentCompletionValidationModal()" style="padding: 10px 20px; background-color: #e5e7eb; color: #374151; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#d1d5db'" onmouseout="this.style.backgroundColor='#e5e7eb'">
            취소
        </button>
    `;

    if (invalidResults.length > 0) {
        // 문제가 있는 경우
        if (validResults.length > 0) {
            // 일부만 문제있음 - 문제없는 것만 발송 옵션 제공
            buttonsHtml += `
                <button onclick="sendOnlyValidPaymentCompletionOrders()" style="padding: 10px 20px; background-color: #3b82f6; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#2563eb'" onmouseout="this.style.backgroundColor='#3b82f6'">
                    문제없는 ${validResults.length}개 주문만 발송
                </button>
            `;
        }

        buttonsHtml += `
            <button onclick="closePaymentCompletionValidationModal(); highlightProblemOrders(${JSON.stringify(invalidResults).replace(/"/g, '&quot;')})" style="padding: 10px 20px; background-color: #dc2626; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#b91c1c'" onmouseout="this.style.backgroundColor='#dc2626'">
                확인 - 문제 주문 확인하기
            </button>
        `;
    } else {
        // 모든 주문이 정상인 경우
        buttonsHtml += `
            <button onclick="confirmPaymentCompletionSend()" style="padding: 10px 20px; background-color: #3b82f6; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#2563eb'" onmouseout="this.style.backgroundColor='#3b82f6'">
                발송하기
            </button>
        `;
    }

    buttonsContainer.innerHTML = buttonsHtml;

    // 모달 표시
    modal.style.display = 'flex';
}

function showQuotationValidationModal(validationData) {
    const modal = document.getElementById('quotationValidationModal');
    const content = document.getElementById('quotationValidationContent');
    const buttonsContainer = document.getElementById('quotationValidationButtons');

    // 유효한 주문들과 무효한 주문들 분리
    const validResults = validationData.results.filter(r => r.valid);
    const invalidResults = validationData.results.filter(r => !r.valid);

    validOrderIds = validResults.map(r => r.order_id);

    // 컨텐츠 생성
    let html = `<p style="margin-bottom: 16px; color: #6b7280;">다음 ${validationData.results.length}개 주문에 이메일을 발송합니다:</p>`;

    html += '<div style="max-height: 400px; overflow-y: auto;">';

    // 유효한 주문들
    validResults.forEach(result => {
        html += `
            <div style="padding: 12px; margin-bottom: 12px; background-color: #f0fdf4; border: 1px solid #86efac; border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <span style="color: #16a34a; font-size: 18px;">✓</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #166534; margin-bottom: 4px;">Order ${result.order_id} (${result.customer_name})</div>
                        <div style="font-size: 14px; color: #15803d;">
                            <div>• 결제 금액: ${result.payment_amount ? Number(result.payment_amount).toLocaleString() + '원' : '-'}</div>
                            <div>• 이메일: ${result.email}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    // 무효한 주문들
    invalidResults.forEach(result => {
        html += `
            <div style="padding: 12px; margin-bottom: 12px; background-color: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <span style="color: #dc2626; font-size: 18px;">✗</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #991b1b; margin-bottom: 4px;">Order ${result.order_id} (${result.customer_name || '정보 없음'})</div>
                        <div style="font-size: 14px; color: #b91c1c;">
                            <div>• 결제 금액: ${result.payment_amount ? Number(result.payment_amount).toLocaleString() + '원' : '<span style="color: #dc2626; font-weight: 600;">미입력 ← 필수 항목</span>'}</div>
                            <div>• 이메일: ${result.email || '<span style="color: #dc2626; font-weight: 600;">미입력 ← 필수 항목</span>'}</div>
        `;

        if (result.errors.length > 0) {
            html += '<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #fca5a5;">';
            result.errors.forEach(error => {
                html += `<div style="color: #dc2626;">⚠️ ${error}</div>`;
            });
            html += '</div>';
        }

        html += `
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';

    // 요약 메시지
    if (invalidResults.length > 0) {
        html += `<div style="margin-top: 16px; padding: 12px; background-color: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; color: #92400e;">
            <strong>총 ${validationData.results.length}개 주문 중 ${invalidResults.length}개에 문제가 있습니다.</strong>
        </div>`;
    }

    content.innerHTML = html;

    // 버튼 생성
    let buttonsHtml = `
        <button onclick="closeQuotationValidationModal()" style="padding: 10px 20px; background-color: #e5e7eb; color: #374151; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#d1d5db'" onmouseout="this.style.backgroundColor='#e5e7eb'">
            취소
        </button>
    `;

    if (invalidResults.length > 0) {
        // 문제가 있는 경우
        if (validResults.length > 0) {
            // 일부만 문제있음 - 문제없는 것만 발송 옵션 제공
            buttonsHtml += `
                <button onclick="sendOnlyValidOrders()" style="padding: 10px 20px; background-color: #059669; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#047857'" onmouseout="this.style.backgroundColor='#059669'">
                    문제없는 ${validResults.length}개 주문만 발송
                </button>
            `;
        }

        buttonsHtml += `
            <button onclick="closeQuotationValidationModal(); highlightProblemOrders(${JSON.stringify(invalidResults).replace(/"/g, '&quot;')})" style="padding: 10px 20px; background-color: #dc2626; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#b91c1c'" onmouseout="this.style.backgroundColor='#dc2626'">
                    확인 - 문제 주문 확인하기
                </button>
        `;
    } else {
        // 모든 주문이 정상인 경우
        buttonsHtml += `
            <button onclick="confirmQuotationSend()" style="padding: 10px 20px; background-color: #059669; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#047857'" onmouseout="this.style.backgroundColor='#059669'">
                발송하기
            </button>
        `;
    }

    buttonsContainer.innerHTML = buttonsHtml;

    // 모달 표시
    modal.style.display = 'flex';
}

// 속기록 초안/수정안 검증 모달
let validDraftRequestIds = [];

function showDraftValidationModal(validationData) {
    const modal = document.getElementById('draftValidationModal');
    const content = document.getElementById('draftValidationContent');
    const buttonsContainer = document.getElementById('draftValidationButtons');

    // 유효한 요청들과 무효한 요청들 분리
    const validResults = validationData.results.filter(r => r.valid);
    const invalidResults = validationData.results.filter(r => !r.valid);

    validDraftRequestIds = validResults.map(r => r.request_id);

    // 컨텐츠 생성
    let html = `<p style="margin-bottom: 16px; color: #6b7280;">다음 ${validationData.results.length}개 요청에 이메일을 발송합니다:</p>`;

    html += '<div style="max-height: 400px; overflow-y: auto;">';

    // 유효한 요청들
    validResults.forEach(result => {
        const fileName = result.transcript_file ? result.transcript_file.split('/').pop() : '-';
        html += `
            <div style="padding: 12px; margin-bottom: 12px; background-color: #f0fdf4; border: 1px solid #86efac; border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <span style="color: #16a34a; font-size: 18px;">✓</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #166534; margin-bottom: 4px;">Request ${result.request_id} (${result.customer_name})</div>
                        <div style="font-size: 14px; color: #15803d;">
                            <div>• 속기록 파일: ${fileName}</div>
                            <div>• 이메일: ${result.email}</div>
                            <div>• 상태: ${result.status_display}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    // 무효한 요청들
    invalidResults.forEach(result => {
        const fileName = result.transcript_file ? result.transcript_file.split('/').pop() : '<span style="color: #dc2626; font-weight: 600;">미업로드 ← 필수 항목</span>';
        html += `
            <div style="padding: 12px; margin-bottom: 12px; background-color: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <span style="color: #dc2626; font-size: 18px;">✗</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #991b1b; margin-bottom: 4px;">Request ${result.request_id} (${result.customer_name || '정보 없음'})</div>
                        <div style="font-size: 14px; color: #b91c1c;">
                            <div>• 속기록 파일: ${fileName}</div>
                            <div>• 이메일: ${result.email || '<span style="color: #dc2626; font-weight: 600;">미입력 ← 필수 항목</span>'}</div>
                            <div>• 상태: ${result.status_display || '-'}</div>
        `;

        if (result.errors.length > 0) {
            html += '<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #fca5a5;">';
            result.errors.forEach(error => {
                html += `<div style="color: #dc2626;">⚠️ ${error}</div>`;
            });
            html += '</div>';
        }

        html += `
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';

    // 요약 메시지
    if (invalidResults.length > 0) {
        html += `<div style="margin-top: 16px; padding: 12px; background-color: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; color: #92400e;">
            <strong>총 ${validationData.results.length}개 요청 중 ${invalidResults.length}개에 문제가 있습니다.</strong>
        </div>`;
    }

    content.innerHTML = html;

    // 버튼 생성
    let buttonsHtml = `
        <button onclick="closeDraftValidationModal()" style="padding: 10px 20px; background-color: #e5e7eb; color: #374151; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#d1d5db'" onmouseout="this.style.backgroundColor='#e5e7eb'">
            취소
        </button>
    `;

    if (invalidResults.length > 0) {
        // 문제가 있는 경우
        if (validResults.length > 0) {
            // 일부만 문제있음 - 문제없는 것만 발송 옵션 제공
            buttonsHtml += `
                <button onclick="sendOnlyValidDrafts()" style="padding: 10px 20px; background-color: #059669; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#047857'" onmouseout="this.style.backgroundColor='#059669'">
                    문제없는 ${validResults.length}개 요청만 발송
                </button>
            `;
        }

        buttonsHtml += `
            <button onclick="closeDraftValidationModal(); highlightProblemRequests(${JSON.stringify(invalidResults).replace(/"/g, '&quot;')})" style="padding: 10px 20px; background-color: #dc2626; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#b91c1c'" onmouseout="this.style.backgroundColor='#dc2626'">
                확인 - 문제 요청 확인하기
            </button>
        `;
    } else {
        // 모든 요청이 정상인 경우
        buttonsHtml += `
            <button onclick="confirmDraftSend()" style="padding: 10px 20px; background-color: #059669; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#047857'" onmouseout="this.style.backgroundColor='#059669'">
                발송하기
            </button>
        `;
    }

    buttonsContainer.innerHTML = buttonsHtml;

    // 모달 표시
    modal.style.display = 'flex';
}

function closeDraftValidationModal() {
    document.getElementById('draftValidationModal').style.display = 'none';
    validDraftRequestIds = [];
}

function confirmDraftSend() {
    const requestIdsToSend = [...validDraftRequestIds];
    closeDraftValidationModal();

    // 중복 발송 이력 확인
    fetch('/api/send/check-history/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            request_ids: requestIdsToSend,
            email_type: 'draft_guide'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.has_duplicate) {
            showDraftDuplicateModal(data.duplicate_history, requestIdsToSend);
        } else {
            executeSendDraft(requestIdsToSend);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('발송 이력 확인 중 오류가 발생했습니다.', 'error');
    });
}

function sendOnlyValidDrafts() {
    confirmDraftSend();
}

function highlightProblemRequests(invalidResults) {
    // 기존 하이라이트 제거
    document.querySelectorAll('tr[data-request-id]').forEach(row => {
        row.style.borderLeft = '';
    });

    // 문제있는 요청의 셀들을 하이라이트
    invalidResults.forEach(result => {
        const row = document.querySelector(`tr[data-request-id="${result.request_id}"]`);
        if (row) {
            result.errors.forEach(error => {
                if (error.includes('속기록 파일')) {
                    const fileCell = row.querySelector('td[data-field="transcript_file"]');
                    if (fileCell) {
                        fileCell.style.backgroundColor = '#ffb3b3';
                        fileCell.style.transition = 'all 0.3s';
                    }
                }

                if (error.includes('이메일')) {
                    const emailCell = row.querySelector('td[data-field="email"]');
                    if (emailCell) {
                        emailCell.style.backgroundColor = '#ffb3b3';
                        emailCell.style.transition = 'all 0.3s';
                    }
                }

                if (error.includes('상태')) {
                    const statusCell = row.querySelector('td[data-field="status"]');
                    if (statusCell) {
                        statusCell.style.backgroundColor = '#ffb3b3';
                        statusCell.style.transition = 'all 0.3s';
                    }
                }
            });

            row.style.borderLeft = '4px solid #dc2626';
        }
    });

    setTimeout(() => {
        const firstInvalidRow = document.querySelector(`tr[data-request-id="${invalidResults[0].request_id}"]`);
        if (firstInvalidRow) {
            firstInvalidRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, 100);
}

// 속기록 최종안 검증 모달
let validFinalDraftRequestIds = [];

function showFinalDraftValidationModal(validationData) {
    const modal = document.getElementById('finalDraftValidationModal');
    const content = document.getElementById('finalDraftValidationContent');
    const buttonsContainer = document.getElementById('finalDraftValidationButtons');

    // 유효한 요청들과 무효한 요청들 분리
    const validResults = validationData.results.filter(r => r.valid);
    const invalidResults = validationData.results.filter(r => !r.valid);

    validFinalDraftRequestIds = validResults.map(r => r.request_id);

    // 컨텐츠 생성
    let html = `<p style="margin-bottom: 16px; color: #6b7280;">다음 ${validationData.results.length}개 요청에 이메일을 발송합니다:</p>`;

    html += '<div style="max-height: 400px; overflow-y: auto;">';

    // 유효한 요청들
    validResults.forEach(result => {
        const fileName = result.transcript_file ? result.transcript_file.split('/').pop() : '-';
        html += `
            <div style="padding: 12px; margin-bottom: 12px; background-color: #f0fdf4; border: 1px solid #86efac; border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <span style="color: #16a34a; font-size: 18px;">✓</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #166534; margin-bottom: 4px;">Request ${result.request_id} (${result.customer_name})</div>
                        <div style="font-size: 14px; color: #15803d;">
                            <div>• 속기록 파일: ${fileName}</div>
                            <div>• 이메일: ${result.email}</div>
                            <div>• 상태: ${result.status_display}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    // 무효한 요청들
    invalidResults.forEach(result => {
        const fileName = result.transcript_file ? result.transcript_file.split('/').pop() : '<span style="color: #dc2626; font-weight: 600;">미업로드 ← 필수 항목</span>';
        html += `
            <div style="padding: 12px; margin-bottom: 12px; background-color: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <span style="color: #dc2626; font-size: 18px;">✗</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #991b1b; margin-bottom: 4px;">Request ${result.request_id} (${result.customer_name || '정보 없음'})</div>
                        <div style="font-size: 14px; color: #b91c1c;">
                            <div>• 속기록 파일: ${fileName}</div>
                            <div>• 이메일: ${result.email || '<span style="color: #dc2626; font-weight: 600;">미입력 ← 필수 항목</span>'}</div>
                            <div>• 상태: ${result.status_display || '-'}</div>
        `;

        if (result.errors.length > 0) {
            html += '<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #fca5a5;">';
            result.errors.forEach(error => {
                html += `<div style="color: #dc2626;">⚠️ ${error}</div>`;
            });
            html += '</div>';
        }

        html += `
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';

    // 요약 메시지
    if (invalidResults.length > 0) {
        html += `<div style="margin-top: 16px; padding: 12px; background-color: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; color: #92400e;">
            <strong>총 ${validationData.results.length}개 요청 중 ${invalidResults.length}개에 문제가 있습니다.</strong>
        </div>`;
    }

    content.innerHTML = html;

    // 버튼 생성
    let buttonsHtml = `
        <button onclick="closeFinalDraftValidationModal()" style="padding: 10px 20px; background-color: #e5e7eb; color: #374151; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#d1d5db'" onmouseout="this.style.backgroundColor='#e5e7eb'">
            취소
        </button>
    `;

    if (invalidResults.length > 0) {
        // 문제가 있는 경우
        if (validResults.length > 0) {
            // 일부만 문제있음 - 문제없는 것만 발송 옵션 제공
            buttonsHtml += `
                <button onclick="sendOnlyValidFinalDrafts()" style="padding: 10px 20px; background-color: #059669; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#047857'" onmouseout="this.style.backgroundColor='#059669'">
                    문제없는 ${validResults.length}개 요청만 발송
                </button>
            `;
        }

        buttonsHtml += `
            <button onclick="closeFinalDraftValidationModal(); highlightProblemRequests(${JSON.stringify(invalidResults).replace(/"/g, '&quot;')})" style="padding: 10px 20px; background-color: #dc2626; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#b91c1c'" onmouseout="this.style.backgroundColor='#dc2626'">
                확인 - 문제 요청 확인하기
            </button>
        `;
    } else {
        // 모든 요청이 정상인 경우
        buttonsHtml += `
            <button onclick="confirmFinalDraftSend()" style="padding: 10px 20px; background-color: #059669; color: white; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#047857'" onmouseout="this.style.backgroundColor='#059669'">
                발송하기
            </button>
        `;
    }

    buttonsContainer.innerHTML = buttonsHtml;

    // 모달 표시
    modal.style.display = 'flex';
}

function closeFinalDraftValidationModal() {
    document.getElementById('finalDraftValidationModal').style.display = 'none';
    validFinalDraftRequestIds = [];
}

function confirmFinalDraftSend() {
    const requestIdsToSend = [...validFinalDraftRequestIds];
    closeFinalDraftValidationModal();

    // 중복 발송 이력 확인
    fetch('/api/send/check-history/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            request_ids: requestIdsToSend,
            email_type: 'final_draft_guide'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.has_duplicate) {
            showDraftDuplicateModal(data.duplicate_history, requestIdsToSend, true);
        } else {
            executeSendFinalDraft(requestIdsToSend);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('발송 이력 확인 중 오류가 발생했습니다.', 'error');
    });
}

function sendOnlyValidFinalDrafts() {
    confirmFinalDraftSend();
}

function showDuplicateModal(duplicateHistory, endpoint, orderIds, emailType) {
    const modal = document.getElementById('duplicateSendModal');
    const content = document.getElementById('duplicateHistoryContent');

    // 모달 내용 생성
    let html = `
        <p style="color: #374151; margin-bottom: 16px;">다음 주문에 대해 이미 <strong style="color: #dc2626;">${emailType}</strong>를 발송한 이력이 있습니다:</p>
    `;

    duplicateHistory.forEach(item => {
        html += `
            <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; margin-bottom: 12px; border-radius: 4px;">
                <div style="display: grid; grid-template-columns: auto 1fr; gap: 8px; font-size: 14px;">
                    <span style="font-weight: 600; color: #991b1b;">주문번호:</span>
                    <span style="color: #374151;">${item.order_id}</span>

                    <span style="font-weight: 600; color: #991b1b;">발송 상태:</span>
                    <span style="color: #374151;">${item.email_type_display}</span>

                    <span style="font-weight: 600; color: #991b1b;">발송 시간:</span>
                    <span style="color: #374151;">${item.sent_at}</span>

                    <span style="font-weight: 600; color: #991b1b;">안내 금액:</span>
                    <span style="color: #374151;">${Number(item.payment_amount).toLocaleString()}원</span>

                    <span style="font-weight: 600; color: #991b1b;">수신자:</span>
                    <span style="color: #374151;">${item.recipient_email}</span>

                    <span style="font-weight: 600; color: #991b1b;">발송 횟수:</span>
                    <span style="color: #dc2626; font-weight: 600;">${item.send_count}회</span>
                </div>
            </div>
        `;
    });

    html += `<p style="color: #991b1b; font-weight: 500; margin-top: 16px;">정말 다시 발송하시겠습니까?</p>`;

    content.innerHTML = html;

    // 발송 데이터 저장
    pendingSendData = {
        endpoint: endpoint,
        orderIds: orderIds,
        successMessage: `${emailType}를 재발송했습니다.`
    };

    // 모달 표시
    modal.style.display = 'flex';
}

// 초안/최종안용 중복 발송 모달
function showDraftDuplicateModal(duplicateHistory, requestIds, isFinalDraft = false) {
    const modal = document.getElementById('duplicateSendModal');
    const content = document.getElementById('duplicateHistoryContent');

    const emailTypeText = isFinalDraft ? '최종안' : '초안/수정안';

    // 모달 내용 생성
    let html = `
        <p style="color: #374151; margin-bottom: 16px;">선택한 파일 중 다음 파일들은 이미 <strong style="color: #dc2626;">${emailTypeText}</strong>를 발송한 이력이 있습니다:</p>
    `;

    duplicateHistory.forEach(item => {
        html += `
            <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; margin-bottom: 12px; border-radius: 4px;">
                <div style="display: grid; grid-template-columns: auto 1fr; gap: 8px; font-size: 14px;">
                    <span style="font-weight: 600; color: #991b1b;">Request ID:</span>
                    <span style="color: #374151;">${item.request_id}</span>

                    <span style="font-weight: 600; color: #991b1b;">발송 타입:</span>
                    <span style="color: #374151;">${item.email_type_display}</span>

                    <span style="font-weight: 600; color: #991b1b;">발송 시간:</span>
                    <span style="color: #374151;">${item.sent_at}</span>

                    <span style="font-weight: 600; color: #991b1b;">수신자:</span>
                    <span style="color: #374151;">${item.recipient_email}</span>

                    <span style="font-weight: 600; color: #991b1b;">발송 횟수:</span>
                    <span style="color: #dc2626; font-weight: 600;">${item.send_count}회</span>
                </div>
            </div>
        `;
    });

    if (!isFinalDraft) {
        html += `<p style="color: #f59e0b; font-weight: 500; margin-top: 16px; padding: 12px; background-color: #fffbeb; border-radius: 4px; border-left: 4px solid #f59e0b;">⚠️ 수정안을 여러 번 보내는 것은 정상적인 프로세스입니다.</p>`;
    }

    html += `<p style="color: #991b1b; font-weight: 500; margin-top: 16px;">다시 발송하시겠습니까?</p>`;

    content.innerHTML = html;

    // 발송 데이터 저장
    pendingSendData = {
        requestIds: requestIds,
        isFinalDraft: isFinalDraft
    };

    // 모달 표시
    modal.style.display = 'flex';
}

// 결제 완료 안내 발송
function sendPaymentCompletionGuide() {
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkedBoxes.length === 0) {
        showNotification('선택된 주문이 없습니다.', 'error');
        return;
    }

    const orderIds = Array.from(checkedBoxes).map(checkbox =>
        checkbox.getAttribute('data-order-id')
    );

    paymentCompletionOrderIds = orderIds;

    // 검증 API 호출
    fetch('/api/send/validate-payment-completion/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            order_ids: orderIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        // 검증 모달 표시
        showPaymentCompletionValidationModal(data);
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('검증 중 오류가 발생했습니다.', 'error');
    });
}

// 속기록 초안/수정안 요청 안내 발송
function sendDraftGuide() {
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkedBoxes.length === 0) {
        showNotification('선택된 요청이 없습니다.', 'error');
        return;
    }

    const requestIds = Array.from(checkedBoxes).map(checkbox =>
        checkbox.getAttribute('data-request-id')
    );

    // 검증 API 호출
    fetch('/api/send/validate-draft-guide/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            request_ids: requestIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        // 검증 모달 표시
        showDraftValidationModal(data);
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('검증 중 오류가 발생했습니다.', 'error');
    });
}

// 초안/수정안 발송 실행
function executeSendDraft(requestIds) {
    fetch('/api/send/draft-guide/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            request_ids: requestIds
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw { status: response.status, data: data };
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            if (data.errors && data.errors.length > 0) {
                data.errors.forEach(error => {
                    showNotification(error, 'error');
                });
            }
            // 발송 성공 시 페이지 새로고침
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showNotification(data.error || '발송에 실패했습니다.', 'error');
            if (data.errors && data.errors.length > 0) {
                data.errors.forEach(error => {
                    showNotification(error, 'error');
                });
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (error.data && error.data.error) {
            showNotification(error.data.error, 'error');
            if (error.data.errors && error.data.errors.length > 0) {
                error.data.errors.forEach(err => {
                    showNotification(err, 'error');
                });
            }
        } else {
            showNotification('발송 중 오류가 발생했습니다.', 'error');
        }
    });
}

// 속기록 최종안 안내 발송
function sendFinalDraftGuide() {
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkedBoxes.length === 0) {
        showNotification('선택된 요청이 없습니다.', 'error');
        return;
    }

    const requestIds = Array.from(checkedBoxes).map(checkbox =>
        checkbox.getAttribute('data-request-id')
    );

    // 검증 API 호출
    fetch('/api/send/validate-final-draft-guide/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            request_ids: requestIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        // 검증 모달 표시
        showFinalDraftValidationModal(data);
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('검증 중 오류가 발생했습니다.', 'error');
    });
}

// 최종안 발송 실행
function executeSendFinalDraft(requestIds) {
    fetch('/api/send/final-draft-guide/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            request_ids: requestIds
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw { status: response.status, data: data };
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            if (data.errors && data.errors.length > 0) {
                data.errors.forEach(error => {
                    showNotification(error, 'error');
                });
            }
            // 발송 성공 시 페이지 새로고침
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showNotification(data.error || '발송에 실패했습니다.', 'error');
            if (data.errors && data.errors.length > 0) {
                data.errors.forEach(error => {
                    showNotification(error, 'error');
                });
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (error.data && error.data.error) {
            showNotification(error.data.error, 'error');
            if (error.data.errors && error.data.errors.length > 0) {
                error.data.errors.forEach(err => {
                    showNotification(err, 'error');
                });
            }
        } else {
            showNotification('발송 중 오류가 발생했습니다.', 'error');
        }
    });
}


// 파일 업로드 후 탭 생성
async function createFileSettingsTabs(files) {
    console.log(`[CREATE TABS] createFileSettingsTabs 호출 - files.length: ${files.length}`);
    console.log(`[CREATE TABS] 기존 fileTabsData.length: ${fileTabsData.length}`);
    console.log(`[CREATE TABS] 기존 uploadedFilesData.length: ${uploadedFilesData.length}`);
    
    const tabsContainer = document.getElementById('fileTabs');
    const settingsPanel = document.getElementById('fileSettingsPanel');
    const fileTabsContainer = document.getElementById('fileTabsContainer');
    
    // 컨테이너 표시
    fileTabsContainer.style.display = 'block';
    
    // 기존 탭과 패널 초기화
    tabsContainer.innerHTML = '';
    settingsPanel.innerHTML = '';
    fileTabsData = []; // 매번 전체를 다시 생성
    
    // 각 파일에 대해 탭과 설정 패널 생성
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const orderId = document.getElementById('orderIdInput').value;
        const requestId = `${orderId}${String(i).padStart(2, '0')}`;
        
        // 미디어 길이 추출 (업로드 전에 미리 저장된 길이 사용)
        let duration = '00:00:00';
        if (file.file_type && (file.file_type.startsWith('audio/') || file.file_type.startsWith('video/'))) {
            // 파일 객체에서 미리 계산된 duration이 있는지 확인
            duration = file.duration || '00:00:00';
            console.log(`[DEBUG] createFileSettingsTabs - 미디어 파일: ${file.original_name}, duration: ${duration}`);
        } else {
            console.log(`[DEBUG] createFileSettingsTabs - 일반 파일: ${file.original_name}, duration: 00:00:00 (기본값)`);
        }
        
        // 파일 탭 데이터 저장
        console.log(`[DEBUG] fileTabsData 생성 - 파일: ${file.original_name}, duration: ${duration}`);
        fileTabsData.push({
            file: file,
            requestId: requestId,
            recordingType: '전체',
            recordingLocation: '통화',
            totalDuration: duration,
            partialRange: '',
            speakerCount: 1,
            speakerNames: '',
            recordingDate: '',
            additionalInfo: ''
        });
        
        // 탭 버튼 생성
        const tab = document.createElement('div');
        tab.id = `fileTab${i}`;
        tab.className = 'file-tab';
        tab.dataset.index = i;
        
        // 파일명만 표시 (Request ID 제거하고 길이 제한)
        const fileName = file.original_name || file.name;
        // 동적 탭 너비 계산 (파일 개수에 따라 크롬 탭처럼 작아짐)
        const containerWidth = 800; // 대략적인 컨테이너 너비
        const maxTabWidth = 250;
        const minTabWidth = 100;
        const tabWidth = Math.max(minTabWidth, Math.min(maxTabWidth, Math.floor(containerWidth / files.length) - 4));
        
        const displayName = fileName.length > (tabWidth / 8) ? fileName.substring(0, Math.floor(tabWidth / 8) - 3) + '...' : fileName;
        
        tab.style.cssText = `
            flex: 0 1 ${tabWidth}px;
            min-width: ${minTabWidth}px;
            max-width: ${maxTabWidth}px;
            padding: 12px 8px;
            background-color: ${i === 0 ? '#ffffff' : '#f8f9fa'};
            color: ${i === 0 ? '#059669' : '#6b7280'};
            border: 2px solid #e5e7eb;
            border-bottom: ${i === 0 ? '2px solid #ffffff' : '2px solid #e5e7eb'};
            border-radius: 0;
            cursor: pointer;
            font-size: 13px;
            font-weight: ${i === 0 ? '600' : '500'};
            position: relative;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            margin-right: 2px;
            box-shadow: ${i === 0 ? '0 -2px 4px rgba(0,0,0,0.1)' : 'none'};
            z-index: ${i === 0 ? '2' : '1'};
        `;
        
        tab.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; position: relative;">
                <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 20px;" title="${fileName}">${displayName}</span>
                <button class="tab-delete-btn" style="position: absolute; right: 2px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; border: none; background: none; color: #dc2626; cursor: pointer; font-size: 14px; font-weight: bold; opacity: 0; transition: opacity 0.2s; border-radius: 50%; display: flex; align-items: center; justify-content: center;" data-tab-index="${i}" title="삭제">×</button>
            </div>
        `;
        
        // 탭 클릭 이벤트
        // 삭제 버튼 이벤트 리스너 추가
        const deleteBtn = tab.querySelector('.tab-delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const tabIndex = parseInt(deleteBtn.getAttribute('data-tab-index'));
                await deleteFileTab(tabIndex, e);
            });
        }
        
        // 탭 클릭 이벤트
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            switchFileTab(i);
        });
        
        // 탭 호버 이벤트 (삭제 버튼 표시/숨김)
        tab.addEventListener('mouseenter', () => {
            const deleteBtn = tab.querySelector('.tab-delete-btn');
            if (deleteBtn) deleteBtn.style.opacity = '1';
        });
        
        tab.addEventListener('mouseleave', () => {
            const deleteBtn = tab.querySelector('.tab-delete-btn');
            if (deleteBtn) deleteBtn.style.opacity = '0';
        });
        
        tabsContainer.appendChild(tab);
    }
    
    // 첫 번째 탭 활성화
    if (files.length > 0) {
        switchFileTab(0);
    }
}


// 파일 탭 전환
function switchFileTab(index) {
    // 주문자명 필드 validation 방지
    const nameInput = document.getElementById('nameInput');
    if (nameInput) {
        nameInput.required = false;
    }
    
    activeFileTabIndex = index;
    
    // 모든 탭 비활성화
    document.querySelectorAll('.file-tab').forEach((tab, i) => {
        if (i === index) {
            tab.style.backgroundColor = '#ffffff';
            tab.style.color = '#059669';
            tab.style.borderBottom = '2px solid #ffffff';
            tab.style.fontWeight = '600';
            tab.style.boxShadow = '0 -2px 4px rgba(0,0,0,0.1)';
            tab.style.zIndex = '2';
        } else {
            tab.style.backgroundColor = '#f8f9fa';
            tab.style.color = '#6b7280';
            tab.style.borderBottom = '2px solid #e5e7eb';
            tab.style.fontWeight = '500';
            tab.style.boxShadow = 'none';
            tab.style.zIndex = '1';
        }
    });
    
    // 설정 패널 내용 업데이트
    updateFileSettingsPanel(index);
}


// 파일 설정 패널 업데이트
async function updateFileSettingsPanel(index) {
    const settingsPanel = document.getElementById('fileSettingsPanel');
    const fileData = fileTabsData[index];
    
    if (!fileData) return;
    
    console.log(`[DEBUG] updateFileSettingsPanel - index: ${index}, fileData.totalDuration: ${fileData.totalDuration}`);
    
    const panel = document.createElement('div');
    panel.innerHTML = `
        <div style="background-color: #f9fafb; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
            <div style="font-weight: 600; color: #374151; margin-bottom: 8px;">📄 ${fileData.file.original_name || fileData.file.name}</div>
            <div style="font-size: 13px; color: #6b7280;">Request ID: ${fileData.requestId}</div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px;">
            <div>
                <label style="display: block; margin-bottom: 8px; font-size: 14px; font-weight: 500; color: #374151;">녹취 타입 <span style="color: #dc2626;">*</span></label>
                <select id="recordingType${index}" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; box-sizing: border-box;" onchange="updateFileTabData(${index}, 'recordingType', this.value); togglePartialRange(${index})">
                    <option value="전체">전체</option>
                    <option value="부분">부분</option>
                </select>
            </div>
            <div>
                <label style="display: block; margin-bottom: 8px; font-size: 14px; font-weight: 500; color: #374151;">녹음 종류 <span style="color: #dc2626;">*</span></label>
                <select id="recordingLocation${index}" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; box-sizing: border-box;" onchange="updateFileTabData(${index}, 'recordingLocation', this.value)">
                    <option value="통화">통화</option>
                    <option value="현장">현장</option>
                </select>
            </div>
            <div>
                <label style="display: block; margin-bottom: 8px; font-size: 14px; font-weight: 500; color: #374151;">총 길이</label>
                <input id="totalDuration${index}" type="text" value="${fileData.totalDuration}" placeholder="예: 01:30:00" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; box-sizing: border-box;" oninput="updateFileTabData(${index}, 'totalDuration', this.value)">
            </div>
        </div>

        <div style="margin-bottom: 16px;">
            <label style="display: block; margin-bottom: 8px; font-size: 14px; font-weight: 500; color: #374151;">부분 녹취 구간 <span id="partialRangeRequired${index}" style="color: #dc2626; display: none;">*</span></label>
            <textarea id="partialRange${index}" rows="2" placeholder="예: 00:00:00-00:30:00 또는 00:00:00-00:30:00, 00:45:00-01:00:00" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; box-sizing: border-box; resize: vertical; background-color: #f3f4f6; color: #9ca3af;" disabled oninput="updateFileTabData(${index}, 'partialRange', this.value)"></textarea>
            <div id="partialRangeError${index}" style="color: #dc2626; font-size: 12px; margin-top: 4px; display: none;"></div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 16px; margin-bottom: 16px;">
            <div>
                <label style="display: block; margin-bottom: 8px; font-size: 14px; font-weight: 500; color: #374151;">화자수 <span style="color: #dc2626;">*</span></label>
                <input id="speakerCount${index}" type="number" min="1" max="10" value="${fileData.speakerCount}" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; box-sizing: border-box;" oninput="updateFileTabData(${index}, 'speakerCount', this.value)">
            </div>
            <div>
                <label style="display: block; margin-bottom: 8px; font-size: 14px; font-weight: 500; color: #374151;">화자 이름</label>
                <input id="speakerNames${index}" type="text" placeholder="예: 홍길동,김철수" value="${fileData.speakerNames}" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; box-sizing: border-box;" oninput="updateFileTabData(${index}, 'speakerNames', this.value)">
            </div>
        </div>
        
        <div style="margin-bottom: 16px;">
            <label for="recordingDate${index}" style="display: block; margin-bottom: 8px; font-size: 14px; font-weight: 500; color: #374151; cursor: pointer;" onclick="document.getElementById('recordingDate${index}').focus(); document.getElementById('recordingDate${index}').showPicker()">녹음 일시</label>
            <input id="recordingDate${index}" type="datetime-local" value="${fileData.recordingDate}" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; box-sizing: border-box; cursor: pointer;" oninput="updateFileTabData(${index}, 'recordingDate', this.value)" onclick="this.showPicker()">
        </div>
        
        <div style="margin-bottom: 16px;">
            <label style="display: block; margin-bottom: 8px; font-size: 14px; font-weight: 500; color: #374151;">상세 정보</label>
            <textarea id="additionalInfo${index}" rows="3" placeholder="추가 정보를 입력하세요" value="${fileData.additionalInfo}" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; box-sizing: border-box; resize: vertical;" oninput="updateFileTabData(${index}, 'additionalInfo', this.value)">${fileData.additionalInfo}</textarea>
        </div>
    `;
    
    settingsPanel.innerHTML = '';
    settingsPanel.appendChild(panel);
    
    // 녹취 타입에 따라 부분 구간 필드 토글
    togglePartialRange(index);
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


// 파일 탭 데이터 업데이트
function updateFileTabData(index, field, value) {
    if (fileTabsData[index]) {
        fileTabsData[index][field] = value;
    }
}

// 부분 녹취 구간 필드 토글
function togglePartialRange(index) {
    const recordingType = document.getElementById(`recordingType${index}`).value;
    const partialRange = document.getElementById(`partialRange${index}`);
    const requiredMark = document.getElementById(`partialRangeRequired${index}`);
    const errorDiv = document.getElementById(`partialRangeError${index}`);

    if (recordingType === '전체') {
        partialRange.disabled = true;
        partialRange.style.backgroundColor = '#f3f4f6';
        partialRange.style.color = '#9ca3af';
        partialRange.value = '';
        updateFileTabData(index, 'partialRange', '');
        if (requiredMark) requiredMark.style.display = 'none';
        if (errorDiv) errorDiv.style.display = 'none';
    } else {
        partialRange.disabled = false;
        partialRange.style.backgroundColor = '#ffffff';
        partialRange.style.color = '#374151';
        if (requiredMark) requiredMark.style.display = 'inline';
    }
}

// 부분 녹취 구간 형식 검증 (HH:MM:SS-HH:MM:SS 또는 다중 구간)
function validatePartialRange(rangeText) {
    if (!rangeText || rangeText.trim() === '') {
        return { valid: false, error: '부분 녹취 구간을 입력해주세요.' };
    }

    // 쉼표로 구간 분리 (다중 구간 지원)
    const ranges = rangeText.split(',').map(r => r.trim()).filter(r => r.length > 0);

    if (ranges.length === 0) {
        return { valid: false, error: '부분 녹취 구간을 입력해주세요.' };
    }

    // HH:MM:SS 형식 정규식
    const timeRegex = /^([0-1][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])$/;

    for (let i = 0; i < ranges.length; i++) {
        const range = ranges[i];

        // 구간은 "HH:MM:SS-HH:MM:SS" 또는 "HH:MM:SS - HH:MM:SS" 형식
        const parts = range.split('-').map(p => p.trim());

        if (parts.length !== 2) {
            return { valid: false, error: `구간 ${i + 1}: 시작-종료 형식이 아닙니다. (예: 00:00:00-00:30:00)` };
        }

        const [startTime, endTime] = parts;

        // 시작 시간 형식 검증
        if (!timeRegex.test(startTime)) {
            return { valid: false, error: `구간 ${i + 1}: 시작 시간이 HH:MM:SS 형식이 아닙니다. (${startTime})` };
        }

        // 종료 시간 형식 검증
        if (!timeRegex.test(endTime)) {
            return { valid: false, error: `구간 ${i + 1}: 종료 시간이 HH:MM:SS 형식이 아닙니다. (${endTime})` };
        }

        // 시작 시간 < 종료 시간 검증
        const startSeconds = timeToSeconds(startTime);
        const endSeconds = timeToSeconds(endTime);

        if (startSeconds >= endSeconds) {
            return { valid: false, error: `구간 ${i + 1}: 시작 시간이 종료 시간보다 크거나 같습니다. (${startTime} >= ${endTime})` };
        }
    }

    return { valid: true, error: null };
}

// HH:MM:SS를 초로 변환
function timeToSeconds(timeStr) {
    const parts = timeStr.split(':');
    const hours = parseInt(parts[0], 10);
    const minutes = parseInt(parts[1], 10);
    const seconds = parseInt(parts[2], 10);
    return hours * 3600 + minutes * 60 + seconds;
}

// 파일 탭 삭제
async function deleteFileTab(index, event) {
    console.log(`[DELETE TAB] deleteFileTab 호출 - index: ${index}`);
    console.log(`[DELETE TAB] fileTabsData.length: ${fileTabsData.length}`);
    console.log(`[DELETE TAB] uploadedFilesData.length: ${uploadedFilesData.length}`);
    
    if (event) event.stopPropagation();
    
    if (fileTabsData.length <= 1) {
        showNotification('최소 하나의 파일은 필요합니다.', 'error');
        return;
    }
    
    if (confirm('이 파일을 삭제하시겠습니까?')) {
        // 파일 데이터에서 제거
        const fileData = fileTabsData[index];
        const fileToDelete = uploadedFilesData[index];
        
        
        // S3/DB에서 파일 삭제
        if (fileToDelete && fileToDelete.file_key) {
            try {
                const response = await fetch('/api/database/delete-uploaded-files/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        file_keys: [fileToDelete.file_key]
                    })
                });
                
                if (!response.ok) {
                    console.error('파일 삭제 실패');
                }
            } catch (error) {
                console.error('파일 삭제 중 오류:', error);
            }
        }
        
        // 현재 활성 탭 인덱스 조정
        const currentActiveIndex = activeFileTabIndex;
        
        fileTabsData.splice(index, 1);
        
        // 업로드된 파일 목록에서도 제거
        uploadedFilesData.splice(index, 1);
        
        // 탭 UI 재생성
        await createFileSettingsTabs(uploadedFilesData);
        
        // 활성 탭 인덱스 재조정
        if (currentActiveIndex >= uploadedFilesData.length) {
            activeFileTabIndex = uploadedFilesData.length - 1;
        } else if (currentActiveIndex === index && index > 0) {
            activeFileTabIndex = index - 1;
        } else {
            activeFileTabIndex = currentActiveIndex > index ? currentActiveIndex - 1 : currentActiveIndex;
        }
        
        // 올바른 탭으로 전환
        if (uploadedFilesData.length > 0) {
            switchFileTab(activeFileTabIndex);
        }
        
        showNotification('파일이 삭제되었습니다.', 'success');
    }
}

// 파일 설정 데이터 수집
function getFileSettingsData() {
    return fileTabsData.map(fileData => ({
        file_key: fileData.file.file_key,
        original_name: fileData.file.original_name,
        file_type: fileData.file.file_type,
        file_size: fileData.file.file_size,
        recording_type: fileData.recordingType,
        recording_location: fileData.recordingLocation,
        total_duration: fileData.totalDuration,
        partial_range: fileData.partialRange,
        speaker_count: fileData.speakerCount,
        speaker_names: fileData.speakerNames,
        recording_date: fileData.recordingDate || null,
        additional_info: fileData.additionalInfo
    }));
}

