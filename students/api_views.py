from django.db.models import Count
from rest_framework import permissions, viewsets

from .models import Course, Student
from .serializers import CourseSerializer, StudentSerializer


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.select_related('course').all()
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAdminUser]


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.annotate(student_count=Count('students')).all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAdminUser]
