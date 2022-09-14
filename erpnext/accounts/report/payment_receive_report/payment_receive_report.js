// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Payment Receive Report"] = {
	"filters": [
		{
			"fieldname":"posting_date",
			"label": __("Posting Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"mode_of_payment",
			"label": __("Mode of Payment"),
			"fieldtype": "Link",
			"options": "Mode of Payment"
		},
		{
			"fieldname":"mode_of_payment_type",
			"label": __("Mode of Payment Type"),
			"fieldtype": "Select",
			"options": "\nCash\nCard\nBank\nGeneral\nPhone"
		}
	]
};
