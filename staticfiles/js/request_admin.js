django.jQuery(function($) {
    var $checkbox = $('#id_has_additional_info');
    var $additionalInfo = $('.field-additional_info');
    var $textarea = $('#id_additional_info');

    // 초기 상태 설정
    if (!$checkbox.is(':checked')) {
        $additionalInfo.hide();
    }

    // 체크박스 상태 변경 시 이벤트
    $checkbox.on('change', function() {
        if ($(this).is(':checked')) {
            $additionalInfo.show();
            $textarea.attr('placeholder', '예시:\n- 속기 시 주의사항\n- 특별한 요청사항\n- 기타 참고사항');
        } else {
            $additionalInfo.hide();
        }
    });

    // 페이지 로드 시 placeholder 설정
    $textarea.attr('placeholder', '예시:\n- 속기 시 주의사항\n- 특별한 요청사항\n- 기타 참고사항');
}); 