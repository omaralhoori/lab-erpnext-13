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

class TransferToBank(Document):
	def __init__(self, *args, **kwargs):
		super(TransferToBank, self).__init__(*args, **kwargs)

	def on_submit(self):
		if self.transfer_amount != self.total_transfer:
			frappe.throw(_('Total transfer amount must be equal to bank transfer amount '))
		else:
			self.update_covid_form()

	def on_cancel(self):
		self.update_covid_form(cancel=1)

	def update_covid_form (self, cancel=0):
		for sample in self.get("covid_forms_bank_transfer"):
			if cancel:
				if sample.transfer_amount > 0:
					prv_bank_transfer = frappe.db.get_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "bank_transfer")
					if prv_bank_transfer:
						new_bank_transfer = prv_bank_transfer - sample.transfer_amount
					else:
						new_bank_transfer = sample.transfer_amount
					frappe.db.set_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "bank_transfer", new_bank_transfer)
			else:
				if sample.transfer_amount > 0:
					prv_bank_transfer = frappe.db.get_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "bank_transfer")
					if prv_bank_transfer:
						new_bank_transfer = prv_bank_transfer + sample.transfer_amount
					else:
						new_bank_transfer = sample.transfer_amount
					frappe.db.set_value("COVID Analysis Form", {"company": self.company,"name": sample.covid_form_serial}, "bank_transfer", new_bank_transfer)

	@frappe.whitelist()
	def get_form_received_bydate(self):
		company = self.company
		customer_payment_type = self.customer_payment_type
		if customer_payment_type =='Receivable':
			receivable_payment_type = self.receivable_payment_type
		else:
			receivable_payment_type = None
			
		from_date = self.from_date
		to_date = self.to_date

		self.set("covid_forms_bank_transfer", [])

		gr_sample=''

		if customer_payment_type =='Receivable':
			gr_sample = frappe.db.sql("""select caf.name,caf.date,
										caf.custmer_name,
										if(caf.payment_type='Receivable',caf.paid_amount - caf.bank_transfer ,caf.analysis_amount - caf.bank_transfer) paid_amount,
										caf.analysis_amount,caf.receivable_payment_type,
										caf.bank_transfer,
										caf.party_list,  
										caf.payment_type  
										from `tabCOVID Analysis Form` caf
										where caf.company = '{0}' 
										and caf.paid_amount - caf.bank_transfer >caf.bank_transfer 
										and caf.payment_type='Receivable'
										and caf.receivable_payment_type='{4}' 
										and DATE_FORMAT(caf.date,'%Y-%m-%d') between DATE_FORMAT('{2}','%Y-%m-%d') and DATE_FORMAT('{3}','%Y-%m-%d')
										order by caf.date ASC,paid_amount DESC """.format(company,customer_payment_type,from_date,to_date,receivable_payment_type), as_dict=True)
		else:
			gr_sample = frappe.db.sql("""select caf.name,caf.date,
										caf.custmer_name,
										if(caf.payment_type='Receivable',caf.paid_amount - caf.bank_transfer,caf.analysis_amount - caf.bank_transfer) paid_amount,
										caf.analysis_amount,caf.receivable_payment_type,
										caf.bank_transfer,
										caf.party_list,  
										caf.payment_type  
										from `tabCOVID Analysis Form` caf
										where caf.company = '{0}' 
										and caf.analysis_amount - caf.bank_transfer >caf.bank_transfer 
										and caf.payment_type<>'Receivable'
										and caf.payment_type= '{1}' 
										and DATE_FORMAT(caf.date,'%Y-%m-%d') between DATE_FORMAT('{2}','%Y-%m-%d') and DATE_FORMAT('{3}','%Y-%m-%d')
										order by caf.date ASC,paid_amount DESC """.format(company,customer_payment_type,from_date,to_date), as_dict=True)
		
		counter = 0
		#z=self.transfer_amount - self.total_transfer
		z=self.transfer_amount 

		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("covid_forms_bank_transfer")
			group_sample.covid_form_serial = d.name
			group_sample.customer_name = d.custmer_name
			group_sample.party_list = d.party_list
			group_sample.paid_amount = d.paid_amount
			group_sample.analysis_amount = d.analysis_amount
			group_sample.transfer_amount = d.transfer_amount
			group_sample.received_date = d.date
			group_sample.customer_payment_type = d.payment_type
			group_sample.receivable_payment_type = d.receivable_payment_type
			
			self.total_paid=self.total_paid + flt(group_sample.paid_amount)

			x=flt(group_sample.paid_amount)-flt(group_sample.transfer_amount)
			if z>x:
				group_sample.transfer_amount=x
			
			elif z<=x and z>0:
				group_sample.transfer_amount=z
			else:
				group_sample.transfer_amount=0.00
			z=z-x					

			self.total_transfer=self.total_transfer + flt(group_sample.transfer_amount)
	
	@frappe.whitelist()
	def get_form_received_byserial(self):
		company = self.company
		customer_payment_type = self.customer_payment_type
		if customer_payment_type =='Receivable':
			receivable_payment_type = self.receivable_payment_type
		else:
			receivable_payment_type = None
			
		from_serial = self.from_serial
		to_serial = self.to_serial

		self.set("covid_forms_bank_transfer", [])

		gr_sample=''

		if customer_payment_type =='Receivable':
			gr_sample = frappe.db.sql("""select caf.name,caf.date,
										caf.custmer_name,
										if(caf.payment_type='Receivable',caf.paid_amount - caf.bank_transfer ,caf.analysis_amount - caf.bank_transfer) paid_amount,
										caf.analysis_amount,caf.receivable_payment_type,
										caf.bank_transfer,
										caf.party_list,  
										caf.payment_type  
										from `tabCOVID Analysis Form` caf
										where caf.company = '{0}' 
										and caf.paid_amount - caf.bank_transfer >caf.bank_transfer 
										and caf.payment_type='Receivable'
										and caf.receivable_payment_type='{4}' 
										and `tabCOVID Analysis Form`.daily_serial between '{2}' and '{3}'
										order by caf.date ASC,paid_amount DESC """.format(company,customer_payment_type,from_serial,to_serial,receivable_payment_type), as_dict=True)
		else:
			gr_sample = frappe.db.sql("""select caf.name,caf.date,
										caf.custmer_name,
										if(caf.payment_type='Receivable',caf.paid_amount - caf.bank_transfer,caf.analysis_amount - caf.bank_transfer) paid_amount,
										caf.analysis_amount,caf.receivable_payment_type,
										caf.bank_transfer,
										caf.party_list,  
										caf.payment_type  
										from `tabCOVID Analysis Form` caf
										where caf.company = '{0}' 
										and caf.analysis_amount - caf.bank_transfer >caf.bank_transfer 
										and caf.payment_type<>'Receivable'
										and caf.payment_type= '{1}' 
										and `tabCOVID Analysis Form`.daily_serial between '{2}' and '{3}'
										order by caf.date ASC,paid_amount DESC """.format(company,customer_payment_type,from_serial,to_serial,receivable_payment_type), as_dict=True)

		
		counter = 0
		#z=self.transfer_amount - self.total_transfer
		z=self.transfer_amount 

		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("covid_forms_bank_transfer")
			group_sample.covid_form_serial = d.name
			group_sample.customer_name = d.custmer_name
			group_sample.party_list = d.party_list
			group_sample.paid_amount = d.paid_amount
			group_sample.analysis_amount = d.analysis_amount
			group_sample.transfer_amount = d.transfer_amount
			group_sample.received_date = d.date
			group_sample.customer_payment_type = d.payment_type
			group_sample.receivable_payment_type = d.receivable_payment_type
			
			self.total_paid=self.total_paid + flt(group_sample.paid_amount)

			x=flt(group_sample.paid_amount)-flt(group_sample.transfer_amount)
			if z>x:
				group_sample.transfer_amount=x
			
			elif z<=x and z>0:
				group_sample.transfer_amount=z
			else:
				group_sample.transfer_amount=0.00
			z=z-x					

			self.total_transfer=self.total_transfer + flt(group_sample.transfer_amount)
