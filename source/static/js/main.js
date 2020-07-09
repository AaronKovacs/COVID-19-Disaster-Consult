function isIE() {
    return window.document.documentMode != null;
}

function hideOnIE(elementID) {
    if (isIE())
        document.getElementById(elementID).style.display = "none";
}


function getDateTimeString() {
    var currentdate = new Date();
    return currentdate.getDate() + "/"
        + (currentdate.getMonth() + 1) + "/"
        + currentdate.getFullYear() + " at "
        + currentdate.getHours() + ":"
        + currentdate.getMinutes() + ":"
        + currentdate.getSeconds();
}
