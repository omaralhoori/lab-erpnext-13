// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Receivable Invoice', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1){
			$(`button[data-original-title="Print"]`).show()
			$(`span[data-label="Print"]`).parent().show()
		}else{
			$(`button[data-original-title="Print"]`).hide()
			$(`span[data-label="Print"]`).parent().hide()
		}

		frm.set_query("insurance_party", function (doc) {
			return {
				"filters": {
					"customer_type": ["in","Payer,Insurance Company,Insurance Company Parties"],
				}
			}
		});
	},
});
