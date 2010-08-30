
// JS Ajax code for SignaleAbsenceGrSemestre
// Contributed by YLB

function ajaxFunction(mod, etudid, dat){
	var ajaxRequest;  // The variable that makes Ajax possible!
	
	try{
		// Opera 8.0+, Firefox, Safari
		ajaxRequest = new XMLHttpRequest();
	} catch (e){
		// Internet Explorer Browsers
		try{
			ajaxRequest = new ActiveXObject("Msxml2.XMLHTTP");
		} catch (e) {
			try{
				ajaxRequest = new ActiveXObject("Microsoft.XMLHTTP");
			} catch (e){
				// Something went wrong
				alert("Your browser broke!");
				return false;
			}
		}
	}
	// Create a function that will receive data sent from the server
	ajaxRequest.onreadystatechange = function(){
		if(ajaxRequest.readyState == 4 && ajaxRequest.status == 200){
			document.getElementById("AjaxDiv").innerHTML=ajaxRequest.responseText;
		}
	}
	ajaxRequest.open("POST", "doSignaleAbsenceGrSemestre", true);
	ajaxRequest.setRequestHeader("Content-type","application/x-www-form-urlencoded");
	oForm = document.forms[0];
	oSelectOne = oForm.elements["moduleimpl_id"];
	index = oSelectOne.selectedIndex;
        modul_id = oSelectOne.options[index].value;
	if (mod == 'add') {
		ajaxRequest.send("reply=0&moduleimpl_id=" + modul_id +"&abslist:list=" + etudid + ":" + dat);
	}
	if (mod == 'remove') {
		ajaxRequest.send("reply=0&moduleimpl_id=" + modul_id +"&etudids=" + etudid + "&dates=" + dat);
	}
}

