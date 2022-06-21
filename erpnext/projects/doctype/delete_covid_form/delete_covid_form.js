// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delete COVID Form', {
	get_form_received: function(frm) {
		if(!frm.doc.from_date) {
			frappe.msgprint(__("Enter from date"));
		}

		if(!frm.doc.to_date) {
			frappe.msgprint(__("Enter to date"));
		}

		var me = this;
		return frm.call({
			doc:frm.doc,
			method: "get_form_received_bydate",
			callback: function(r, rt) {
				cur_frm.cscript.update_totals(frm.doc);
			}
		});
	}
});

