from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Course, StaffProfile, Student


class StudentManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='staff',
            password='strong-test-password-781',
            is_staff=True,
        )
        cls.course = Course.objects.create(
            course_name='Computer Science',
            course_code='CS101',
            course_duration='3 years',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def student_data(self, **overrides):
        data = {
            'full_name': 'Alex Student',
            'email': 'alex@example.com',
            'phone_number': '555-0101',
            'gender': 'N',
            'date_of_birth': '2002-05-12',
            'address': '100 Campus Road',
            'course': self.course.pk,
        }
        data.update(overrides)
        return data

    @override_settings(DEBUG=True)
    def test_staff_login_logout_and_password_change(self):
        self.client.logout()
        self.assertContains(
            self.client.get(reverse('login')),
            'Create first admin',
        )
        login = self.client.post(
            reverse('login'),
            {'username': 'staff', 'password': 'strong-test-password-781'},
        )
        self.assertRedirects(login, reverse('dashboard'))
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

        changed = self.client.post(
            reverse('password_change'),
            {
                'old_password': 'strong-test-password-781',
                'new_password1': 'another-strong-password-792',
                'new_password2': 'another-strong-password-792',
            },
        )
        self.assertRedirects(changed, reverse('password_change_done'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('another-strong-password-792'))

        logout = self.client.post(reverse('logout'))
        self.assertRedirects(logout, reverse('login'))
        self.assertRedirects(self.client.get(reverse('dashboard')), reverse('login') + '?next=/')

    def test_student_web_crud_search_and_registration(self):
        create = self.client.post(reverse('student-create'), self.student_data())
        self.assertRedirects(create, reverse('student-list'))
        student = Student.objects.get(email='alex@example.com')
        self.assertTrue(student.student_id.startswith('STU-'))

        detail = self.client.get(reverse('student-detail', args=[student.pk]))
        self.assertContains(detail, 'Alex Student')

        update = self.client.post(
            reverse('student-update', args=[student.pk]),
            self.student_data(full_name='Alex Updated'),
        )
        self.assertRedirects(update, reverse('student-list'))
        student.refresh_from_db()
        self.assertEqual(student.full_name, 'Alex Updated')

        results = self.client.get(reverse('student-list'), {'q': 'Alex Updated', 'course': self.course.pk})
        self.assertEqual(list(results.context['students']), [student])
        self.assertEqual(results.context['students'].count(), 1)

        delete = self.client.post(reverse('student-delete', args=[student.pk]))
        self.assertRedirects(delete, reverse('student-list'))
        self.assertFalse(Student.objects.filter(pk=student.pk).exists())

        self.client.logout()
        registration = self.client.post(
            reverse('student-registration'),
            self.student_data(
                email='new@example.com',
                password1='Giraffe!Cloud#7264',
                password2='Giraffe!Cloud#7264',
            ),
        )
        self.assertRedirects(registration, reverse('student-portal'))
        student = Student.objects.get(email='new@example.com')
        self.assertIsNotNone(student.user)
        self.assertTrue(student.user.check_password('Giraffe!Cloud#7264'))
        self.assertEqual(self.client.get(reverse('student-portal')).status_code, 200)

    def test_course_web_crud_and_protected_delete(self):
        create = self.client.post(
            reverse('course-create'),
            {
                'course_name': 'Mathematics',
                'course_code': 'MATH1',
                'course_duration': '2 years',
                'description': 'Applied mathematics',
            },
        )
        self.assertRedirects(create, reverse('course-list'))
        course = Course.objects.get(course_code='MATH1')

        update = self.client.post(
            reverse('course-update', args=[course.pk]),
            {
                'course_name': 'Advanced Mathematics',
                'course_code': 'MATH1',
                'course_duration': '3 years',
                'description': '',
            },
        )
        self.assertRedirects(update, reverse('course-list'))
        course.refresh_from_db()
        self.assertEqual(course.course_name, 'Advanced Mathematics')

        student = Student.objects.create(
            full_name='Enrolled Student',
            email='enrolled@example.com',
            course=course,
        )
        protected_delete = self.client.post(reverse('course-delete', args=[course.pk]))
        self.assertRedirects(protected_delete, reverse('course-list'))
        self.assertTrue(Course.objects.filter(pk=course.pk).exists())
        student.delete()

        delete = self.client.post(reverse('course-delete', args=[course.pk]))
        self.assertRedirects(delete, reverse('course-list'))
        self.assertFalse(Course.objects.filter(pk=course.pk).exists())

    def test_student_and_course_api_support_crud_methods(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        course_url = reverse('api-course-list')
        student_url = reverse('api-student-list')

        course_response = api.post(
            course_url,
            {
                'course_name': 'Data Science',
                'course_code': 'DATA1',
                'course_duration': '2 years',
                'description': 'Data and statistics',
            },
            format='json',
        )
        self.assertEqual(course_response.status_code, 201)
        course_id = course_response.data['id']
        course_detail_url = reverse('api-course-detail', args=[course_id])
        self.assertEqual(api.get(course_url).status_code, 200)
        self.assertEqual(
            api.put(
                course_detail_url,
                {
                    'course_name': 'Data Science and AI',
                    'course_code': 'DATA1',
                    'course_duration': '2 years',
                    'description': 'Data, statistics, and AI',
                },
                format='json',
            ).status_code,
            200,
        )
        self.assertEqual(
            api.patch(course_detail_url, {'course_duration': '3 years'}, format='json').status_code,
            200,
        )

        student_response = api.post(
            student_url,
            {
                'full_name': 'API Student',
                'email': 'api@example.com',
                'phone_number': '',
                'gender': 'F',
                'date_of_birth': None,
                'address': '',
                'course': course_id,
            },
            format='json',
        )
        self.assertEqual(student_response.status_code, 201)
        student_id = student_response.data['id']
        student_detail_url = reverse('api-student-detail', args=[student_id])
        self.assertEqual(api.get(student_url).status_code, 200)
        self.assertEqual(
            api.put(
                student_detail_url,
                {
                    'full_name': 'API Student Updated',
                    'email': 'api@example.com',
                    'phone_number': '555-0110',
                    'gender': 'F',
                    'date_of_birth': None,
                    'address': 'New address',
                    'course': course_id,
                },
                format='json',
            ).status_code,
            200,
        )
        self.assertEqual(
            api.patch(student_detail_url, {'full_name': 'Patched Student'}, format='json').status_code,
            200,
        )
        self.assertEqual(api.delete(student_detail_url).status_code, 204)
        self.assertEqual(api.delete(course_detail_url).status_code, 204)

    def test_management_pages_and_api_require_authentication(self):
        self.client.logout()
        self.assertRedirects(
            self.client.get(reverse('student-list')),
            reverse('login') + '?next=/students/',
        )
        response = self.client.get(reverse('api-student-list'))
        self.assertIn(response.status_code, (401, 403))

    def test_default_courses_are_created_once_with_requested_durations(self):
        expected = {
            'BSA': ('BSA', '3 years'),
            'BSCCS': ('BSc CS', '3 years'),
            'MCA': ('MCA', '2 years'),
            'MSC': ('MSc', '2 years'),
        }
        for code, (name, duration) in expected.items():
            course = Course.objects.get(course_code=code)
            self.assertEqual(course.course_name, name)
            self.assertEqual(course.course_duration, duration)

    def test_staff_profiles_are_managed_in_django_admin(self):
        admin_user = get_user_model().objects.create_superuser(
            username='administrator',
            password='strong-admin-password-783',
        )
        self.client.force_login(admin_user)
        response = self.client.get(reverse('admin:students_staffprofile_add'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Department')
        self.assertContains(
            self.client.get(reverse('admin:auth_user_add')),
            'Department',
        )

        profile = StaffProfile.objects.create(
            user=self.user,
            job_title='Registrar',
            department='Admissions',
            phone_number='555-0123',
        )
        self.assertEqual(profile.user, self.user)
        self.assertContains(
            self.client.get(reverse('admin:students_staffprofile_changelist')),
            'Admissions',
        )

    def test_student_login_is_email_based_and_only_shows_own_profile(self):
        self.client.logout()
        registration = self.client.post(
            reverse('student-registration'),
            self.student_data(
                full_name='Portal Student',
                email='portal@example.com',
                password1='Giraffe!Cloud#7264',
                password2='Giraffe!Cloud#7264',
            ),
        )
        self.assertRedirects(registration, reverse('student-portal'))
        student = Student.objects.get(email='portal@example.com')
        other_student = Student.objects.create(
            full_name='Private Other Student',
            email='other@example.com',
            course=self.course,
        )
        portal = self.client.get(reverse('student-portal'))
        self.assertContains(portal, 'Portal Student')
        self.assertNotContains(portal, other_student.full_name)
        self.assertRedirects(
            self.client.get(reverse('student-list')),
            reverse('student-portal'),
        )

        self.client.post(reverse('student-logout'))
        staff_login = self.client.post(
            reverse('login'),
            {
                'username': student.user.username,
                'password': 'Giraffe!Cloud#7264',
            },
        )
        self.assertEqual(staff_login.status_code, 200)
        student_login = self.client.post(
            reverse('student-login'),
            {
                'username': 'PORTAL@example.com',
                'password': 'Giraffe!Cloud#7264',
            },
        )
        self.assertRedirects(student_login, reverse('student-portal'))

        api = APIClient()
        api.force_authenticate(user=student.user)
        self.assertEqual(api.get(reverse('api-student-list')).status_code, 403)

    def test_staff_registration_requires_permission_and_creates_profile(self):
        registration_url = reverse('staff-registration')
        self.client.logout()
        self.assertRedirects(
            self.client.get(registration_url),
            reverse('login') + '?next=' + registration_url,
        )

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(registration_url).status_code, 403)

        admin_user = get_user_model().objects.create_superuser(
            username='staff-admin',
            password='strong-admin-password-783',
        )
        self.client.force_login(admin_user)
        self.assertEqual(self.client.get(registration_url).status_code, 200)
        response = self.client.post(
            registration_url,
            {
                'username': 'new-registrar',
                'email': 'registrar@example.com',
                'first_name': 'New',
                'last_name': 'Registrar',
                'job_title': 'Registrar',
                'department': 'Admissions',
                'phone_number': '555-0199',
                'password1': 'Riverstone!Orbit4726',
                'password2': 'Riverstone!Orbit4726',
            },
        )
        self.assertRedirects(response, reverse('dashboard'))
        new_user = get_user_model().objects.get(username='new-registrar')
        self.assertTrue(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)
        self.assertTrue(new_user.check_password('Riverstone!Orbit4726'))
        self.assertEqual(new_user.staff_profile.department, 'Admissions')

    @override_settings(DEBUG=True)
    def test_first_admin_setup_is_one_time_and_creates_admin_profile(self):
        setup_url = reverse('admin-setup')
        self.client.logout()
        self.assertContains(self.client.get(reverse('login')), 'Create first admin')
        self.assertEqual(self.client.get(setup_url).status_code, 200)

        response = self.client.post(
            setup_url,
            {
                'username': 'first-admin',
                'email': 'admin@example.com',
                'first_name': 'Campus',
                'last_name': 'Administrator',
                'job_title': 'Administrator',
                'department': 'Administration',
                'phone_number': '555-0188',
                'password1': 'Amber!Harbor_5730',
                'password2': 'Amber!Harbor_5730',
            },
        )
        self.assertRedirects(response, reverse('dashboard'))
        admin_user = get_user_model().objects.get(username='first-admin')
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_staff)
        self.assertEqual(admin_user.staff_profile.department, 'Administration')
        self.assertEqual(self.client.get(setup_url).status_code, 404)
        self.assertNotContains(self.client.get(reverse('login')), 'Create first admin')
        self.assertContains(self.client.get(reverse('login')), 'Create admin')

        admin_registration_url = reverse('admin-registration')
        self.assertEqual(self.client.get(admin_registration_url).status_code, 200)
        response = self.client.post(
            admin_registration_url,
            {
                'username': 'second-admin',
                'email': 'second-admin@example.com',
                'first_name': 'Second',
                'last_name': 'Administrator',
                'job_title': 'Administrator',
                'department': 'Administration',
                'phone_number': '',
                'password1': 'Harbor!Maple_8402',
                'password2': 'Harbor!Maple_8402',
            },
        )
        self.assertRedirects(response, reverse('dashboard'))
        second_admin = get_user_model().objects.get(username='second-admin')
        self.assertTrue(second_admin.is_superuser)
        self.assertEqual(second_admin.staff_profile.department, 'Administration')

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(admin_registration_url).status_code, 404)
