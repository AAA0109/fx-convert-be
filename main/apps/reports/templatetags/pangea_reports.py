from decimal import Decimal

from django import template

register = template.Library()


@register.simple_tag()
def lookup(arr, *args):
    if not len(arr):
        return None

    level = arr.get(args[0])
    for key in args[1:]:
        if not level:
            return None
        level = level.get(key)
    return level


@register.simple_tag()
def float_lookup(arr, decimals, *args):
    val = lookup(arr, *args)

    if not isinstance(val, float):
        return val

    f_val = ("{0:.%sf}" % decimals).format(round(val, decimals))
    return Decimal(f_val)
