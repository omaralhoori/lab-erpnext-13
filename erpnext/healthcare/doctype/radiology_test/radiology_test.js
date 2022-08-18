// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Radiology Test', {
	refresh: function(frm) {
		if (frm.doc.record_status == "Finalized"){
			frm.set_df_property("test_results","read_only",1);
		}else{
			frm.set_df_property("test_results","read_only",0);
		}
		
		if(frappe.user.has_role('Xray Technician')){
			frm.add_custom_button("Finalize",  () => {
				frappe.call({
					method: "erpnext.healthcare.doctype.radiology_test.radiology_test.finalize_selected",
					args: {
						tests:  [`"${frm.doc.name}"`]
					}
					,callback: () => {
						frm.reload_doc();
					}
				})
			})

			frm.add_custom_button("Definalize",  () => {
				frappe.call({
					method: "erpnext.healthcare.doctype.radiology_test.radiology_test.definalize_selected",
					args: {
						tests: [`"${frm.doc.name}"`]
					}
					,callback: () => {
						frm.reload_doc();
					}
				})
			})
			frm.add_custom_button("Realese",  () => {
				frappe.call({
					method: "erpnext.healthcare.doctype.radiology_test.radiology_test.release_selected",
					args: {
						tests: [`"${frm.doc.name}"`]
					}
					,callback: () => {
						frm.reload_doc();
					}
				})
			})

			frm.add_custom_button("Unrealese",  () => {
				frappe.call({
					method: "erpnext.healthcare.doctype.radiology_test.radiology_test.unrelease_selected",
					args: {
						tests: [`"${frm.doc.name}"`]
					}
					,callback: () => {
						frm.reload_doc();
					}
				})
			})
			frm.add_custom_button("Print",  () => {
				let url = `/api/method/erpnext.healthcare.doctype.lab_test.lab_test_print.get_xray_report?sales_invoice=${frm.doc.sales_invoice}`
							window.open(url, '_blank')
			})
		}
		
	}
});
