
// Met à jour bul_show_rank lorsque checkbox modifiees:
function update_rk(e) {
    var rk;
    if (e.checked)
	rk='1';
    else
	rk='0';
    $('.epmsg').load('partition_set_bul_show_rank?partition_id=' + e.name + '&bul_show_rank=' + rk);

    return;
} 

