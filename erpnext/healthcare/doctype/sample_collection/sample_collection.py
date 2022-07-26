# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

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
		prg_serial = make_autoname(format_ser, "Sample Collection")
		self.collection_serial = prg_serial

	def on_submit(self):
		validate_invoice_paid(self.patient, self.sales_invoice)
