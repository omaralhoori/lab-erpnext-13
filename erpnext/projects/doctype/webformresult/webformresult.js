// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('WebFormResult', {
	customer_password: function(frm) {
		if(frm.doc.customer_password != null) {
			frappe.call({
				method: "erpnext.projects.doctype.webformresult.webformresult.get_customer_data",
				args: {
					customer_password:frm.doc.customer_password
				},
				callback: function(r, rt) {
					frm.set_value("customer_name", r.message.customer_name);
					frm.set_value("analysis_result", r.message.analysis_result);
				}
			})
		}
	},
});
