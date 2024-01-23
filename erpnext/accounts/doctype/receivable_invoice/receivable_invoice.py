# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ReceivableInvoice(Document):
	def get_sales_invoices(self):
		conditions = get_conditions(self)
		
		invoices = get_invoices(conditions)
		return invoices

def get_conditions(invoice):
	conditions = ""
	conditions += f" AND inv.company ='{invoice.company}'"
	if invoice.from_date: conditions += f" AND inv.posting_date >='{invoice.from_date}'"
	if invoice.to_date: conditions += f" AND inv.posting_date <='{invoice.to_date}'"
	if invoice.insurance_party: conditions += f" AND (inv.insurance_party='{invoice.insurance_party}' or inv.insurance_party_child='{invoice.insurance_party}')"
	return conditions

def get_invoices_old(conditions):
	invoices = frappe.db.sql(f"""
		select name, posting_date, customer,
		insurance_party,total_discount_provider -  discount_amount as company_net
		from `tabSales Invoice`
		where docstatus = 1 {conditions} order by posting_date , name """
		 , as_dict=1)
	return invoices
def get_invoices(conditions):
	invoices = frappe.db.sql(f"""
		select inv.name, inv.posting_date, inv.customer,
		inv.insurance_party,
		SUM(invItem.discount_amount * invItem.qty) -  SUM(invItem.contract_discount) as company_net
		from  `tabSales Invoice Item` as invItem
		INNER JOIN `tabSales Invoice` as inv ON inv.name=invItem.parent
		where inv.docstatus = 1 {conditions}
		GROUP BY inv.name
		order by inv.posting_date , inv.name 
		"""
		 , as_dict=1)
	return invoices