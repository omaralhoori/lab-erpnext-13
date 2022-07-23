// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Permitted Patient', {
	refresh: function(frm) {
		var url = window.location.href.split("?")
		console.log(url);
		if(url.length > 1){
			var patient = url[1].split("=")
			if(patient.length > 1){
				frm.set_value("patient", patient[1])
			}
		}
	}
});
