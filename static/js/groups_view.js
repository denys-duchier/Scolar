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

// Selectionne tous les etudiants:
function select_tous() {
    var url = groups_view_url();
    var default_group_id = $("#group_selector")[0].default_group_id.value;
    delete url.param()['group_ids'];
    url.param()['group_ids'] = [ default_group_id ];

    reload_groups_view(url);
}

function reload_groups_view(url) {
    var query_string = $.param(url.param(), traditional=true );
    window.location = url.attr('base') + url.attr('path') + '?' + query_string;
}

// Recharge la page en changeant les groupes selectionnés et en conservant le tab actif:
function submit_group_selector() {
    reload_groups_view(groups_view_url());
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