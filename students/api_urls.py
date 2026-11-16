from rest_framework.routers import DefaultRouter

from .api_views import CourseViewSet, StudentViewSet

router = DefaultRouter()
router.register('students', StudentViewSet, basename='api-student')
router.register('courses', CourseViewSet, basename='api-course')

urlpatterns = router.urls
