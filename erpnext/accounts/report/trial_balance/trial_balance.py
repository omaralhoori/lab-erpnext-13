# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, msgprint
from frappe.utils import cstr, flt, formatdate, getdate

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.report.financial_statements import (
	filter_accounts,
	filter_out_zero_value_rows,
	set_gl_entries_by_account,
	sort_accounts,
)

value_fields = ("opening_debit", "opening_credit", "debit", "credit", "closing_debit", "closing_credit")

def execute(filters=None):
	validate_filters(filters)
	data = get_data(filters)
	columns = get_columns()
	return columns, data

def validate_filters(filters):
	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))

	fiscal_year = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True)
	if not fiscal_year:
		frappe.throw(_("Fiscal Year {0} does not exist").format(filters.fiscal_year))
	else:
		filters.year_start_date = getdate(fiscal_year.year_start_date)
		filters.year_end_date = getdate(fiscal_year.year_end_date)

	if not filters.from_date:
		filters.from_date = filters.year_start_date

	if not filters.to_date:
		filters.to_date = filters.year_end_date

	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	if (filters.from_date < filters.year_start_date) or (filters.from_date > filters.year_end_date):
		frappe.msgprint(_("From Date should be within the Fiscal Year. Assuming From Date = {0}")\
			.format(formatdate(filters.year_start_date)))

		filters.from_date = filters.year_start_date

	if (filters.to_date < filters.year_start_date) or (filters.to_date > filters.year_end_date):
		frappe.msgprint(_("To Date should be within the Fiscal Year. Assuming To Date = {0}")\
			.format(formatdate(filters.year_end_date)))
		filters.to_date = filters.year_end_date


def get_data(filters):
	#ibrahim
	if not flt(filters.all_company):
		filters.all_company = 0

	#frappe.msgprint(cstr(filters.all_company))
	#frappe.msgprint(cstr(not not flt(filters.all_company)))

	
	if filters.all_company == 0:
		accounts = frappe.db.sql("""select name, account_number, parent_account, account_name, root_type, report_type,level, lft, rgt
			from `tabAccount` where company=%s order by lft""", filters.company, as_dict=True)
	else:
		accounts = frappe.db.sql("""
				select a.name, a.account_number, 
				(select b.name from `tabAccount` b where b.name = a.parent_account ) as parent_account, 
				a.account_name, a.root_type, a.report_type,a.level, a.lft, a.rgt
				from `tabAccount` a order by lft""",  as_dict=True)
		

	company_currency = filters.presentation_currency or erpnext.get_company_currency(filters.company)

	if not accounts:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)
	#for d in accounts:
	#	frappe.msgprint(d.account_number)

	if filters.all_company == 0:
		min_lft, max_rgt = frappe.db.sql("""select min(lft), max(rgt) from `tabAccount`
			where company=%s""", (filters.company,))[0]
	else:
		min_lft, max_rgt = frappe.db.sql("""select min(lft), max(rgt) from `tabAccount`
			""", )[0]

	gl_entries_by_account = {}

	opening_balances = get_opening_balances(filters)


	#add filter inside list so that the query in financial_statements.py doesn't break
	if filters.project:
		filters.project = [filters.project]

	set_gl_entries_by_account(filters.company, filters.from_date,
		filters.to_date, min_lft, max_rgt, filters, gl_entries_by_account, ignore_closing_entries=not flt(filters.with_period_closing_entry),all_company=not not flt(filters.all_company))

	#####################################################################
	if filters.all_company == 1:
		accounts1 = frappe.db.sql("""
				select distinct a.account_number,CONCAT(a.account_number , ' - ' , a.account_name) as full_account_name,
				(select CONCAT(b.account_number , ' - ' , b.account_name)  from `tabAccount` b where b.name = a.parent_account ) as parent_account, 
				a.account_name, a.root_type, a.report_type,a.level
				from `tabAccount` a 
				where (a.account_number is not null )
				order by a.lft
				""",  as_dict=True)

		parent_children_map1 = {}
		accounts_by_name1 = {}
		for d in accounts1:
			accounts_by_name1[d.full_account_name] = d
			parent_children_map1.setdefault(d.parent_account or None, []).append(d)

		filtered_accounts1 = []

		def add_to_list(parent, level):
			if level < 20:
				children = parent_children_map1.get(parent) or []
				sort_accounts(children, is_root=True if parent==None else False,key="full_account_name")

				for child in children:
					child.indent = level
					filtered_accounts1.append(child)
					add_to_list(child.full_account_name, level + 1)

		add_to_list(None, 0)

		accounts = filtered_accounts1
		parent_children_map = parent_children_map1
		accounts_by_name = accounts_by_name1

		###for d in accounts:
		###	frappe.msgprint(d.full_account_name )

	#####################################################################


	total_row = calculate_values(accounts, gl_entries_by_account, opening_balances, filters, company_currency)
	accumulate_values_into_parents(accounts, accounts_by_name)

	data = prepare_data(accounts, filters, total_row, parent_children_map, company_currency)
	data = filter_out_zero_value_rows(data, parent_children_map, show_zero_values=filters.get("show_zero_values"))

	return data

