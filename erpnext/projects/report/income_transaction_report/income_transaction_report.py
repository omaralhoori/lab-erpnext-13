from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.projects.report.party_transaction import get_columns_income,get_data_income

def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns_income()
	data = get_data_income(filters)

	return columns, data
