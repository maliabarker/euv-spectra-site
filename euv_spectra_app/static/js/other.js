// For rotating manual parameter form arrow
manualCaret = document.getElementById('manual-caret')
manualText = document.getElementById('manual-text')

manualCaret.addEventListener('click', rotateCaret)
manualText.addEventListener('click', rotateCaret)

function rotateCaret() {
    console.log(manualCaret)
    if (manualCaret.classList.contains('open')){
        manualCaret.className = 'fa-solid fa-caret-right';
    } else {
        manualCaret.className = 'fa-solid fa-caret-right open';
    }
}