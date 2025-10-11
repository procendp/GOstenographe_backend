/**
 * Excel Database - Configuration
 * 상태 정보 및 전환 규칙 정의
 */

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

