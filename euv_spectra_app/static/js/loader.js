//—————————————————————————LOADER START————————————————————————
const loader = document.querySelector("#loading");
const overlay = document.getElementById("overlay");

// showing loading
function displayLoading() {
    loader.classList.add("display");
    overlay.style.display = "block";
}

// hiding loading
function hideLoading() {
    loader.classList.remove("display");
    overlay.style.display = "none";
}
//—————————————————————————LOADER END————————————————————————