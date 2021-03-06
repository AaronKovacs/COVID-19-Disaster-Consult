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

function showInternalUseWarning(){
    toastr['error']('<p class="pb-0 mb-0">This Disaster is <b style="font-weight:700;">private</b></p><p class="pb-0 mb-0">Do NOT share this outside the project team.</p>', '<b style="font-weight:700;">Internal Use Only!</b>',
        {
            "closeButton": true,
            "autohide": false,
            "debug": false,
            "newestOnTop": false,
            "progressBar": false,
            "positionClass": "md-toast-top-center",
            "preventDuplicates": false,
            "timeOut": 99999999,
            "extendedTimeOut": 99999999,
            "showEasing": "swing",
            "hideEasing": "linear",
            "showMethod": "fadeIn",
            "hideMethod": "fadeOut"
        });

}