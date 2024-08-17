// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Data Clean', {
	refresh: function (frm) {
		frm.disable_save();
		frm.add_custom_button(__('Start Cleaning'), function () {
			frappe.confirm(`Are you sure you want to delete all data until ${frm.doc.to_date}?`,
				() => {
					frappe.confirm(`Are you sure you want to continue? This process is irreversible`,

						() => {
							frm.set_value("status", "In Progress")
							frm.set_value("error", "")
							frappe.call({
								"method": "erpnext.healthcare.doctype.data_clean.data_clean.clean_data_enque",
								"args": {
									"to_date": frm.doc.to_date
								},
								callback: res => {

								}
							})
							//frm.save()
						},
						() => {

						}
					)

				}, () => {
					// action to perform if No is selected
				})
		},);
	}
});
