# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, cstr, flt

def get_columns_income():
	return [
		{
			"label": _("Payment Type"),
			"fieldtype": "Data",
			"fieldname": "payment_type",
			"width": 150
		},
		{
			"label": _("Before Select Date"),
			"fieldtype": "Float",
			"fieldname": "befdate_amt",
			"width": 250
		},
		{
			"label": _("Count"),
			"fieldtype": "Int",
			"fieldname": "befdate_cnt",
			"width": 150
		},
		{
			"label": _("At Selected Date"),
			"fieldtype": "Float",
			"fieldname": "atdate_amt",
			"width": 250
		},
		{
			"label": _("Count"),
			"fieldtype": "Int",
			"fieldname": "atdate_cnt",
			"width": 150
		},
		{
			"label": _("Paid"),
			"fieldtype": "Float",
			"fieldname": "paid",
			"width": 150
		},
		{
			"label": _("Net Balance"),
			"fieldtype": "Float",
			"fieldname": "net_balance",
			"width": 150
		},
	]

def get_columns_total():
	return [
		{
			"label": _("Party"),
			"fieldtype": "Link",
			"fieldname": "party",
			"options": "Third Party",
			"width": 250
		},
		{
			"label": _("Debit"),
			"fieldtype": "Float",
			"fieldname": "debit",
			"width": 150
		},
		{
			"label": _("Credit"),
			"fieldtype": "Float",
			"fieldname": "credit",
			"width": 150
		},
		{
			"label": _("Balance"),
			"fieldtype": "Float",
			"fieldname": "balance",
			"width": 150
		},
		{
			"label": _("Customer Count"),
			"fieldtype": "Int",
			"fieldname": "customer_count",
			"width": 150
		},
		{
			"label": _("Customer Paid"),
			"fieldtype": "Int",
			"fieldname": "customer_paid",
			"width": 150
		},
	]

def get_columns():
	return [
		{
			"label": _("Voucher No"),
			"fieldtype": "Data",
			"fieldname": "voucher_number",
			"width": 150
		},
		{
			"label": _("Transaction Date"),
			"fieldtype": "Data",
			"fieldname": "voucher_date",
			"width": 150
		},
		{
			"label": _("Debit"),
			"fieldtype": "Float",
			"fieldname": "debit",
			"width": 100
		},
		{
			"label": _("Credit"),
			"fieldtype": "Float",
			"fieldname": "credit",
			"width": 100
		},
		{
			"label": _("Balance"),
			"fieldtype": "Float",
			"fieldname": "balance",
			"width": 100
		},
	]

def get_data(filters):
	data = []
	if(filters.from_date > filters.to_date):
		frappe.msgprint(_(" From Date can not be greater than To Date"))
		return data

	if filters.party:
		party_trx = get_party_transaction(filters)
		
		pervious_balance = 0.0
		balance = 0.0
		pervious_flg = 1

		for row in party_trx:
			from_date, to_date = filters.from_date, filters.to_date

			#if row.to_time < from_time or row.from_time > to_time:
			#	continue

			if getdate(row.get("voucher_date")) < getdate(from_date) and pervious_flg == 1:
				pervious_balance += (row.debit - row.credit)
				balance += (row.debit - row.credit)
				continue
			else:
				if pervious_flg == 1:
					pervious_flg = 2

			if pervious_flg == 2:
				pervious_flg = 3
				debit = ''
				credit = ''
				if pervious_balance < 0:
					credit = pervious_balance
				if pervious_balance > 0:
					debit = pervious_balance
				
				data.append({
					"voucher_number": 'Pervious Balance', 
					"Date": '', 
					"debit": debit,
					"credit": credit,
					"balance": balance
				})
			if pervious_flg == 3:
				if getdate(row.get("voucher_date")) > getdate(to_date):
					break
				else:
					balance += row.debit - row.credit
					if row.debit:
						debit = row.debit
					else:
						debit = ''
					if row.credit:
						credit = row.credit
					else:
						credit = ''
					data.append({
						"voucher_number": row.voucher_no, 
						"voucher_date": row.voucher_date, 
						"debit": debit,
						"credit": credit,
						"balance": balance
					})

	return data

def get_data_total(filters):
	data = []

	party_balance = get_party_balance_total(filters)
	data = party_balance

	return data

