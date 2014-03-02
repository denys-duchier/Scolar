// Affiche popup avec info sur etudiant (pour les listes d'etudiants)
// affecte les elements de classe "etudinfo" portant l'id d'un etudiant
// utilise jQuery / qTip

function get_etudid_from_elem(e) {
    // renvoie l'etudid, obtenu a partir de l'id de l'element
    // qui est soit de la forme xxxx-etudid, soit tout simplement etudid
    var etudid = e.id.split("-")[1];
    if (etudid == undefined) {
        return e.id;
    } else {
        return etudid;
    }
}

$().ready(function(){

    var elems = $(".etudinfo");
    for (var i=0; i < elems.length; i++) {
	$(elems[i]).qtip(
        {
	        content: {
		        ajax: {
			        url: "etud_info_html?etudid=" + get_etudid_from_elem(elems[i])
		        },
		        text: "Loading..."
	        },
	        position: {
		        at: "right bottom",
		        my: "left top"
	        },
	        style: {
		        classes: 'qtip-etud'
	        },
            // utile pour debugguer le css: 
            // hide: { event: 'unfocus' }
        }
    );
    }
});


$().ready(function(){

    var elems = $(".etudinfo-trombi");
    for (var i=0; i < elems.length; i++) {
	$(elems[i]).qtip(
        {
	        content: {
		        ajax: {
			        url: "etud_info_html?with_photo=0&etudid=" + get_etudid_from_elem(elems[i])
		        },
		        text: "Loading..."
	        },
	        position: {
		        target: 'mouse'
	        },
	        style: {
		        classes: 'qtip-etud'
	        },
            // utile pour debugguer le css: 
            // hide: { event: 'unfocus' }
        }
    );
    }
});
