// change_list 화면에서 검색 버튼 옆에 삭제 버튼 삽입
function insertDeleteButton() {
  const searchForm = document.querySelector('.changeform-search, .search-form, form[action$="/request/"]');
  if (!searchForm || document.getElementById('custom-delete-btn')) return;
  const searchBtn = searchForm.querySelector('button[type="submit"]');
  if (!searchBtn) return;
  const deleteBtn = document.createElement('button');
  deleteBtn.id = 'custom-delete-btn';
  deleteBtn.type = 'button';
  deleteBtn.className = 'btn btn-danger ml-2';
  deleteBtn.style.opacity = 0.5;
  deleteBtn.style.cursor = 'not-allowed';
  deleteBtn.disabled = true;
  deleteBtn.innerText = '삭제';
  searchBtn.insertAdjacentElement('afterend', deleteBtn);
}

// 삭제 버튼 활성화/비활성화
function updateDeleteButton() {
  const checkboxes = document.querySelectorAll('input[type="checkbox"][name="_selected_action"]');
  const deleteBtn = document.getElementById('custom-delete-btn');
  const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
  if (deleteBtn) {
    if (anyChecked) {
      deleteBtn.disabled = false;
      deleteBtn.style.opacity = 1;
      deleteBtn.style.cursor = 'pointer';
    } else {
      deleteBtn.disabled = true;
      deleteBtn.style.opacity = 0.5;
      deleteBtn.style.cursor = 'not-allowed';
    }
  }
}

document.addEventListener('DOMContentLoaded', function() {
  insertDeleteButton();
  updateDeleteButton();
  document.body.addEventListener('change', function(e) {
    if (e.target && e.target.name === '_selected_action') {
      updateDeleteButton();
    }
  });
  const deleteBtn = document.getElementById('custom-delete-btn');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', function() {
      if (deleteBtn.disabled) return;
      if (!confirm('정말 선택한 요청서를 삭제하시겠습니까? 관련 첨부파일도 S3에서 삭제됩니다.')) return;
      // 선택된 요청서 id 수집
      const checkboxes = document.querySelectorAll('input[type="checkbox"][name="_selected_action"]:checked');
      const ids = Array.from(checkboxes).map(cb => cb.value);
      if (ids.length === 0) return;
      // 삭제 form 생성 및 전송
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = window.location.pathname;
      // CSRF 토큰
      const csrf = document.querySelector('input[name="csrfmiddlewaretoken"]');
      if (csrf) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrf.value;
        form.appendChild(csrfInput);
      }
      // action 값
      const actionInput = document.createElement('input');
      actionInput.type = 'hidden';
      actionInput.name = 'action';
      actionInput.value = 'delete_selected_with_s3';
      form.appendChild(actionInput);
      // id 값
      ids.forEach(id => {
        const idInput = document.createElement('input');
        idInput.type = 'hidden';
        idInput.name = '_selected_action';
        idInput.value = id;
        form.appendChild(idInput);
      });
      document.body.appendChild(form);
      form.submit();
    });
  }
}); 