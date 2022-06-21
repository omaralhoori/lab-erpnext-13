// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Group Sample Collection', {
	onload: function(frm) {
		frm.set_value('transaction_date', frappe.datetime.now_date()); 
		frm.set_value('form_received_date', frappe.datetime.now_date()); 

		frm.set_query("covid_form_serial","group_sample_collection_table", function() {
			return {
				query: 'erpnext.projects.doctype.group_sample_collection.group_sample_collection.get_covid_form_serial_for_sample',
				filters: {
					link_company: frm.doc.company,
					link_sample_flag: "0"
				}
			};
		})

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

frappe.ui.form.on("Group Sample Collection Table", {
	covid_form_serial: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.covid_form_serial != null) {
			frappe.call({
				method: "erpnext.projects.doctype.group_sample_collection.group_sample_collection.get_covid_form_data",
				args: {
					company: frm.doc.company,
					covid_form_serial:row.covid_form_serial
				},
				callback: function(r, rt) {
					frappe.model.set_value(cdt, cdn, "customer_name",r.message.custmer_name);
					frappe.model.set_value(cdt, cdn, "received_date",r.message.date);
					frappe.model.set_value(cdt, cdn, "medical_analysis_direction",r.message.medical_direction);
					frappe.model.set_value(cdt, cdn, "party_list",r.message.party_list);
					frappe.model.set_value(cdt, cdn, "collection_date",frappe.datetime.now_date());
					frappe.model.set_value(cdt, cdn, "collection_time",frappe.datetime.now_time());
				}
			})

		}
		
	},


})

