// For rotating manual parameter form arrow
var manualCaret = $('#manual-caret');
var manualText = $('#manual-text');

manualCaret.on('click', rotateCaret);
manualText.on('click', rotateCaret);

function rotateCaret() {
    if (manualCaret.hasClass('fa-caret-right')) {
        // form is closed, open form and rotate down
        manualCaret.removeClass('fa-caret-right').addClass('fa-caret-down');
        manualText.html('Click Here to Hide Form');
    } else if (manualCaret.hasClass('fa-caret-down')) {
        // form is open, close form and rotate to the right
        manualCaret.removeClass('fa-caret-down').addClass('fa-caret-right');
        manualText.html('Click Here to Enter Parameters Manually')
    }
}