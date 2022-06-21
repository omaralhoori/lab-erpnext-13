from __future__ import unicode_literals

import frappe
from frappe import _

no_cache = 1

def get_context(context):
	context.customer_password = '5';
	if frappe.session.user=='Guest':
		frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)

def has_website_permission(doc, ptype, user, verbose=False):
	doc.customer_password = 55;

@frappe.whitelist()
def get_customer_data(customer_password):
	customer_name = frappe.db.get_value("COVID Analysis Form",
		{"customer_password": customer_password}, "custmer_name")

	analysis_result = frappe.db.get_value("COVID Analysis Form",
		{"customer_password": customer_password}, "analysis_result")


	return {
		"customer_name": customer_name,
		"analysis_result": analysis_result,
	}



