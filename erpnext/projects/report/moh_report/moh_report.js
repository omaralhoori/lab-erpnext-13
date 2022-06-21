// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["MOH Report"] = {
	"filters": [
			{
				"fieldname": "company",
				"label": __("Company"),
				"fieldtype": "Link",
				"options": "Company",
				"default": frappe.defaults.get_user_default("Company"),
				"reqd": 1
			},
			{
				"fieldname": "from_date",
				"label": __("From Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.now_date(),
				//"default": frappe.defaults.get_user_default("year_start_date"),

			},
			{
				"fieldname": "to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.now_date(),
				//"default": frappe.defaults.get_user_default("year_end_date"),
			},
			{
				"fieldname": "party_list",
				"label": __("Party List"),
				"fieldtype": "Link",
				"options": "Third Party",

			},
			{
				fieldname: "analysis_result",
				label: __("Result"),
				//fieldtype: "Link",
				//options: "Donors"
				fieldtype: "MultiSelectList",
				get_data: function(txt) {
					return frappe.db.get_link_options('Analysis Result', txt );
				}
			},
			{
				fieldname: "direction_name",
				label: __("Medical Direction"),
				//fieldtype: "Link",
				//options: "Donors"
				fieldtype: "MultiSelectList",
				get_data: function(txt) {
					return frappe.db.get_link_options('Medical Analysis Direction', txt );
				}
			},

	]
};
