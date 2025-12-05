import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class ComplexPasswordValidator:
    """
    Validate whether the password contains:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    def validate(self, password, user=None):
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code='password_no_upper',
            )

        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code='password_no_lower',
            )

        # Check for at least one digit
        if not re.search(r'\d', password):
            raise ValidationError(
                _("Password must contain at least one number."),
                code='password_no_number',
            )

        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _("Password must contain at least one special character (e.g. ! @ # ?)."),
                code='password_no_symbol',
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least 8 characters, "
            "including 1 uppercase letter, 1 number, and 1 special character."
        )