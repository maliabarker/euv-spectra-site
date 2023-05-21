function showModal() {
    var myModalEl = document.getElementById('myModal');
    var modal = new bootstrap.Modal(myModalEl);
    modal.show();
};


function populateManualValue(obj) {
    radioBtn = obj.previousElementSibling;
    radioBtn.value = obj.value;
}

function checkManualRadio(obj) {
    obj.previousElementSibling.checked = true;
};

function checkErrFlux(obj) {
    errRadioBtn = document.getElementById('fuv_err-1')
    errRadioBtn.checked = true;
};

function validateView() {
    form = document.getElementById('modal-form')
    // need all form-check-input and form-control in form
    const btns = form.querySelectorAll(`[class*="form-check-input"]`);
    const texts = form.querySelectorAll(`[class*="form-control"]`)
}
