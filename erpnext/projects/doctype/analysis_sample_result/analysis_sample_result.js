// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Analysis Sample Result', {
	onload: function(frm) {
		frm.set_value('date', frappe.datetime.now_date()); 
		frm.set_query("customer_name", function() {
			return {
				query: 'erpnext.projects.doctype.analysis_sample_result.analysis_sample_result.get_customer_name',
				filters: {
					link_company: frm.doc.company
				}
			};
		})

	},
	customer_name: function(frm) {
		if(frm.doc.customer_name != null) {
			frappe.call({
				method: "erpnext.projects.doctype.analysis_sample_result.analysis_sample_result.get_customer_name_data",
				args: {
					company:frm.doc.company,
					customer_name:frm.doc.customer_name
				},
				callback: function(r, rt) {
					frm.set_value("desc", r.message.desc);
					frm.set_value("collection_date", r.message.collection_date);
					frm.set_value("collection_date_old", r.message.collection_date);
					frm.set_value("collection_time", r.message.collection_time);
					frm.set_value("collection_time_old", r.message.collection_time);
					frm.set_value("result_date", r.message.result_date);
					frm.set_value("result_date_old", r.message.result_date);
					frm.set_value("result_time", r.message.result_time);
					frm.set_value("result_time_old", r.message.result_time);
					frm.set_value("analysis_result", r.message.analysis_result);
					frm.set_value("analysis_result_old", r.message.analysis_result);
				}
			})
			
		}
	},


});
