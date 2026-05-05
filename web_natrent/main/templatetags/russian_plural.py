from django import template

register = template.Library()


@register.filter
def ru_plural(value, forms):
    """
    Selects one of 3 Russian plural forms.
    forms format: "form1,form2,form5"
    Example: "ь,и,ей" for "ноч".
    """
    try:
        number = abs(int(value))
    except (TypeError, ValueError):
        return ""

    parts = [part for part in forms.split(",")]
    if len(parts) != 3:
        return ""


    print(number)
    if 11 <= (number % 100) <= 14:
        return parts[2]
    if number % 10 == 1:
        return parts[0]
    if 2 <= (number % 10) <= 4:
        print("penis")
        return parts[1]
    return parts[2]
