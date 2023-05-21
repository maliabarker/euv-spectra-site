const fuvFlagRadioBtns = document.querySelectorAll('input[name="fuv_flag"]');
const fuvNullRadio = document.getElementById('fuv_flag-0')
const fuvUpLimRadio = document.getElementById('fuv_flag-1')
const fuvSatRadio = document.getElementById('fuv_flag-2')
const fuvInput = document.getElementById('fuv');
const fuvErrInput = document.getElementById('fuv_err');

const nuvFlagRadioBtns = document.querySelectorAll('input[name="nuv_flag"]');
const nuvNullRadio = document.getElementById('nuv_flag-0')
const nuvUpLimRadio = document.getElementById('nuv_flag-1')
const nuvSatRadio = document.getElementById('nuv_flag-2')
const nuvInput = document.getElementById('nuv');
const nuvErrInput = document.getElementById('nuv_err');

function updateFuvRequired() {
    if (fuvNullRadio.checked) {
        // if the fuv null flag is checked make fuv inputs not required
        // disable nuv null flag radio btn and add tooltip to give more info
        // set input states
        fuvInput.required = false;
        fuvErrInput.required = false;
        // set radio states 
        nuvNullRadio.disabled = true;
        nuvSatRadio.disabled = false;
        nuvUpLimRadio.disabled = false;
        // set popover states (remove sat, add null)
        nuvSatRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvSatRadio.parentElement.removeAttribute('data-bs-placement');
        nuvSatRadio.parentElement.removeAttribute('title');
        nuvSatRadio.parentElement.removeAttribute('data-bs-original-title');
        nuvUpLimRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvUpLimRadio.parentElement.removeAttribute('data-bs-placement');
        nuvUpLimRadio.parentElement.removeAttribute('title');
        nuvUpLimRadio.parentElement.removeAttribute('data-bs-original-title');
        nuvNullRadio.parentElement.setAttribute('data-bs-toggle', 'tooltip');
        nuvNullRadio.parentElement.setAttribute('data-bs-placement', 'top');
        nuvNullRadio.parentElement.setAttribute('title', 'Cannot have both flux densities be null. Please see question 3 on the FAQs page for more information.');
    } else if (fuvUpLimRadio.checked) {
        // set input states
        fuvInput.required = true;
        fuvErrInput.required = false;
        // set radio states
        nuvNullRadio.disabled = false;
        nuvSatRadio.disabled = false;
        nuvUpLimRadio.disabled = true;
        // set popover states (remove null, add sat)
        nuvNullRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvNullRadio.parentElement.removeAttribute('data-bs-placement');
        nuvNullRadio.parentElement.removeAttribute('title');
        nuvNullRadio.parentElement.removeAttribute('data-bs-original-title');
        nuvSatRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvSatRadio.parentElement.removeAttribute('data-bs-placement');
        nuvSatRadio.parentElement.removeAttribute('title');
        nuvSatRadio.parentElement.removeAttribute('data-bs-original-title');
        nuvUpLimRadio.parentElement.setAttribute('data-bs-toggle', 'tooltip');
        nuvUpLimRadio.parentElement.setAttribute('data-bs-placement', 'top');
        nuvUpLimRadio.parentElement.setAttribute('title', 'Cannot have both flux densities be upper limits. Please see question 3 on the FAQs page for more information.');
    } else if (fuvSatRadio.checked) {
        // set input states
        fuvInput.required = true;
        fuvErrInput.required = false;
        // set radio states
        nuvNullRadio.disabled = false;
        nuvSatRadio.disabled = true;
        nuvUpLimRadio.disabled = false;
        // set popover states (remove null, add sat)
        nuvNullRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvNullRadio.parentElement.removeAttribute('data-bs-placement');
        nuvNullRadio.parentElement.removeAttribute('title');
        nuvNullRadio.parentElement.removeAttribute('data-bs-original-title');
        nuvUpLimRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvUpLimRadio.parentElement.removeAttribute('data-bs-placement');
        nuvUpLimRadio.parentElement.removeAttribute('title');
        nuvUpLimRadio.parentElement.removeAttribute('data-bs-original-title');
        nuvSatRadio.parentElement.setAttribute('data-bs-toggle', 'tooltip');
        nuvSatRadio.parentElement.setAttribute('data-bs-placement', 'top');
        nuvSatRadio.parentElement.setAttribute('title', 'Cannot have both flux densities be saturated. Please see question 3 on the FAQs page for more information.');
    } else {
        // else if the flag value is equal to None (nothing checked) or any other option
        // make fuv inputs required, make sure other nuv null flag is not disabled, and remove tooltip
        // set input states
        fuvInput.required = true;
        fuvErrInput.required = true;
        // set radio states
        nuvNullRadio.disabled = false;
        nuvSatRadio.disabled = false;
        nuvUpLimRadio.disabled = false;
        // set popover states (remove null and sat)
        nuvNullRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvNullRadio.parentElement.removeAttribute('data-bs-placement');
        nuvNullRadio.parentElement.removeAttribute('title');
        nuvNullRadio.parentElement.removeAttribute('data-bs-original-title');
        nuvSatRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvSatRadio.parentElement.removeAttribute('data-bs-placement');
        nuvSatRadio.parentElement.removeAttribute('title');
        nuvSatRadio.parentElement.removeAttribute('data-bs-original-title');
        nuvUpLimRadio.parentElement.removeAttribute('data-bs-toggle');
        nuvUpLimRadio.parentElement.removeAttribute('data-bs-placement');
        nuvUpLimRadio.parentElement.removeAttribute('title');
        nuvUpLimRadio.parentElement.removeAttribute('data-bs-original-title');
    }
    // run tooltip instantiation every time tooltips change
    runToolTips();
}


