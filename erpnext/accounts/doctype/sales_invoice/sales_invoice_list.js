// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// render
frappe.listview_settings['Sales Invoice'] = {
	add_fields: ["customer", "customer_name", "base_grand_total", "outstanding_amount", "due_date", "company",
		"currency", "is_return"],
	get_indicator: function(doc) {
		const status_colors = {
			"Draft": "grey",
			"Unpaid": "orange",
			"Paid": "green",
			"Return": "gray",
			"Credit Note Issued": "gray",
			"Unpaid and Discounted": "orange",
			"Partly Paid and Discounted": "yellow",
			"Overdue and Discounted": "red",
			"Overdue": "red",
			"Partly Paid": "yellow",
			"Internal Transfer": "darkgrey"
		};
		return [__(doc.status), status_colors[doc.status], "status,=,"+doc.status];
	},
	right_column: "grand_total",
	onload: function (listview) {
		//ibrahim	
		//listview.page.add_menu_item(__("Clear Error Logs"), function() {
		//	frappe.call({
		//		method:'frappe.core.doctype.error_log.error_log.clear_error_logs',
		//		callback: function() {
		//			listview.refresh();
		//		}
		//	});
		//});


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
			if(urls[urls.length - 1] === "sales-invoice"){
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
					method: "erpnext.healthcare.barcode_query.find_sales_invoice",
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
};



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
