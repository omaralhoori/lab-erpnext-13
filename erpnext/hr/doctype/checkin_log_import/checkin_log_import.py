# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from erpnext.hr.doctype.employee_checkin.employee_checkin import add_log_based_on_employee_field
import frappe
from frappe.model.document import Document

class CheckinLogImport(Document):
	def start_import(self):
		if parse_log_file(self.log_file):
			self.db_set("status", "Success")
			return True
def get_log_type(log):
	log_types= {
		"I": "IN",
		"O": "OUT",
		"IN": "IN",
		"OUT": "OUT",
		"0": "IN",
		"1": "OUT"
	}
	return log_types.get(log)

def parse_log_file(log_file):
	"""
		17090	2023-04-26 16:26:11	102	1	17090	I	0
		EmployeeId CheckinDate-CheckinTime DeviceId UK UK LogType UK
	"""
	with open( get_full_path(log_file), "r") as f:
		logs = f.readlines()
		for log in logs:
			log_details = log.split("\t")
			if len(log_details) > 5:
				add_log_based_on_employee_field(
					employee_field_value=log_details[0],
					timestamp=log_details[1],
					device_id=log_details[2],
					log_type=get_log_type(log_details[5])
				)
	return True

@frappe.whitelist()
def form_start_import(data_import):
	return frappe.get_doc("Checkin Log Import", data_import).start_import()


def get_full_path(file_path):
		"""Returns file path from given file name"""

		if file_path.startswith("/private/files/"):
			pass

		elif file_path.startswith("/files/"):
			file_path = "/public" + file_path

		elif file_path.startswith("http"):
			return file_path


		return frappe.local.site + file_path