function updateNuvRequired() {
    if (nuvNullRadio.checked) {
        // if the nuv null flag is checked make nuv inputs not required
        // disable fuv null flag radio btn and add tooltip to give more info
        // set input states 
        nuvInput.required = false;
        nuvErrInput.required = false;
        // set radio states
        fuvNullRadio.disabled = true;
        fuvSatRadio.disabled = false;
        fuvUpLimRadio.disabled = false;
        // set popover states (remove sat, add null)
        fuvSatRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvSatRadio.parentElement.removeAttribute('data-bs-placement');
        fuvSatRadio.parentElement.removeAttribute('title');
        fuvSatRadio.parentElement.removeAttribute('data-bs-original-title');
        fuvUpLimRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvUpLimRadio.parentElement.removeAttribute('data-bs-placement');
        fuvUpLimRadio.parentElement.removeAttribute('title');
        fuvUpLimRadio.parentElement.removeAttribute('data-bs-original-title');
        fuvNullRadio.parentElement.setAttribute('data-bs-toggle', 'tooltip');
        fuvNullRadio.parentElement.setAttribute('data-bs-placement', 'top');
        fuvNullRadio.parentElement.setAttribute('title', 'Cannot have both flux densities be null. See Q3 on the FAQs page for more information.');
    } 
    else if (nuvUpLimRadio.checked) {
        // set input states
        nuvInput.required = true;
        nuvErrInput.required = false;
        // set radio states
        fuvNullRadio.disabled = false;
        fuvSatRadio.disabled = false;
        fuvUpLimRadio.disabled = true;
        // set popover states (remove null, add sat)
        fuvNullRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvNullRadio.parentElement.removeAttribute('data-bs-placement');
        fuvNullRadio.parentElement.removeAttribute('title');
        fuvNullRadio.parentElement.removeAttribute('data-bs-original-title');
        fuvSatRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvSatRadio.parentElement.removeAttribute('data-bs-placement');
        fuvSatRadio.parentElement.removeAttribute('title');
        fuvSatRadio.parentElement.removeAttribute('data-bs-original-title');
        fuvUpLimRadio.parentElement.setAttribute('data-bs-toggle', 'tooltip');
        fuvUpLimRadio.parentElement.setAttribute('data-bs-placement', 'top');
        fuvUpLimRadio.parentElement.setAttribute('title', 'Cannot have both flux densities be upper limits. See Q3 on the FAQs page for more information.');
    } 
    else if (nuvSatRadio.checked) {
        // set input states
        nuvInput.required = true;
        nuvErrInput.required = false;
        // set radio states
        fuvNullRadio.disabled = false;
        fuvSatRadio.disabled = true;
        fuvUpLimRadio.disabled = false;
        // set popover states (remove null, add sat)
        fuvNullRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvNullRadio.parentElement.removeAttribute('data-bs-placement');
        fuvNullRadio.parentElement.removeAttribute('title');
        fuvNullRadio.parentElement.removeAttribute('data-bs-original-title');
        fuvUpLimRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvUpLimRadio.parentElement.removeAttribute('data-bs-placement');
        fuvUpLimRadio.parentElement.removeAttribute('title');
        fuvUpLimRadio.parentElement.removeAttribute('data-bs-original-title');
        fuvSatRadio.parentElement.setAttribute('data-bs-toggle', 'tooltip');
        fuvSatRadio.parentElement.setAttribute('data-bs-placement', 'top');
        fuvSatRadio.parentElement.setAttribute('title', 'Cannot have both flux densities be saturated. See Q3 on the FAQs page for more information.');
    }
    else {
        // else if the flag value is equal to None (nothing checked) or any other option
        // make nuv inputs required, make sure other fuv null flag is not disabled, and remove tooltip
        // set input states
        nuvInput.required = true;
        nuvErrInput.required = true;
        // set radio states
        fuvNullRadio.disabled = false;
        fuvSatRadio.disabled = false;
        fuvUpLimRadio.disabled = false;
        // set popover states (remove both)
        fuvNullRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvNullRadio.parentElement.removeAttribute('data-bs-placement');
        fuvNullRadio.parentElement.removeAttribute('title');
        fuvNullRadio.parentElement.removeAttribute('data-bs-original-title');
        fuvSatRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvSatRadio.parentElement.removeAttribute('data-bs-placement');
        fuvSatRadio.parentElement.removeAttribute('title');
        fuvSatRadio.parentElement.removeAttribute('data-bs-original-title');
        fuvUpLimRadio.parentElement.removeAttribute('data-bs-toggle');
        fuvUpLimRadio.parentElement.removeAttribute('data-bs-placement');
        fuvUpLimRadio.parentElement.removeAttribute('title');
        fuvUpLimRadio.parentElement.removeAttribute('data-bs-original-title');
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
}

for (let i=0; i < nuvFlagRadioBtns.length; i++) {
    // adding change function on every radio in flags for NUV
    nuvFlagRadioBtns[i].addEventListener('change', updateNuvRequired);
}

 // initial calls to set required attributes based on initial state of radio button and instantiate tooltips
updateFuvRequired();
updateNuvRequired();
runToolTips();