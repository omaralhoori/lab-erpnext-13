// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Group Set Result', {
	onload: function(frm) {
		frm.set_value('transaction_date', frappe.datetime.now_date()); 
		frm.set_value('form_received_date', frappe.datetime.now_date()); 

		frm.set_query("covid_form_serial","group_result_table", function() {
			return {
				query: 'erpnext.projects.doctype.group_set_result.group_set_result.get_covid_form_serial_for_result',
				filters: {
					link_company: frm.doc.company,
					link_sample_flag: "1",
					link_result_flag: "1"
				}
			};
		});

	},
	
	set_analysis_result_to: function(frm) {
		if (frm.doc.set_analysis_result_to != null) {
			if (frm.doc.set_analysis_result_to == "Not Collected") {
				frappe.throw(__("Not Collected result not allowed here "));
			}
		}
	},
	get_form_received: function(frm) {
		var me = this;
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

frappe.ui.form.on("Group Result Table", {
	covid_form_serial: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.covid_form_serial != null) {
			frappe.call({
				method: "erpnext.projects.doctype.group_set_result.group_set_result.get_covid_form_data",
				args: {
					company: frm.doc.company,
					covid_form_serial:row.covid_form_serial
				},
				callback: function(r, rt) {
					frappe.model.set_value(cdt, cdn, "customer_name",r.message.custmer_name);
					frappe.model.set_value(cdt, cdn, "received_date",r.message.date);
					frappe.model.set_value(cdt, cdn, "party_list",r.message.party_list);
					frappe.model.set_value(cdt, cdn, "medical_analysis_direction",r.message.medical_direction);
					frappe.model.set_value(cdt, cdn, "mobile_no",r.message.mobile_no);
					frappe.model.set_value(cdt, cdn, "national_id",r.message.national_id);
					frappe.model.set_value(cdt, cdn, "email_address",r.message.email_address);
					frappe.model.set_value(cdt, cdn, "date_of_birth",r.message.date_of_birth);
					frappe.model.set_value(cdt, cdn, "passport_id",r.message.passport_id);
					frappe.model.set_value(cdt, cdn, "gender",r.message.gender);
					frappe.model.set_value(cdt, cdn, "medical_direction_code",r.message.medical_direction_code);
					frappe.model.set_value(cdt, cdn, "collection_date",r.message.collection_date);
					frappe.model.set_value(cdt, cdn, "collection_time",r.message.collection_time);
					frappe.model.set_value(cdt, cdn, "result_date",frappe.datetime.now_date());
					frappe.model.set_value(cdt, cdn, "result_time",frappe.datetime.now_time());
				}
			})

		}
		
	},


})

