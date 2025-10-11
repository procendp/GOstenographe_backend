/**
 * Excel Database - Global Variables
 * 전역 변수를 하나의 네임스페이스로 관리
 */

window.ExcelDB = {
    // 파일 탭 관련
    files: {
        activeTabIndex: 0,
        tabsData: [],
        uploadedFiles: []
    },
    
    // 주문 삭제 관련
    delete: {
        orderIds: []
    },
    
    // 검증 관련
    validation: {
        quotationOrderIds: [],
        validOrderIds: [],
        paymentCompletionOrderIds: [],
        validPaymentCompletionOrderIds: [],
        validDraftRequestIds: [],
        validFinalDraftRequestIds: []
    },
    
    // 필드 편집 관련
    fieldEdit: {
        currentRequestId: null,
        currentFieldName: null,
        currentFieldType: null
    },
    
    // 중복 발송 확인 관련
    duplicate: {
        pendingSendData: null
    },
    
    // 테이블 정렬 관련
    table: {
        currentSort: { column: null, direction: null }
    }
};

// 레거시 전역 변수들 (호환성 유지)
let activeFileTabIndex = 0;
let fileTabsData = [];
let uploadedFilesData = [];
let deleteOrderIds = [];
let quotationOrderIds = [];
let validOrderIds = [];
let paymentCompletionOrderIds = [];
let validPaymentCompletionOrderIds = [];
let validDraftRequestIds = [];
let validFinalDraftRequestIds = [];
let currentEditRequestId = null;
let currentEditFieldName = null;
let currentEditFieldType = null;
let pendingSendData = null;
let currentSort = { column: null, direction: null };

