// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Radiology Test', {
	refresh: function(frm) {
		if (frm.doc.record_status == "Finalized"){
			frm.set_df_property("test_results","read_only",1);
		}else{
			frm.set_df_property("test_results","read_only",0);
		}
		if(frappe.user.has_role('Xray Approver')){
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
		}
		if(frappe.user.has_role('Xray Technician')){
			
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


frappe.ui.form.on("Radiology Test Result", {
	get_template: async function(frm, cdt, cdn) {
		console.log(cdt, cdn)
		var template_name = frappe.model.get_value("Radiology Test Result", cdn, "radiology_template")
		if (!template_name) return;
		var res = await frappe.db.get_value("Radiology Template", "HAND X-RAY", "template")
		if (!res.message.template) return;
		frappe.model.set_value("Radiology Test Result", cdn, "test_result", res.message.template)
	}
	});