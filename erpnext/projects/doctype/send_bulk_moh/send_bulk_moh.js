// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Send Bulk MOH', {
	onload: function(frm) {
		if (!frm.doc.transaction_date)		{frm.set_value('transaction_date', frappe.datetime.now_date());} 
		if (!frm.doc.form_received_date)	{frm.set_value('form_received_date', frappe.datetime.now_date());} 

		frm.set_query("covid_form_serial","group_sms_form_table", function() {
			return {
				query: 'erpnext.projects.doctype.send_bulk_sms.send_bulk_sms.get_covid_form_serial_for_sms',
				filters: {
					link_company: frm.doc.company,
					link_sample_flag: "1",
					link_result_flag: "1"
				}
			};
		})


	},
	get_form_received: function(frm) {
		var me = this;
		if(frm.doc.all_medical_direction == 1){frm.set_value("medical_direction", null);}
		if(frm.doc.all_results == 1){frm.set_value("analysis_result", null);}
		if (!frm.doc.get_data_by_serial ){
			if(!frm.doc.form_received_date) {
				frappe.msgprint(__("Please enter Forms Received Date"));
			} else {
				return frm.call({
					doc:frm.doc,
					method: "get_form_received_bydate",
					callback: function(r, rt) {
					}
				});
			}
		} else {
			if(!frm.doc.from_serial || !frm.doc.to_serial) {
				frappe.msgprint(__("Please enter currect Serial Range"));
			} else {
				return frm.call({
					doc:frm.doc,
					method: "get_form_received_byserial",
					callback: function(r, rt) {
					}
				});
			}
		}
	},
	

 


});

frappe.ui.form.on("Send Bulk MOH",{
	on_submit: function(frm) {
	
	}
})
