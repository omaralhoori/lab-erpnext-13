frappe.listview_settings['Sample Collection'] = {

    onload: function (listview) {
		let disabled = false;
		let query = "";
		let url = location.href;
		document.body.addEventListener('click', ()=>{
			requestAnimationFrame(()=>{
			if(url!==location.href){
				//$(document).find('*').off('keydown');
				disabled = true;
				query = "";
				url = location.href
			}
            let urls = location.href.split("/");
			if(urls[urls.length - 1] === "sample-collection"){
				disabled = false;
			}
			});
		}, true);
		
		$(document).keydown(function(e) {
			if(abandonedChars(e.which) || disabled ) return; // || !frm.is_dirty()
			query += String.fromCharCode(switchedChars(e.which));
			//console.log(e.which)
			if(e.which == 13) {
				// ctrl+b pressed
				frappe.call({
					method: "erpnext.healthcare.barcode_query.find_sample_collection",
					args: {
						"test_code": query
					},
					callback: (res) => {
						if(res.message != null && res.message != ""){
							window.location.href =  res.message;
						}
					}
				})
				query = "";
			}
			
		});
			
	}
}



function abandonedChars(charCode){
	if(charCode == 16){
		return true;
	}
	return false;
}

function switchedChars(charCode){
    if(charCode == 189){
		return 45;
	}
	return charCode;
}
