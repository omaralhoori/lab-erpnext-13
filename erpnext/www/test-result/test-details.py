import frappe
import pdfkit
import tempfile
import os
from frappe import _
from erpnext.healthcare.doctype.lab_test.lab_test_print import get_lab_test_result, user_test_result

no_cache = 1

def get_context(context):
    context.no_cache = 1
    frappe.form_dict.usercode
    # if not (frappe.form_dict.usercode):
    #     return print_error_message(context, "usercode is required")

    # usercode = frappe.form_dict.usercode.split("_")
    # if len(usercode) < 2:
    #     return print_error_message(context, "usercode is not correct")
    
    # patient_password, file_no = usercode[0], usercode[1]
    # patient = frappe.db.get_value("Patient", {"patient_number": file_no, "patient_password": patient_password}, ["name", "patient_name"])
    # if not patient:
    #     return print_error_message(context, "Patient name or password is not correct")
    return "sss"    
    return context