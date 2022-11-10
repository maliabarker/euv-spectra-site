function showModal() {
    var myModalEl = document.getElementById('myModal');
    var modal = new bootstrap.Modal(myModalEl);
    modal.show();
};

//—————————————————————————SELECT ALL START————————————————————————
function selectAll(obj) {
    console.log(obj.id)

    // get all selectall buttons
    const selectAllBtns = document.getElementById('star_name_parameter_form_table').querySelectorAll(`[id*="catalog_name"]`);
    console.log(selectAllBtns)
    // check to make sure no other select all buttons are checked
    for (i=0; i < selectAllBtns.length; i++) {
        if ( selectAllBtns[i].id != obj.id ) {
            selectAllBtns[i].checked = false;
        }
    };

    // get identifying number
    const num = obj.id.match(/(\d+)/)[0];
    // get all radios w identifying number
    const btns = document.getElementById('star_name_parameter_form_table').querySelectorAll(`[id*="${num}"]`);

    if (obj.checked) {
        console.log('checked, now we need to select all')
        // check radio btns
        for( i = 0 ; i < btns.length ; i++ ) {
            if(!(btns[i].disabled)){
                btns[i].checked = true;
            };
        };
        obj.nextElementSibling.innerHTML = 'Deselect All'
    } else {
        console.log('unchecked, now we need to uncheck and deselect all')
        obj.checked = false;
        // uncheck radio btns
        for( i = 0 ; i < btns.length ; i++ ) {
            if(!(btns[i].disabled)){
                btns[i].checked = false;
            };
        };
        obj.nextElementSibling.innerHTML = 'Select All'
    }
};

function selectAllGalex(obj) {
    const btns = document.getElementById('star_name_flux_form_table').querySelectorAll(`[id*="0"]`);

    if (obj.checked) {
        console.log('unchecked, now we need to check and select all')
        for( i = 0 ; i < btns.length ; i++ ) {
            btns[i].checked = true;
        };
        // document.getElementById('fuv-0').checked = true;
        // document.getElementById('nuv-0').checked = true;
        // document.getElementById('fuv_err-0').checked = true;
        // document.getElementById('nuv_err-0').checked = true;
        obj.nextElementSibling.innerHTML = 'Deselect All'
    } else {
        console.log('checked, now we need to uncheck and deselect all')
        obj.checked = false;
        for( i = 0 ; i < btns.length ; i++ ) {
            btns[i].checked = false;
        };
        // document.getElementById('fuv-0').checked = false;
        // document.getElementById('nuv-0').checked = false;
        // document.getElementById('fuv_err-0').checked = false;
        // document.getElementById('nuv_err-0').checked = false;
        obj.nextElementSibling.innerHTML = 'Select All'
    }
    
}
//—————————————————————————SELECT ALL END————————————————————————


//—————————————————————————MANUAL BTN CHECKS START————————————————————————
function populateManualValue(obj) {
    console.log(obj);
    console.log(obj.value);

    radioBtn = obj.previousElementSibling;
    radioBtn.value = obj.value;
    console.log(radioBtn)
    console.log(radioBtn.value)
}

function checkManualRadio(obj) {
    obj.previousElementSibling.checked = true;
};

function checkManualInputs(){
    // check all radio buttons and if a manual radio button is clicked assign the value from manual input to the actual input
    const manualBtns = document.querySelectorAll(`[id*="{{ last_num }}"]`);
    for(i = 0; i < manualBtns.length; i++){
        if (manualBtns[i].checked) {
            const newVal = manualBtns[i].nextElementSibling.value
            manualBtns[i].value = newVal
        };
    };
    return true; // submit the form
};

//—————————————————————————NOT DETECTED FLAG CHECKS————————————————————————
function populateNullFlux(obj) {
    console.log(obj.id)
    whichFlux = obj.id.slice(0,3)
    console.log(whichFlux)
    const fluxInputs = document.getElementById('parameter-form').querySelectorAll(`[id*="${whichFlux}"]`);
    for(i = 0; i < fluxInputs.length; i++) {
        if (fluxInputs[i].id != obj.id){
            fluxInputs[i].value = parseFloat(-999.0);
        };
    };
}
