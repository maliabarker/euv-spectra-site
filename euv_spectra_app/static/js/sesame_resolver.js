const nameInput = document.querySelector('#name-form-input-group');
const searchBtn = document.querySelector('#name-form-submit');
const searchNameInput = document.querySelector('#name-form-input-group');
let timeoutId;  // Variable to store the timeout ID
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
      popover.dispose();
    }
  
    clearTimeout(timeoutId);
  
    if (searchNameInput.value.length !== 0) {
      searchNameInput.setAttribute('data-bs-toggle', 'popover');
      searchNameInput.setAttribute('data-bs-trigger', 'manual');
      searchNameInput.setAttribute('data-bs-placement', 'top');
      searchNameInput.setAttribute('data-bs-content', 'Loading...');
  
      // Show the popover immediately
      searchNameInput.dispatchEvent(new Event('mouseenter'));
    } else {
      popover.dispose();
    }
  
    // Set a new timeout to execute the function after 2 seconds of inactivity
    timeoutId = setTimeout(() => {
        fetch(`https://cds.unistra.fr/cgi-bin/nph-sesame/-oIx/~S?${name}`)
            .then(response => response.text())
            .then(xmlString => {
                // Rest of your code...
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
            // runPopovers();
            });
    }, 500); // Delay set to 0.5 seconds (500 milliseconds)
    runPopovers();
  }


// function checkName() {
//     const name = nameInput.value;
//     popover = bootstrap.Popover.getInstance(searchNameInput);
//     if (popover) {
//         popover.dispose()
//     } 
//     if (searchNameInput.value.length !== 0) {
//         searchNameInput.setAttribute('data-bs-toggle', 'popover');
//         searchNameInput.setAttribute('data-bs-trigger', 'manual');
//         searchNameInput.setAttribute('data-bs-placement', 'top');
//         searchNameInput.setAttribute('data-bs-content', 'Loading...')
//     } else {
//         popover.dispose();
//     }

//     // Clear the previous timeout
//     clearTimeout(timeoutId);

//     // Set a new timeout to execute the function after 2 seconds of inactivity
//     timeoutId = setTimeout(() => {
//         fetch(`https://cds.unistra.fr/cgi-bin/nph-sesame/-oIx/~S?${name}`)
//             .then(response => response.text())
//             .then(xmlString => {
//                 // Rest of your code...
//                 const parser = new DOMParser();
//                 const xmlDoc = parser.parseFromString(xmlString, "text/xml");
//                 const resolver = xmlDoc.querySelector("Resolver");
//                 if (resolver) {
//                     console.log(resolver);
//                     searchBtn.removeAttribute('disabled');
//                     searchNameInput.classList.remove('not-found');
//                     searchNameInput.classList.add('found');
//                     searchNameInput.style.color = 'seagreen';

//                     popover = bootstrap.Popover.getInstance(searchNameInput);
//                     if (popover) {
//                         popover.dispose()
//                     } 
//                     if (searchNameInput.value.length !== 0) {
//                         searchNameInput.setAttribute('data-bs-toggle', 'popover');
//                         searchNameInput.setAttribute('data-bs-trigger', 'manual');
//                         searchNameInput.setAttribute('data-bs-placement', 'top');
//                         searchNameInput.setAttribute('data-bs-content', `${searchNameInput.value} resolved by SESAME (SIMBAD).`)
//                     } else {
//                         popover.dispose();
//                     }
//                 } else {
//                     searchBtn.setAttribute('disabled', '');
//                     searchNameInput.classList.remove('found');
//                     searchNameInput.classList.add('not-found');
//                     searchNameInput.style.color = 'tomato';

//                     popover = bootstrap.Popover.getInstance(searchNameInput);
//                     if (popover) {
//                         popover.dispose();
//                     } 
//                     if (searchNameInput.value.length !== 0) {
//                         searchNameInput.setAttribute('data-bs-toggle', 'popover');
//                         searchNameInput.setAttribute('data-bs-trigger', 'manual');
//                         searchNameInput.setAttribute('data-bs-placement', 'top');
//                         searchNameInput.setAttribute('data-bs-content', `${searchNameInput.value} not resolved.`);
//                     } else {
//                         popover.dispose();
//                     }
//                 }
//                 runPopovers();
//             });
//         runPopovers();
//         }, 2000); // Delay set to 2 seconds (2000 milliseconds)
//     }

//     fetch(`https://cds.unistra.fr/cgi-bin/nph-sesame/-oIx/~S?${name}`)
//         .then(response => response.text())
//             .then(xmlString => {
//                 const parser = new DOMParser();
//                 const xmlDoc = parser.parseFromString(xmlString, "text/xml");
//                 const resolver = xmlDoc.querySelector("Resolver");
//                 if (resolver) {
//                     console.log(resolver);
//                     searchBtn.removeAttribute('disabled');
//                     searchNameInput.classList.remove('not-found');
//                     searchNameInput.classList.add('found');
//                     searchNameInput.style.color = 'seagreen';

//                     popover = bootstrap.Popover.getInstance(searchNameInput);
//                     if (popover) {
//                         popover.dispose()
//                     } 
//                     if (searchNameInput.value.length !== 0) {
//                         searchNameInput.setAttribute('data-bs-toggle', 'popover');
//                         searchNameInput.setAttribute('data-bs-trigger', 'manual');
//                         searchNameInput.setAttribute('data-bs-placement', 'top');
//                         searchNameInput.setAttribute('data-bs-content', `${searchNameInput.value} resolved by SESAME (SIMBAD).`)
//                     } else {
//                         popover.dispose();
//                     }
//                 } else {
//                     searchBtn.setAttribute('disabled', '');
//                     searchNameInput.classList.remove('found');
//                     searchNameInput.classList.add('not-found');
//                     searchNameInput.style.color = 'tomato';

//                     popover = bootstrap.Popover.getInstance(searchNameInput);
//                     if (popover) {
//                         popover.dispose();
//                     } 
//                     if (searchNameInput.value.length !== 0) {
//                         searchNameInput.setAttribute('data-bs-toggle', 'popover');
//                         searchNameInput.setAttribute('data-bs-trigger', 'manual');
//                         searchNameInput.setAttribute('data-bs-placement', 'top');
//                         searchNameInput.setAttribute('data-bs-content', `${searchNameInput.value} not resolved.`);
//                     } else {
//                         popover.dispose();
//                     }
//                 }
//                 runPopovers();
//             })
//     runPopovers();
// }