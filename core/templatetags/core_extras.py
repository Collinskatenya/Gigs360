from django import template

register = template.Library()

@register.filter(name='mask_phone')
def mask_phone(value):
    """Masks a phone number, showing only the last 4 digits."""
    if value and len(value) > 4:
        return "*" * (len(value) - 4) + value[-4:]
    return value

@register.filter(name='mask_account')
def mask_account(value):
    """Masks an account number, showing only the last 4 chars."""
    if value and len(str(value)) > 4:
        val_str = str(value)
        return "•••• " + val_str[-4:]
    return value