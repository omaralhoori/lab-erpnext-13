# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, msgprint, scrub
from frappe.utils import cint, cstr, flt, fmt_money, formatdate, get_link_to_form, nowdate
from erpnext.accounts.general_ledger import make_gl_entries, process_gl_map
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import (
	check_if_stock_and_account_balance_synced,
	get_account_currency,
	get_balance_on,
	get_stock_accounts,
	get_stock_and_account_balance,
)
from erpnext.controllers.accounts_controller import AccountsController


class ChequeEntry(AccountsController):
	def __init__(self, *args, **kwargs):
		super(ChequeEntry, self).__init__(*args, **kwargs)

	def validate(self):
		self.validate_cheque_info()

	def on_submit(self):
		self.make_gl_entries()
		self.update_cheque_info()

	def on_cancel(self):
		self.ignore_linked_doctypes = ('GL Entry')
		self.make_gl_entries(cancel=1)
		self.update_cheque_info(cancel=1)


	def make_gl_entries(self, cancel=0, adv_adj=0,merge_entries=False):
		gl_entries = []
		if self.entry_type=='Send Cheques':
			self.add_gl_entries_send_cheques(gl_entries)
		if self.entry_type=="Paid Cheques":
			self.add_gl_entries_paid_cheques(gl_entries)
		if self.entry_type=='Returned Cheques':
			self.add_gl_entries_return_cheques(gl_entries)
		if self.entry_type=='Canceled Cheques':
			self.add_gl_entries_cancel_cheques(gl_entries)

		gl_entries = process_gl_map(gl_entries)
		make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj,merge_entries=merge_entries)

	def add_gl_entries_send_cheques(self, gl_entries):
		company_currency = frappe.db.get_value("Company", {"name":self.company}, "default_currency")

		for chq in self.get("cheque_transaction"):
			trxremarks = self.remarks + " - Cheque no " +  chq.cheque_no + "/"  + chq.cheque_bank + "/ Vocuher No." + chq.payment_entry_no
			gl_entries.append(
				self.get_gl_dict({
					"account": self.account_no,
					"account_currency": company_currency,
					"against": chq.account_paid_to,
					"debit_in_account_currency": flt(chq.cheque_paid_amount),
					"debit": flt(chq.cheque_paid_amount),
					"remarks": trxremarks
				}, item=chq)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": chq.account_paid_to,
					"account_currency": company_currency,
					"against": self.account_no,
					"credit_in_account_currency": flt(chq.cheque_paid_amount),
					"credit": flt(chq.cheque_paid_amount),
					"remarks": trxremarks
				}, item=chq)
			)

	def add_gl_entries_paid_cheques(self, gl_entries):
		company_currency = frappe.db.get_value("Company", {"name":self.company}, "default_currency")

		for chq in self.get("cheque_transaction"):
			trxremarks = self.remarks + " - Cheque no " +  chq.cheque_no + "/"  + chq.cheque_bank + "/ Vocuher No." + chq.payment_entry_no
			gl_entries.append(
				self.get_gl_dict({
					"account": self.account_no,
					"account_currency": company_currency,
					"against": self.collection_account,
					"debit_in_account_currency": flt(chq.cheque_paid_amount),
					"debit": flt(chq.cheque_paid_amount),
					"remarks": trxremarks
				}, item=chq)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.collection_account,
					"account_currency": company_currency,
					"against": self.account_no,
					"credit_in_account_currency": flt(chq.cheque_paid_amount),
					"credit": flt(chq.cheque_paid_amount),
					"remarks": trxremarks
				}, item=chq)
			)

	def add_gl_entries_return_cheques(self, gl_entries):
		company_currency = frappe.db.get_value("Company", {"name":self.company}, "default_currency")

		for chq in self.get("cheque_transaction"):
			trxremarks = self.remarks + " - Cheque no " +  chq.cheque_no + "/"  + chq.cheque_bank + "/ Vocuher No." + chq.payment_entry_no
			gl_entries.append(
				self.get_gl_dict({
					"account": self.account_no,
					"account_currency": company_currency,
					"against": chq.account_paid_to,
					"debit_in_account_currency": flt(chq.cheque_paid_amount),
					"debit": flt(chq.cheque_paid_amount),
					"remarks": trxremarks
				}, item=chq)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": chq.account_paid_to,
					"account_currency": company_currency,
					"against": self.account_no,
					"credit_in_account_currency": flt(chq.cheque_paid_amount),
					"credit": flt(chq.cheque_paid_amount),
					"remarks": trxremarks
				}, item=chq)
			)

	def add_gl_entries_cancel_cheques(self, gl_entries):
		company_currency = frappe.db.get_value("Company", {"name":self.company}, "default_currency")

		for chq in self.get("cheque_transaction"):
			trxremarks = self.remarks + " - Cheque no " +  chq.cheque_no + "/"  + chq.cheque_bank + "/ Vocuher No." + chq.payment_entry_no
			gl_entries.append(
				self.get_gl_dict({
					"account": chq.account_paid_from,
					"party_type": chq.party_type,
					"party": chq.party,
					"account_currency": company_currency,
					"against": chq.account_paid_to,
					"debit_in_account_currency": flt(chq.cheque_paid_amount),
					"debit": flt(chq.cheque_paid_amount),
					"remarks": trxremarks
				}, item=chq)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": chq.account_paid_to,
					"account_currency": company_currency,
					"against": chq.account_paid_from,
					"credit_in_account_currency": flt(chq.cheque_paid_amount),
					"credit": flt(chq.cheque_paid_amount),
					"remarks": trxremarks
				}, item=chq)
			)

	def validate_cheque_info (self):
		if self.entry_type in ('Paid Cheques','Returned Cheques'):
			for chq in self.get("cheque_transaction"):
				chq_bank = frappe.db.get_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "company_bank")
				if chq_bank != chq_bank:
					frappe.throw(_('Cheque {0} not related to select bank').format(chq.cheque_no))

	def update_cheque_info (self, cancel=0):
		if self.entry_type=='Send Cheques':
			for chq in self.get("cheque_transaction"):
				if cancel:
					chq_status = frappe.db.get_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status")
					#if chq_status not in ('Collection'):
					#	frappe.throw(_('Cheque {0} status changed , can not cancel').format(chq.cheque_no))
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status", chq.chq_old_status)
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "company_bank", '')
				else:
					chq_status = frappe.db.get_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status")
					if chq_status not in ('Standing','Returned'):
						frappe.throw(_('Cheque {0} status not Standing or Returned').format(chq.cheque_no))
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status", "Collection")
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "company_bank", self.bank)

		if self.entry_type=='Paid Cheques':
			for chq in self.get("cheque_transaction"):
				if cancel:
					chq_status = frappe.db.get_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status")
					#if chq_status not in ('Paid'):
					#	frappe.throw(_('Cheque {0} status changed , can not cancel').format(chq.cheque_no))
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status", chq.chq_old_status)
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "cheque_paid_amount", 0)
				else:
					chq_status = frappe.db.get_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status")
					if chq_status not in ('Collection'):
						frappe.throw(_('Cheque {0} status not Collection').format(chq.cheque_no))
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status", "Paid")
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "cheque_paid_amount", flt(chq.cheque_paid_amount))
					
		if self.entry_type=='Returned Cheques':
			for chq in self.get("cheque_transaction"):
				if cancel:
					chq_status = frappe.db.get_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status")
					#if chq_status not in ('Returned'):
					#	frappe.throw(_('Cheque {0} status changed , can not cancel').format(chq.cheque_no))
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status", chq.chq_old_status)
				else:
					chq_status = frappe.db.get_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status")
					if chq_status not in ('Collection','Paid'):
						frappe.throw(_('Cheque {0} status not Collection or not paid').format(chq.cheque_no))
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status", "Returned")
					
		if self.entry_type=='Canceled Cheques':
			for chq in self.get("cheque_transaction"):
				if cancel:
					chq_status = frappe.db.get_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status")
					#if chq_status not in ('Canceled'):
					#	frappe.throw(_('Cheque {0} status changed , can not cancel').format(chq.cheque_no))
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status", chq.chq_old_status)
				else:
					chq_status = frappe.db.get_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status")
					if chq_status not in ('Standing','Returned'):
						frappe.throw(_('Cheque {0} status not Standing or Returned').format(chq.cheque_no))
					frappe.db.set_value("Cheque Info", {"name":chq.chq_info_name,"cheque_no":chq.cheque_no}, "chq_status", "Canceled")
					

