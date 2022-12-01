form = document.getElementById('name-parameters-form')
'{% for field, errors in star_name_parameters_form.errors.items() %}'
    fields = form.querySelectorAll(`[id*="{{ field }}"]`);
    for (i=0; i < fields.length; i++){
        console.log(fields[i])
        fields[i].classList.add('is-invalid');
    }
'{% endfor %}'