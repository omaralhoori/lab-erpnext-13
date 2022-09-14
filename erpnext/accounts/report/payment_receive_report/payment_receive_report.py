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
	conditions = get_conditions(filters)
	payments = frappe.db.sql(f"""
		SELECT payment_type, SUM(paid_amount) FROM `tabPayment Entry`
		{conditions}
		GROUP BY payment_type
	""")
	for payment in payments:
		if payment[0] == "Pay":
			data.append((payment[0], -1 * payment[1]))
		else:
			data.append(payment)
	return columns, data


def get_conditions(filters):
	where_stmt = "WHERE docstatus=1 AND payment_type<>'Internal Transfer'"#", AND True"
	if filters.get("posting_date"): where_stmt += f""" AND posting_date='{filters.get("posting_date")}'"""
	if filters.get("mode_of_payment"): where_stmt += f""" AND mode_of_payment='{filters.get("mode_of_payment")}'"""
	if filters.get("mode_of_payment_type"): where_stmt += f""" AND mode_of_payment_type='{filters.get("mode_of_payment_type")}'"""
	return where_stmt