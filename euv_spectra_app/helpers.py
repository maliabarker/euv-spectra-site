def insert_data_into_form(obj, form):
    attrs = vars(obj)
    for attr_name, attr_value in attrs.items():
        if hasattr(attr_value, '__dict__'):
            # is an object, go again
            print(f'{attr_name} is an object')
            insert_data_into_form(attr_value, form)
        elif hasattr(form, attr_name):
            # is not an object, check if it exists in form and if True, add to form data
            radio_input = getattr(form, attr_name)
            radio_input.choices.insert(
                0, (attr_value, attr_value))