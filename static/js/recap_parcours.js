// Affichage parcours etudiant

function toggle_vis(e) { // change visi of following row in table
    var tr = e.parentNode.parentNode;
    // current state: use alt attribute of current image
    if (e.childNodes[0].alt == '+') {
        state=1;
    } else {
        state=0;
    }
    // find next tr in siblings
    var sibl = tr.nextSibling;
    while ((sibl != null) && sibl.nodeType != 1 && sibl.tagName != 'TR') {
        sibl = sibl.nextSibling;
    }
    if (sibl) {
        var td_disp = 'none';
        if (state) {
            sibl.style.display = 'table-row';
            e.innerHTML = '<img width="13" height="13" border="0" title="" alt="-" src="/ScoDoc/icons/minus_img"/>';
            td_disp = 'inline';
        } else {
            sibl.style.display = 'none';
            e.innerHTML = '<img width="13" height="13" border="0" title="" alt="+" src="/ScoDoc/icons/plus_img"/>';
        }
        // acronymes d'UE
        sibl = e.parentNode.nextSibling;
        while (sibl != null) {
            if (sibl.nodeType == 1 && sibl.className == 'ue_acro')
                sibl.childNodes[0].style.display = td_disp; 
            sibl = sibl.nextSibling;
        }
    }
}

