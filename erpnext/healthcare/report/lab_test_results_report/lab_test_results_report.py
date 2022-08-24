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
			'label': _("Lab Status"),
			'fieldname': 'lab_status',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _("Radiology Status"),
			'fieldname': 'rad_status',
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
			'label': _("Passport"),
			'fieldname': 'passport_no',
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
		},
		{
			'label': "Print Xray",
			'fieldname': "xray_btn",
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
		select si.name as sales_invoice,p.passport_no, si.creation as visiting_date, si.insurance_party, si.patient, si.mobile_no as mobile,
		p.dob as birth_date, lt.status as lab_status, rt.record_status as rad_status,
		IF(lt.status IN ('Finalized', 'Partially Finalized'), CONCAT('<button class=''btn btn-sm'' with_header=''{1}'' data=''', lt.name ,''' onClick=''print_result(this.getAttribute("data"), this.getAttribute("with_header"))''>Print Test</button>'), '' )as print_btn,
		IF(rt.record_status IN ('Finalized'), CONCAT('<button class=''btn btn-sm'' with_header=''{1}'' data=''', si.name ,''' onClick=''print_xray(this.getAttribute("data"), this.getAttribute("with_header"))''>Print Xray</button>'), '' ) as xray_btn
		 {0}
		from`tabSales Invoice` as si 
		LEFT JOIN  `tabLab Test` as lt  ON si.name=lt.sales_invoice
		INNER JOIN `tabPatient` as p ON p.name=si.patient
		LEFT JOIN `tabRadiology Test` as rt ON rt.sales_invoice=si.name
		where %s order by si.creation""".format(additional_query_columns or '', with_header) %
		conditions, filters, as_dict=1)
	return invoices
