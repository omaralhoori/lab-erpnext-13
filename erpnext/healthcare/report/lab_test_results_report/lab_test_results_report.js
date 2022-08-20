// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Lab Test Results Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			"width": "80"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"insurance_party",
			"label": __("Insurance/Payer"),
			"fieldtype": "Link",
			"options": "Customer",
			"get_query": function() {
				return {
					"filters": {
						"customer_type": ["in","Payer,Insurance Company,Insurance Company Parties"],
					}
				}
			}
		},
		{
			"fieldname":"patient",
			"label": __("Patient"),
			"fieldtype": "Link",
			"options": "Patient"
		},
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"finalized",
			"label": __("Only Finalized"),
			"fieldtype": "Check",
			"default": 0
		},
	]
}

erpnext.utils.add_dimensions('Lab Test Results Report', 7);

const print_result = (msg) =>
{
	let url = `/api/method/erpnext.healthcare.doctype.lab_test.lab_test_print.print_report_result?lab_test=${msg}`;
	window.open(url, '_blank');
}