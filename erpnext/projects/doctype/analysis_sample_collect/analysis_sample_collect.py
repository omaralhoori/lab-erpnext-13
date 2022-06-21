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



class AnalysisSampleCollect(Document):
	def __init__(self, *args, **kwargs):
		super(AnalysisSampleCollect, self).__init__(*args, **kwargs)

	def on_submit(self):
		self.update_collect_sample_flag()
		self.update_voucher_barcode()

	def on_cancel(self):
		self.update_collect_sample_flag(cancel=1)
		self.update_voucher_barcode(cancel=1)



	def update_collect_sample_flag (self, cancel=0):
		if cancel:
			frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET sample_collect_flag = 0
				WHERE name = %s and company = %s """, (self.customer_name,self.company))

			#frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET analysis_result = %s
			#	WHERE name = %s and company = %s """, ("Negative",self.customer_name,self.company))

		else:
			frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET sample_collect_flag = 1 , collection_date = %s , collection_time = %s , collection_users = %s
				WHERE name = %s and company = %s """,  (self.date,self.time,self.owner,self.customer_name,self.company))

			#frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET analysis_result = %s
			#	WHERE name = %s and company = %s """, ("Negative",self.customer_name,self.company))

	def update_voucher_barcode (self, cancel=0):
		if cancel:
			frappe.db.sql(""" UPDATE `tabAnalysis Sample Collect` SET barcode = %s
				WHERE customer_name = %s and company = %s """, ("",self.customer_name,self.company))

			frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET barcode = %s
				WHERE name = %s and company = %s """, ("",self.customer_name,self.company))

		else:
			barcode = get_barcode(self.company,self.customer_name,self.date)
			self.barcode = barcode

			frappe.db.sql(""" UPDATE `tabAnalysis Sample Collect` SET barcode = %s
				WHERE customer_name = %s and company = %s """,  (barcode,self.customer_name,self.company))

			frappe.db.sql(""" UPDATE `tabCOVID Analysis Form` SET barcode = %s
				WHERE name = %s and company = %s """, (barcode,self.customer_name,self.company))


@frappe.whitelist()
def get_barcode(company,customer_name,date):
	#2020-09-19
	#0123456789
	dayval=date[8:10]
	monval=date[5:7]
	
	daystr = ""
	if dayval=="01":
		daystr = "A"
	if dayval=="02":
		daystr = "B"
	if dayval=="03":
		daystr = "C"
	if dayval=="04":
		daystr = "D"
	if dayval=="05":
		daystr = "E"
	if dayval=="06":
		daystr = "F"
	if dayval=="07":
		daystr = "G"
	if dayval=="08":
		daystr = "H"
	if dayval=="09":
		daystr = "I"
	if dayval=="10":
		daystr = "J"
	if dayval=="11":
		daystr = "K"
	if dayval=="12":
		daystr = "L"
	if dayval=="13":
		daystr = "M"
	if dayval=="14":
		daystr = "N"
	if dayval=="15":
		daystr = "O"
	if dayval=="16":
		daystr = "P"
	if dayval=="17":
		daystr = "Q"
	if dayval=="18":
		daystr = "R"
	if dayval=="19":
		daystr = "S"
	if dayval=="20":
		daystr = "T"
	if dayval=="21":
		daystr = "U"
	if dayval=="22":
		daystr = "V"
	if dayval=="23":
		daystr = "W"
	if dayval=="24":
		daystr = "X"
	if dayval=="25":
		daystr = "Y"
	if dayval=="26":
		daystr = "Z"
	if dayval=="27":
		daystr = "AG"
	if dayval=="28":
		daystr = "AK"
	if dayval=="29":
		daystr = "AL"
	if dayval=="30":
		daystr = "AM"
	if dayval=="31":
		daystr = "AN"
	
	monstr = ""
	if monval=="01":
		monstr = "JA"
	if monval=="02":
		monstr = "F"
	if monval=="03":
		monstr = "M"
	if monval=="04":
		monstr = "A"
	if monval=="05":
		monstr = "M"
	if monval=="06":
		monstr = "J"
	if monval=="07":
		monstr = "JU"
	if monval=="08":
		monstr = "O"
	if monval=="09":
		monstr = "S"
	if monval=="10":
		monstr = "O"
	if monval=="11":
		monstr = "N"
	if monval=="12":
		monstr = "D"

	medical_direction_code = get_medical_direction_code(company,customer_name)
	
	transaction_count = get_transaction_count(company,date)

	barcode = medical_direction_code + "-" + daystr + "-" + transaction_count + "-" + monstr	#self.date[8:10]+":"+self.date[5:7]
	
	return	barcode 


@frappe.whitelist()
def get_transaction_count(company,date):

	res = frappe.db.sql(
			'select '
			'count(*) as transaction_count '
			'from '
			'`tabAnalysis Sample Collect` '
			'where '
			'`tabAnalysis Sample Collect`.company = %s and '
			'`tabAnalysis Sample Collect`.date = %s and '
			'`tabAnalysis Sample Collect`.docstatus = 1 ',
			(company,date), as_dict=1
		)

	transaction_count = res[0].get('transaction_count', 0) if res else 0
	
	transaction_count = transaction_count 

	return cstr(transaction_count)

@frappe.whitelist()
def get_medical_direction_code(company,customer_name):

	res = frappe.db.sql(
			'select '
			'`tabCOVID Analysis Form`.medical_direction_code as medical_direction_code '
			'from '
			'`tabCOVID Analysis Form` '
			'where '
			'`tabCOVID Analysis Form`.company = %s and '
			'`tabCOVID Analysis Form`.name = %s ',
			(company, customer_name), as_dict=1
		)

	medical_direction_code = res[0].get('medical_direction_code', "0") if res else "0"

	return medical_direction_code

@frappe.whitelist()
def get_customer_name(doctype, txt, searchfield, start, page_len, filters):
	link_company = filters.pop('link_company')

	return frappe.db.sql("""select
			`tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name 
		from
			`tabCOVID Analysis Form`
		where
			`tabCOVID Analysis Form`.company = %(link_company)s and
			`tabCOVID Analysis Form`.sample_collect_flag = 0 
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

	return {
		"desc":desc
	}

