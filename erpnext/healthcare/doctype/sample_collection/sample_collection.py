# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.core.doctype.sms_settings.sms_settings import send_sms

from erpnext.healthcare.doctype.lab_test.lab_test import send_received_msg_order

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt
from erpnext.healthcare.doctype.patient.patient import validate_invoice_paid


class SampleCollection(Document):
	def validate(self):
		for detail in self.sample_collection_detail:
			if flt(detail.sample_qty) <= 0:
				frappe.throw(_('Sample Quantity cannot be negative or 0'), title=_('Invalid Quantity'))
	
	def before_insert(self):
		format_ser = "bar-" + ".########"
		if frappe.get_cached_value("Healthcare Settings",None, "use_branch_code"):
			abbr = frappe.db.get_value("Company", self.company, ["abbr"])
			if abbr:
				format_ser = "bar-" + abbr + ".######"
			
		prg_serial = make_autoname(format_ser, "Sample Collection")
		self.collection_serial = prg_serial

	def on_submit(self):
		if frappe.local.conf.is_embassy:
			if self.record_status != "Released": frappe.throw(_('Sample not verified with fingerprint'))
		#validate_invoice_paid(self.patient, self.sales_invoice)
		test_name = frappe.db.get_value("Lab Test", {"sample": self.name}, ["name"])
		if test_name:
			send_received_msg_order(self.name, test_name, self.company)
			frappe.db.set_value("Lab Test", test_name, {"status": "Received", "sample_collected": 1})
			frappe.db.sql("""
				UPDATE `tabNormal Test Result` SET status='Received'
			WHERE parent='{test_name}' AND status IS NULL
			""".format(test_name=test_name))
		if not self.sms_sent and frappe.db.get_single_value("Healthcare Settings", "sample_collection_sms"):
			self.send_survey_message()
	def send_survey_message(self):
		survey_msg = frappe.db.get_single_value("Healthcare Settings", "patient_survey_message")
		if not survey_msg:
			frappe.msgprint("Patient Survey Message is not provided in the Healthcare Settings!")
			return
		if not self.patient_mobile:
			frappe.msgprint("Patient Mobile Number is not provided!")
			return
		result_url = frappe.db.get_single_value("Healthcare Settings", "result_url")
		if not result_url or result_url == "":
			frappe.msgprint(_("Failed to send sms. Result url is empty in Healthcare Settings."))
			return

		if result_url[-1] != "/":
			result_url += '/'
		patient_password = frappe.db.get_value("Patient", self.patient, ["patient_password"])
		if not patient_password:
			frappe.msgprint(_("Failed to send sms. Patient information is incomplete."))
			return
		result_url += "patient-satisfaction-survey?new=1&invoice=" + self.sales_invoice +"_"+ patient_password
		survey_msg = survey_msg.format(url=result_url, patient=self.patient_name)
		send_sms(msg=survey_msg, receiver_list=[self.patient_mobile])
		self.db_set('sms_sent', 1)

import json
@frappe.whitelist()
def release_selected(tests):
	tests = json.loads(tests)
	frappe.db.sql("""
	UPDATE `tabSample Collection` SET record_status="Released"
	WHERE name in ({tests}) AND record_status IN ('Draft')
	""".format(tests=",".join(tests)))

@frappe.whitelist()
def unrelease_selected(tests):
	tests = json.loads(tests)
	frappe.db.sql("""
	UPDATE `tabSample Collection` SET record_status="Draft"
	WHERE name in ({tests}) AND record_status IN ('Released')
	""".format(tests=",".join(tests)))


@frappe.whitelist()
def uncollect_sample(sample):
	frappe.db.set_value("Sample Collection", sample, "docstatus", 0)