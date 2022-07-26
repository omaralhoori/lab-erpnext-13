import frappe
import pdfkit
import tempfile
import os

from erpnext.healthcare.doctype.lab_test.lab_test_print import get_lab_test_result

no_cache = 1

def get_context(context):
    context.no_cache = 1
    context.title = "Test Result"
    if not (frappe.form_dict.usercode):
        return print_error_message("usercode is required")

    usercode = frappe.form_dict.usercode.split("_")
    if len(usercode) < 2:
        return print_error_message("usercode is not correct")
    
    patient_password, patient_name = usercode[0], usercode[1]

    if not frappe.db.get_value("Patient", {"name": patient_name, "patient_password": patient_password}, "name"):
        return print_error_message("Patient name or password is not correct")

    show_all_results = frappe.db.get_single_value("Healthcare Settings", "show_all_results")

    test_results = get_lab_test_result(patient_name, show_all_results or False)
    if len(test_results) == 0:
        return print_error_message("No test found")
    elif len(test_results) == 1:
        html = frappe.render_template('templates/test_result/test_result.html', test_results[0])

    
    return {
        "body": html
    }


@frappe.whitelist(allow_guest=True)
def download_pdf(patient, password):
    if not frappe.db.get_value("Patient", {"name": patient, "patient_password": password}, "name"):
        return print_error_message("Patient name or password is not correct")

    test_results = get_lab_test_result(patient, False)
    if len(test_results) == 0:
        return print_error_message("No test found")
    elif len(test_results) == 1:
        html = frappe.render_template('templates/test_result/test_result.html', test_results[0])
        html_header = frappe.render_template('templates/test_result/test_result_header.html', test_results[0])
    style = """
    <style>
    button{
        display: none;
    }
    body{
        padding: 0 !important;
    }
    </style>
    """


    name = patient + "_" + password + ".pdf"
    # with open( name.replace("/", "-"), "w+") as f:
    #     f.write(html)
    options = {  "enable-local-file-access": None, } #'quiet': '' ,

    # try:
    #     with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode="w") as header_html:
    #         options['header-html'] = header_html.name
    #         header_html.write(html_header)
    #         pdf = pdfkit.from_string(style + html, False, options) 
    # finally:
    #     # Ensure temporary file is deleted after finishing work
    #     os.remove(options['header-html'])

    frappe.local.response.filename = name
    frappe.local.response.filecontent = pdfkit.from_string(style + html, False, options)  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"

def print_error_message(msg):
    return {
            "body": """<h1>Error</h1>
                <p>{msg}</p>
                """.format(msg=msg)
        }