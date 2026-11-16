from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import Http404
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    AdminRegistrationForm,
    CourseForm,
    StaffAuthenticationForm,
    StaffRegistrationForm,
    StudentAuthenticationForm,
    StudentForm,
    StudentRegistrationForm,
)
from .models import Course, Student

User = get_user_model()


class StaffLoginView(LoginView):
    form_class = StaffAuthenticationForm
    template_name = 'registration/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        has_superuser = User._default_manager.filter(is_superuser=True).exists()
        context['admin_setup_available'] = settings.DEBUG and not has_superuser
        context['admin_registration_available'] = has_superuser
        return context


def staff_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect('student-portal')
        return view_func(request, *args, **kwargs)

    return wrapped


@staff_required
def dashboard(request):
    totals = Student.objects.aggregate(total=Count('id'))
    courses = Course.objects.annotate(student_count=Count('students'))
    context = {
        'total_students': totals['total'],
        'total_courses': Course.objects.count(),
        'recent_students': Student.objects.select_related('course')[:5],
        'courses': courses,
    }
    return render(request, 'students/dashboard.html', context)


class StudentListView(ListView):
    model = Student
    template_name = 'students/student_list.html'
    context_object_name = 'students'
    paginate_by = 10

    def get_queryset(self):
        queryset = Student.objects.select_related('course')
        query = self.request.GET.get('q', '').strip()
        course_id = self.request.GET.get('course', '')
        gender = self.request.GET.get('gender', '')
        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query)
                | Q(student_id__icontains=query)
                | Q(email__icontains=query)
                | Q(course__course_name__icontains=query)
            )
        if course_id.isdigit():
            queryset = queryset.filter(course_id=course_id)
        if gender in dict(Student.GENDER_CHOICES):
            queryset = queryset.filter(gender=gender)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['courses'] = Course.objects.all()
        context['selected_course'] = self.request.GET.get('course', '')
        context['selected_gender'] = self.request.GET.get('gender', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['gender_choices'] = Student.GENDER_CHOICES
        return context


class StudentDetailView(DetailView):
    model = Student
    queryset = Student.objects.select_related('course')
    template_name = 'students/student_detail.html'
    context_object_name = 'student'


class StudentCreateView(CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('student-list')

    def form_valid(self, form):
        messages.success(self.request, 'Student added successfully.')
        return super().form_valid(form)


class StudentUpdateView(UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('student-list')

    def form_valid(self, form):
        messages.success(self.request, 'Student details updated.')
        return super().form_valid(form)


class StudentDeleteView(DeleteView):
    model = Student
    template_name = 'students/student_confirm_delete.html'
    success_url = reverse_lazy('student-list')

    def form_valid(self, form):
        messages.success(self.request, 'Student deleted.')
        return super().form_valid(form)


class CourseListView(ListView):
    model = Course
    template_name = 'students/course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.annotate(student_count=Count('students'))


class CourseCreateView(CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'students/course_form.html'
    success_url = reverse_lazy('course-list')

    def form_valid(self, form):
        messages.success(self.request, 'Course added successfully.')
        return super().form_valid(form)


class CourseUpdateView(UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'students/course_form.html'
    success_url = reverse_lazy('course-list')

    def form_valid(self, form):
        messages.success(self.request, 'Course updated successfully.')
        return super().form_valid(form)


class CourseDeleteView(DeleteView):
    model = Course
    template_name = 'students/course_confirm_delete.html'
    success_url = reverse_lazy('course-list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'This course has students assigned and cannot be deleted.')
            return redirect(self.success_url)
        messages.success(self.request, 'Course deleted.')
        return response


def student_registration(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()
            login(request, student.user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Registration complete. Welcome to your student portal.')
            return redirect('student-portal')
    else:
        form = StudentRegistrationForm()
    return render(request, 'students/registration_form.html', {'form': form})


def registration_success(request):
    return render(request, 'students/registration_success.html')


@login_required
@permission_required('auth.add_user', raise_exception=True)
def staff_registration(request):
    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Staff account for {user.get_full_name()} created.')
            return redirect('dashboard')
    else:
        form = StaffRegistrationForm()
    return render(request, 'students/staff_registration_form.html', {'form': form})


def admin_setup(request):
    if not settings.DEBUG or User._default_manager.filter(is_superuser=True).exists():
        raise Http404

    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                if User._default_manager.filter(is_superuser=True).exists():
                    form.add_error(None, 'An administrator has already been created.')
                    user = None
                else:
                    user = form.save()
            if user:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Administrator account created. Welcome to the dashboard.')
                return redirect('dashboard')
    else:
        form = AdminRegistrationForm()
    return render(request, 'registration/admin_setup_form.html', {'form': form})


@login_required
def admin_registration(request):
    if not request.user.is_superuser:
        raise Http404

    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Administrator account for {user.get_full_name()} created.')
            return redirect('dashboard')
    else:
        form = AdminRegistrationForm()
    return render(request, 'registration/admin_registration_form.html', {'form': form})


class StudentLoginView(LoginView):
    form_class = StudentAuthenticationForm
    template_name = 'registration/student_login.html'
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return reverse_lazy('student-portal')

    def get_success_url(self):
        return self.get_default_redirect_url()


class StudentLogoutView(LogoutView):
    next_page = reverse_lazy('student-login')


@login_required(login_url='student-login')
def student_portal(request):
    if request.user.is_staff:
        return redirect('dashboard')
    student = get_object_or_404(
        Student.objects.select_related('course'),
        user=request.user,
    )
    return render(request, 'students/student_portal.html', {'student': student})
