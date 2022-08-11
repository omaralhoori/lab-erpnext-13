# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, msgprint
from frappe.model.meta import get_field_precision
from frappe.utils import flt

def execute(filters=None):
	return _execute(filters)

def _execute(filters, additional_table_columns=None, additional_query_columns=None):
	if not filters: filters = frappe._dict({})

	invoice_list = get_invoices(filters, additional_query_columns)
	columns = get_columns(invoice_list, additional_table_columns)

	if not invoice_list:
		msgprint(_("No record found"))
		return columns, invoice_list

	company_currency = frappe.get_cached_value('Company',  filters.get("company"),  "default_currency")

	data = []
	for inv in invoice_list:
		# invoice details

		row = {
			'invoice': inv.name,
			'posting_date': inv.posting_date,
			'customer': inv.customer,
			'insurance_party': inv.insurance_party
		}

		if additional_query_columns:
			for col in additional_query_columns:
				row.update({
					col: inv.get(col)
				})

		row.update({
			'customer_group': inv.get("customer_group"),
		})

		# map income values
		base_net_total = 0

		# net total
		row.update({'net_total': inv.total_discount_provider}) #  base_net_total or inv.base_net_total})

		# total tax, grand total, outstanding amount & rounded total

		row.update({
			'grand_total': inv.total,
			'total_patient': inv.total_patient, 
			'outstanding_amount': inv.outstanding_amount
		})

		data.append(row)

	return columns, data

def get_columns(invoice_list, additional_table_columns):
	"""return columns based on filters"""
	columns = [
		{
			'label': _("Invoice No"),
			'fieldname': 'invoice',
			'fieldtype': 'Link',
			'options': 'Sales Invoice',
			'width': 120
		},
		{
			'label': _("Posting Date"),
			'fieldname': 'posting_date',
			'fieldtype': 'Date',
			'width': 80
		},
		{
			'label': _("Insurance Payer"),
			'fieldname': 'insurance_party',
			'fieldtype': 'Link',
			'options': 'Customer',
			'width': 120
		},
		{
			'label': _("Customer"),
			'fieldname': 'customer',
			'fieldtype': 'Link',
			'options': 'Customer',
			'width': 120
		},
	]

	if additional_table_columns:
		columns += additional_table_columns

	columns +=[
		{
			'label': _("Customer Group"),
			'fieldname': 'customer_group',
			'fieldtype': 'Link',
			'options': 'Customer Group',
			'width': 120
		},
	]

	total_columns = [
		{
			"label": _("Full Charge"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"options": 'currency',
			"width": 120
		},
		{
			"label": _("Provider/Discount"),
			"fieldname": "net_total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": _("Patient Share"),
			"fieldname": "total_patient",
			"fieldtype": "Currency",
			"options": 'currency',
			"width": 120
		},
		{
			"label": _("Outstanding Amount"),
			"fieldname": "outstanding_amount",
			"fieldtype": "Currency",
			"options": 'currency',
			"width": 120
		}
	]

	columns = columns +  total_columns

	return columns

def get_conditions(filters):
	conditions = ""

	if filters.get("company"): conditions += " and company=%(company)s"
	if filters.get("customer"): conditions += " and customer = %(customer)s"
	if filters.get("insurance_party"): conditions += " and insurance_party = %(insurance_party)s"

	if filters.get("from_date"): conditions += " and posting_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and posting_date <= %(to_date)s"

	return conditions

def get_invoices(filters, additional_query_columns):
	if additional_query_columns:
		additional_query_columns = ', ' + ', '.join(additional_query_columns)

	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select name, posting_date, debit_to,  customer, total, total_discount_provider, total_patient,
		insurance_party,  customer_group,
		base_net_total, base_grand_total, base_rounded_total, outstanding_amount,
		is_internal_customer, represents_company, company {0}
		from `tabSales Invoice`
		where docstatus = 1 %s order by posting_date , name """.format(additional_query_columns or '') %
		conditions, filters, as_dict=1)

