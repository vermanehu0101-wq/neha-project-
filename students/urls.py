from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('students/register/', views.student_registration, name='student-registration'),
    path('students/registered/', views.registration_success, name='registration-success'),
    path('students/login/', views.StudentLoginView.as_view(), name='student-login'),
    path('students/logout/', views.StudentLogoutView.as_view(), name='student-logout'),
    path('students/portal/', views.student_portal, name='student-portal'),
    path('staff/register/', views.staff_registration, name='staff-registration'),
    path('staff/register-admin/', views.admin_registration, name='admin-registration'),
    path('setup-admin/', views.admin_setup, name='admin-setup'),
    path('students/', views.staff_required(views.StudentListView.as_view()), name='student-list'),
    path('students/add/', views.staff_required(views.StudentCreateView.as_view()), name='student-create'),
    path('students/<int:pk>/', views.staff_required(views.StudentDetailView.as_view()), name='student-detail'),
    path('students/<int:pk>/edit/', views.staff_required(views.StudentUpdateView.as_view()), name='student-update'),
    path('students/<int:pk>/delete/', views.staff_required(views.StudentDeleteView.as_view()), name='student-delete'),
    path('courses/', views.staff_required(views.CourseListView.as_view()), name='course-list'),
    path('courses/add/', views.staff_required(views.CourseCreateView.as_view()), name='course-create'),
    path('courses/<int:pk>/edit/', views.staff_required(views.CourseUpdateView.as_view()), name='course-update'),
    path('courses/<int:pk>/delete/', views.staff_required(views.CourseDeleteView.as_view()), name='course-delete'),
]