def get_opening_balances(filters):
	balance_sheet_opening = get_rootwise_opening_balances(filters, "Balance Sheet")
	pl_opening = get_rootwise_opening_balances(filters, "Profit and Loss")

	balance_sheet_opening.update(pl_opening)
	return balance_sheet_opening


def get_rootwise_opening_balances(filters, report_type):
	additional_conditions = ""
	if not filters.show_unclosed_fy_pl_balances:
		additional_conditions = " and posting_date >= %(year_start_date)s" \
			if report_type == "Profit and Loss" else ""

	if not flt(filters.with_period_closing_entry):
		additional_conditions += " and ifnull(voucher_type, '')!='Period Closing Voucher'"

	if filters.cost_center:
		lft, rgt = frappe.db.get_value('Cost Center', filters.cost_center, ['lft', 'rgt'])
		additional_conditions += """ and cost_center in (select name from `tabCost Center`
			where lft >= %s and rgt <= %s)""" % (lft, rgt)

	if filters.project:
		additional_conditions += " and project = %(project)s"

	if filters.finance_book:
		fb_conditions = " AND finance_book = %(finance_book)s"
		if filters.include_default_book_entries:
			fb_conditions = " AND (finance_book in (%(finance_book)s, %(company_fb)s, '') OR finance_book IS NULL)"

		additional_conditions += fb_conditions

	accounting_dimensions = get_accounting_dimensions(as_list=False)

	query_filters = {
		"all_company": filters.all_company,
		"company": filters.company,
		"from_date": filters.from_date,
		"report_type": report_type,
		"year_start_date": filters.year_start_date,
		"project": filters.project,
		"finance_book": filters.finance_book,
		"company_fb": frappe.db.get_value("Company", filters.company, 'default_finance_book')
	}

	if accounting_dimensions:
		for dimension in accounting_dimensions:
			if filters.get(dimension.fieldname):
				if frappe.get_cached_value('DocType', dimension.document_type, 'is_tree'):
					filters[dimension.fieldname] = get_dimension_with_children(dimension.document_type,
						filters.get(dimension.fieldname))
					additional_conditions += "and {0} in %({0})s".format(dimension.fieldname)
				else:
					additional_conditions += "and {0} in (%({0})s)".format(dimension.fieldname)

				query_filters.update({
					dimension.fieldname: filters.get(dimension.fieldname)
				})

	gle = frappe.db.sql("""
		select
			account, sum(debit) as opening_debit, sum(credit) as opening_credit
		from `tabGL Entry`
		where
			(company=%(company)s or %(all_company)s = 1)
			{additional_conditions}
			and (posting_date < %(from_date)s or ifnull(is_opening, 'No') = 'Yes')
			and account in (select name from `tabAccount` where report_type=%(report_type)s)
			and is_cancelled = 0
		group by account""".format(additional_conditions=additional_conditions), query_filters , as_dict=True)

	opening = frappe._dict()
	for d in gle:
		opening.setdefault(d.account, d)

	return opening

def calculate_values(accounts, gl_entries_by_account, opening_balances, filters, company_currency):
	init = {
		"opening_debit": 0.0,
		"opening_credit": 0.0,
		"debit": 0.0,
		"credit": 0.0,
		"closing_debit": 0.0,
		"closing_credit": 0.0
	}

	total_row = {
		"account": "'" + _("Total") + "'",
		"account_name": "'" + _("Total") + "'",
		"warn_if_negative": True,
		"opening_debit": 0.0,
		"opening_credit": 0.0,
		"debit": 0.0,
		"credit": 0.0,
		"closing_debit": 0.0,
		"closing_credit": 0.0,
		"parent_account": None,
		"indent": 0,
		"has_value": True,
		"currency": company_currency
	}

	if filters.all_company == 1:
		for d in accounts:
			d.update(init.copy())

			trx = frappe.db.sql("""
				select name from tabAccount ta  where ta.account_name = %s
				""",d.account_name , as_dict=True)
			
			if trx:
				for dd in trx:
					d["opening_debit"] += flt(opening_balances.get(dd.name, {}).get("opening_debit", 0))
					d["opening_credit"] += flt(opening_balances.get(dd.name, {}).get("opening_credit", 0))

					for entry in gl_entries_by_account.get(dd.name, []):
						if cstr(entry.is_opening) != "Yes":
							d["debit"] += flt(entry.debit)
							d["credit"] += flt(entry.credit)

					d["closing_debit"] = d["opening_debit"] + d["debit"]
					d["closing_credit"] = d["opening_credit"] + d["credit"]

			prepare_opening_closing(d)

			for field in value_fields:
				total_row[field] += d[field]
	else:
		for d in accounts:
			d.update(init.copy())

			# add opening
			d["opening_debit"] = opening_balances.get(d.name, {}).get("opening_debit", 0)
			d["opening_credit"] = opening_balances.get(d.name, {}).get("opening_credit", 0)

			for entry in gl_entries_by_account.get(d.name, []):
				if cstr(entry.is_opening) != "Yes":
					d["debit"] += flt(entry.debit)
					d["credit"] += flt(entry.credit)

			d["closing_debit"] = d["opening_debit"] + d["debit"]
			d["closing_credit"] = d["opening_credit"] + d["credit"]

			prepare_opening_closing(d)

			for field in value_fields:
				total_row[field] += d[field]

	return total_row

