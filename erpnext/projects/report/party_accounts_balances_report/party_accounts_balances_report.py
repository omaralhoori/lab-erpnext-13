# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.projects.report.party_transaction import get_columns,get_columns_total, get_data,get_data_total

def execute(filters=None):
	filters = frappe._dict(filters or {})

	if filters.rep_type == "0":
		columns = get_columns()
		data = get_data(filters)

	if filters.rep_type == "1":
		columns = get_columns_total()
		data = get_data_total(filters)

	return columns, data