@frappe.whitelist()
def get_chq_info(bank,chq_info_name):

	cheque_no = frappe.db.get_value("Cheque Info",{"name": chq_info_name}, "cheque_no")
	cheque_date = frappe.db.get_value("Cheque Info",{"name": chq_info_name}, "cheque_date")
	cheque_amount = frappe.db.get_value("Cheque Info",{"name": chq_info_name}, "cheque_amount")
	cheque_bank = frappe.db.get_value("Cheque Info",{"name": chq_info_name}, "cheque_bank")
	notes = frappe.db.get_value("Cheque Info",{"name": chq_info_name}, "notes")
	chq_status = frappe.db.get_value("Cheque Info",{"name": chq_info_name}, "chq_status")
	cheque_paid_amount = frappe.db.get_value("Cheque Info",{"name": chq_info_name}, "cheque_paid_amount")
	payment_entry_no = frappe.db.get_value("Cheque Info",{"name": chq_info_name}, "parent")
	party_type = frappe.db.get_value("Payment Entry",{"name": payment_entry_no}, "party_type")
	party = frappe.db.get_value("Payment Entry",{"name": payment_entry_no}, "party")
	account_paid_from = frappe.db.get_value("Payment Entry",{"name": payment_entry_no}, "paid_from")
	account_paid_to = frappe.db.get_value("Payment Entry",{"name": payment_entry_no}, "paid_to")
	if chq_status == 'Paid':
		account_paid_to = frappe.db.get_value("Bank Account",{"bank": bank,"account_type":'Current Account'}, "account")
	if chq_status == 'Collection':
		account_paid_to = frappe.db.get_value("Bank Account",{"bank": bank,"account_type":'Cheque Collection Account'}, "account")
	if chq_status == 'Returned':
		account_paid_to = frappe.db.get_value("Bank Account",{"bank": bank,"account_type":'Cheque Return Account'}, "account")

	return {
		"cheque_no": cheque_no,
		"cheque_date": cheque_date,
		"cheque_amount": cheque_amount,
		"cheque_bank": cheque_bank,
		"notes": notes,
		"chq_status": chq_status,
		"cheque_paid_amount": cheque_paid_amount,
		"payment_entry_no": payment_entry_no,
		"party_type": party_type,
		"party": party,
		"account_paid_from": account_paid_from,
		"account_paid_to": account_paid_to
	}

