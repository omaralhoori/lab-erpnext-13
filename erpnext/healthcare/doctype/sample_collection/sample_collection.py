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
		validate_invoice_paid(self.patient, self.sales_invoice)
		test_name = frappe.db.get_value("Lab Test", {"sample": self.name}, ["name"])
		if test_name:
			send_received_msg_order(self.name, test_name)
			frappe.db.set_value("Lab Test", test_name, {"status": "Received", "sample_collected": 1})
			frappe.db.sql("""
				UPDATE `tabNormal Test Result` SET status='Received'
			WHERE parent='{test_name}'
			""".format(test_name=test_name))