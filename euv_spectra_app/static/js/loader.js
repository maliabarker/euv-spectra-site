//—————————————————————————LOADER START————————————————————————
const loader = document.querySelector("#loading");
const overlay = document.getElementById("overlay");
const overlayText = document.getElementById("overlay-box");

// showing loading
function displayLoading() {
    loader.classList.add("display");
    overlay.style.display = "block";
    overlayText.style.display = "block";
}

// hiding loading
function hideLoading() {
    loader.classList.remove("display");
    overlay.style.display = "none";
    overlayText.style.display = "none";
}
//—————————————————————————LOADER END————————————————————————