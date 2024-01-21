// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Lab Test TAT Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default":  frappe.datetime.get_today(),
			"width": "80",
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"lab_test",
			"label": __("Lab Test"),
			"fieldtype": "Link",
			"options": "Lab Test Template",
			"get_query": function() {
				return {
					"filters": {
						"lab_test_template_type": ["=","Single"],
					}
				}
			}
		},
	]
};
