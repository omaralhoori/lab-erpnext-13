// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Embassy Report', {
	refresh: function(frm) {
		if(!frm.is_new())
		{
			frm.add_custom_button(__('Print'), function(){
				//let url = `/printview?doctype=Lab%20Test&name=${frm.doc.name}&trigger_print=1&format=Lab%20Test%20Print&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en-US`;
				let url = `/api/method/erpnext.healthcare.doctype.lab_test.lab_test_print.get_embassy_cover?sales_invoice=${frm.doc.sales_invoice}`
				window. open(url, '_blank')
			})
		}
	}
});
