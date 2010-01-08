// Affichage parcours etudiant
// (uses jQuery)

function toggle_vis(e, new_state) { // change visibility of tr (UE in tr and next tr)
    // e is the span containg the clickeg +/- icon
    var tr = e.parentNode.parentNode;
    if (new_state == undefined) {
	// current state: use alt attribute of current image
	if (e.childNodes[0].alt == '+') {
            new_state=false;
	} else {
            new_state=true;
	}
    } 
    // find next tr in siblings
    var sibl = tr.nextSibling;
    while ((sibl != null) && sibl.nodeType != 1 && sibl.tagName != 'TR') {
        sibl = sibl.nextSibling;
    }
    if (sibl) {
        var td_disp = 'none';
        if (new_state) {
            sibl.style.display = 'none';
            e.innerHTML = '<img width="13" height="13" border="0" title="" alt="+" src="/ScoDoc/icons/plus_img"/>';
        } else {
            sibl.style.display = 'table-row';
            e.innerHTML = '<img width="13" height="13" border="0" title="" alt="-" src="/ScoDoc/icons/minus_img"/>';
            td_disp = 'inline';
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

var sems_state = false;

function toggle_all_sems(e) {
    var elems = $("span.toggle_sem"); 
    for (var i=0; i < elems.length; i++) {
	toggle_vis(elems[i], sems_state);
    }
    sems_state = !sems_state;
    if (sems_state) {
	e.innerHTML = '<img width="18" height="18" border="0" title="" alt="-" src="/ScoDoc/icons/minus18_img"/>';
    } else {
	e.innerHTML = '<img width="18" height="18" border="0" title="" alt="+" src="/ScoDoc/icons/plus18_img"/>';
    }
}