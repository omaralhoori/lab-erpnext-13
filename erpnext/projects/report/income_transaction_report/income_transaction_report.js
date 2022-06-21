// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Income Transaction Report"] = {
	"filters": [
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			//default: frappe.datetime.add_days(frappe.datetime.month_start(),-1),
		}
	]
}
