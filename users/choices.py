from django.db.models import TextChoices

class UserChoices(TextChoices):
    REPORTER = "REPORTER" #! oddiy fuqaro
    EXECUTOR = "EXECUTOR" #! ijrochi
    DISPATCHER = "DISPATCHER" #! boshqaruvchi admin