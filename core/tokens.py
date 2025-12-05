from django.contrib.auth.tokens import PasswordResetTokenGenerator

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # In Python 3, we use str() instead of six.text_type()
        return (
            str(user.pk) + str(timestamp) +
            str(user.is_active)
        )

account_activation_token = AccountActivationTokenGenerator()