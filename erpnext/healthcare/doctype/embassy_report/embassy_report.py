# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmbassyReport(Document):
	def prepare_report_data(self):
		invoice_date = frappe.db.get_value("Sales Invoice", self.sales_invoice,"creation")
		data  = {
			"patient_name": self.patient_name,
			"gender": self.gender,
			"age": self.age,
			"status": self.status,
			"nationality": self.nationality,
			"passport_no": self.passport_no,
			"passport_date": self.passport_date_of_issue,
			"passport_place": self.passport_place_of_issue,
			"report_date": frappe.utils.get_datetime(invoice_date).strftime("%d/%m/%Y",) if invoice_date else frappe.utils.get_datetime().strftime("%d/%m/%Y",)
		}
		attributes = frappe.db.sql(f"""
			SELECT attribute, result FROM `tabEmbassy Report Attribute Result` WHERE parent="{self.name}"
		""", as_dict=True)
		if len(attributes) > 0:
			attributes_dict = {item["attribute"] :item["result"] for item in attributes}
			data=dict(data,**attributes_dict)
		return data
