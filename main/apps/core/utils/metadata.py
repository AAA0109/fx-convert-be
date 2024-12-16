


def get_float_type_columns(model):
    return [field_name.name for field_name in model._meta.get_fields() if
            field_name.__class__.__name__ == 'FloatField']
