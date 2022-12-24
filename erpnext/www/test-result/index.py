from frappe.utils.pdf import get_pdf
import frappe
import pdfkit
import tempfile
import os
from frappe import _
from erpnext.healthcare.doctype.lab_test.lab_test_print import format_xray_header, get_lab_test_result, get_normal_xray_tbody, get_print_tbody, get_uploaded_tests, get_uploaded_tests_with_content, user_test_result, get_print_style, get_print_html_base, get_print_header

no_cache = 1

def get_context(context):
    context.no_cache = 1
    context.title = "Test Result"
    user_visists = frappe.db.get_value("Header Footer", "User Visits", ["header", "footer"])
    context.header = user_visists[0] if user_visists and user_visists[0] else ""
    context.footer = user_visists[1] if user_visists and user_visists[1] else ""

    if not (frappe.form_dict.usercode):
        return print_error_message(context, "usercode is required")

    usercode = frappe.form_dict.usercode.split("_")
    if len(usercode) < 2:
        return print_error_message(context, "usercode is not correct")
    
    patient_password, file_no = usercode[0], usercode[1]
    patient = frappe.db.get_value("Patient", {"patient_number": file_no, "patient_password": patient_password}, ["name", "patient_name"])
    if not patient:
        return print_error_message(context, "Patient name or password is not correct")

    show_all_results = frappe.db.get_single_value("Healthcare Settings", "show_all_results")
    lab_test = frappe.db.get_value("Lab Test", {"patient": patient[0]}, ["name"])

    invoices = frappe.db.sql("""
        select "Laboratory Test" as result_type,tlt.name as result_name, tlt.status as result_status, tbi.name as invoice_name, tbi.creation as visit_date from `tabSales Invoice` tbi
        INNER JOIN `tabLab Test` as tlt on tbi.name=tlt.sales_invoice
        where tbi.patient=%s and sms_to_payer=0
        UNION ALL
        select "Radiology Test" as result_type, trt.name as result_name, trt.record_status as result_status, tbi.name as invoice_name, tbi.creation as visit_date from `tabSales Invoice` tbi
        INNER JOIN `tabRadiology Test` trt on tbi.name=trt.sales_invoice 
        where tbi.patient=%s and sms_to_payer=0;
    """,(patient[0],patient[0]),as_dict=True)
    context.patient_name =patient[1]
    context.file_no = file_no
    context.invoices=invoices
    context.usercode = frappe.form_dict.usercode
    return context
    # test_results = get_lab_test_result(patient, show_all_results or False)
    # if len(test_results) == 0:
    #     return print_error_message("No test found")
    # elif len(test_results) == 1:
    #     html = frappe.render_template('templates/test_result/test_result.html', test_results[0])

    
    # return {
    #     "body": html
    # }

@frappe.whitelist(allow_guest=True)
def user_result(usercode):
    if not (frappe.form_dict.usercode):
        return print_error_message("usercode is required")

    usercode = frappe.form_dict.usercode.split("_")
    if len(usercode) < 2:
        return print_error_message("usercode is not correct")
    
    patient_password, patient_name = usercode[0], usercode[1]
    patient = frappe.db.get_value("Patient", {"patient_number": patient_name, "patient_password": patient_password}, "name")
    if not patient:
        return print_error_message("Patient name or password is not correct")
    lab_test = frappe.db.get_value("Lab Test", {"patient": patient}, ["name"])
    user_test_result(lab_test)
    

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

TEST_TYPES = ['Laboratory Test', 'Radiology Test']

@frappe.whitelist(allow_guest=True)
def test_details(usercode, test_type, test_name):
    usercode = frappe.form_dict.usercode.split("_")
    if len(usercode) < 2:
        return format_error_message("usercode is not correct")
    patient_password, file_no = usercode[0], usercode[1]
    patient = frappe.db.get_value("Patient", {"patient_number": file_no, "patient_password": patient_password}, ["name", "patient_name"])
    if not patient:
        return format_error_message("Patient name or password is not correct")
    if not test_type in TEST_TYPES: return format_error_message("Test type is not known")

    if test_type == 'Laboratory Test':
        return get_lab_tests(test_name)
    elif test_type == 'Radiology Test':
        return get_rad_tests(test_name)
    else:
        return format_error_message("Test type is not known")

