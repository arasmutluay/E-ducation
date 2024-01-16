let timeout = null;

function logoutUser() {
    fetch('/check_login_status', {
        method: 'POST',
        credentials: 'same-origin'
    })
        .then(response => {
            return response.json();
        })
        .then(data => {
            if (data.isLoggedIn) {
                window.location.href = '/logout';
            } else {
                console.log('User is not logged in.');
            }
        })
        .catch(error => {
            console.error('Error checking login status:', error);
        });
}

function resetTimeout() {// FOR RESETTING THE TIMEOUT WHEN MOUSE MOVEMENT OR KEYBOARD PRESS
    clearTimeout(timeout);
    timeout = setTimeout(logoutUser, 30 * 60 * 1000);
}

window.onload = resetTimeout;
document.onmousemove = resetTimeout;
document.onkeypress = resetTimeout;