//—————————————————————————LOADER START————————————————————————
const loader = document.querySelector("#loading");
const overlay = document.getElementById("overlay");
const overlayBox = document.getElementById("overlay-box");
const overlayTitle = document.getElementById("overlay-title");

// showing loading
function displayLoading(event) {
    loader.classList.add("display");
    overlay.style.display = "block";
    if (event == 'modal'){
        overlayTitle.innerHTML = 'Searching the PEGASUS Grid';
    } else if (event == 'search') {
        overlayTitle.innerHTML = 'Querying Databases';
    };
    overlayBox.style.display = "block";
}

// hiding loading
function hideLoading() {
    loader.classList.remove("display");
    overlay.style.display = "none";
    overlayText.style.display = "none";
}
//—————————————————————————LOADER END————————————————————————