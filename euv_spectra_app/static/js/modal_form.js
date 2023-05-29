let errFUVManualRadioBtn = document.getElementById('fuv_err-1')
let errFUVRadioBtn = document.getElementById('fuv_err-0')
let errNUVManualRadioBtn = document.getElementById('nuv_err-1')
let errNUVRadioBtn = document.getElementById('nuv_err-0')

function showModal() {
    var myModalEl = document.getElementById('myModal');
    var modal = new bootstrap.Modal(myModalEl);
    modal.show();
};

function populateManualValue(obj) {
    radioBtn = obj.previousElementSibling;
    radioBtn.value = obj.value;
};

function checkManualRadio(obj) {
    obj.previousElementSibling.checked = true;
};

function checkManualFUVErrFlux() {
    console.log('Manual FUV err checked')
    errFUVManualRadioBtn.checked = true;
    errFUVRadioBtn.checked = false;
};

function checkFUVErrFlux() {
    console.log('Given FUV err checked')
    errFUVManualRadioBtn.checked = false;
    errFUVRadioBtn.checked = true;
};

function checkManualNUVErrFlux() {
    console.log('Manual NUV err checked')
    errNUVManualRadioBtn.checked = true;
    errNUVRadioBtn.checked = false;
};

function checkNUVErrFlux() {
    console.log('Given NUV err checked')
    errNUVManualRadioBtn.checked = false;
    errNUVRadioBtn.checked = true;
};

function validateView() {
    form = document.getElementById('modal-form')
    // need all form-check-input and form-control in form
    const btns = form.querySelectorAll(`[class*="form-check-input"]`);
    const texts = form.querySelectorAll(`[class*="form-control"]`);
};
