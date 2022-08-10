from __future__ import unicode_literals


import frappe
from frappe import _

@frappe.whitelist()
def find_lab_test(test_code):
    test_name = frappe.db.get_value("Lab Test", {"sales_invoice": test_code.strip()}, ["name"])
    if test_name and test_name != "":
        return '/app/lab-test/' + test_name
    frappe.msgprint(_("Unable to find test with invoice: ") + test_code)

@frappe.whitelist()
def find_sample_collection(test_code):
    test_name = frappe.db.get_value("Sample Collection", {"sales_invoice": test_code.strip()}, ["name"])
    if test_name and test_name != "":
        return '/app/sample-collection/' + test_name
    frappe.msgprint(_("Unable to find sample collection with invoice: ") + test_code)

@frappe.whitelist()
def find_rad_test(test_code):
    test_name = frappe.db.get_value("Radiology Test", {"sales_invoice": test_code.strip()}, ["name"])
    if test_name and test_name != "":
        return '/app/radiology-test/' + test_name
    frappe.msgprint(_("Unable to find Radiology test with invoice: ") + test_code)

@frappe.whitelist()
def find_sales_invoice(test_code):
    test_name = frappe.db.get_value("Sales Invoice", {"name": test_code.strip()}, ["name"])
    if test_name and test_name != "":
        return '/app/sales-invoice/' + test_name
    frappe.msgprint(_("Unable to find sales invoice with code: ") + test_code)