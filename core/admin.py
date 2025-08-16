from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import User

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone')

class CustomLogEntry(LogEntry):
    class Meta:
        proxy = True
        verbose_name = '활동 내역'
        verbose_name_plural = '활동 내역'

    def get_edited_object(self):
        """편집된 객체의 문자열 표현을 반환합니다."""
        content_type = ContentType.objects.get_for_id(self.content_type_id)
        if content_type.model == 'request':
            return f"{self.object_repr}"
        elif content_type.model == 'user':
            return f"{self.object_repr}"
        return self.object_repr

    def get_action_type(self):
        """작업 유형을 한글로 반환합니다."""
        if self.action_flag == ADDITION:
            return "추가"
        elif self.action_flag == CHANGE:
            return "수정"
        elif self.action_flag == DELETION:
            return "삭제"
        return "기타"

    def get_action_message(self):
        """활동 메시지를 생성합니다."""
        obj_name = self.get_edited_object()
        action = self.get_action_type()
        
        if self.content_type.model == 'user':
            if self.action_flag == CHANGE:
                return f"사용자 권한이 변경되었습니다"
            elif self.action_flag == ADDITION:
                return f"새로운 사용자가 추가되었습니다"
        elif self.content_type.model == 'request':
            return f"{obj_name}님의 신청서가 {action}되었습니다"
        
        return f"{obj_name}이(가) {action}되었습니다"

    def __str__(self):
        return self.get_action_message()

@admin.register(CustomLogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['action_time', 'user', 'content_type', 'object_repr', 'action_flag']
    list_filter = ['action_time', 'user', 'content_type']
    ordering = ['-action_time']
    readonly_fields = [field.name for field in LogEntry._meta.fields]
    search_fields = ['object_repr', 'change_message']
    date_hierarchy = 'action_time'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ('username', 'email', 'phone', 'is_admin', 'is_staff')
    list_filter = ('is_admin', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'phone')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'phone')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_admin', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'password1', 'password2'),
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form
