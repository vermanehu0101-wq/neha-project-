from rest_framework import serializers

from .models import Course, Student


class CourseSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'course_name', 'course_code', 'course_duration', 'description', 'student_count']
        read_only_fields = ['id', 'student_count']


class StudentSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.course_name', read_only=True)

    class Meta:
        model = Student
        fields = [
            'id',
            'student_id',
            'full_name',
            'email',
            'phone_number',
            'gender',
            'date_of_birth',
            'address',
            'course',
            'course_name',
            'profile_image',
            'registration_date',
        ]
        read_only_fields = ['id', 'student_id', 'registration_date']
