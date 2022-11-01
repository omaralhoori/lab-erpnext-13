# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import date
from erpnext import get_company_currency
from erpnext.accounts.party import get_party_account_currency
import frappe
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf
import threading
import os
import shutil
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa
from frappe import _

class BalanceConfirmationStatement(Document):
	pass

def get_customers_based_on_sales_person(sales_person):
	lft, rgt = frappe.db.get_value("Sales Person",
		sales_person, ["lft", "rgt"])
	records = frappe.db.sql("""
		select distinct parent, parenttype
		from `tabSales Team` steam
		where parenttype = 'Customer'
			and exists(select name from `tabSales Person` where lft >= %s and rgt <= %s and name = steam.sales_person)
	""", (lft, rgt), as_dict=1)
	sales_person_records = frappe._dict()
	for d in records:
		sales_person_records.setdefault(d.parenttype, set()).add(d.parent)
	if sales_person_records.get('Customer'):
		return frappe.get_list('Customer', fields=['name', 'email_id'], \
			filters=[['name', 'in', list(sales_person_records['Customer'])]])
	else:
		return []

@frappe.whitelist()
def fetch_customers(customer_collection, collection_name):
	customer_list = []
	customers = []

	if customer_collection == 'Sales Person':
		customers = get_customers_based_on_sales_person(collection_name)
		if not bool(customers):
			frappe.throw(_('No Customers found with selected options.'))
	else:
		if customer_collection == 'Sales Partner':
			customers = frappe.get_list('Customer', fields=['name', 'email_id'], \
				filters=[['default_sales_partner', '=', collection_name]])
		else:
			customers = get_customers_based_on_territory_or_customer_group(customer_collection, collection_name)

	for customer in customers:
		primary_email = customer.get('email_id') or ''


		customer_list.append({
			'name': customer.name,
			'primary_email': primary_email,
		})
	return customer_list


def get_customers_based_on_territory_or_customer_group(customer_collection, collection_name):
	fields_dict = {
		'Customer Group': 'customer_group',
		'Supplier Group': 'supplier_group',
		'Territory': 'territory',
	}
	collection = frappe.get_doc(customer_collection, collection_name)
	selected = [customer.name for customer in frappe.get_list(customer_collection, filters=[
			['lft', '>=', collection.lft],
			['rgt', '<=', collection.rgt]
		],
		fields=['name'],
		order_by='lft asc, rgt desc'
	)]
	table= 'Customer'
	if customer_collection == 'Supplier Group': table = 'Supplier'
	return frappe.get_list(table, fields=['name', 'email_id'], \
		filters=[[fields_dict[customer_collection], 'IN', selected]])

def get_customers_based_on_sales_person(sales_person):
	lft, rgt = frappe.db.get_value("Sales Person",
		sales_person, ["lft", "rgt"])
	records = frappe.db.sql("""
		select distinct parent, parenttype
		from `tabSales Team` steam
		where parenttype = 'Customer'
			and exists(select name from `tabSales Person` where lft >= %s and rgt <= %s and name = steam.sales_person)
	""", (lft, rgt), as_dict=1)
	sales_person_records = frappe._dict()
	for d in records:
		sales_person_records.setdefault(d.parenttype, set()).add(d.parent)
	if sales_person_records.get('Customer'):
		return frappe.get_list('Customer', fields=['name', 'email_id'], \
			filters=[['name', 'in', list(sales_person_records['Customer'])]])
	else:
		return []

@frappe.whitelist()
def prepare_statements(docname):
	doc = frappe.get_doc("Balance Confirmation Statement", docname)
	site = frappe.local.site
	
	doc.db_set("status", "In Progress") 
	frappe.db.commit()

	kwargs={"doc": doc, "site": site}

	thread = threading.Thread(target=get_customers_statements, kwargs=kwargs)
	thread.start()

	

def get_customers_statements(doc, site):
	frappe.init(site=site)
	frappe.connect()
	full_path = site + "/private/files/balance-statements/" + doc.name
	output_file = "/private/files/balance-statements/" + doc.name
	create_path(full_path)
	template_list = []
	letter_head = {}
	if doc.get("letter_head"):
		letter_head = frappe.db.get_value("Letter Head", doc.letter_head, ["content", "footer"], as_dict=True)
	for customer in doc.customers:
		customer_doc = frappe.get_doc(customer.customer_type, customer.customer)


		tax_id = customer_doc.tax_id
		presentation_currency = get_party_account_currency(customer.customer_type, customer_doc.name, doc.company) \
				or  get_company_currency(doc.company)

		filters= frappe._dict({
			'from_date':date(2000, 1, 1),
			'to_date': doc.to_date,
			'company': doc.company,
			'finance_book':  None,
			'account':  None,
			'party_type': customer.customer_type,
			'party': [customer_doc.name],
			'presentation_currency': presentation_currency,
			'group_by': 'Group by Voucher (Consolidated)',
			'cost_center': [],
			'project': [],
			'show_opening_entries': 0,
			'include_default_book_entries': 0,
			'tax_id':  None
		})
		col, res = get_soa(filters)
		context = {
			"doc": doc,
			"customer": customer_doc,
			"balance": round(res[-1]['balance'], 3)
		}

		template = frappe.render_template(get_letter_head(doc.print_format, letter_head), context)
		
		if doc.consolidate_statements:
			template_list.append(template)
		else:
			report = get_pdf(template)
			file_name = doc.name + "-" + customer_doc.name
			file_name.replace("/", "-")
			with open(full_path + "/" + doc.name + "-" + customer_doc.name + ".pdf", "wb" ) as f:
				f.write(report)

	if doc.consolidate_statements:
		templates = '<div style="page-break-after:always;clear:both;"></div>'.join(template_list)
		report = get_pdf(templates)
		with open(site + output_file + ".pdf", "wb" ) as f:
				f.write(report)
		doc.db_set("download_link", output_file + ".pdf")
	else:
		shutil.make_archive( site + output_file, 'zip', full_path)
		doc.db_set("download_link", output_file + ".zip")

	doc.db_set("status", "Processed")
	frappe.db.commit()

def create_path(full_path):
	isExist = os.path.exists(full_path)
	if isExist:
		shutil.rmtree(full_path)
	os.makedirs(full_path)

@frappe.whitelist()
def download_statements(download_link):
	site = frappe.local.site
	content = None
	with open(site + download_link, "rb") as f:
		content = f.read()
	frappe.local.response.filename = download_link.split('/')[-1]
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"

def get_letter_head(printformat, letterhead=None):
	if letterhead.get("content"):
		printformat =  "<div id='header-html'>" + letterhead.get("content") + "</div>" + printformat
	
	if letterhead.get("footer"):
		printformat += "<div id='footer-html'>" + letterhead.get("footer") + "</div>"

	return printformat
	