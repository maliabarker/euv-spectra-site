const fuvFlagRadioBtns = document.querySelectorAll('input[name="fuv_flag"]');
const fuvNullRadio = document.getElementById('fuv_flag-0')
const fuvSatRadio = document.getElementById('fuv_flag-2')
const fuvInput = document.getElementById('fuv');
const fuvErrInput = document.getElementById('fuv_err');

const nuvFlagRadioBtns = document.querySelectorAll('input[name="nuv_flag"]');
const nuvNullRadio = document.getElementById('nuv_flag-0')
const nuvSatRadio = document.getElementById('nuv_flag-2')
const nuvInput = document.getElementById('nuv');
const nuvErrInput = document.getElementById('nuv_err');


const jBandCont = document.getElementById('j_band');
const jBandInput = jBandCont.querySelector('.form-control');
const jBandSelect = jBandCont.querySelector('.form-select')


function showJBandInput() {
    if (fuvNullRadio.checked || nuvNullRadio.checked || fuvSatRadio.checked || nuvSatRadio.checked) {
        jBandCont.style.display = '';
        jBandInput.required = true;
        jBandSelect.required = true;
    } else {
        jBandCont.style.display = 'none';
        jBandInput.required = false;
        jBandSelect.required = false;
    }
}


function updateFuvRequired() {
    if (fuvNullRadio.checked) {
        // if the fuv null flag is checked make fuv inputs not required
        // disable nuv null flag radio btn and add tooltip to give more info
        fuvInput.required = false;
        fuvErrInput.required = false;
        nuvNullRadio.disabled = true;
        nuvNullRadio.parentElement.setAttribute('data-bs-toggle', 'tooltip');
        nuvNullRadio.parentElement.setAttribute('data-bs-placement', 'top');
        nuvNullRadio.parentElement.setAttribute('title', 'Cannot have both flux densities be null. Please see question 3 on the FAQs page for more information.');
    } else {
        // else if the flag value is equal to None (nothing checked) or any other option
        // make fuv inputs required, make sure other nuv null flag is not disabled, and remove tooltip
        fuvInput.required = true;
        fuvErrInput.required = true;
        nuvNullRadio.disabled = false;
        nuvNullRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvNullRadio.parentElement.removeAttribute('data-bs-placement');
        nuvNullRadio.parentElement.removeAttribute('title');
        nuvNullRadio.parentElement.removeAttribute('data-bs-original-title');
    }
    // run tooltip instantiation every time tooltips change
    runToolTips();
}

function updateNuvRequired() {
    console.log(nuvNullRadio.value);
    if (nuvNullRadio.checked) {
        // if the nuv null flag is checked make nuv inputs not required
        // disable fuv null flag radio btn and add tooltip to give more info
        nuvInput.required = false;
        nuvErrInput.required = false;
        fuvNullRadio.disabled = true;
        fuvNullRadio.parentElement.setAttribute('data-bs-toggle', 'tooltip');
        fuvNullRadio.parentElement.setAttribute('data-bs-placement', 'top');
        fuvNullRadio.parentElement.setAttribute('title', 'Cannot have both flux densities be null. See Q3 on the FAQs page for more information.');
    } else {
        // else if the flag value is equal to None (nothing checked) or any other option
        // make nuv inputs required, make sure other fuv null flag is not disabled, and remove tooltip
        nuvInput.required = true;
        nuvErrInput.required = true;
        fuvNullRadio.disabled = false;
        fuvNullRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvNullRadio.parentElement.removeAttribute('data-bs-placement');
        fuvNullRadio.parentElement.removeAttribute('title');
        fuvNullRadio.parentElement.removeAttribute('data-bs-original-title');
    }
    // run tooltip instantiation every time tooltips change
    runToolTips();
}

function runToolTips() {
    // tooltip instantiation, need to make tooltips work
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
}

for (let i=0; i < fuvFlagRadioBtns.length; i++) {
    // adding change function on every radio in flags for FUV
    fuvFlagRadioBtns[i].addEventListener('change', updateFuvRequired);
    fuvFlagRadioBtns[i].addEventListener('change', showJBandInput);
}

for (let i=0; i < nuvFlagRadioBtns.length; i++) {
    // adding change function on every radio in flags for NUV
    nuvFlagRadioBtns[i].addEventListener('change', updateNuvRequired);
    nuvFlagRadioBtns[i].addEventListener('change', showJBandInput);
}

 // initial calls to set required attributes based on initial state of radio button and instantiate tooltips
updateFuvRequired();
updateNuvRequired();
showJBandInput();
runToolTips();