# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters={}):
	columns, data = get_columns(), get_data(filters=filters)
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "report_code",
			"label": _("Test ID"),
			'fieldtype': 'Link',
			'options': 'Lab Test Template',
			'width': '80'
		},
		{
			"fieldname": "lab_test_name",
			"label": _("Test Name"),
			'fieldtype': 'Data',
			'width': '200'
		},
		{
			"fieldname": "test_count",
			"label": _("Test Count"),
			'fieldtype': 'Data',
			'width': '80'
		},
	]
# 	

def get_data(filters):
	where_stmt = ""
	if filters.get('report_code'):
		where_stmt += " AND res.report_code=%(report_code)s"
	return frappe.db.sql("""
		SELECT DISTINCT res.report_code,res.parent, tmplt.lab_test_name, 
		count(DISTINCT res.report_code, res.parent) as test_count FROM `tabNormal Test Result` as res
		INNER JOIN `tabLab Test` as test ON test.name=res.parent
		INNER JOIN `tabLab Test Template` as tmplt on tmplt.name =res.report_code
		WHERE test.creation BETWEEN %(from_date)s AND %(to_date)s AND test.company=%(company)s {where_stmt}
		GROUP BY res.report_code
		ORDER BY test_count DESC
	""".format(where_stmt=where_stmt), {**filters}, as_dict=True)