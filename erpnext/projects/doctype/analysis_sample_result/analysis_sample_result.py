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

class AnalysisSampleResult(Document):
	def __init__(self, *args, **kwargs):
		super(AnalysisSampleResult, self).__init__(*args, **kwargs)

	def on_submit(self):
		self.update_collect_sample_result()

	def on_cancel(self):
		self.update_collect_sample_result(cancel=1)



	def update_collect_sample_result (self, cancel=0):
		if cancel:
			frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET analysis_result = %s , update_result_date = %s , update_result_time = %s , 
				update_result_user = %s,collection_date = %s , collection_time = %s ,result_date = %s , result_time = %s WHERE name = %s and company = %s """,  (self.analysis_result_old,self.collection_date_old,self.collection_time_old,"",self.collection_date_old,self.collection_time_old,self.result_date_old,self.result_time_old,self.customer_name,self.company))
		else:
			frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET analysis_result = %s , update_result_date = %s , update_result_time = %s , 
				update_result_user = %s,collection_date = %s , collection_time = %s ,result_date = %s , result_time = %s WHERE name = %s and company = %s """,  (self.analysis_result,self.date,self.time,frappe.session.user,self.collection_date,self.collection_time,self.result_date,self.result_time,self.customer_name,self.company))



@frappe.whitelist()
def get_customer_name(doctype, txt, searchfield, start, page_len, filters):
	link_company = filters.pop('link_company')

	return frappe.db.sql("""select
			`tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name 
		from
			`tabCOVID Analysis Form`
		where
			`tabCOVID Analysis Form`.company = %(link_company)s and
			`tabCOVID Analysis Form`.sample_collect_flag = 1 and
			`tabCOVID Analysis Form`.result_flage = 1 
		order by `tabCOVID Analysis Form`.date desc
		limit %(start)s, %(page_len)s """, {
			'txt': '%' + txt + '%',
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'link_company': link_company
		})



@frappe.whitelist()
def get_customer_name_data(company,customer_name):

	desc = frappe.db.get_value("COVID Analysis Form",
		{"company": company,"name":customer_name}, "custmer_name")

	collection_date = frappe.db.get_value("COVID Analysis Form",
		{"company": company,"name":customer_name}, "collection_date")

	collection_time = frappe.db.get_value("COVID Analysis Form",
		{"company": company,"name":customer_name}, "collection_time")

	result_date = frappe.db.get_value("COVID Analysis Form",
		{"company": company,"name":customer_name}, "result_date")

	result_time = frappe.db.get_value("COVID Analysis Form",
		{"company": company,"name":customer_name}, "result_time")

	analysis_result = frappe.db.get_value("COVID Analysis Form",
		{"company": company,"name":customer_name}, "analysis_result")

	return {
		"desc":desc,
		"collection_date":collection_date,
		"collection_time":collection_time,
		"analysis_result":analysis_result,
	}

