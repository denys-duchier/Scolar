// Affiche carte google map des lycees

$().ready(function(){
    $('#lyc_map_canvas').gmap(
	{ 'center': '48.955741,2.34141', 
	  'zoom' : 8,
	  'mapTypeId': google.maps.MapTypeId.ROADMAP
	}).bind('init', function(event, map) {
	    for (var i =0; i < lycees_coords.length; i++) {
		var lycee = lycees_coords[i];
		$('#lyc_map_canvas').gmap('addMarker', {'position': lycee['position'], 'bounds': true, 'nomlycee' : lycee['name'] } ).click(
		    function() {
			$('#lyc_map_canvas').gmap('openInfoWindow', {'content': this.nomlycee}, this);
		    }
		);
	    }
	});
});