def accumulate_values_into_parents(accounts, accounts_by_name):
	for d in reversed(accounts):
		if d.parent_account:
			for key in value_fields:
				accounts_by_name[d.parent_account][key] += d[key]

def prepare_data(accounts, filters, total_row, parent_children_map, company_currency):
	data = []

	for d in accounts:
		# Prepare opening closing for group account
		if parent_children_map.get(d.account):
			prepare_opening_closing(d)

		has_value = False
		has_value = get_account_level(d.account_number,filters)

		#ibrahim
		if has_value:
			row = {
				"account": d.name,
				"account_number": d.account_number,
				"account_level": d.level,
				"account_fname": d.account_name,
				"parent_account": d.parent_account,
				"indent": d.indent,
				"from_date": filters.from_date,
				"to_date": filters.to_date,
				"currency": company_currency,
				"account_name": ('{} - {}'.format(d.account_number, d.account_name)
					if d.account_number else d.account_name)
			}

		#ibrahim
		#row = {
		#	"account": d.name,
		#	"parent_account": d.parent_account,
		#	"indent": d.indent,
		#	"from_date": filters.from_date,
		#	"to_date": filters.to_date,
		#	"currency": company_currency,
		#	"account_name": ('{} - {}'.format(d.account_number, d.account_name)
		#		if d.account_number else d.account_name)
		#}
		
		#ibrahim
		if has_value:
			foundTrue = False
			for key in value_fields:
				#row[key] = fmt_money(flt(d.get(key, 0.0), 0),precision=0,currency=None)
				row[key] = flt(d.get(key, 0.0), 3)
				if abs(flt(row[key])) >= 0.005:
					# ignore zero values
					has_value = True
					foundTrue = True
				else:
					if foundTrue == False:
						has_value = False

			#msgprint(_(d.account_number) + " dd " + cstr(has_value))
			row["has_value"] = has_value
			data.append(row)

	data.extend([{},total_row])


	#	for key in value_fields:
	#		row[key] = flt(d.get(key, 0.0), 3)

	#		if abs(row[key]) >= 0.005:
	#			# ignore zero values
	#			has_value = True

	#	row["has_value"] = has_value
	#	data.append(row)

	#data.extend([{},total_row])

	return data

#ibrahim
def get_account_level(account_number, filters):
	level_flg = 1
	level_string = "9"
	level_conditions = ""

	if flt(filters.lvl_1):
		level_flg = 1
		if level_string:
			level_string += ","
		level_string += "1"

	if flt(filters.lvl_2):
		level_flg = 1
		if level_string:
			level_string += ","
		level_string += "2"		

	if flt(filters.lvl_3):
		level_flg = 1
		if level_string:
			level_string += ","
		level_string += "3"		

	if flt(filters.lvl_4):
		level_flg = 1
		if level_string:
			level_string += ","
		level_string += "4"		

	if flt(filters.lvl_5):
		level_flg = 1
		if level_string:
			level_string += ","
		level_string += "5"
	
	level_conditions += " and level in ({0}) ".format(level_string)

	query_filters = {
		"company": filters.company,
		"account_number":account_number
	}

	data_lvl = frappe.db.sql(""" SELECT count(account_number) wcount
		FROM `tabAccount`
		where company=%(company)s
		and account_number=%(account_number)s
		{level_conditions}
		""".format(level_conditions=level_conditions), query_filters, as_dict=1)

	rec_found = False
	for d in data_lvl:
		if d.wcount==0:
			rec_found = False
		else:
			rec_found = True

	return rec_found
	#return frappe._dict(data_lvl)

def get_columns():
	return [
		{
			"fieldname": "account_level",
			"label": _("Account Level"),
			"fieldtype": "Data",
			"width": 1,
			"hidden": 1
		},
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1
		},
		{
			"fieldname": "opening_debit",
			"label": _("Opening (Dr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "opening_credit",
			"label": _("Opening (Cr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "closing_debit",
			"label": _("Closing (Dr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "closing_credit",
			"label": _("Closing (Cr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		}
	]

def prepare_opening_closing(row):
	dr_or_cr = "debit" if row["root_type"] in ["Asset", "Equity", "Expense"] else "credit"
	reverse_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"

	for col_type in ["opening", "closing"]:
		valid_col = col_type + "_" + dr_or_cr
		reverse_col = col_type + "_" + reverse_dr_or_cr
		row[valid_col] -= row[reverse_col]
		if row[valid_col] < 0:
			row[reverse_col] = abs(row[valid_col])
			row[valid_col] = 0.0
		else:
			row[reverse_col] = 0.0
