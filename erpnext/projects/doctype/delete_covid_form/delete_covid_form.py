# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.model.meta import get_field_precision
from frappe.model.document import Document
from frappe.utils import  flt ,getdate ,nowdate,get_datetime, cint, cstr , now_datetime ,datetime
from datetime import timedelta

class DeleteCOVIDForm(Document):
	def __init__(self, *args, **kwargs):
		super(DeleteCOVIDForm, self).__init__(*args, **kwargs)

	def on_submit(self):
		self.delete_forms()

	@frappe.whitelist()
	def get_form_received_bydate(self):
		company = self.company
		from_date = self.from_date
		to_date = self.to_date
		conditions = " and 1=1 "

		if 	self.party_list:
			conditions = conditions + " and party_list='" + self.party_list + "'"

		if 	self.payment_type:
			conditions = conditions + " and payment_type='" + self.payment_type + "'"

		if 	self.analysis_result:
			conditions = conditions + " and analysis_result='" + self.analysis_result + "'"

		if 	self.medical_direction:
			conditions = conditions + " and medical_direction='" + self.medical_direction + "'"

		self.set("delete_covid_form_details", [])

		if from_date<=to_date:	
			gr_sample = frappe.db.sql("""
				select name,custmer_name,collection_date,analysis_result,result_date,payment_type,party_list,medical_direction
				from `tabCOVID Analysis Form`
				where company = %(company)s
				{conditions}
				and DATE_FORMAT(creation,'%%Y-%%m-%%d') between DATE_FORMAT(%(from_date)s,'%%Y-%%m-%%d') and DATE_FORMAT(%(to_date)s,'%%Y-%%m-%%d')
				order by `tabCOVID Analysis Form`.creation DESC
					""".format(conditions=conditions), {
					"company": company,
					"from_date": from_date,
					"to_date": to_date
					}, as_dict=True)

			for d in gr_sample:
				group_sample = self.append("delete_covid_form_details")
				group_sample.covid_form_serial = d.name
				group_sample.customer_name = d.custmer_name
				group_sample.collection_date = d.collection_date
				group_sample.analysis_result = d.analysis_result
				group_sample.result_date = d.result_date
				group_sample.payment_type = d.payment_type
				group_sample.party_list = d.party_list
				group_sample.medical_direction = d.medical_direction
				
	@frappe.whitelist()
	def delete_forms (self, cancel=0):
		for sample in self.get("delete_covid_form_details"):
			frappe.db.delete("Group Sample Collection Table", {"covid_form_serial": sample.covid_form_serial})
			frappe.db.delete("Group Result Table", {"covid_form_serial": sample.covid_form_serial})
			frappe.db.delete("Analysis Sample Result", {"customer_name": sample.covid_form_serial})
			frappe.db.delete("Group SMS Form Table", {"covid_form_serial": sample.covid_form_serial})
			frappe.db.delete("group party list paid", {"covid_form_serial": sample.covid_form_serial})
			frappe.db.delete("Covid Form Bank Transfer", {"covid_form_serial": sample.covid_form_serial})
			frappe.db.delete("COVID Analysis Form", {"name": sample.covid_form_serial})

	

