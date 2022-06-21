// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transfer To Bank', {
	// refresh: function(frm) {

	// }
	get_form_received: function(frm) {
		var me = this;
		
		if (!frm.doc.get_data_by_serial ){
			if(!frm.doc.from_date ||  !frm.doc.to_date ) {
				frappe.msgprint(__("Please enter date range (From Date / To Date) "));
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

frappe.ui.form.on("Covid Form Bank Transfer", {
	transfer_amount: function(frm, cdt, cdn) {
		cur_frm.cscript.update_totals(frm.doc);
	},

	covid_forms_bank_transfer_remove: function(frm, cdt, cdn) {
		cur_frm.cscript.update_totals(frm.doc);
	},
	covid_forms_bank_transfer_add: function(frm, cdt, cdn) {
		cur_frm.cscript.update_totals(frm.doc);
	},
	
});

cur_frm.cscript.update_totals = function(doc) {
	var total_paid=0.0;
	var total_transfer=0.0;

	var covid_forms_bank_transfer = doc.covid_forms_bank_transfer || [];
	for(var i in covid_forms_bank_transfer) 
	{
		total_paid += flt(covid_forms_bank_transfer[i].paid_amount);
		total_transfer += flt(covid_forms_bank_transfer[i].transfer_amount);
    }

	var doc = locals[doc.doctype][doc.name];
	doc.total_paid = total_paid;
	doc.total_transfer = total_transfer;
	refresh_many(['total_paid','total_transfer']);
}

