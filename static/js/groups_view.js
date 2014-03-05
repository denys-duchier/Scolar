// Affichage progressif du trombinoscope html

$().ready(function(){
    var spans = $(".unloaded_img");
    for (var i=0; i < spans.size(); i++) {
	var sp = spans[i];
	var etudid = sp.id;
	$(sp).load('etud_photo_html?etudid='+etudid);
    }
});


// L'URL pour recharger l'état courant de la page (groupes et tab selectionnes)
// (ne fonctionne que pour les requetes GET: manipule la query string)

function groups_view_url() {
    var url = $.url();
    delete url.param()['group_ids']; // retire anciens groupes de l'URL
    delete url.param()['curtab']; // retire ancien tab actif
    if (CURRENT_TAB_HASH) {
        url.param()['curtab'] = CURRENT_TAB_HASH;
    }
    delete url.param()['formsemestre_id'];
    url.param()['formsemestre_id'] = $("#group_selector")[0].formsemestre_id.value;

    var selected_groups = $("#group_selector select").val();
    url.param()['group_ids'] = selected_groups;    // remplace par groupes selectionnes
 
    return url;
}

// Selectionne tous les etudiants et recharge la page:
function select_tous() {
    var url = groups_view_url();
    var default_group_id = $("#group_selector")[0].default_group_id.value;
    delete url.param()['group_ids'];
    url.param()['group_ids'] = [ default_group_id ];

    var query_string = $.param(url.param(), traditional=true );
    window.location = url.attr('base') + url.attr('path') + '?' + query_string;
}

// L'URL pour l'état courant de la page:
function get_current_url() {
    var url = groups_view_url();
    var query_string = $.param(url.param(), traditional=true );
    return url.attr('base') + url.attr('path') + '?' + query_string;
}

// Recharge la page en changeant les groupes selectionnés et en conservant le tab actif:
function submit_group_selector() {
    window.location = get_current_url();
}

function show_current_tab() {
    $('.nav-tabs [href="#'+CURRENT_TAB_HASH+'"]').tab('show');
}

var CURRENT_TAB_HASH = $.url().param()['curtab'];

$().ready(function(){
    $('.nav-tabs a').on('shown.bs.tab', function (e) {
        CURRENT_TAB_HASH = e.target.hash.slice(1); // sans le #
    });

    show_current_tab();
});

function change_list_options() {
    var url = groups_view_url();
    var selected_options = $("#group_list_options").val();
    var options = [ "with_paiement", "with_archives", "with_annotations", "with_codes" ];
    for (var i=0; i<options.length; i++) {
        var option = options[i];
        delete url.param()[option];
        if ($.inArray( option, selected_options ) >= 0) {
            url.param()[option] = 1;
        }
    }
    var query_string = $.param(url.param(), traditional=true );
    window.location = url.attr('base') + url.attr('path') + '?' + query_string;
}


// Trombinoscope
$().ready(function(){

    var elems = $(".trombi-photo");
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
		        at : "right",
                my : "left top"
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
