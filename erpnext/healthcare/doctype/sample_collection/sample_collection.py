# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
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
			send_received_msg_order(self.name, test_name)
			frappe.db.set_value("Lab Test", test_name, {"status": "Received", "sample_collected": 1})
			frappe.db.sql("""
				UPDATE `tabNormal Test Result` SET status='Received'
			WHERE parent='{test_name}' AND status IS NULL
			""".format(test_name=test_name))

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