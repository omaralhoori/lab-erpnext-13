// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Group Set Paid",{
	onload: function(frm) {
			if (!frm.doc.transaction_date)		{frm.set_value('transaction_date', frappe.datetime.now_date());}
			if (!frm.doc.from_date)	{frm.set_value('from_date', frappe.datetime.now_date());}
 			if (!frm.doc.to_date)	{frm.set_value('to_date', frappe.datetime.now_date());}

	},
	get_form_received: function(frm) {
		var me = this;
		
		if (!frm.doc.get_data_by_serial ){
			if(!frm.doc.from_date) {
				frappe.msgprint(__("Please enter Forms Received Date"));
			} else {
				return frm.call({
					doc:frm.doc,
					method: "get_form_received_bydate",
					callback: function(r, rt) {
						cur_frm.cscript.update_totals(frm.doc);
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
						cur_frm.cscript.update_totals(frm.doc);
					}
				});
			}
		}
	},
	
});
frappe.ui.form.on("group party list paid", {
	paid_amount: function(frm, cdt, cdn) {
		cur_frm.cscript.update_totals(frm.doc);
	},
	analysis_amount: function(frm, cdt, cdn) {
		cur_frm.cscript.update_totals(frm.doc);
	},
	previous: function(frm, cdt, cdn) {
		cur_frm.cscript.update_totals(frm.doc);
	},

	group_party_list_paid_remove: function(frm, cdt, cdn) {
		cur_frm.cscript.update_totals(frm.doc);
	},
	group_party_list_paid_add: function(frm, cdt, cdn) {
		cur_frm.cscript.update_totals(frm.doc);
	},
	
})

cur_frm.cscript.update_totals = function(doc) {
	var main_total=0.0;
	var total_prev=0.0;
	var total_amount=0.0;

	var group_party_list_paid = doc.group_party_list_paid || [];
	for(var i in group_party_list_paid) 
	{
		main_total += flt(group_party_list_paid[i].paid_amount);
		total_prev += flt(group_party_list_paid[i].previous);
		total_amount += flt(group_party_list_paid[i].analysis_amount);
     	 }
	var doc = locals[doc.doctype][doc.name];
	doc.total_paid = main_total;
	doc.total_previous = total_prev;
	doc.total_analysis = total_amount;
	refresh_many(['total_paid','total_previous','total_analysis']);
      }

