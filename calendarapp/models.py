from django.db import models

# Create your models here.
class Note(models.Model):
    user_id = models.BigIntegerField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id}: {self.text[:30]}"
