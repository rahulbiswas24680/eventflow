from django import template
register = template.Library()

@register.filter
def startswith(text, starts):
    if isinstance(text, str) and starts in text:
        # return text.startswith(starts)
        return True
    return False