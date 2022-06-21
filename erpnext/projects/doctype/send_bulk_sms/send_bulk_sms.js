// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Send Bulk SMS', {
	refresh: function(frm) {
	    cur_frm.fields_dict["group_sms_form_table"].$wrapper.find('.grid-body .rows').find(".grid-row").each(function(i, item) {
			let d = locals[cur_frm.fields_dict["group_sms_form_table"].grid.doctype][$(item).attr('data-name')];
			$(item).find('.grid-static-col').css({'background-color': 'transparent'});
 
			if( ((d["mobile_no"].includes('96277', 0)) || (d["mobile_no"].includes('96278', 0)) || (d["mobile_no"].includes('96279', 0))) &&  (d["mobile_no"].length == 12) ){
				 $(item).find('.grid-static-col').css({'background-color': 'transparent'});
			}
			else {
				$(item).find('.grid-static-col').css({'background-color': 'yellow'});
			}
		 });
	},	
	onload: function(frm) {
		frm.set_value('transaction_date', frappe.datetime.now_date()); 
		frm.set_value('form_received_date', frappe.datetime.now_date()); 

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
	party_list: function(frm) {
		if(frm.doc.party_list != null) {
			frappe.call({
				method: "erpnext.projects.doctype.send_bulk_sms.send_bulk_sms.get_party_list_data",
				args: {
					party_list:frm.doc.party_list
				},
				callback: function(r, rt) {
					frm.set_value("party_mobile_no", r.message.party_mobile_no);
				}
			})
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

frappe.ui.form.on("Group SMS Form Table", {
	covid_form_serial: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.covid_form_serial != null) {
			frappe.call({
				method: "erpnext.projects.doctype.send_bulk_sms.send_bulk_sms.get_covid_form_data",
				args: {
					company: frm.doc.company,
					covid_form_serial:row.covid_form_serial
				},
				callback: function(r, rt) {
					frappe.model.set_value(cdt, cdn, "customer_name",r.message.custmer_name);
					frappe.model.set_value(cdt, cdn, "mobile_no",r.message.mobile_no);
					frappe.model.set_value(cdt, cdn, "analysis_result",r.message.analysis_result);
					frappe.model.set_value(cdt, cdn, "collection_date",r.message.collection_date);
					frappe.model.set_value(cdt, cdn, "customer_password",r.message.customer_password);
					frappe.model.set_value(cdt, cdn, "party_list",r.message.party_list);



				}
			})

		}
	},
	mobile_no: function(frm, cdt, cdn) {
	    cur_frm.fields_dict["group_sms_form_table"].$wrapper.find('.grid-body .rows').find(".grid-row").each(function(i, item) {
            let d = locals[cur_frm.fields_dict["group_sms_form_table"].grid.doctype][$(item).attr('data-name')];
			if( ((d["mobile_no"].includes('96277', 0)) || (d["mobile_no"].includes('96278', 0)) || (d["mobile_no"].includes('96279', 0))) &&  (d["mobile_no"].length == 12) ){
				$(item).find('.grid-static-col').css({'background-color': 'transparent'});
			}
			else {
				$(item).find('.grid-static-col').css({'background-color': 'yellow'});
			}
	   });
    },



})

