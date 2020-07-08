function isIE(){
    return window.document.documentMode != null;
}

function hideOnIE(elementID){
     if (isIE())
         document.getElementById(elementID).style.display = "none";
}
