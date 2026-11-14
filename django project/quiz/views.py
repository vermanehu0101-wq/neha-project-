from time import time

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RegistrationForm
from .models import QuizScore


QUIZ_DURATION_SECONDS = 5 * 60
QUIZ_DEADLINE_SESSION_KEY = "quiz_deadline"


questions = [
    {
        "question": "1. What is Python?",
        "options": ["Programming Language", "Browser", "Database", "Operating System"],
        "answer": "Programming Language",
    },
    {
        "question": "2. Who developed Python?",
        "options": ["Google", "Guido van Rossum", "Microsoft", "Apple"],
        "answer": "Guido van Rossum",
    },
    {
        "question": "3. Which symbol is used for comments in Python?",
        "options": ["//", "#", "/*", "@"],
        "answer": "#",
    },
    {
        "question": "4. Which function displays output?",
        "options": ["input()", "print()", "show()", "display()"],
        "answer": "print()",
    },
    {
        "question": "5. Which data type stores True or False?",
        "options": ["String", "Integer", "Boolean", "List"],
        "answer": "Boolean",
    },
]


@login_required
def quiz_home(request):
    return redirect("quiz_start")


@login_required
def quiz_start(request):
    if request.method == "POST":
        deadline = request.session.pop(QUIZ_DEADLINE_SESSION_KEY, None)
        timed_out = deadline is not None and time() >= deadline
        score = 0
        for index, question in enumerate(questions):
            if request.POST.get(f"q{index}") == question["answer"]:
                score += 1

        if timed_out:
            message = "Time is up! Your answers have been submitted."
        elif score >= 4:
            message = "Excellent! You passed the quiz."
        elif score >= 2:
            message = "Good try! Keep practising."
        else:
            message = "Keep learning and try again!"

        QuizScore.objects.create(user=request.user, score=score, total=len(questions))
        return render(
            request,
            "result.html",
            {"score": score, "total": len(questions), "message": message},
        )

    now = int(time())
    deadline = request.session.get(QUIZ_DEADLINE_SESSION_KEY)
    if deadline is None:
        deadline = now + QUIZ_DURATION_SECONDS
        request.session[QUIZ_DEADLINE_SESSION_KEY] = deadline

    return render(
        request,
        "quiz.html",
        {
            "questions": questions,
            "remaining_seconds": max(0, deadline - now),
        },
    )


def register(request):
    if request.user.is_authenticated:
        return redirect("quiz_start")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("quiz_start")
    else:
        form = RegistrationForm()

    return render(request, "register.html", {"form": form})
