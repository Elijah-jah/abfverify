from django.contrib.auth.tokens import PasswordResetTokenGenerator

class EmailTokenGenerator(PasswordResetTokenGenerator):
    pass

email_token = EmailTokenGenerator()