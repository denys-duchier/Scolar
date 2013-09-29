// Affiche popup avec info sur etudiant (pour les listes d'etudiants)
// affecte les elements de classe "etudinfo" portant l'id d'un etudiant
// utilise jQuery / qTip

$().ready(function(){

    var elems = $(".etudinfo");
    for (var i=0; i < elems.length; i++) {
	$(elems[i]).qtip(
        {
	        content: {
		        ajax: {
			        url: "etud_info_html?etudid=" + elems[i].id
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
            // utile pour debugguer le css: hide: { event: 'unfocus' }
        }
    );
    }
});


