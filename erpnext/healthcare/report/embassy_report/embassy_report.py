# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns()
	return columns, data



def get_columns( additional_table_columns=[]):
	"""return columns based on filters"""
	columns = [
		{
			'label': _("Invoice No"),
			'fieldname': 'sales_invoice',
			'fieldtype': 'Link',
			'options': 'Sales Invoice',
			'width': 120
		},
		{
			'label': _("Invoice Status"),
			'fieldname': 'invoice_status',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _("Visiting Date"),
			'fieldname': 'visiting_date',
			'fieldtype': 'Date',
			'width': 80
		},
		{
			'label': _("Patient"),
			'fieldname': 'patient',
			'fieldtype': 'Link',
			'options': 'Patient',
			'width': 240
		},
		{
			'label': _("Destination"),
			'fieldname': 'destination',
			'fieldtype': 'Link',
			'options': 'Country',
			'width': 240
		},

	]

	if additional_table_columns:
		columns += additional_table_columns

	return columns


def get_conditions(filters):
	conditions = ""

	if filters.get("company"): conditions += " si.company=%(company)s"
	else: conditions = " True"
	if filters.get("patient"): conditions += " and si.patient = %(patient)s"
	if filters.get("from_date"): conditions += " and si.posting_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and si.posting_date <= %(to_date)s"
	if filters.get("destination"): conditions += " and er.destination = %(destination)s"
	if filters.get("submitted"): conditions += " and si.docstatus=1"

	return conditions

def get_data(filters, additional_query_columns=[]):
	if additional_query_columns:
		additional_query_columns = ', ' + ', '.join(additional_query_columns)
	conditions = get_conditions(filters)
	cover_btn = ''
	if frappe.local.conf.is_embassy:
		cover_btn = """
		,  CONCAT('<a target="_blank" class=''btn btn-sm'' href="/api/method/erpnext.healthcare.doctype.lab_test.lab_test_print.get_embassy_cover?sales_invoice=',si.name,'">Print Cover</a>') as cover_btn
		"""
	invoices = frappe.db.sql("""
		select si.name as sales_invoice, si.posting_date as visiting_date,  si.patient,
		si.status as invoice_status, er.destination
		from`tabSales Invoice` as si 
		INNER JOIN  `tabEmbassy Report` as er  ON si.name=er.sales_invoice
		where %s order by si.creation""" %
		conditions, filters, as_dict=1)
	return invoices
