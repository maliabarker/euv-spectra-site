const nameInput = document.querySelector('#name-form-input-group');
const searchBtn = document.querySelector('#name-form-submit')
nameInput.addEventListener('input', checkName);

function checkName() {
    const name = nameInput.value;
    fetch(`https://cds.unistra.fr/cgi-bin/nph-sesame/-oIx/~S?${name}`)
        .then(response => response.text())
            .then(xmlString => {
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(xmlString, "text/xml");
                const resolver = xmlDoc.querySelector("Resolver");
                if (resolver) {
                    console.log("Resolver exists");
                    console.log(resolver)
                    searchBtn.removeAttribute('disabled');
                } else {
                    console.log("Resolver does not exist");
                    searchBtn.setAttribute('disabled', '');
                }
            })
}