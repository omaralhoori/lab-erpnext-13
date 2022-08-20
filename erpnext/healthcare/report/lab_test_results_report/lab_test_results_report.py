# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	data = get_tests(filters)
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
			'label': _("Status"),
			'fieldname': 'status',
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
			'label': _("Insurance Payer"),
			'fieldname': 'insurance_party',
			'fieldtype': 'Link',
			'options': 'Customer',
			'width': 120
		},
		{
			'label': _("Patient"),
			'fieldname': 'patient',
			'fieldtype': 'Link',
			'options': 'Patient',
			'width': 240
		},
		{
			'label': _("Mobile"),
			'fieldname': 'mobile',
			'fieldtype': 'Data',
			'width': 120
		},
			{
			'label': _("Birth Date"),
			'fieldname': 'birth_date',
			'fieldtype': 'Date',
			'width': 120
		},
		{
			'label': "Print Result",
			'fieldname': "print_btn",
			'fieldtype': 'html',
			'width': 120
		}
	]

	if additional_table_columns:
		columns += additional_table_columns

	return columns



def get_conditions(filters):
	conditions = ""

	if filters.get("company"): conditions += " lt.company=%(company)s"
	if filters.get("patient"): conditions += " and lt.patient = %(patient)s"
	if filters.get("insurance_party"): conditions += " and si.insurance_party = %(insurance_party)s"

	if filters.get("from_date"): conditions += " and si.posting_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and si.posting_date <= %(to_date)s"
	if filters.get("finalized"): conditions += " and lt.status IN ('Finalized', 'Partially Finalized') "
	return conditions


def get_tests(filters, additional_query_columns=[]):
	if additional_query_columns:
		additional_query_columns = ', ' + ', '.join(additional_query_columns)
	with_header = filters.get("with_header") or ''
	conditions = get_conditions(filters)
	invoices = frappe.db.sql("""
		select lt.name,lt.sales_invoice, lt.creation as visiting_date, si.insurance_party, lt.patient, lt.patient_mobile as mobile,
		p.dob as birth_date, lt.status,
		IF(lt.status IN ('Finalized', 'Partially Finalized'), CONCAT('<button class=''btn btn-sm'' with_header=''{1}'' data=''', lt.name ,''' onClick=''print_result(this.getAttribute("data"), this.getAttribute("with_header"))''>Print</button>'), '' )as print_btn
		 {0}
		from `tabLab Test` as lt
		INNER JOIN `tabSales Invoice` as si ON si.name=lt.sales_invoice
		INNER JOIN `tabPatient` as p ON p.name=lt.patient
		where %s order by lt.creation""".format(additional_query_columns or '', with_header) %
		conditions, filters, as_dict=1)
	return invoices
