from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q

from .models import Course, StaffProfile, Student

User = get_user_model()


class StudentAdminForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        eligible_users = User.objects.filter(
            is_staff=False,
            staff_profile__isnull=True,
        ).filter(Q(student_record__isnull=True) | Q(pk=self.instance.user_id))
        self.fields['user'].queryset = eligible_users


class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    can_delete = False
    extra = 0


class StaffUserAdmin(UserAdmin):
    inlines = [*UserAdmin.inlines, StaffProfileInline]


admin.site.unregister(User)
admin.site.register(User, StaffUserAdmin)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'job_title', 'department', 'phone_number')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = ('department', 'job_title')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'course_code', 'course_duration')
    search_fields = ('course_name', 'course_code')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
    list_display = ('student_id', 'full_name', 'email', 'user', 'course', 'registration_date')
    list_filter = ('course', 'gender')
    search_fields = ('student_id', 'full_name', 'email', 'user__username', 'user__email')
