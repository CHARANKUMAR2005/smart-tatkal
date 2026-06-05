from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def multiply(value, arg):
    try:
        return int(value) * int(arg)
    except:
        return 0
