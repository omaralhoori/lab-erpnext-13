# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import now_datetime, cint, cstr
from frappe import _, throw
from frappe.model.document import Document
import re
from six import string_types

class WebFormResult(Document):
	def __init__(self, *args, **kwargs):
		super(WebFormResult, self).__init__(*args, **kwargs)

@frappe.whitelist()
def get_customer_data(customer_password):
	customer_name = frappe.db.get_value("COVID Analysis Form",
		{"customer_password": customer_password}, "custmer_name")

	analysis_result = frappe.db.get_value("COVID Analysis Form",
		{"customer_password": customer_password}, "analysis_result")


	return {
		"customer_name": customer_name,
		"analysis_result": analysis_result,
	}


