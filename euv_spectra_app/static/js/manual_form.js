const fuvFlagRadioBtns = document.querySelectorAll('input[name="fuv_flag"]');
const fuvFlagRadio = document.querySelector('input[name="fuv_flag"]');
const fuvInput = document.getElementById('fuv');
const fuvErrInput = document.getElementById('fuv_err');

const nuvFlagRadioBtns = document.querySelectorAll('input[name="nuv_flag"]');
const nuvFlagRadio = document.querySelector('input[name="nuv_flag"]');
const nuvInput = document.getElementById('nuv');
const nuvErrInput = document.getElementById('nuv_err');

function updateFuvRequired() {
  if (fuvFlagRadio.checked) {
    console.log('FUV CHECKED')
    fuvInput.required = false;
    fuvErrInput.required = false;
  } else {
    console.log('FUV UNCHECKED')
    fuvInput.required = true;
    fuvErrInput.required = true;
  }
}

function updateNuvRequired() {
    console.log(nuvFlagRadio.value);
    if (nuvFlagRadio.checked) {
        console.log('NUV CHECKED')
        nuvInput.required = false;
        nuvErrInput.required = false;
    } else {
        console.log('NUV UNCHECKED')
        nuvInput.required = true;
        nuvErrInput.required = true;
    }
}

for (let i=0; i < fuvFlagRadioBtns.length; i++) {
    fuvFlagRadioBtns[i].addEventListener('change', updateFuvRequired);
}

for (let i=0; i < nuvFlagRadioBtns.length; i++) {
    nuvFlagRadioBtns[i].addEventListener('change', updateNuvRequired);
}

updateFuvRequired(); // initial call to set required attributes based on initial state of radio button
updateNuvRequired();