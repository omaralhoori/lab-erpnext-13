// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Party Accounts Balances Report"] = {
	"filters": [
		{
			fieldname: "all_party",
			label: __("All party"),
			fieldtype: "Check",
			default: 1,
			on_change: () => {
				var all_party_filter = frappe.query_report.get_filter_value('all_party');
				var party_list_filter = frappe.query_report.get_filter('party_list');
				if (all_party_filter=="0") { 
					party_list_filter.toggle(true);
				} else {
					party_list_filter.toggle(false);  
				}
				party_list_filter.refresh();
				frappe.query_report.refresh();
			}
		},
		{
			fieldname: "party_list",
			label: __("Party List"),
			//fieldtype: "Link",
			//options: "Third Party"
			fieldtype: "MultiSelectList",
			hidden:1,
			get_data: function(txt) {
				return frappe.db.get_link_options('Third Party', txt );
			},
		},
		{
			fieldname: "rep_type",
			label: __("Report Type"),
			fieldtype: "Select",
			options: [
				{ "value": "0", "label": __("Transaction Report") },
				{ "value": "1", "label": __("Balance Report") }
			],
			default: "1",
			on_change: () => {
				var rep_type_filter = frappe.query_report.get_filter_value('rep_type');
				var from_date_filter = frappe.query_report.get_filter('from_date');
				var to_date_filter = frappe.query_report.get_filter('to_date');
				var all_party_filter = frappe.query_report.get_filter('all_party');
				var party_list_filter = frappe.query_report.get_filter('party_list');
				var party_filter = frappe.query_report.get_filter('party');
				if (rep_type_filter=="0") { //if = Transaction Report enable from_date , to_date 
					from_date_filter.toggle(true);
					to_date_filter.toggle(true);
					all_party_filter.toggle(false);
					party_list_filter.toggle(false);
					party_filter.toggle(true);
				} else {
					from_date_filter.toggle(false);  
					to_date_filter.toggle(false);
					all_party_filter.toggle(true);
					party_list_filter.toggle(true);
					party_filter.toggle(false);
				}
				from_date_filter.refresh();
				to_date_filter.refresh();
				all_party_filter.refresh();
				party_list_filter.refresh();
				party_filter.refresh();
				frappe.query_report.refresh();
			}

		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "Link",
			options: "Third Party",
			hidden:1,
		},
		{
			fieldname:"from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_start_date"),
			hidden:1
			//default: frappe.datetime.add_months(frappe.datetime.month_start(), -1),
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			hidden:1
			//default: frappe.datetime.add_days(frappe.datetime.month_start(),-1),
		},
	]
}
