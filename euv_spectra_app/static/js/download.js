function checkDirectory(filename){
    fetch(`/check-directory/${filename}`)
        .then(response => response.json())
        .then(data => {
            if (data.exists) {
                // Do something if the directory exists
                console.log('file exists')
                window.location = `/download/${filename}`
            } else {
                // Do something if the directory does not exist
                console.log('file does not exist')
                errorBox = document.getElementById(`${filename}-errorbox`)
                errorBox.innerHTML = 'File does not exist yet, unable to download'
                setTimeout(function() { errorBox.style.display = 'none'; }, 5000);
            }
        });
}