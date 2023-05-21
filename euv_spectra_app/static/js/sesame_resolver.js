const nameInput = document.querySelector('#name-form-input-group');
const searchBtn = document.querySelector('#name-form-submit');
const searchNameInput = document.querySelector('#name-form-input-group');
nameInput.addEventListener('input', checkName);

function runPopovers() {
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        var popover = new bootstrap.Popover(popoverTriggerEl);
        popover.show(); // show the popover immediately
        return popover;
    });
}


function checkName() {
    const name = nameInput.value;
    popover = bootstrap.Popover.getInstance(searchNameInput);
    if (popover) {
        popover.dispose()
    } 
    if (searchNameInput.value.length !== 0) {
        searchNameInput.setAttribute('data-bs-toggle', 'popover');
        searchNameInput.setAttribute('data-bs-trigger', 'manual');
        searchNameInput.setAttribute('data-bs-placement', 'top');
        searchNameInput.setAttribute('data-bs-content', 'Loading...')
    } else {
        popover.dispose();
    }
    fetch(`https://cds.unistra.fr/cgi-bin/nph-sesame/-oIx/~S?${name}`)
        .then(response => response.text())
            .then(xmlString => {
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(xmlString, "text/xml");
                const resolver = xmlDoc.querySelector("Resolver");
                if (resolver) {
                    console.log(resolver);
                    searchBtn.removeAttribute('disabled');
                    searchNameInput.classList.remove('not-found');
                    searchNameInput.classList.add('found');
                    searchNameInput.style.color = 'seagreen';

                    popover = bootstrap.Popover.getInstance(searchNameInput);
                    if (popover) {
                        popover.dispose()
                    } 
                    if (searchNameInput.value.length !== 0) {
                        searchNameInput.setAttribute('data-bs-toggle', 'popover');
                        searchNameInput.setAttribute('data-bs-trigger', 'manual');
                        searchNameInput.setAttribute('data-bs-placement', 'top');
                        searchNameInput.setAttribute('data-bs-content', `${searchNameInput.value} resolved by SESAME (SIMBAD).`)
                    } else {
                        popover.dispose();
                    }
                } else {
                    searchBtn.setAttribute('disabled', '');
                    searchNameInput.classList.remove('found');
                    searchNameInput.classList.add('not-found');
                    searchNameInput.style.color = 'tomato';

                    popover = bootstrap.Popover.getInstance(searchNameInput);
                    if (popover) {
                        popover.dispose();
                    } 
                    if (searchNameInput.value.length !== 0) {
                        searchNameInput.setAttribute('data-bs-toggle', 'popover');
                        searchNameInput.setAttribute('data-bs-trigger', 'manual');
                        searchNameInput.setAttribute('data-bs-placement', 'top');
                        searchNameInput.setAttribute('data-bs-content', `${searchNameInput.value} not resolved.`);
                    } else {
                        popover.dispose();
                    }
                }
                runPopovers();
            })
    runPopovers();
}