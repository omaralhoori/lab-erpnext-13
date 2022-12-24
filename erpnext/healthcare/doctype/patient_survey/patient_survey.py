# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
class PatientSurvey(Document):
	pass



@frappe.whitelist(allow_guest=True)
def is_survey_enabled(sales_invoice):
	if(len(sales_invoice.split("_")) < 2): 
		frappe.msgprint(_("Provided url is not correct."))
		return False
	survey = frappe.db.get_value("Patient Survey", {"sales_invoice": sales_invoice.split("_")[0]}, "name")
	if survey: return False
	if frappe.db.sql("""
		SELECT inv.name FROM `tabSales Invoice` as inv
		INNER JOIN `tabPatient` as ptn ON ptn.name=inv.patient
		WHERE inv.name=%s AND ptn.patient_password=%s
	""",(sales_invoice.split("_")[0], sales_invoice.split("_")[1])):
		return True
	else:
		frappe.msgprint(_("Provided information is not correct"))
	return False