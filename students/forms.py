from datetime import date
from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Course, StaffProfile, Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'full_name',
            'email',
            'phone_number',
            'gender',
            'date_of_birth',
            'address',
            'course',
            'profile_image',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['course'].widget.attrs['class'] = 'form-select'

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth >= date.today():
            raise forms.ValidationError('Date of birth must be in the past.')
        return date_of_birth


class StudentRegistrationForm(StudentForm):
    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('password1', 'password2'):
            self.fields[field_name].widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model()._default_manager.filter(email__iexact=email).exists():
            raise ValidationError('An account already uses this email address.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'The passwords do not match.')
        elif password1:
            name_parts = cleaned_data.get('full_name', '').split(maxsplit=1)
            user = get_user_model()(
                username='student',
                email=cleaned_data.get('email', ''),
                first_name=name_parts[0] if name_parts else '',
                last_name=name_parts[1] if len(name_parts) > 1 else '',
            )
            try:
                password_validation.validate_password(password1, user)
            except ValidationError as error:
                self.add_error('password1', error)
        return cleaned_data

    def save(self, commit=True):
        student = super().save(commit=False)
        if not commit:
            return student

        with transaction.atomic():
            student.save()
            name_parts = student.full_name.split(maxsplit=1)
            user = get_user_model()._default_manager.create_user(
                username=f'student-{uuid4().hex}',
                email=student.email,
                password=self.cleaned_data['password1'],
                first_name=name_parts[0] if name_parts else '',
                last_name=name_parts[1] if len(name_parts) > 1 else '',
            )
            student.user = user
            student.save(update_fields=['user'])
        return student


class StudentAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Enter the correct email address and password for a student account.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'] = forms.EmailField(
            label='Email address',
            max_length=254,
            widget=forms.EmailInput(
                attrs={'autofocus': True, 'autocomplete': 'email', 'class': 'form-control'}
            ),
        )
        self.fields['password'].widget.attrs['class'] = 'form-control'

    def clean(self):
        email = self.cleaned_data.get('username')
        if email:
            student = Student.objects.select_related('user').filter(email__iexact=email).first()
            if not student or not student.user_id:
                raise ValidationError(self.error_messages['invalid_login'], code='invalid_login')
            self.cleaned_data['username'] = student.user.get_username()
        cleaned_data = super().clean()
        if self.user_cache and self.user_cache.is_staff:
            raise ValidationError(self.error_messages['invalid_login'], code='invalid_login')
        return cleaned_data


class StaffAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Enter the correct username and password for a staff account.',
    }

    def clean(self):
        cleaned_data = super().clean()
        if self.user_cache and not self.user_cache.is_staff:
            raise ValidationError(self.error_messages['invalid_login'], code='invalid_login')
        return cleaned_data


class StaffRegistrationForm(UserCreationForm):
    is_superuser = False

    email = forms.EmailField()
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    job_title = forms.CharField(max_length=100, required=False)
    department = forms.CharField(max_length=100, required=False)
    phone_number = forms.CharField(max_length=20, required=False)

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model()._default_manager.filter(email__iexact=email).exists():
            raise ValidationError('An account already uses this email address.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_staff = True
        user.is_superuser = self.is_superuser

        if commit:
            with transaction.atomic():
                user.save()
                StaffProfile.objects.create(
                    user=user,
                    job_title=self.cleaned_data['job_title'],
                    department=self.cleaned_data['department'],
                    phone_number=self.cleaned_data['phone_number'],
                )
        return user


class AdminRegistrationForm(StaffRegistrationForm):
    is_superuser = True


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_name', 'course_code', 'course_duration', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
