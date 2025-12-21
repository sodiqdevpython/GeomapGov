from django.db import models
from uuid import uuid4

class BaseModel(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        abstract = True