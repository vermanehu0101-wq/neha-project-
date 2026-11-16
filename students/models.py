import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class StaffProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile',
    )
    job_title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.get_username()} profile'


class Course(models.Model):
    course_name = models.CharField(max_length=120)
    course_code = models.CharField(max_length=20, unique=True)
    course_duration = models.CharField(max_length=60, help_text='For example: 2 years')
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['course_name']

    def __str__(self):
        return f'{self.course_name} ({self.course_code})'


class Student(models.Model):
    GENDER_CHOICES = [
        ('F', 'Female'),
        ('M', 'Male'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]

    student_id = models.CharField(max_length=12, unique=True, blank=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='student_record',
        blank=True,
        null=True,
    )
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='students')
    profile_image = models.ImageField(upload_to='student_profiles/', blank=True, null=True)
    registration_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-registration_date', 'full_name']

    def clean(self):
        super().clean()
        if self.user_id:
            if self.user.is_staff:
                raise ValidationError({'user': 'Staff accounts cannot be linked to student records.'})
            if StaffProfile.objects.filter(user_id=self.user_id).exists():
                raise ValidationError({'user': 'This account already has a staff profile.'})

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = f'STU-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.student_id} - {self.full_name}'
