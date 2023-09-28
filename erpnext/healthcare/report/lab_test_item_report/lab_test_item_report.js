// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Lab Test Item Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.now_date(),
			"reqd": 1
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"default": frappe.defaults.get_default("Company"),
			"options": "Company",
			"reqd": 1

		},
		{
			"fieldname": "report_code",
			"label": __("Lab Test"),
			"fieldtype": "Link",
			"options": "Lab Test Template",
			get_query: () => {
				return {
					filters: {
						'lab_test_template_type': 'Multiline',
						'disabled': 0
					}
				}
			}

		},
	]
};
