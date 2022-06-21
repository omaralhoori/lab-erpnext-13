// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Analysis Amount Update', {
	onload: function(frm) {
		frm.set_value('date', frappe.datetime.now_date()); 
		frm.set_query("customer_name", function() {
			return {
				query: 'erpnext.projects.doctype.analysis_amount_update.analysis_amount_update.get_customer_name',
				filters: {
					link_company: frm.doc.company
				}
			};
		})

	},
	customer_name: function(frm) {
		if(frm.doc.customer_name != null) {
			frappe.call({
				method: "erpnext.projects.doctype.analysis_amount_update.analysis_amount_update.get_customer_name_data",
				args: {
					company:frm.doc.company,
					customer_name:frm.doc.customer_name
				},
				callback: function(r, rt) {
					frm.set_value("desc", r.message.desc);
					frm.set_value("analysis_amount", r.message.analysis_amount);
					frm.set_value("analysis_amount_old", r.message.analysis_amount);
				}
			})
			
		}
	},
});