def get_lab_tests(test_name):
    header_footer = frappe.db.get_value("Header Footer", "Lab User Result", ["header", "footer"])
    header, footer = "", ""
    if header_footer: header, footer = header_footer
    test_doc = frappe.get_doc("Lab Test", test_name)
    patient_header = get_print_header(test_doc)
    tests_body = get_print_tbody(test_doc, (header or "") + patient_header , only_finalized=True)
    tests_count = frappe.db.sql("""
    select count(*) as test_count, status FROM (
	SELECT count(*), report_code, status  FROM `tabNormal Test Result` tntr
	WHERE tntr.parent=%s and tntr.allow_blank=0 and status != "Rejected"
	GROUP BY report_code, status
        ) as tests
        GROUP BY status;
    """,(test_name), as_dict=True)
    requested_tests, completed_tests, pending_tests=0, 0, 0
    for test in tests_count:
        requested_tests += int(test['test_count'])
        if test['status'] == 'Finalized': completed_tests += int(test['test_count'])
        else: pending_tests += int(test['test_count'])
    if footer: footer = footer.format(requested_tests=str(requested_tests), completed_tests=str(completed_tests), pending_tests=str(pending_tests))
    html = get_print_html_base() + (footer or "")
    html = html.format(body=tests_body, style=get_style())
    options = { "--margin-left" : "5mm","margin-left" : "5mm","--margin-right" : "5mm","margin-right" : "5mm","--margin-bottom": "30mm",
    "quiet":""}
    output = get_pdf(html, options)#pdfkit.from_string(html, False, options)
    uploaded_tests = get_uploaded_tests(test_doc, only_finalized=True)
    if len(uploaded_tests) > 0:
        output = get_uploaded_tests_with_content(uploaded_tests, output)
    frappe.response.filename = test_doc.patient + "-Laboratory Test Result.pdf"
    frappe.response.filecontent = output
    frappe.response.type = "pdf"

def get_rad_tests(test_name):
    header_footer = frappe.db.get_value("Header Footer", "Rad User Result", ["header", "footer"])
    header, footer = "", ""
    if header_footer: header, footer = header_footer

    xray_test = frappe.get_doc("Radiology Test", test_name)
    if not xray_test: frappe.throw("No Radiology Test created with this invoice.")
    if xray_test.record_status != "Finalized": frappe.throw("Radiology test not finalized.")
    if len(xray_test.test_results) == 0: frappe.throw("Radiology test has no test result.")
    reports = { result.test_name: result.test_result.replace("<p>", "<tr><td>").replace("</p>", "</td></tr>") for result in xray_test.test_results  if result.status != "Rejected"}
    header = (header or "")  + format_xray_header(xray_test, False)
    html = get_print_html_base()
    tbody = get_normal_xray_tbody(reports, header) + ( footer or "")
    html = html.format(body=tbody,style=get_style())
    options = { "--margin-left" : "5mm","margin-left" : "5mm","--margin-right" : "5mm","margin-right" : "5mm","--margin-bottom": "30mm",
    "quiet":""}
    with open('xray.html' , "w") as f:
        f.write(html)
    output = get_pdf(html, options)#pdfkit.from_string(html, False, options)
    frappe.response.filename = xray_test.patient + "-Radiology Test Result.pdf"
    frappe.response.filecontent = output
    frappe.response.type = "pdf"

def get_style():
    style = get_print_style()
    style += """
    <style>
        body{
            font-size: .75em !important ;
        }
        .header td{
            font-size: 1.2em !important ;
        }
        .xray-reports tr, .xray-reports tbody,
        .xray-reports td, .xray-reports, 
        .ql-editor, .ql-editor p {
            page-break-inside:  inherit !important;
        }

        * {
    overflow: visible !important;
        }
    </style>
    """
    return style
    
def format_error_message(msg):
    # content =  f"""
    #     <h1>{_('Error')}</h1>
    #     <div>
    #         {_(msg)}
    #     </div>
    # """
    # print(frappe.local.response)
    # #frappe.local.response.filecontent = content
    # #frappe.local.response.filename = "result"
    # #frappe.local.response['http_status_code'] = 400
    # #frappe.local.response.type = "page"
    return _(msg)

def print_error_message(context, msg):
    context.error = _(msg)
    return context