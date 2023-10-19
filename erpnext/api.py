import frappe
from erpnext.healthcare.doctype.lab_test.lab_test_print import lab_test_result
@frappe.whitelist(allow_guest=True)
def patient_results(invoice, password):
    patient = frappe.db.get_value("Sales Invoice", invoice, ['patient'])
    if not patient: return
    if frappe.db.get_value("Patient", patient, 'patient_password') != password: return
    lab_test = frappe.db.get_value("Lab Test", {"sales_invoice": invoice}, "name")
    return lab_test_result(lab_test, only_finilized=True, head=True)
