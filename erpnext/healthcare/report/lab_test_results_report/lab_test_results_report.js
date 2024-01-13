// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */
// frappe.datetime.add_days(frappe.datetime.get_today(), -1),
frappe.query_reports["Lab Test Results Report"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default":  frappe.datetime.get_today(),
			"width": "80"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"patient",
			"label": __("Patient"),
			"fieldtype": "Link",
			"options": "Patient"
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
		{
			"fieldname":"with_header",
			"label": __("Print with Header"),
			"fieldtype": "Check",
			"default": 1
		},
	]
}

erpnext.utils.add_dimensions('Lab Test Results Report', 7);

const print_result = (msg, with_header, print_previous) =>
{
	frappe.call({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.check_invoice_paid",
		args: {
			doctype: "Lab Test",
			docname: msg
		},
		callback: function(res){
			if (res.message){
				var prev= ''
				if (print_previous){
					prev = '&previous=1'
				}
				let url = `/api/method/erpnext.healthcare.doctype.lab_test.lab_test_print.lab_test_result?lab_test=${msg}&head=${with_header}&only_finilized=1${prev}`;
				window.open(url, '_blank');
			}else{
				frappe.msgprint({
					title: __('Warning'),
					indicator: 'red',
					message: __("The invoice for this test has not been paid")
				});
			}
		}
})
}

const send_sms = (lab_test) =>
{
	frappe.call({
		method: "erpnext.healthcare.doctype.lab_test.lab_test.send_patient_result_sms",
		args: {
			lab_test: lab_test
		},
		callback: function(res){
			if (res.message){
				frappe.msgprint("Sms sent successfully")
			}else{
				frappe.msgprint("Unable to send sms")
			}
		}
})
}
const print_clinical = (msg, with_header, print_previous) =>
{
	frappe.call({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.check_invoice_paid",
		args: {
			doctype: "Lab Test",
			docname: msg
		},
		callback: function(res){
			if (res.message){
				var prev= ''
				if (print_previous){
					prev = '&previous=1'
				}
				let url = `/api/method/erpnext.healthcare.doctype.clinical_testing.clinical_testing.clnc_test_result?lab_test=${msg}&head=${with_header}&only_finilized=1${prev}`;
				window.open(url, '_blank');
			}else{
				frappe.msgprint({
					title: __('Warning'),
					indicator: 'red',
					message: __("The invoice for this test has not been paid")
				});
			}
		}
})
}


const print_xray = (msg, with_header) =>
{
	frappe.call({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.check_invoice_paid",
		args: {
			invoice: msg
		},
		callback: function(res){
			if (res.message){
				let url = `/api/method/erpnext.healthcare.doctype.lab_test.lab_test_print.print_report_xray?sales_invoice=${msg}&with_header=${with_header}`;
				window.open(url, '_blank');
			}else{
				frappe.msgprint({
					title: __('Warning'),
					indicator: 'red',
					message: __("The invoice for this test has not been paid")
				});
			}
		}
})
}