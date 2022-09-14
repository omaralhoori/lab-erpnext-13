# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns = [
		{
			"fieldname": "payment_type",
			"label": _("Payment Type"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "paid_amount",
			"label": _("Paid Amount"),
			"fieldtype": "Float",
			"width": 120
		},
	]

	data = frappe.db.sql("""
		SELECT payment_type, SUM(paid_amount) FROM `tabPayment Entry`
		WHERE docstatus=1 AND payment_type<>'Internal Transfer'
		GROUP BY payment_type
	""")
	return columns, data
