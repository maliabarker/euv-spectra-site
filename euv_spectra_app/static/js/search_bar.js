const searchSelect = document.getElementById('search-select')

const nameForm = document.getElementById('name-form-cont')
const positionForm = document.getElementById('position-form-cont')

searchSelect.addEventListener('change', function handleChange(e) {
    if (e.target.value == 'name'){
        nameForm.style.display = 'block';
        positionForm.style.display = 'none';
    } else if (e.target.value == 'position') {
        nameForm.style.display = 'none';
        positionForm.style.display = 'block';
    }
});