def get_data_income(filters):
	data = []

	if ( filters.to_date):
		income_total = get_income_total(filters)
		net_balance=0.0
		for row in income_total:
			
			if row.payment_type != 'Receivable':
				net_balance_show = ''
			else:
				net_balance += row.befdate_amt + row.atdate_amt - row.paid 
				net_balance_show = net_balance
			data.append({
				"payment_type": row.payment_type, 
				"befdate_amt": row.befdate_amt, 
				"befdate_cnt": row.befdate_cnt, 
				"atdate_amt": row.atdate_amt, 
				"atdate_cnt": row.atdate_cnt, 
				"paid": row.paid,
				"net_balance":net_balance_show
			})

	return data


def get_conditions_total(filters):
	conditions_total = ""
	
	conditions_total = " caf.payment_type = 'Receivable' "

	if filters.all_party != 1: 
		if filters.get("party_list"):
			conditions_total += " and caf.party_list in %(party_list)s "
		else:
			conditions_total += " and caf.party_list = '999' "
	

	return conditions_total

def get_party_balance_total(filters):
	conditions_total = get_conditions_total(filters)

	party_total =  frappe.db.sql("""SELECT
			caf.party_list , 
			sum(nvl(caf.analysis_amount,0)) debit , sum(nvl(caf.paid_amount,0)) credit , 
			sum(nvl(caf.analysis_amount,0)- nvl(caf.paid_amount,0)) balance , 
			count(caf.name) customer_count , if(nvl(caf.paid_amount,0)>0 ,count(caf.name),0) customer_paid
		FROM 
			`tabCOVID Analysis Form` caf
		WHERE 
			{0}
		group by caf.party_list
		order by caf.party_list""".format(conditions_total), filters, as_list=1)


	return party_total


def get_party_transaction(filters):
	conditions_trn = ""
	conditions_cof = ""

	if filters.get("party"): 
		conditions_trn += " and gsp.party_list = %(party)s "
		conditions_cof += " and caf.party_list = %(party)s "

	party_trx =  frappe.db.sql("""
		select  voucher_no, voucher_date  , debit , credit from (
			select  
  				gsp.name voucher_no , gsp.transaction_date voucher_date , 0 debit , sum(nvl(gplp.paid_amount  ,0)) credit 
			from `tabGroup Set Paid` gsp ,  `tabgroup party list paid` gplp  
			where gsp.name = gplp.parent
			and   gsp.docstatus = 1
				{0}
			group by gsp.name ,gsp.transaction_date
			union
			select
				'Customer Collection' voucher_no, caf.date voucher_date , sum(nvl(caf.analysis_amount,0)) debit , 0 credit 
			from `tabCOVID Analysis Form` caf
      		where caf.payment_type = 'Receivable'
      			{1}
			group by caf.date
		) party_trn
		order by voucher_date""".format(conditions_trn,conditions_cof), filters, as_dict=1)


	#party_trx_map = frappe._dict()
	#for d in party_trx:
	#	party_trx_map.setdefault(d.name, d)

	return party_trx



def get_income_total(filters):

	income_total =  frappe.db.sql("""
		select
			payment_type , sum(nvl(befdate_amt,0)) befdate_amt ,sum(nvl(befdate_cnt,0)) befdate_cnt ,
			sum(nvl(atdate_amt,0)) atdate_amt ,sum(nvl(atdate_cnt,0)) atdate_cnt , 
			sum(nvl(paid,0)) paid
		from (
			SELECT
				caf.payment_type, sum(nvl(caf.analysis_amount,0)) befdate_amt , count(*) befdate_cnt , 
				0 atdate_amt , 0 atdate_cnt , 
				0 paid
			FROM 
				`tabCOVID Analysis Form` caf
      		where 
			  	caf.date < %(to_date)s
			group by caf.payment_type
			union
			SELECT
				caf.payment_type, 0 befdate_amt , 0 befdate_cnt , 
				sum(nvl(caf.analysis_amount,0)) atdate_amt , count(*) atdate_cnt , 
				0 paid
			FROM 
				`tabCOVID Analysis Form` caf
			where 
				caf.date = %(to_date)s
			group by caf.payment_type
			union
			select  
				caf.payment_type, 0 befdate_amt , 0 befdate_cnt , 
				0 atdate_amt , 0 atdate_cnt , 
				sum(nvl(gplp.paid_amount,0)) paid
			from 
				`tabGroup Set Paid` gsp ,  `tabgroup party list paid` gplp   ,`tabCOVID Analysis Form` caf
			where 
				caf.date <= %(to_date)s
				and   gsp.docstatus = 1
				and	  gsp.name = gplp.parent
				and   gplp.covid_form_serial = caf.name
			group by caf.payment_type
		) vcov
		group by payment_type
		order by payment_type""", filters, as_dict=1)


	return income_total

	#and caf.daily_serial between %(from_serial)s and %(to_serial)s
