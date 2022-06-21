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

class GroupSetPaid(Document):
	def __init__(self, *args, **kwargs):
		super(GroupSetPaid, self).__init__(*args, **kwargs)

	def on_submit(self):
		if self.party_list == None:
			frappe.throw(_('No Party List '))
		else:
			self.update_resutl_flage()

	def on_cancel(self):
		self.update_resutl_flage(cancel=1)


	@frappe.whitelist()
	def get_form_received_bydate(self):
		company = self.company
		from_date = self.from_date
		to_date = self.to_date
		party_list = self.party_list
		self.set("group_party_list_paid", [])

		if party_list and from_date<=to_date:	
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name,`tabCOVID Analysis Form`.date,
`tabCOVID Analysis Form`.custmer_name,
`tabCOVID Analysis Form`.paid_amount,
`tabCOVID Analysis Form`.analysis_amount,
`tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` 
where `tabCOVID Analysis Form`.company = '{0}' 
and `tabCOVID Analysis Form`.analysis_amount>`tabCOVID Analysis Form`.paid_amount 
and `tabCOVID Analysis Form`.payment_type= "Receivable" 
and DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') between DATE_FORMAT('{2}','%Y-%m-%d') and DATE_FORMAT('{3}','%Y-%m-%d')
and `tabCOVID Analysis Form`.party_list='{1}' 
order by `tabCOVID Analysis Form`.date ASC,paid_amount DESC """.format(company,party_list,from_date,to_date), as_dict=True)
		
			counter = 0
			z=self.paid_amount
			for d in gr_sample:
				counter = counter + 1
				group_sample = self.append("group_party_list_paid")
				group_sample.covid_form_serial = d.name
				group_sample.customer_name = d.custmer_name
				group_sample.party_list = d.party_list
				group_sample.previous = d.paid_amount
				group_sample.analysis_amount = d.analysis_amount
				group_sample.received_date = d.date
				
				x=group_sample.analysis_amount-group_sample.previous				
				if z>x:
					group_sample.paid_amount=x
				
				elif z<=x and z>0:
					group_sample.paid_amount=z
				else:
					group_sample.paid_amount=0.00
				z=z-x					

		
		elif party_list:
			frappe.msgprint(_("Enter Date Correct Please "))
			
		else:
			
			frappe.msgprint(_("Enter Party "))

	@frappe.whitelist()
	def get_form_received_byserial(self):
		company = self.company
		party_list = self.party_list
		from_serial = self.from_serial
		to_serial = self.to_serial
		self.set("group_party_list_paid", [])

		if party_list:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.paid_amount,`tabCOVID Analysis Form`.analysis_amount,`tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}'  
and `tabCOVID Analysis Form`.analysis_amount>`tabCOVID Analysis Form`.paid_amount 
and `tabCOVID Analysis Form`.payment_type= "Receivable"
and `tabCOVID Analysis Form`.party_list='{1}' 
and `tabCOVID Analysis Form`.daily_serial between '{2}' and '{3}' order by paid_amount ASC    """.format(company,party_list,from_serial,to_serial), as_dict=True)

			counter = 0
			z=self.paid_amount
			for d in gr_sample:
				counter = counter + 1
				group_sample = self.append("group_party_list_paid")
				group_sample.covid_form_serial = d.name
				group_sample.customer_name = d.custmer_name
				group_sample.party_list = d.party_list
				group_sample.previous = d.paid_amount
				group_sample.analysis_amount = d.analysis_amount
				group_sample.received_date = d.date
	
				x=group_sample.analysis_amount-group_sample.previous				
				if z>x:
					group_sample.paid_amount=x
				
				elif z<=x and z>0:
					group_sample.paid_amount=z
				else:
					group_sample.paid_amount=0.00
				z=z-x					
			


		else:
			frappe.msgprint(_("Enter Party"))
			



			
	def update_resutl_flage (self, cancel=0):
		for sample in self.get("group_party_list_paid"):
			if cancel:
				prv_amount = frappe.db.get_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "paid_amount")
				new_amount = prv_amount - sample.paid_amount
				frappe.db.set_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "paid_amount", new_amount)
				if sample.paid_amount > 0:
					frappe.db.set_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "receivable_payment_type", None)

			else:
				prv_amount = frappe.db.get_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "paid_amount")
				if prv_amount:
					new_amount = prv_amount + sample.paid_amount
				else:
					new_amount = sample.paid_amount
				frappe.db.set_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "paid_amount", new_amount)
				if sample.paid_amount > 0:
					frappe.db.set_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "receivable_payment_type", self.payment_method)

	

