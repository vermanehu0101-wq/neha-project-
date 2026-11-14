from django.urls import path

from . import views


urlpatterns = [
    path("", views.quiz_home, name="quiz_home"),
    path("quiz/", views.quiz_start, name="quiz_start"),
]
