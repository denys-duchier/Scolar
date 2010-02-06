// Affiche popup avec info sur etudiant (pour les listes d'etudiants)
// affecte les elements de classe "etudinfo" portant l'id d'un etudiant
// utilise jQuery / qTip

$().ready(function(){

    var elems = $(".etudinfo");
    for (var i=0; i < elems.length; i++) {
	$(elems[i]).qtip({
	    content: {
		url : 'etud_info_html?etudid=' + elems[i].id
	    },
	    position: {
		corner: {
		    target: 'rightTop',
		    tooltip: 'leftTop'
		}
	    },
	    style: {
		width: 'auto',
		padding: 0,
	    }
	});
    }
});


