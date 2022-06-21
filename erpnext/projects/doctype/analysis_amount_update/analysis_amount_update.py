# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import now_datetime, cint, cstr
from frappe.model.document import Document
import re
from six import string_types

class AnalysisAmountUpdate(Document):
	def __init__(self, *args, **kwargs):
		super(AnalysisAmountUpdate, self).__init__(*args, **kwargs)

	def on_submit(self):
		self.update_analysis_amount_result()

	def on_cancel(self):
		self.update_analysis_amount_result(cancel=1)



	def update_analysis_amount_result (self, cancel=0):
		if cancel:
			frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET analysis_amount = %s WHERE name = %s and company = %s """,  (self.analysis_amount_old,self.customer_name,self.company))
		else:
			frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET analysis_amount = %s WHERE name = %s and company = %s """,  (self.analysis_amount,self.customer_name,self.company))



@frappe.whitelist()
def get_customer_name(doctype, txt, searchfield, start, page_len, filters):
	link_company = filters.pop('link_company')

	fields = ["caf.name","caf.custmer_name"]
	fields = ", ".join(fields)
		
	return frappe.db.sql("""select
			{field} 
		from
			`tabCOVID Analysis Form` caf
		where	
			caf.company = %(link_company)s  and
			(
			caf.name like %(txt)s  or
			caf.custmer_name like %(txt)s  
			) 
		order by caf.date desc
		limit %(start)s, %(page_len)s """.format(**{
			'field': fields,
			'key': frappe.db.escape(searchfield)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': 50,
			'link_company': link_company
		})




@frappe.whitelist()
def get_customer_name_data(company,customer_name):

	desc = frappe.db.get_value("COVID Analysis Form",
		{"company": company,"name":customer_name}, "custmer_name")

	analysis_amount = frappe.db.get_value("COVID Analysis Form",
		{"company": company,"name":customer_name}, "analysis_amount")


	return {
		"desc":desc,
		"analysis_amount":analysis_amount,
	}

