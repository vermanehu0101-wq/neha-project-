from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import QuizScore


class QuizTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="Student-test-password-42")

    def test_quiz_requires_login(self):
        response = self.client.get(reverse("quiz_start"))
        self.assertRedirects(response, "/login/?next=/quiz/")

    def test_quiz_has_five_questions_with_four_choices(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("quiz_start"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["questions"]), 5)
        self.assertTrue(all(len(question["options"]) == 4 for question in response.context["questions"]))
        self.assertContains(response, "Submit answers")
        self.assertContains(response, 'data-remaining-seconds="300"')

    @patch("quiz.views.time", side_effect=[1000, 1090])
    def test_quiz_timer_keeps_counting_after_refresh(self, mock_time):
        self.client.force_login(self.user)

        first_response = self.client.get(reverse("quiz_start"))
        refreshed_response = self.client.get(reverse("quiz_start"))

        self.assertEqual(first_response.context["remaining_seconds"], 300)
        self.assertEqual(refreshed_response.context["remaining_seconds"], 210)

    @patch("quiz.views.time", side_effect=[1000, 1301])
    def test_expired_quiz_submission_is_reported(self, mock_time):
        self.client.force_login(self.user)
        self.client.get(reverse("quiz_start"))

        response = self.client.post(reverse("quiz_start"), {})

        self.assertContains(response, "Time is up! Your answers have been submitted.")

    def test_perfect_score_is_displayed_and_saved(self):
        self.client.force_login(self.user)
        answers = {
            "q0": "Programming Language",
            "q1": "Guido van Rossum",
            "q2": "#",
            "q3": "print()",
            "q4": "Boolean",
        }

        response = self.client.post(reverse("quiz_start"), answers)

        self.assertContains(response, "5")
        self.assertContains(response, "Excellent! You passed the quiz.")
        self.assertTrue(QuizScore.objects.filter(user=self.user, score=5, total=5).exists())

    def test_result_message_depends_on_score(self):
        self.client.force_login(self.user)

        low_score = self.client.post(reverse("quiz_start"), {})
        self.assertContains(low_score, "Keep learning and try again!")

        good_answers = {"q0": "Programming Language", "q1": "Guido van Rossum"}
        good_score = self.client.post(reverse("quiz_start"), good_answers)
        self.assertContains(good_score, "Good try! Keep practising.")

    def test_regular_user_login_redirects_to_quiz(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "Student-test-password-42"},
        )

        self.assertRedirects(response, reverse("quiz_start"), fetch_redirect_response=False)

    def test_registration_creates_and_signs_in_student(self):
        response = self.client.post(
            reverse("register"),
            {"username": "new_student", "password": "New-student-password-42"},
        )

        self.assertRedirects(response, reverse("quiz_start"), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username="new_student").exists())
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_removed_admin_and_extra_pages_are_unavailable(self):
        self.assertEqual(self.client.get("/admin/").status_code, 404)
        self.client.force_login(self.user)
        for path in ("/manage/", "/scores/", "/attempts/", "/how-to-play/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
