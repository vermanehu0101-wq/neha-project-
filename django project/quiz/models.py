from django.contrib.auth.models import User
from django.db import models


class QuizScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_scores")
    score = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-score", "created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.score}/{self.total}"
