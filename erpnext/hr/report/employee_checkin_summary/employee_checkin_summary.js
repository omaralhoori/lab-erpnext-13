// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employee Checkin Summary"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"filter_based_on",
			"label": __("Filter Based On"),
			"fieldtype": "Select",
			"options": ["Date", "Date Range"],
			"default": ["Date"],
			"reqd": 1,
			on_change: function() {
				let filter_based_on = frappe.query_report.get_filter_value('filter_based_on');
				frappe.query_report.toggle_filter_display('from_date', filter_based_on === 'Date');
				frappe.query_report.toggle_filter_display('to_date', filter_based_on === 'Date');
				frappe.query_report.toggle_filter_display('log_date', filter_based_on === 'Date Range');

				frappe.query_report.refresh();
			}
		},
		{
			"fieldname":"log_date",
			"label": __("Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"hidden": 1,
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"hidden": 1,
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"holiday_as_overtime",
			"label": __("Holidays As Overtime"),
			"fieldtype": "Check",
			"default": true
		},
	]
};
