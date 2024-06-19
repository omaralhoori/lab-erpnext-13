# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	data = get_tests(filters)
	columns = get_columns()
	return columns, data


def get_columns( additional_table_columns=[]):
	show_whatsapp_button = frappe.db.get_single_value("LIS Settings", "show_whatsapp_send_button")
	if show_whatsapp_button:
		send_whatsapp = [
			{
			'label': _("Whatsapp Status"),
			'fieldname': 'whatsapp_status',
			'fieldtype': 'Data',
			'width': 120
		},
			{
			'label': "Send Whatsapp",
			'fieldname': "whatsapp_btn",
			'fieldtype': 'html',
			'width': 120
		}]
	else:
		send_whatsapp = []
	"""return columns based on filters"""
	columns = [
		{
			'label': _("Invoice No"),
			'fieldname': 'sales_invoice',
			'fieldtype': 'Link',
			'options': 'Sales Invoice',
			'width': 120
		},
		{
			'label': _("Lab Status"),
			'fieldname': 'lab_status',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _("Radiology Status"),
			'fieldname': 'rad_status',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _("Visiting Date"),
			'fieldname': 'visiting_date',
			'fieldtype': 'Date',
			'width': 80
		},
		{
			'label': _("Insurance Payer"),
			'fieldname': 'insurance_party',
			'fieldtype': 'Link',
			'options': 'Customer',
			'width': 120
		},
		{
			'label': _("Patient"),
			'fieldname': 'patient',
			'fieldtype': 'Link',
			'options': 'Patient',
			'width': 240
		},
		{
			'label': _("Mobile"),
			'fieldname': 'mobile',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _("Passport"),
			'fieldname': 'passport_no',
			'fieldtype': 'Data',
			'width': 120
		},
			{
			'label': _("Birth Date"),
			'fieldname': 'birth_date',
			'fieldtype': 'Date',
			'width': 120
		},
			{
			'label': _("SMS Status"),
			'fieldname': 'sms_status',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': "Print Result",
			'fieldname': "print_btn",
			'fieldtype': 'html',
			'width': 120
		},
		{
			'label': "Send SMS",
			'fieldname': "sms_btn",
			'fieldtype': 'html',
			'width': 120
		},		
	]
	if show_whatsapp_button:
		columns += send_whatsapp

	columns += [
		{
			'label': "Print Xray",
			'fieldname': "xray_btn",
			'fieldtype': 'html',
			'width': 120
		},
		{
			'label': "Clinical Test",
			'fieldname': "clinical_btn",
			'fieldtype': 'html',
			'width': 120
		}
	]

	if frappe.local.conf.is_embassy:
		columns += [{
			'label': "Print Cover",
			'fieldname': "cover_btn",
			'fieldtype': 'html',
			'width': 120
		}]

	if additional_table_columns:
		columns += additional_table_columns

	return columns



def get_conditions(filters):
	conditions = ""

	if filters.get("company"): conditions += " lt.company=%(company)s"
	else: conditions = " True"
	if filters.get("patient"): conditions += " and lt.patient = %(patient)s"
	if filters.get("insurance_party"): conditions += " and si.insurance_party = %(insurance_party)s"

	if filters.get("from_date"): conditions += " and si.posting_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and si.posting_date <= %(to_date)s"
	if filters.get("finalized"): conditions += " and lt.status IN ('Finalized', 'Partially Finalized') "
	return conditions


def get_tests(filters, additional_query_columns=[]):
	if additional_query_columns:
		additional_query_columns = ', ' + ', '.join(additional_query_columns)
	with_header = filters.get("with_header") or ''
	conditions = get_conditions(filters)
	cover_btn = ''
	if frappe.local.conf.is_embassy:
		cover_btn = """
		,  CONCAT('<a target="_blank" class=''btn btn-sm'' href="/api/method/erpnext.healthcare.doctype.lab_test.lab_test_print.get_embassy_cover?sales_invoice=',si.name,'">Print Cover</a>') as cover_btn
		"""
	print_permission = ''
	user_roles = frappe.get_roles()
	if "Operation User Print" not in user_roles and "Operation User Print Previous" not in user_roles:
		print_permission = 'hide'
	show_sms = 'hide'
	if "SMS_Sender_After_Finilize" in user_roles:
		show_sms = ""
	with_previous = 1 if "Operation User Print Previous" in user_roles else 0
	invoices = frappe.db.sql("""
		select si.name as sales_invoice,p.passport_no, si.creation as visiting_date, si.insurance_party, si.patient as patient, si.mobile_no as mobile,
		p.dob as birth_date, lt.status as lab_status, rt.record_status as rad_status,
		IF(lt.sms_sent, 'Sent', 'Not Sent') as sms_status, IF(lt.whatsapp_status, 'Sent', 'Not Sent') as whatsapp_status,
		IF(lt.status IN ('Finalized', 'Partially Finalized'), CONCAT('<button class=''btn btn-sm {2}'' with_header=''{1}'' data=''', lt.name ,''' onClick=''print_result(this.getAttribute("data"), this.getAttribute("with_header"), {3})''>Print Test</button>'), '' )as print_btn,
		IF(lt.status IN ('Finalized', 'Partially Finalized'), CONCAT('<button class=''btn btn-sm {4}'' data=''', lt.name ,''' onClick=''send_sms(this.getAttribute("data"))''>Send SMS</button>'), '' ) as sms_btn,
		IF(lt.status IN ('Finalized', 'Partially Finalized'), CONCAT('<button class=''btn btn-sm {4}'' data=''', lt.name ,''' onClick=''send_whatsapp(this.getAttribute("data"))''>Send Whatsapp</button>'), '' ) as whatsapp_btn,
		IF(rt.record_status IN ('Finalized'), CONCAT('<button class=''btn btn-sm'' with_header=''{1}'' data=''', si.name ,''' onClick=''print_xray(this.getAttribute("data"), this.getAttribute("with_header"))''>Print Xray</button>'), '' ) as xray_btn,
		IF(ct.status IN ('Finalized', 'Partially Finalized'), CONCAT('<button class=''btn btn-sm {2}'' with_header=''{1}'' data=''', ct.name ,''' onClick=''print_clinical(this.getAttribute("data"), this.getAttribute("with_header"), {3})''>Print Clinical</button>'), '' )as clinical_btn
		 {0}
		from`tabSales Invoice` as si 
		LEFT JOIN  `tabLab Test` as lt  ON si.name=lt.sales_invoice
		INNER JOIN `tabPatient` as p ON p.name=si.patient
		LEFT JOIN `tabRadiology Test` as rt ON rt.sales_invoice=si.name
		LEFT JOIN `tabClinical Testing` as ct ON ct.sales_invoice=si.name
		where %s order by si.creation""".format(cover_btn or '', with_header, print_permission, with_previous, show_sms) %
		conditions, filters, as_dict=1)
	return invoices


@frappe.whitelist()
def get_patient_result_whatsapp(lab_test):
	lab_test_doc = frappe.get_doc("Lab Test", lab_test)
	result_msg = lab_test_doc.get_result_msg()
	url = 'https://web.whatsapp.com/send?phone={mobile}&text={msg}'.format(mobile=format_mobile_number(lab_test_doc.patient_mobile), msg=result_msg)
	frappe.db.set_value("Lab Test", lab_test, "whatsapp_status", 1)
	frappe.db.commit()
	frappe.flags.redirect_location = url
	frappe.local.flags.redirect_location = url
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = url
def format_mobile_number(mobile_number):
	if mobile_number.startswith("+"):
		return mobile_number
	return "+" + mobile_number