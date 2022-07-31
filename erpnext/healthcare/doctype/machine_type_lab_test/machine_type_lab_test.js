// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Machine Type Lab Test', {
	refresh : function(frm) {
		frm.set_query('lab_test_template', 'machine_type_lab_test_template', function() {
			return {
				filters: {
					lab_test_template_type: ['in', ['Multiline','Single']],
					disabled: ['in', ['0','1']]
				}
			};
		});
		frm.set_query('lab_test_parent_parent', 'machine_type_lab_test_template', function() {
			return {
				filters: {
					lab_test_template_type: ['in', ['Multiline']],
					disabled: ['in', ['0','1']]
				}
			};
		});
	},
});