@frappe.whitelist()
def get_chq_list(doctype, txt, searchfield, start, page_len, filters):
	link_company = filters.pop('link_company')
	link_entry_type = filters.pop('link_entry_type')
	link_bank = filters.pop('link_bank')

	fields = ["ci.name","ci.cheque_no","ci.cheque_date","ci.cheque_bank","ci.cheque_amount","pe.party_name"]
	fields = ", ".join(fields)

	if link_entry_type=='Send Cheques':
		chqstatus = "ci.chq_status in ('Standing','Returned') and %(link_bank)s = %(link_bank)s"

	if link_entry_type=='Paid Cheques':
		chqstatus = "ci.chq_status in ('Collection') and ci.company_bank =  %(link_bank)s"

	if link_entry_type=='Returned Cheques':
		chqstatus = "ci.chq_status in ('Collection','Paid') and ci.company_bank =  %(link_bank)s"

	if link_entry_type=='Canceled Cheques':
		chqstatus = "ci.chq_status in ('Standing','Returned')"

	return frappe.db.sql("""select
			{field} 
		from
			`tabCheque Info` ci , `tabPayment Entry` pe 
		where
			pe.company = %(link_company)s and
			pe.docstatus = 1 and 
			pe.name = ci.parent and 
			{chqstatus} 
			and
			(
			ci.cheque_no like %(txt)s  or
			ci.cheque_amount like %(txt)s  or
			ci.cheque_bank like %(txt)s  or
			pe.party_name like %(txt)s  
			) 
		order by ci.cheque_date 
		limit %(start)s, %(page_len)s """.format(**{
			'field': fields,
			'chqstatus': chqstatus,
			'key': frappe.db.escape(searchfield)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': 50,
			'link_company': link_company,
			'link_bank': link_bank
		})
