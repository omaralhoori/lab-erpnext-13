from __future__ import unicode_literals
from asyncore import write
import json

import frappe
from frappe.permissions import get_valid_perms
from frappe.utils.pdf import get_file_data_from_writer

def get_lab_test_result(patient_name, show_all_results, where_stmt=None):
    show_all_results = True if show_all_results == 1 else False
    if not where_stmt:
        where_stmt = "WHERE p.name='{patient_name}' AND lt.docstatus=1".format(patient_name=patient_name)
    limit_stmt = "" if show_all_results else "LIMIT 1"
    fields = [
        "p.patient_name", "lt.patient_age", "p.patient_number", "p.sex as patient_gender", "lt.creation","lt.company",
     "lt.sales_invoice", "sc.modified as sample_date", "lt.practitioner_name", "lt.name as test_name"] # p.dob
    query = """
        SELECT {fields}
        FROM `tabLab Test` AS lt
        INNER JOIN `tabPatient` AS p ON lt.patient=p.name
        left JOIN `tabSample Collection` AS sc ON lt.sample=sc.name
        {where_stmt}
        ORDER BY lt.creation DESC
        {limit_stmt}
    """.format(fields=",".join(fields), where_stmt=where_stmt, limit_stmt=limit_stmt)

    lab_tests = frappe.db.sql(query, as_dict=True)
    patient = frappe.get_doc("Patient", patient_name)
    for test in lab_tests:
        test["results"] = frappe.db.sql("""
            SELECT ntr.lab_test_name, ntr.result_value, ntr.result_percentage, ntr.lab_test_uom, ntr.secondary_uom_result,ntr.secondary_uom as si_unit_name, 
            ntr.lab_test_comment, ntr.template, ltt.normal_range_label, ntr.report_code, ntr.custom_normal_range
            FROM `tabNormal Test Result` as ntr
            INNER JOIN `tabLab Test Template` as ltt
            ON ltt.name=ntr.template
            WHERE ntr.parent='{test_name}' AND ntr.parenttype='Lab Test' AND ntr.status IN ('Finalized', 'Released')
        """.format(test_name=test["test_name"]), as_dict=True)

        results = {}
        for result in test["results"]:
            if result.get('custom_normal_range') and result.get('custom_normal_range') != "":
                result['template'] = parse_custom_normal_range(result.get('custom_normal_range'))
            else:
                result['template'] = filter_ranges(get_normal_ranges(result['template'], test['creation'], branch=test['company']), patient)
            if result['report_code']:
                if not results.get(result['report_code']):
                    results[result['report_code']] = []
                results[result['report_code']].append(result)
        test["results"] = results
    return lab_tests

def parse_custom_normal_range(normal_range_str):
    normal_ranges = normal_range_str.split("\n")
    return list(map(lambda normal_range:parse_one_custom_range(normal_range), normal_ranges))
    
def parse_one_custom_range(normal_range_str):
    normal_range = normal_range_str.split(";")
    return {
        "range_type": "Normal",
        "gender": "All",
        "criteria_text": normal_range[1] if len(normal_range) > 1 else "",
        "range_text": normal_range[0],
        "si_range_text": normal_range[2] if len(normal_range) > 2 else "",
        "age_range": "All", "hide_normal_range": 0, "range_from": 0, "range_to": 0, "min_si_value": 0, "max_si_value": 0,
        "from_age": "", "from_age_period": "", "to_age": "", "to_age_period": "", "result_type": ""
    }

def map_test_report_code(test_results):
    results = {}
    return results

def get_normal_ranges(lab_test_template, creation,branch=None):
    if branch:
        custom_nr = frappe.db.sql("""
        SELECT anr.range_type, anr.gender, anr.criteria_text, anr.range_text, anr.si_range_text, 
        anr.age_range, anr.from_age, anr.from_age_period, anr.to_age, anr.to_age_period, anr.result_type, anr.hide_normal_range,
        anr.range_from, anr.range_to, anr.min_si_value, anr.max_si_value
        FROM `tabCustom Normal Range` as anr
        WHERE anr.parent="{lab_test_template}" AND anr.company="{company}" AND anr.parenttype='Lab Test Template' AND anr.range_type!='Machine Edge' AND (anr.effective_date IS NULL OR "{creation}" >= anr.effective_date) AND (anr.expiry_date IS NULL OR "{creation}" <= anr.expiry_date)
        ORDER BY anr.range_order
        """.format(lab_test_template=lab_test_template, creation=creation.date(), company=branch), as_dict=True)
        if len(custom_nr) > 0: return custom_nr
    return frappe.db.sql("""
    SELECT anr.range_type, anr.gender, anr.criteria_text, anr.range_text, anr.si_range_text, 
    anr.age_range, anr.from_age, anr.from_age_period, anr.to_age, anr.to_age_period, anr.result_type, anr.hide_normal_range,
    anr.range_from, anr.range_to, anr.min_si_value, anr.max_si_value
    FROM `tabAttribute Normal Range` as anr
    WHERE anr.parent="{lab_test_template}" AND anr.parenttype='Lab Test Template' AND anr.range_type!='Machine Edge' AND (anr.effective_date IS NULL OR "{creation}" >= anr.effective_date) AND (anr.expiry_date IS NULL OR "{creation}" <= anr.expiry_date)
    ORDER BY anr.range_order
    """.format(lab_test_template=lab_test_template, creation=creation.date()), as_dict=True)

def filter_range_by_gender(range, patient):
    if range['gender'] in ['Male', 'Female']:
        if range['gender'] == patient.sex:
            return True
        else:
            return False
    
    return True

import datetime

def filter_range_by_age(range, patient):
    if patient.dob:
        today = datetime.date.today()
        patient_days = today - patient.dob
        patient_days = patient_days.days
        if range['age_range'] in ['>', '<', '=']:
            if range['age_range'] == '>':
                if range['from_age_period'] == 'Day(s)':
                    return patient_days > int(range['from_age'])
                elif range['from_age_period'] == 'Month(s)':
                    return patient_days > (int(range['from_age']) * 30)
                else: return patient_days > (int(range['from_age']) * 365)

            elif range['age_range'] == '<':
                if range['from_age_period'] == 'Day(s)':
                    return patient_days < int(range['from_age'])
                elif range['from_age_period'] == 'Month(s)':
                    return patient_days < (int(range['from_age']) * 30)
                else: return patient_days < (int(range['from_age']) * 365)

            elif range['age_range'] == '=':
                if range['from_age_period'] == 'Day(s)':
                    return patient_days > int(range['from_age'])
                elif range['from_age_period'] == 'Month(s)':
                    return patient_days > (int(range['from_age']) * 25) and patient_days < (int(range['from_age']) * 35) 

                else: 
                    return patient_days > (int(range['from_age']) * 330) and patient_days < (int(range['from_age']) * 400)

        elif range['age_range'] == 'Between':
            from_days = 0
            to_days = 0
            if range['from_age_period'] == 'Day(s)':
                from_days = int(range['from_age'])
            elif range['from_age_period'] == 'Month(s)':
                from_days =  int(range['from_age']) * 30
            else:
                from_days =  int(range['from_age']) * 365   
            if range['to_age_period'] == 'Day(s)':
                to_days = int(range['to_age'])
            elif range['to_age_period'] == 'Month(s)':
                to_days =  int(range['to_age']) * 30
            else:
                to_days =  int(range['to_age']) * 365
            return patient_days > from_days and patient_days < to_days
    return True

def compare_age(age_period, age_range, dob):
    pass

def filter_ranges(ranges, patient):
    ranges = list(filter(lambda range: filter_range_by_gender(range, patient), ranges ))
    ranges = list(filter(lambda range: filter_range_by_age(range, patient), ranges ))
    return ranges


import pdfkit

def user_test_result(lab_test, get_html=True):
    # f = open("test-print.html", "r")
    # html  = f.read()
    # f.close()
    test_doc = frappe.get_doc("Lab Test", lab_test)
    if not test_doc:
        frappe.throw("Lab Test not found")
    html = get_print_html_base()
    url = frappe.local.request.host
    header = get_print_header(test_doc, f'<img class="img-header" src="http://{url}/files/josante-logo.png" />')
    tbody = get_print_tbody(test_doc, header, True)
    body = get_print_body(header, tbody)
    html = html.format(body=body,style=get_print_style())
    # if get_html:
    #     return html
    options = { "quiet":""}
    frappe.local.response.filename = test_doc.patient_name + ".pdf" #"Test.pdf"
    frappe.local.response.filecontent = pdfkit.from_string(html, False, options)  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"


@frappe.whitelist()
def print_report_xray(sales_invoice, with_header=False):
    get_xray_report(sales_invoice, False, with_header)

def print_all_xray_report(invoices):
    writer = None
    expectedValue = 0
    for idx, sales_invoice in enumerate(invoices):
        xray = get_xray_report(sales_invoice, return_html=True)
        if xray == "": 
            expectedValue +=1
            continue
        if idx == expectedValue:
            writer = get_pdf_writer(xray)
        else:
            reader = PdfFileReader(io.BytesIO(xray), strict=False)
            writer.appendPagesFromReader(reader)
    if not writer: return "Tests couldn't printed"
    output = get_file_data_from_writer(writer)

    frappe.local.response.filename = "Test Result"
    frappe.local.response.filecontent = output #get_pdf(html)
    frappe.local.response.type = "pdf"

@frappe.whitelist()
def print_report_result(lab_test, with_header=False):
    test_doc = frappe.get_doc("Lab Test", lab_test)
    if not test_doc:
        frappe.throw("Lab Test not found")
    html = get_print_html_base()
    url = frappe.local.request.host
    #url = frappe.local.request.host
    head = f'<img class="img-header" src="http://josante-outpatient.erp/files/josante-logo.png" />' if with_header else None
    if frappe.local.conf.is_embassy:
        header = get_print_header_embassy(test_doc, head)
        tbody = get_print_tbody_embassy(test_doc, header, True)
    else:
        header = get_print_header(test_doc, head)
        tbody = get_print_tbody(test_doc, header, True)
    body = get_print_body(header, tbody)
    html = html.format(body=body,style=get_print_style())
    footer = get_lab_result_footer(test_doc)
    # if get_html:
    #     return html
    options = {  "--margin-left" : "0","--margin-right" : "0","--margin-bottom": "25mm", 
   "--footer-html" : footer, "quiet":"", "footer-center": "Page [page]/[topage]"}
    if not with_header:
        options['--margin-top'] = '45mm'
    output = pdfkit.from_string(html, False, options)
    uploaded_tests = get_uploaded_tests(test_doc, True)
    if len(uploaded_tests) > 0:
        output = get_uploaded_tests_with_content(uploaded_tests, output)
    frappe.local.response.filename = test_doc.patient_name + ".pdf" #"Test.pdf"
    frappe.local.response.filecontent =   output or ''#get_pdf(html)
    frappe.local.response.type = "pdf"


@frappe.whitelist()
def lab_test_result_selected(lab_test, selected_tests):
    # f = open("test-print.html", "r")
    # html  = f.read()
    # f.close()
    if selected_tests:
        selected_tests = json.loads(selected_tests)
    else: selected_tests = []
    if frappe.local.conf.is_embassy:
        embassy_test_result(lab_test, selected_tests=selected_tests)
        return
    test_doc = frappe.get_doc("Lab Test", lab_test)
    if not test_doc:
        frappe.throw("Lab Test not found")

    html = get_print_html_base()
    header = get_print_header(test_doc)

    document_status = "Released"
    if test_doc.status == 'Finalized':
        document_status = 'Finalized'
    footer, margin_bottom =  get_print_asset('lab_assets', 'Footer', test_doc.company, False, document_status=document_status)# get_lab_result_footer(test_doc)
    if footer:
        result_link = format_patient_result_link(test_doc)
        footer = frappe.render_template(footer, {"username":frappe.utils.get_fullname(), "result_link": result_link, "qrcode_gen": qrcode_gen})
    footer_link = get_asset_file(lab_test,footer)
    default_margin_top = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_top")
    default_margin_left = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_left")
    default_margin_right = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_right")
    default_margin_bottom = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_bottom")
    options = {"--margin-top" :  default_margin_top, "--margin-left" : default_margin_left,  "--margin-right" : default_margin_right,
                "margin-bottom": margin_bottom or default_margin_bottom, "--margin-bottom": margin_bottom or default_margin_bottom,
                "footer-html": footer_link, "footer-center": "Page [page]/[topage]",
    "quiet":""}
    
    tbody = get_print_tbody(test_doc, header, selected_tests=selected_tests)
    body = get_print_body(header, tbody)
    html = html.format(body=body,style=get_print_style())

    output = pdfkit.from_string(html, False, options)
    uploaded_tests = get_uploaded_tests(test_doc, True, selected_tests)
    if len(uploaded_tests) > 0:
        output = get_uploaded_tests_with_content(uploaded_tests, output)
    remove_asset(footer_link)
    frappe.local.response.filename = test_doc.patient_name + ".pdf"
    frappe.local.response.filecontent = output  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"


@frappe.whitelist()
def lab_test_result(lab_test, previous=None, only_finilized=False, head=None, return_html =False):
    # f = open("test-print.html", "r")
    # html  = f.read()
    # f.close()
    if frappe.local.conf.is_embassy:
        embassy_test_result(lab_test, only_finilized=only_finilized, head=head, previous=previous)
        return
    test_doc = frappe.get_doc("Lab Test", lab_test)
    if not test_doc:
        frappe.throw("Lab Test not found")
    html = get_print_html_base()
    margin_top = None
    if head:
        head = get_print_asset('lab_assets', 'Header', test_doc.company, False)
        if head:
            head, margin_top = head
    header = get_print_header(test_doc, head)
    document_status = "Released"
    if test_doc.status == 'Finalized' or only_finilized:
        document_status = 'Finalized'
    footer, margin_bottom =  get_print_asset('lab_assets', 'Footer', test_doc.company, False, document_status=document_status)# get_lab_result_footer(test_doc)
    if footer:
        result_link = format_patient_result_link(test_doc)
        footer = frappe.render_template(footer, {"username":frappe.utils.get_fullname(), "result_link": result_link, "qrcode_gen": qrcode_gen})
    footer_link = get_asset_file(lab_test,footer)
    tbody = get_print_tbody(test_doc, header, previous=previous, only_finalized=only_finilized)
    body = get_print_body(header, tbody)
    html = html.format(body=body,style=get_print_style(), footer='')
    # with open("testss.html", "w") as f:
    #     f.write(html)
    default_margin_top = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_top")
    default_margin_left = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_left")
    default_margin_right = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_right")
    default_margin_bottom = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_bottom")
    options = {"--margin-top" :margin_top or default_margin_top, "--margin-left" : default_margin_left,  "--margin-right" : default_margin_right,
                "margin-bottom": margin_bottom or default_margin_bottom, "--margin-bottom": margin_bottom or default_margin_bottom,
                "footer-html": footer_link, "footer-center": "Page [page]/[topage]",
    "quiet":""}
    output = pdfkit.from_string(html, False, options)
    uploaded_tests = get_uploaded_tests(test_doc, True)
    if not frappe.db.get_single_value("Healthcare Settings","print_empty_result"):
        if not tbody or tbody == "":
            output = None
    if len(uploaded_tests) > 0:
        output = get_uploaded_tests_with_content(uploaded_tests, output)
    remove_asset(footer_link)
    if return_html: return output
    frappe.local.response.filename = test_doc.patient_name + ".pdf"
    frappe.local.response.filecontent = output  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"

def format_patient_result_link(test_doc):
    patient_password = frappe.db.get_value("Patient", test_doc.patient, 'patient_password') or ''
    result_link = frappe.db.get_single_value("Healthcare Settings", 'result_url' ) or ''
    if not result_link.endswith('/'):
        result_link += '/'
    result_link += 'api/method/erpnext.api.patient_results?invoice=' + test_doc.name + '&password=' + patient_password
    return result_link

import os
def remove_asset(asset_link):
    os.remove(asset_link)
def get_asset_file(file_name, asset):
    with open(file_name + ".html", "w") as f:
        f.write(asset)
    return file_name + ".html"

@frappe.whitelist()
def embassy_test_result(lab_test, return_html = False, selected_tests=[], head=None, only_finilized=False, previous=None):
    test_doc = frappe.get_doc("Lab Test", lab_test)
    if not test_doc:
        frappe.throw("Lab Test not found")
    margin_top = None
    if head:
        head = get_print_asset('lab_assets', 'Header', test_doc.company, False)
        if head:
            head, margin_top = head
    html = get_print_html_base()
    header = get_print_header_embassy(test_doc, head)
    tbody = get_print_tbody_embassy(test_doc, header, selected_tests= selected_tests, previous=previous)
    body = get_print_body(header, tbody)
    html = html.format(body=body,style=get_print_style())
    # footer = get_lab_result_footer(test_doc)
    document_status = "Released"
    if test_doc.status == 'Finalized' or only_finilized:
        document_status = 'Finalized'
    footer, margin_bottom =  get_print_asset('lab_assets', 'Footer', test_doc.company, False, document_status=document_status)# get_lab_result_footer(test_doc)
    if footer:
        result_link = format_patient_result_link(test_doc)
        footer = frappe.render_template(footer, {"username":frappe.utils.get_fullname(), "result_link": result_link, "qrcode_gen": qrcode_gen})
    footer_link = get_asset_file(lab_test,footer)
    default_margin_top = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_top")
    default_margin_left = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_left")
    default_margin_right = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_right")
    default_margin_bottom = frappe.db.get_single_value("Healthcare Report Settings", "default_lab_margin_bottom")
    options = {"--margin-top" : margin_top or default_margin_top, "--margin-left" : default_margin_left,  "--margin-right" : default_margin_right,
                "margin-bottom": margin_bottom or default_margin_bottom, "--margin-bottom": margin_bottom or default_margin_bottom,
                "footer-html": footer_link, "footer-center": "Page [page]/[topage]",
    "quiet":""}
#     options = {"--margin-top" : "50mm", "--margin-left" : "0","--margin-right" : "0","--margin-bottom": "30mm", 
#    "--footer-html" : footer,
#     "quiet":""}
    pdf_content =  pdfkit.from_string( html, False, options)  or ''
    remove_asset(footer_link)
    if return_html: return pdf_content
    frappe.local.response.filename = test_doc.patient_name + ".pdf"#"Test.pdf"
    frappe.local.response.filecontent = pdf_content#get_pdf(html)
    frappe.local.response.type = "pdf"

def get_lab_result_footer(test_doc=None):
    html = f"""
        <table style="width:90%; margin: 0 auto; border-top: 1px solid;"><tr>
        <td style="width:20%;">
        Result Date/Time</td>
        <td >
            : { frappe.utils.get_datetime().strftime("%d/%m/%Y %r",)}
        </td>
        <td>Lab Director:</td>
        </tr>
        <tr>
            <td>
                User Name
            </td>
            <td colspan="2">
                : {frappe.utils.get_fullname()}
            </td>
        </tr>
        </table>
    """
    with open("footer.html", "w") as f:
        f.write(html)
    return "footer.html"

def get_print_header(test_doc, head=None):
    consultant = test_doc.practitioner_name or "Outpatient Doctor"
    payer_name, payer_label = "", ""
    if test_doc.show_payer_name:
        payer = frappe.db.get_value("Sales Invoice", test_doc.sales_invoice, ["insurance_party_type", "insurance_party"])
        if payer and payer[0] == "Payer": 
            payer_name = payer[1]
            payer_label = "Payer"
            
    if head:
        head= f"""
        <tr>
            <td colspan="4" style="text-align: center">{head}</td> 
        </tr>
        """
    else: head = ""
    return f"""
    <table class="b-bottom header f-s">
        {head}
        <tr >
            <td >
                 Patient Name
            </td>
            <td class="width-35 red">
                : <span class="rtl">{ test_doc.patient_name }</span>
            </td>
            <td>Age</td>
            <td class="width-35">: {test_doc.patient_age}</td>
        </tr>
         <tr>
            <td >
                 File No.
            </td>
            <td >
                : { test_doc.get_patient_file() }
            </td>
            <td >Gender</td>
            <td >: {test_doc.patient_sex}</td>
        </tr>
        <tr>
            <td >
                 Visit No.
            </td>
            <td >
                : { test_doc.sales_invoice }
            </td>
            <td >Sample Date</td>
            <td >: {  frappe.utils.get_datetime(test_doc.creation).strftime("%d/%m/%Y %r",)   }</td>
        </tr>
        <tr>
            <td >
                 Consultant
            </td>
            <td >
                : { consultant }
            </td>
            <td >{payer_label}</td>
            <td >{payer_name}</td>
        </tr>
    </table>
    """

def get_print_body(header, tbody):
    "        <thead>{header}</thead>"
    return tbody
    return f"""
    <table>
        <tbody>{tbody}</tbody>
    </table>
    """

def get_print_tbody(test_doc, header, only_finalized=False, selected_tests=[], previous=None):
    body = ""
    patient = frappe.get_doc("Patient", test_doc.patient)
    hematology_tests = get_hematology_tests(test_doc, only_finalized, selected_tests=selected_tests ,previous=previous)
    if len(hematology_tests) > 0:
        if len(body) > 0: body += get_break()
        body +=  format_hematology_tests(hematology_tests, header)
    chemistry_tests = get_chemistry_tests(test_doc, only_finalized, selected_tests=selected_tests, previous=previous, patient=patient)
    if len(chemistry_tests) > 0:
        if len(body) > 0: body += get_break()
        chemistry_table = format_chemistry_tests(chemistry_tests, header, patient=patient)
        body += chemistry_table
    routine_tests = get_routine_tests(test_doc, only_finalized, selected_tests=selected_tests, previous=previous)
    if len(routine_tests) > 0:
        if len(body) > 0: body += get_break()
        body +=  format_routine_tests(routine_tests, header)
    # if only_finalized:
    #     uploaded_tests = get_uploaded_tests(test_doc, only_finalized, selected_tests=selected_tests)
    #     if len(uploaded_tests) > 0:
            
    #         html = format_uploaded_tests(test_doc,uploaded_tests, header)
    #         if len(body) > 0 and len(html) > 0: body += get_break()
    #         body +=  html
    return body

def get_print_tbody_embassy(test_doc, header, only_finalized=False, selected_tests=[], previous=None):
    body = ""
    embassy_tests = get_embassy_tests(test_doc, only_finalized, selected_tests=selected_tests)
    
    if len(embassy_tests) > 0:
        embassy_table = format_embassy_tests(embassy_tests, header, previous=previous)
        body += embassy_table

    return body

def get_embassy_tests(test_doc, only_finalized=False, selected_tests=[]):
    tests = get_embassy_tests_items(test_doc.name, only_finalized, selected_tests=selected_tests)
    previous_tests = get_embassy_previous_tests(test_doc.name, test_doc.patient)
    #tests.sort(key=lambda x: x['order'])
    patient = frappe.get_doc("Patient", test_doc.patient)
    if patient:
        for test in tests:
            test['previous'] = previous_tests.get(test['template'])
            if test.get('custom_normal_range') and test.get('custom_normal_range') != "":
                test['template'] = parse_custom_normal_range(test.get('custom_normal_range'))
            else:
                test['template'] = filter_ranges(get_normal_ranges(test['template'], test_doc.creation, branch=test_doc.company), patient)
    else: test['template'] = []
    return tests


def format_embassy_tests(tests, header, previous_tests={}, previous=None):
    tests_html = ""
    test_num = 1
    for test in tests:
        normal_crit = ''
        normal_range = ''
        #previous_test = previous_tests.get()
        #print(test['template'])
        if test['template'] and len(test['template']) > 0 and not test['template'][0].get('hide_normal_range'):
            
            if len(test['template']) == 1:
                normal_crit = test['template'][0]['criteria_text'] or ''
            normal_range = test['template'][0]['range_text']
        previousResult = ""
        previousHeader = ""
        if previous:
            previousResult = f"""<td class="width-15 center">{test.get('previous') or ''}</td>"""
            previousHeader = '<td class="width-15 center">Previous Test</td>'
        if test['conv_result']:
            highlight = highlight_abnormal_result(test, test['template'])
            result = format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
            class_name = "highlight-result" if highlight else ""#(test['conv_result'] == "Positive" and test['lab_test_name'] != "Blood Rhesus") else "" 
            test_html = f"""
                <tr >
                <td class="width-40">{test['lab_test_name']}</td>
                <td class="width-5 f-s "></td>
                <td class="width-10 {class_name}">{result} </td>
                <td class="width-10 f-s ">{test['conv_uom'] or ''}</td>
                <td class="f-s width-10">{normal_crit}</td>
                <td class="f-s width-10">{normal_range}</td>
                {previousResult}
                </tr>
            """
            test_html = f"<tr><td ><table>" + test_html + "</table></td></tr>"
            tests_html+= test_html
            if test_num < 15 and test_num % 2 == 0:
                tests_html += "<tr><td>&nbsp;</td></tr>"
            test_num += 1
    html = f"""<table class="f-s">
        <thead>
        <tr>
            <td>{header}</td>
        </tr>
       <tr>
        <td class="b-bottom fb-1">
            <table>
             <tr>
            <td class="width-40">Test</td>
            <td class="width-10">Results</td>
            <td class="width-5"></td>
             <td colspan="2" class="width-20 center">Normal Range</td>
             {previousHeader}
        </tr>
            </table>
        </td>
       </tr>
           
        </thead>
        <tbody class=" fb-1">
           {tests_html}
        </tbody>
        <tfoot>
            <tr>
                <td colspan="8">&nbsp;</td>
            </tr>
        </tfoot>
    </table>"""
    return html


    
def get_routine_tests(test_doc, only_finalized=False, selected_tests=[], previous=None):
    tests = get_tests_by_item_group(test_doc, "Routine", only_finalized, selected_tests=selected_tests, previous=previous)
    patient = frappe.get_doc("Patient", test_doc.patient)
    if patient:
        for test in tests:
            if test.get('custom_normal_range') and test.get('custom_normal_range') != "":
                test['template'] = parse_custom_normal_range(test.get('custom_normal_range'))
            else:
                test['template'] = filter_ranges(get_normal_ranges(test['template'], test_doc.creation, branch=test_doc.company), patient)
    else: test['template'] = []
    new_tests = {}
    for item in tests:
        new_tests[item['parent_template']] = (new_tests.get(item['parent_template']) or []) + ([item])
    # new_tests = {item['parent_template']: (new_tests.get(item['parent_template']) or []) + ([item]) for item in tests}
    return new_tests

def format_routine_tests(tests, header):
    tests_html = ""
    for index, (key, value) in enumerate(tests.items()):
        if index > 0: tests_html += get_break()

        tests_html += format_routine_page_tests(value, header, key)
    
    return tests_html

def format_routine_page_tests(tests, header, test_name):
    tests_html = ""
    prev_tests_html = ""
    # tests.sort(key=lambda x: x['order'])
    microscopt_tests = ""
    prev_microscopt_tests = ""
    normal_test, test_count = "", 0
    prev_normal_test = ""
    prev_date = ""
    for test in tests:
        if test['conv_result']:
            highlight = highlight_abnormal_result(test, test['template'])
            highlight_class = "highlight-result" if highlight else ""
            if test['is_microscopy']:
                test_percentage = '<strong>' + format_float_result(test['result_percentage']) + "</strong> % &emsp;" if test['result_percentage'] else ""
                print_normal_range = True
                if test['template'] and len(test['template']) > 0: 
                    if test['template'][0].get('hide_normal_range'): print_normal_range = False
                test_html = f"""
                    <tr class="{highlight_class}">
                    <td class="width-20">{test['lab_test_name']}</td>
                    <td class="{'width-15' if test['conv_uom'] else 'width-40'}">{format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])}</td>
                    <td class="width-10"> {test['conv_uom'] or ''} </td>
                     <td class="width-50"> {test['template'][0]['range_text'] if test['template'] and print_normal_range else ''} </td>
                    </tr>
                """
                test_html = "<tr><td><table>" + test_html + "</table></td></tr>"
                microscopt_tests += test_html
                if test.get("prev_conv_result")  is not None:
                    prev_test_html = f"""
                        <tr>
                        <td class="width-20">{test['lab_test_name']}</td>
                        <td class="{'width-15' if test['prev_conv_uom'] else 'width-40'}">{format_float_result(test['prev_conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])}</td>
                        <td class="width-10"> {test['prev_conv_uom'] or ''} </td>
                        <td class="width-50"> {test['template'][0]['range_text'] if test['template'] and print_normal_range else ''} </td>
                        </tr>
                    """
                    prev_test_html = "<tr><td><table>" + prev_test_html + "</table></td></tr>"
                    prev_microscopt_tests += prev_test_html
                    prev_date = test['prev_creation']
            else:
                test_count += 1
                normal_test += f"""
                    <td class="width-20 {highlight_class}">{test['lab_test_name']}</td>
                    <td class="width-30 {highlight_class}">: {test['conv_result']}</td>
                """
                if test.get("prev_conv_result")  is not None:
                    prev_normal_test += f"""
                    <td class="width-20">{test['lab_test_name']}</td>
                    <td class="width-30">: {test['prev_conv_result']}</td>
                """
                    prev_date = test['prev_creation']
                if test_count == 2:
                    normal_test = "<tr>" + normal_test + "</tr>"
                    normal_test = "<tr><td><table>" + normal_test + "</table></td></tr>"
                    tests_html+= normal_test
                    normal_test = ""
                    test_count = 0
                    if test.get("prev_conv_result")  is not None:
                        prev_normal_test = "<tr>" + prev_normal_test + "</tr>"
                        prev_normal_test = "<tr><td><table>" + prev_normal_test + "</table></td></tr>"
                        prev_tests_html+= prev_normal_test
                        prev_normal_test = ""
    if test_count == 1:
        normal_test = "<tr>" + normal_test + "<td class='width-20'></td><td class='width-30'></td></tr>"
        normal_test = "<tr><td><table>" + normal_test + "</table></td></tr>"
        tests_html+= normal_test
        if prev_normal_test != "":
            prev_normal_test = "<tr>" + prev_normal_test + "<td class='width-20'></td><td class='width-30'></td></tr>"
            prev_normal_test = "<tr><td><table>" + prev_normal_test + "</table></td></tr>"
            prev_tests_html+= prev_normal_test

    if len(microscopt_tests) > 0:
        microscopt_tests = f"""  
        <tr>
            <td>
             <table>
           <tr>
             <td colspan="4" class="center title b-bottom b-top mt-20">MICROSCOPY</td>
           </tr>
           {microscopt_tests}

            </table>
        </td>
        </tr>
        """
    if len(prev_microscopt_tests) > 0:
        prev_microscopt_tests = f"""  
        <tr>
            <td>
             <table>
           <tr>
             <td colspan="4" class="center title b-bottom b-top mt-20">MICROSCOPY</td>
           </tr>
           {prev_microscopt_tests}

            </table>
        </td>
        </tr>
        """
    html = f"""<table class="f-s">
        <thead>
        <tr>
            <td>{header}</td>
        </tr>
        <tr>
            <td>
                 <table>
                <tr>
            <td colspan="4" class="center title b-bottom">{test_name}</td>

            </tr>
            </table>
            </td>
        </tr>
           
        </thead>
        <tbody>
           {tests_html}
           {microscopt_tests}
        </tbody>
    </table>"""
    if len(prev_tests_html) > 0 or len(prev_microscopt_tests) > 0:
        html += get_break()
        html += f"""<table class="f-s">
        <thead>
        <tr>
            <td>{header}</td>
        </tr>
        <tr>
            <td>
                 <table>
                <tr>
            <td colspan="4" class="center title b-bottom">{test_name} Result On {frappe.utils.get_datetime(prev_date).strftime("%d/%m/%Y",)}</td>

            </tr>
            </table>
            </td>
        </tr>
           
        </thead>
        <tbody>
           {prev_tests_html}
           {prev_microscopt_tests}
        </tbody>
    </table>"""
    return html

def get_hematology_tests(test_doc, only_finalized=False, selected_tests=[], previous=None):
    tests = get_tests_by_item_group(test_doc, "Hematology", only_finalized ,selected_tests=selected_tests, previous=previous)
    patient = frappe.get_doc("Patient", test_doc.patient)
    if patient:
        for test in tests:
            if test.get('custom_normal_range') and test.get('custom_normal_range') != "":
                test['template'] = parse_custom_normal_range(test.get('custom_normal_range'))
            else:
                test['template'] = filter_ranges(get_normal_ranges(test['template'], test_doc.creation, branch=test_doc.company), patient)
    else: test['template'] = []
    return tests


def format_hematology_tests(tests, header):
    tests_html = ""
    prev_tests_html = ""
    prev_date = ""
    diff= 0
    for test in tests:
        if test['conv_result']:
            highlight = highlight_abnormal_result(test, test['template'])
            highlight_class = "highlight-result" if highlight else ""
            prev_result= ""
            result = format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
            if test.get("prev_conv_result") is not None:
                prev_result = format_float_result(test['prev_conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
            precentage = ""
            secondary_result = ""
            prev_secondary_result = ""
            test_title = ""
            if diff == 1:
                test_title = """
                    <tr>
                        <td><table><tr><td class="diff">Differential</td></tr></table></td>
                    </tr>
                """
                diff=2
            if test['result_percentage']:
                secondary_result = format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
                precentage = "%"
                result = format_float_result(test['result_percentage'], 0)
                if  test.get('prev_result_percentage') is not None:
                    prev_secondary_result = format_float_result(test['prev_conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
                    prev_result = format_float_result(test['prev_result_percentage'], 0)
                    prev_date = test['prev_creation']
            elif diff == 2:
                result = format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
                if test.get("prev_conv_result")  is not None:
                    prev_result = format_float_result(test['prev_conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
            test_class = ""
            if test['lab_test_name'] == "Leukocytes":
                test_class = "border-line"
                diff = 1
            if test['control_type'] == "Free Text":
                test_html = f"""
                    <tr class="{highlight_class}">
                        <td class="width-25 hema-test">{test['lab_test_name']}</td>
                        <td class="f-s">{result} </td>
                    </tr>
                """
                if prev_result is not None and prev_result != "":
                    prev_test_html = f"""
                        <tr>
                            <td class="width-25 hema-test">{test['lab_test_name']}</td>
                            <td class="f-s">{prev_result} </td>
                        </tr>
                    """
            else:
                test_html = f"""
                    <tr class="{highlight_class}">
                    <td class="width-25 hema-test">{test['lab_test_name']}</td>
                    <td class="f-s width-10 fb">{result} </td>
                    <td class="width-5 f-s ">{precentage}</td>
                    <td class="width-10 f-s fb">{secondary_result}</td>
                    <td class="width-10 f-s ">{test['conv_uom'] or test['si_uom'] or ''}</td>
                    <td class="f-s width-40">&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;{test['template'][0]['range_text'] if test['template'] else ''}</td>

                    </tr>
                """
                if prev_result is not None and prev_result != "":
                    prev_test_html = f"""
                        <tr >
                        <td class="width-25 hema-test">{test['lab_test_name']}</td>
                        <td class="f-s width-10 fb">{prev_result} </td>
                        <td class="width-5 f-s ">{precentage}</td>
                        <td class="width-10 f-s fb">{prev_secondary_result}</td>
                        <td class="width-10 f-s ">{test['prev_conv_uom'] or test['prev_si_uom'] or ''}</td>
                        <td class="f-s width-40">&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;{test['template'][0]['range_text'] if test['template'] else ''}</td>

                        </tr>
                    """
            test_html = f"{test_title}<tr><td class='{test_class}'><table>" + test_html + "</table></td></tr>"
            if prev_result is not None and prev_result != "": prev_test_html = f"{test_title}<tr><td class='{test_class}'><table>" + prev_test_html + "</table></td></tr>"
            tests_html+= test_html
            if prev_result is not None and prev_result != "": prev_tests_html+= prev_test_html
    html = f"""<table>
        <thead>
        <tr>
            <td>{header}</td>
        </tr>
        <tr>
            <td>
                 <table>
                <tr>
            <td colspan="3" class="center title b-bottom">HEMATOLOGY</td>

            </tr>
            <tr>
                <td colspan="3" class="f-r f-s">Normal Range( Age and Sex releated)</td>
            </tr>
            </table>
            </td>
        </tr>
           
        </thead>
        <tbody>
           {tests_html}
        </tbody>
        <tfoot>
            <tr>
                <td colspan="8">&nbsp;</td>
            </tr>
        </tfoot>
    </table>"""
    if prev_tests_html:
        html += get_break()
        html += f"""<table>
        <thead>
        <tr>
            <td>{header}</td>
        </tr>
        <tr>
            <td>
                 <table>
                <tr>
            <td colspan="3" class="center title b-bottom">HEMATOLOGY Result On {frappe.utils.get_datetime(prev_date).strftime("%d/%m/%Y",)}</td>

            </tr>
            <tr>
                <td colspan="3" class="f-r f-s">Normal Range( Age and Sex releated)</td>
            </tr>
            </table>
            </td>
        </tr>
           
        </thead>
        <tbody>
           {prev_tests_html}
        </tbody>
        <tfoot>
            <tr>
                <td colspan="8">&nbsp;</td>
            </tr>
        </tfoot>
    </table>"""
    return html


def get_chemistry_tests(test_doc, only_finalized=False, selected_tests=[], previous=None, patient=None):
    tests = get_tests_by_item_group(test_doc, "Chemistry", only_finalized, selected_tests=selected_tests, previous=previous)
    #tests.sort(key=lambda x: x['order'])
    if patient:
        for test in tests:
            if test.get('custom_normal_range') and test.get('custom_normal_range') != "":
                test['template'] = parse_custom_normal_range(test.get('custom_normal_range'))
            else:
                if test['print_all_normal_ranges']:
                    test['template'] =  get_normal_ranges(test['template'], test_doc.creation, branch=test_doc.company)
                else:
                    test['template'] = filter_ranges(get_normal_ranges(test['template'], test_doc.creation, branch=test_doc.company), patient)
    else: test['template'] = []
    return tests
    
def get_uploaded_tests(test_doc, only_finalized=False, selected_tests=[], parent_type='Lab Test'):
    where_stmt = " lt.status IN ('Finalized', 'Released')"
    if only_finalized: where_stmt = " lt.status IN ('Finalized')"
    if len(selected_tests)> 0:
        selected_tests = ",".join(selected_tests)
        where_stmt += f" AND lt.name IN ({selected_tests})"
    tests = frappe.db.sql("""
        SELECT  lt.name as test_id, lt.lab_test_name, lt.result_value , lt.lab_test_comment as comment 
        FROM `tabNormal Test Result` as lt
         WHERE lt.parent='{test_name}' AND lt.parenttype='{parent_type}' AND {where_stmt} AND lt.result_value != "" AND lt.result_value IS NOT NULL AND lt.control_type='Upload File'
    """.format(test_name=test_doc.name, where_stmt=where_stmt, parent_type=parent_type), as_dict=True)
    return tests

def get_uploaded_tests_with_content(tests, result_content=None):
    writer = None
    counter = 0
    if result_content:
        writer = get_pdf_writer(result_content)
    for test in tests:
        counter += 1
        file_content = get_uploaded_test_content(test["result_value"])
        if not file_content: continue
        if not writer:
            writer = get_pdf_writer(file_content)
        if not result_content and counter > 1:
            reader = PdfFileReader(io.BytesIO(file_content), strict=False)
            writer.appendPagesFromReader(reader)
        if result_content:
            reader = PdfFileReader(io.BytesIO(file_content), strict=False)
            writer.appendPagesFromReader(reader)
    output = get_file_data_from_writer(writer)
    return output

def format_uploaded_tests(test_doc,tests, header=""):
    tests_html = ""
    result_url = frappe.db.get_single_value("Healthcare Settings", "result_url")
    password = frappe.db.get_value("Patient", test_doc.patient, ["patient_password"])
    if not result_url or result_url == "": return ""
    if result_url[-1] != "/": result_url += "/"
    for test in tests:
        test_html = f"""
            <tr>
                <td class="width-50">
                    &emsp;{test['lab_test_name']}
                </td>
                <td class="width-50"><a  href="{result_url}api/method/erpnext.healthcare.doctype.lab_test.lab_test_print.get_test_uploaded_files?lab_test={test_doc.name}&password={password}&test_name={test['test_id']}">Download Attachement</a></td>
            </tr>
        """
        if test['comment']:
            test_html += f"<tr><td colspan='2' class='red'><strong>Comment: </strong>{test['comment']}</td></tr>"
        test_html += "<tr><td colspan='2'><hr></td></tr>"
        test_html = "<tr><td><table>" + test_html + "</table></td></tr>"
        tests_html += test_html
    html = f"""<table>
        <thead>
        <tr>
            <td>{header}</td>
        </tr>
        <tr>
            <td>
                 <table>
                <tr>
            <th class="width-50">Test Name</th>
            <th class="width-25">Attachment Link</th>
            </tr>
            <tr>
                <td colspan="2"><hr></td>
            </tr>
            </table>
            </td>
        </tr>
           
        </thead>
        <tbody>
           {tests_html}
        </tbody>
    </table>"""
    return html

def format_float_result(result, point=2, round_digits=False):
    result = str(result)
    try:
        if result.startswith("+") or result.startswith("-"): return result
        if round_digits:
            if point != 0:
                return f"%.{point}f" % round(float(result), point)
            else:
                return int(round(float(result), point))
        else:
            if point != 0:
                return f"%.{point}f" % float(result)
            else:
                return int(float(result))
    except ValueError:
        return result

def format_chemistry_tests(tests, header="", patient=None):
    tests_html = ""
    grouped_tests = []
    for test in tests:
        if test['group_tests']:
            idx = next((index for (index, d) in enumerate(grouped_tests) if (type(d) == list and d[0]["parent_template"] == test['parent_template'])), -1)
            if idx >= 0:
                grouped_tests[idx].append(test)
            else:
                grouped_tests.append( [test])
        else:
            grouped_tests.append( test)
    for test in grouped_tests:
        if type(test) == list:
            test_html = ""
            for idx, child_test in enumerate(test):
                normal_ranges =  filter_ranges(child_test['template'], patient) if (child_test.get('print_all_normal_ranges') and child_test.get('highlight_abnormal_result')) else child_test['template']
                if idx == 0:
                    test_html = f"<tr><td colspan='3' >{child_test['parent_template']}</td></tr>" +test_html
                si = ""
                conv = ""
                prev_si = ""
                prev_conv = ""
                highlight = highlight_abnormal_result(child_test, normal_ranges)
                if child_test['si_result'] and child_test['si_uom']:
                    si =str(format_float_result(child_test['si_result'], child_test['si_round_digits'], child_test['round_si_digits']))+ ' ' + child_test['si_uom']
                if child_test['conv_result'] and child_test['conv_uom']:
                    conv = str(format_float_result(child_test['conv_result'], child_test['conventional_round_digits'], child_test['round_conventional_digits'])) + ' ' + child_test['conv_uom']
                # add previous results
                if child_test.get('prev_si_result') and child_test.get('prev_si_uom'):
                    prev_si =str(format_float_result(child_test['prev_si_result'], child_test['si_round_digits'], child_test['round_si_digits']))+ ' ' + child_test['prev_si_uom']
                if child_test.get('prev_conv_result') and child_test.get('prev_conv_uom'):
                    prev_conv = str(format_float_result(child_test['prev_conv_result'], child_test['conventional_round_digits'], child_test['round_conventional_digits'])) + ' ' + child_test['prev_conv_uom']
                
                if (child_test['si_result'] or child_test['conv_result'] ):
                    highlight_class = 'highlight-result' if highlight else ""
                    test_html += f"""
                        <tr class="{highlight_class}">
                            <td class="width-50">
                            &emsp;&emsp;{child_test['lab_test_name']}
                            </td>
                            <td class="width-25">{si}</td>
                            <td class="width-25">{conv}</td>
                        </tr>
                    """
                    if prev_si or prev_conv:
                        test_html += f"""
                            <tr>
                                <td class="width-50 blue">
                                &emsp;&emsp; Previous Result On {frappe.utils.get_datetime(child_test['prev_creation']).strftime("%d/%m/%Y",)}
                                </td>
                                <td class="width-25 blue">{prev_si}</td>
                                <td class="width-25 blue">{prev_conv}</td>
                            </tr>
                        """
                    for idx, normal in enumerate(child_test["template"]):
                        si_range = normal['si_range_text'] if child_test['si_uom'] else ''
                        conv_range = normal['range_text'] if child_test['conv_uom'] else ''
                        if idx == 0:
                            test_html += """<tr><td>&emsp;&emsp;&emsp;Normal Ranges: </td><td></td><td></td></tr>"""
                        test_html += f"""
                            <tr>
                                <td>&emsp;&emsp;&emsp;{normal['criteria_text'] or ''}</td>
                                <td>{si_range or ''}</td>
                                <td>{conv_range or ''}</td>
                            </tr>
                        """
                    if child_test['comment']:
                        test_html += f"<tr><td colspan='3' class='red'><strong>Comment: </strong>{child_test['comment']}</td></tr>"
            test_html = "<tr><td class='b-bottom' style='padding-bottom: 20px;'><table>" + test_html + "</table></td></tr>"
            tests_html += test_html

        else:
            normal_ranges =  filter_ranges(test['template'], patient) if (test.get('print_all_normal_ranges') and test.get('highlight_abnormal_result')) else test['template']
            test_html = ""
            si = ""
            conv = ""
            prev_si = ""
            prev_conv = ""
            print(test.get('print_all_normal_ranges') and test.get('highlight_abnormal_result'))
            highlight = highlight_abnormal_result(test, normal_ranges)
            if test['si_result'] and test['si_uom']:
                si =str(format_float_result(test['si_result'], test['si_round_digits'], test['round_si_digits']))+ ' ' + test['si_uom']
            if test['conv_result'] and test['conv_uom']:
                conv = str(format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])) + ' ' + test['conv_uom']
            
            # add previous results
            if test.get('prev_si_result') and test.get('prev_si_uom'):
                prev_si =str(format_float_result(test['prev_si_result'], test['si_round_digits'], test['round_si_digits']))+ ' ' + test['prev_si_uom']
            if test.get('prev_conv_result') and test.get('prev_conv_uom'):
                prev_conv = str(format_float_result(test['prev_conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])) + ' ' + test['prev_conv_uom']
            
            if (test['si_result'] or test['conv_result'] ):
                highlight_class = "highlight-result" if highlight else ""
                test_html += f"""
                    <tr class="{highlight_class}">
                        <td class="width-50">
                        &emsp;{test['lab_test_name']}
                        </td>
                        <td class="width-25">{si}</td>
                        <td class="width-25">{conv}</td>
                    </tr>
                """
                if prev_si or prev_conv:
                    test_html += f"""
                        <tr>
                            <td class="width-50 blue">
                            &emsp;&emsp; Previous Result On {frappe.utils.get_datetime(test['prev_creation']).strftime("%d/%m/%Y",)}
                            </td>
                            <td class="width-25 blue">{prev_si}</td>
                            <td class="width-25 blue">{prev_conv}</td>
                        </tr>
                    """
                normal_idx = 0
                for idx, normal in enumerate(test["template"]):
                    if normal.get('hide_normal_range'): 
                        normal_idx += 1
                        continue
                    si_range = normal['si_range_text'] if test['si_uom'] else ''
                    conv_range = normal['range_text'] if test['conv_uom'] else ''
                    if idx == normal_idx:
                        test_html += """<tr><td>&emsp;Normal Ranges: </td><td></td><td></td></tr>"""
                    test_html += f"""
                        <tr>
                            <td>&emsp;&emsp;{normal['criteria_text'] or ''}</td>
                            <td>{si_range or ''}</td>
                            <td>{conv_range or ''}</td>
                        </tr>
                    """
                if test['comment']:
                    test_html += f"<tr><td colspan='3' class='red'><strong>Comment: </strong>{test['comment']}</td></tr>"
                test_html = "<tr><td class='b-bottom' style='padding-bottom: 20px;'><table>" + test_html + "</table></td></tr>"
                tests_html += test_html
        
    html = f"""<table class="f-s">
        <thead>
        <tr>
            <td>{header}</td>
        </tr>
        <tr>
            <td class="b-bottom fh-1">
                 <table>
                <tr >
            <th class="width-50">Laboratory Result</th>
            <th class="width-25">SI Units</th>
            <th class="width-25">Conventional Units</th>
            </tr>
            </table>
            </td>
        </tr>
           
        </thead>
        <tbody class="fh-1">
           {tests_html}
        </tbody>
    </table>"""
    return html

def highlight_abnormal_result(test, normal_ranges):
    if not test.get('highlight_abnormal_result'): return False
    highlight = False
    for normal_range in normal_ranges:
        if normal_range.get('result_type') == 'Text':
            if (test['conv_result'] and test['conv_result'] ==  normal_range['range_text']) or (test['si_result'] and test['si_result'] ==  normal_range['si_range_text']) :
                if normal_range.get('range_type') == 'Abnormal':
                        return True
                else: return False
            else:
                if normal_range.get('range_type') == 'Abnormal':
                    highlight= False
                else:
                    highlight = True
        else:
            try:
                if test['conv_uom'] and (normal_range.get('range_from') != 0.0 or normal_range.get('range_to') != 0 ) and (normal_range.get('range_from') or normal_range.get('range_from') == 0) and (normal_range.get('range_to') or normal_range.get('range_to') == 0):
                    if  normal_range.get('range_from') <= float(test['conv_result']) and normal_range.get('range_to') >= float(test['conv_result']):
                        if normal_range.get('range_type') == 'Abnormal':
                            return True
                        else:
                            return False
                    else:
                        if normal_range.get('range_type') == 'Abnormal':
                            highlight= False
                        else:
                            highlight = True
                elif test['si_uom'] and (normal_range.get('min_si_value') != 0.0 or normal_range.get('max_si_value') != 0 ) and (normal_range.get('min_si_value') or normal_range.get('min_si_value') == 0) and (normal_range.get('max_si_value') or normal_range.get('max_si_value') == 0):
                    if  normal_range.get('min_si_value') <= float(test['si_result']) and normal_range.get('max_si_value') >= float(test['si_result']):
                        if normal_range.get('range_type') == 'Abnormal':
                            return True
                        else: return False
                    else:
                        if normal_range.get('range_type') == 'Abnormal':
                            highlight= False
                        else:
                            highlight = True
            except:
                continue
    return highlight

def get_tests_by_item_group(test_doc, item_group, only_finalized=False, selected_tests=[], previous=None):
    prev_join_stmt = ""
    prev_select_stmt = ""
    where_stmt = " lt.status IN ('Finalized', 'Released')"
    if only_finalized: where_stmt = " lt.status IN ('Finalized')"
    order = "tltt.order"
    previous = get_previous_approve(previous, item_group)
    if item_group == "Chemistry":
        item_group = "NOT IN ('Routine', 'Hematology')"
        order = "ltt.order"
    else:
        item_group = f"IN ('{item_group}')"
    if len(selected_tests)> 0:
        selected_tests = ",".join(selected_tests)
        where_stmt += f" AND lt.name IN ({selected_tests})"
    if previous:
        previous_tests = frappe.db.sql("""
        select name from `tabLab Test` where name <> "{test_name}" and patient="{patient_name}" and creation < "{creation}";
        """.format(test_name=test_doc.name, patient_name=test_doc.patient, creation=test_doc.creation))
        if len(previous_tests) > 0: 
            previous_tests = ",".join("'%s'" % tup[0] for tup in previous_tests)
            prev_join_stmt = f"""
            LEFT JOIN (SELECT trp.template ,trp.creation as prev_creation,
            trp.result_value as prev_conv_result,trp.lab_test_uom as prev_conv_uom,  trp.result_percentage as prev_result_percentage,
            trp.secondary_uom_result as prev_si_result, trp.secondary_uom as prev_si_uom, trp.custom_normal_range as prev_custom_normal_range
            FROM `tabNormal Test Result` as trp
            INNER JOIN (select template,max(creation) as creation
                from `tabNormal Test Result` WHERE  parent in ({previous_tests})
                and status IN ('Finalized')
                group by template) recent_tests
            ON trp.template=recent_tests.template
           and trp.creation = recent_tests.creation
                WHERE  trp.parent in ({previous_tests})
                and trp.status IN ('Finalized')
                ) as trp2
                ON  trp2.template=lt.template 
            """
            prev_select_stmt = """
            ,trp2.prev_creation, trp2.prev_conv_result, trp2.prev_conv_uom, trp2.prev_result_percentage, trp2.prev_si_result , trp2.prev_si_uom
            """


    return frappe.db.sql("""
        SELECT  
        lt.template, tltt.control_type, tltt.print_all_normal_ranges, tltt.lab_test_name,ltt.group_tests, lt.result_value as conv_result, lt.result_percentage ,lt.lab_test_uom as conv_uom, {order},
        lt.secondary_uom_result as si_result, lt.secondary_uom as si_uom, tltt.round_conventional_digits, tltt.round_si_digits, tltt.conventional_round_digits, tltt.si_round_digits, 
         lt.lab_test_comment as comment, ltt.lab_test_name as parent_template, tltt.is_microscopy, tltt.highlight_abnormal_result, lt.custom_normal_range
         {prev_select_stmt}
         FROM `tabNormal Test Result` as lt
        LEFT JOIN `tabLab Test Template` as ltt
        ON ltt.name=lt.report_code
        INNER JOIN `tabLab Test Template` as tltt
        ON tltt.name=lt.template
        {prev_join_stmt}
        WHERE lt.parent='{test_name}' AND ltt.lab_test_group {item_group}  AND {where_stmt} AND lt.result_value IS NOT NULL  AND lt.control_type !='Upload File'
        ORDER BY ltt.order, tltt.order
        """.format(test_name=test_doc.name, order= order, item_group=item_group, where_stmt=where_stmt, prev_join_stmt=prev_join_stmt, prev_select_stmt=prev_select_stmt), as_dict=True)

def get_previous_approve(previous, item_group):
    if not previous:return previous
    if item_group == 'Routine':
        return frappe.db.get_single_value("Healthcare Report Settings", "print_previous_routine")
    if item_group == 'Hematology':
        return frappe.db.get_single_value("Healthcare Report Settings", "print_previous_hematology")

    return previous

def get_embassy_previous_tests(test_name, patient):
    tests =  frappe.db.sql(f"""
        SELECT GROUP_CONCAT(lt.template SEPARATOR "/;/") as templates , GROUP_CONCAT(IFNULL(lt.result_value, '')  SEPARATOR "/;/") as results FROM `tabNormal Test Result` as lt
        INNER JOIN `tabLab Test` AS lt1 ON lt1.name=lt.parent
        WHERE lt.parent !="{test_name}" AND lt1.patient="{patient}"
       	GROUP BY lt1.name
        ORDER BY lt1.creation DESC
        LIMIT 1;
    """, as_dict=True)
    if len(tests) == 0:
        return {}
    
    test_templates = tests[0]['templates'].split("/;/")
    test_results = tests[0]['results'].split("/;/")
    if len(test_templates) != len(test_results): return {}
    tests = {template: result for template, result in zip(test_templates, test_results) }
    print(tests)
    return tests
def get_embassy_tests_items(test_name, only_finalized=False, selected_tests=[]):
    where_stmt = " lt.status IN ('Finalized', 'Released')"
    if only_finalized: where_stmt = " lt.status IN ('Finalized')"
    order = "tltt.order"
    if len(selected_tests)> 0:
        selected_tests = ",".join(selected_tests)
        where_stmt += f" AND lt.name IN ({selected_tests})"
    return frappe.db.sql("""
        SELECT  
        lt.template, tltt.lab_test_name, lt.result_value as conv_result, lt.result_percentage ,lt.lab_test_uom as conv_uom, {order},
        lt.secondary_uom_result as si_result, lt.secondary_uom as si_uom, tltt.round_si_digits, tltt.round_conventional_digits,tltt.conventional_round_digits, tltt.si_round_digits, lt.lab_test_comment as comment, ltt.lab_test_name as parent_template, tltt.is_microscopy,
        tltt.highlight_abnormal_result, lt.custom_normal_range
         FROM `tabNormal Test Result` as lt
        LEFT JOIN `tabLab Test Template` as ltt
        ON ltt.name=lt.report_code
        INNER JOIN `tabLab Test Template` as tltt
        ON tltt.name=lt.template
        WHERE lt.parent='{test_name}' AND lt.parenttype='Lab Test' AND {where_stmt} AND lt.result_value IS NOT NULL  AND lt.control_type !='Upload File'
        ORDER BY ltt.order,tltt.order
        """.format(test_name=test_name, order= order, where_stmt=where_stmt), as_dict=True)

@frappe.whitelist()
def preview_test_uploaded_files(test_name):
    file_link = frappe.db.sql(f"""
    SELECT tntr.result_value  FROM `tabNormal Test Result` tntr WHERE name="{test_name}" AND tntr.result_value IS NOT NULL AND tntr.result_value != ""
    """,as_dict=True)

    if len(file_link) > 0: file_link = file_link[0]['result_value']
    file_content = ""
    sub_dir =  ""  if file_link.startswith("/private") else "/public"
    with open(frappe.local.site + sub_dir + file_link, "rb") as f:
        file_content = f.read()
    #print(file_content)
    frappe.local.response.filename = file_link.split("/")[-1]
    frappe.local.response.filecontent = file_content  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"#file_link.split(".")[-1]

@frappe.whitelist(allow_guest=True)
def get_test_uploaded_files(lab_test, password, test_name):
    patient = frappe.db.get_value("Lab Test", lab_test, ["patient"])
    if not patient:
        frappe.throw("Test not found!")
    if not frappe.db.exists("Patient", {"name": patient, "patient_password": password}):
        frappe.throw("Test not found!")
    file_link = frappe.db.sql(f"""
    SELECT tntr.result_value  FROM `tabNormal Test Result` tntr WHERE name="{test_name}" AND parent="{lab_test}" AND tntr.result_value IS NOT NULL AND tntr.result_value != ""
    """,as_dict=True)
    if len(file_link) > 0: file_link = file_link[0]['result_value']
    #frappe.db.get_value("Noraml Test Result", {"name": test_name}, ["result_value"])
    print(file_link)
    print(frappe.local.site)
    file_content = ""
    sub_dir =  ""  if file_link.startswith("/private") else "/public"
    with open(frappe.local.site + sub_dir + file_link, "rb") as f:
        file_content = f.read()
    #print(file_content)
    frappe.local.response.filename = file_link.split("/")[-1]
    frappe.local.response.filecontent = file_content  or ''#get_pdf(html)
    frappe.local.response.type = "download"#file_link.split(".")[-1]

def get_uploaded_test_content(file_link):
    file_content = ""
    if not file_link.lower().endswith("pdf"): return False
    sub_dir =  ""  if file_link.startswith("/private") else "/public"
    try:
        with open(frappe.local.site + sub_dir + file_link, "rb") as f:
            file_content = f.read()
        return file_content
    except:
        return False


from PyPDF2 import PdfFileReader, PdfFileWriter
import io

def get_pdf_writer(filedata):
    reader = PdfFileReader(io.BytesIO(filedata), strict=False)
    writer = PdfFileWriter()
    writer.appendPagesFromReader(reader)
    
    return writer

@frappe.whitelist()
def print_all_reports(lab_test):
    sales_invoice = frappe.db.get_value("Lab Test", lab_test, "sales_invoice")
    result = embassy_test_result(lab_test, return_html=True)
    cover = get_embassy_cover(sales_invoice, return_html=True)
    xray = get_xray_report(sales_invoice, return_html=True)
    writer = get_pdf_writer(result)
    if xray and xray != "":
        reader = PdfFileReader(io.BytesIO(xray), strict=False)
        writer.appendPagesFromReader(reader)
    if cover and cover != "":
        reader = PdfFileReader(io.BytesIO(cover), strict=False)
        writer.appendPagesFromReader(reader)
    output = get_file_data_from_writer(writer)
    frappe.local.response.filename = "Test Result"
    frappe.local.response.filecontent = output #get_pdf(html)
    frappe.local.response.type = "pdf"

@frappe.whitelist()
def get_embassy_cover(sales_invoice, report_name="ksa_report", return_html=False):
    try:
        embassy_report = frappe.get_doc("Embassy Report", {"sales_invoice": sales_invoice})
        if not embassy_report: return ""
        html = frappe.render_template(f'templates/test_result/{report_name}.html', embassy_report.prepare_report_data())
        options = {"--margin-top" : "15mm", "--margin-left" : "10mm","--margin-right" : "10mm", "--margin-bottom": "10mm", "quiet":""}
        pdf_content =  pdfkit.from_string( html, False, options)  or ''

        if return_html: return pdf_content
        frappe.local.response.filename = report_name
        frappe.local.response.filecontent = pdf_content #get_pdf(html)
        frappe.local.response.type = "pdf"
    except:
        return ""


@frappe.whitelist()
def get_xray_report(sales_invoice, return_html = False, with_header=False):
    try:
        xray_test = frappe.get_doc("Radiology Test",{"sales_invoice": sales_invoice})
        if not xray_test: frappe.throw("No Radiology Test created with this invoice.")
        if xray_test.record_status != "Finalized" and xray_test.record_status != "Released": frappe.throw("Radiology test not finalized.")
        if len(xray_test.test_results) == 0: frappe.throw("Radiology test has no test result.")
        reports = { result.test_name: result.test_result for result in xray_test.test_results  if result.status != "Rejected"  }
        url = frappe.local.request.host
        header = format_xray_header(xray_test, with_header, url)
        html = get_print_html_base()
        if frappe.local.conf.is_embassy:
            tbody = get_embassy_xray_tbody(reports, header)
        else:
            tbody = get_normal_xray_tbody(reports, header)
        html = html.format(body=tbody,style=get_print_style())
        options = { "--margin-left" : "0","--margin-right" : "0",  "quiet":""}
        if not with_header:
            options["--margin-top" ] ="50mm"
        if xray_test.record_status == "Finalized":
            # options["--footer-html"] = "templates/xray_footer.html"
            # options["--margin-bottom"] = "20mm"
            footer =  get_print_asset('radiology_assets', 'Footer', xray_test.company, True, document_status='Finalized')
            if footer:
                if footer[0]:
                    options["--footer-html"] = footer[0]
                    options["--margin-bottom"] = footer[1] or "20mm"
        # with open("xray.html", "w") as f:
        #     f.write(html)
        pdf_content =  pdfkit.from_string( html, False, options)  or ''
        if return_html : return pdf_content
        frappe.local.response.filename = xray_test.patient_name + ".pdf"#"Test.pdf"
        frappe.local.response.filecontent = pdf_content#get_pdf(html)
        frappe.local.response.type = "pdf"
    except:
        return ""

def format_xray_header(xray_test, with_header=False, url=""):
    #visit_date = frappe.db.get_value("Sales Invoice", xray_test.sales_invoice, "creation")
    header= ""
    if with_header:
        header = f"""
            <tr>
            <td colspan="6" style="text-align: center"><img class="img-header" src="http://josante-outpatient.erp/files/josante-logo.png" /></td>
        </tr>
        """
    ages = xray_test.patient_age.split(" ")
    try:
        if int(ages[0]) > 0: age = " ".join(ages[:2])
        elif int(ages[2]) > 0: age = ages[2] + " " + ages[3]
        elif int(ages[4]) > 0: age = ages[4] + " " + ages[5]
        else:  age = " ".join(ages[:2])
    except:
        age = " ".join(ages[:2])
    
    if xray_test.get("finalize_date"): finalize_date = xray_test.get("finalize_date")
    elif xray_test.get("release_date"): finalize_date = xray_test.get("release_date")
    else: finalize_date = xray_test.modified

    if xray_test.get("release_date"): release_date = xray_test.get("release_date")
    else: release_date = xray_test.creation

    return f"""
    <table class="b-bottom header">
        {header}
        <tr class="center"><td colspan="6">Radiology Report</td> </tr>
        <tr class="">
            <td >
                 Patient Name
            </td>
            <td >
                : <span class="red rtl">{ xray_test.patient_name }</span>
            </td>
            <td>Age</td>
            <td >: {age}</td>
            <td>Gender</td>
            <td>: {xray_test.patient_sex}</td>
        </tr>
         <tr>
            <td >
                 Visit Date
            </td>
            <td >
                : { frappe.utils.get_datetime(release_date).strftime("%d/%m/%Y %r",) }
            </td>
            <td >Referring Physician</td>
            <td colspan="3">: {xray_test.practitioner_name or "" }</td>
        </tr>
        <tr>
            <td >
                Report Date
            </td>
            <td colspan="5">: {  frappe.utils.get_datetime(finalize_date).strftime("%d/%m/%Y %r",)   }</td>
        </tr>
    </table>
    """

#------------------------------------ASSETS--------------------------------------------

def get_print_asset(parent_field, asset_type, company, return_link=False, document_status='All'):
    user = frappe.session.user
    assets = frappe.db.sql("""
            SELECT ast.asset_link, ast.margin FROM `tabBranch User Print Format Asset` as ast
            WHERE parentfield=%(parent_field)s AND asset_type=%(asset_type)s AND company=%(company)s 
            AND (user IS NULL OR user='' OR user=%(user)s)
            AND document_status=%(document_status)s
            ORDER BY user 
    """,{"parent_field": parent_field, "asset_type": asset_type, 
         "company": company, "user": user, "document_status": document_status}, as_dict=True)
    if len(assets) == 0: return '', 0
    if return_link: return assets[0]['asset_link'], assets[0]['margin']
    file_content = ''
    with open(assets[0]['asset_link'], 'r') as f:
        file_content = f.read()
    return file_content, assets[0]['margin']

#----------------------------------------------------------------------------------------

def get_normal_xray_tbody(reports, header):
    html = ""
    for report in reports:
        if len(html) > 0:
            html += get_break()
        #         <tr class="center fb"><td> {report} </td></tr>

        body = f"""
            <tr><td>
                {reports[report]}
            </td></tr>
        """
        html += f"""
            <table class="xray-reports">
            <thead>
                <tr><td>{header}</td></tr>
            </thead>
            <tbody class="norm-line">
                {body}
            </tbody>
            </table>

        """
    return html


def get_embassy_xray_tbody(reports, header):
    body = ""
    for report in reports:
        body += f"""
            <tr><td>
                {reports[report]}
            </td></tr>
        """
    html = f"""
        <table>
        <thead>
            <tr><td>{header}</td></tr>
        </thead>
        <tbody class="fh-2">
            <tr class="center fb"><td> CHEST X-RAY REPORT </td></tr>
            {body}
        </tbody>
        </table>

    """
    return html


def get_print_html_base():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document</title>
        {style}
    </head>
    <body>
        {body}
    </body>
    </html>
    """

def get_print_header_embassy(test_doc, head=None):
    if head:
        head= f"""
        <tr>
            <td colspan="4" style="text-align: center">{head}</td>
        </tr>
        """
    else: head = ""
    return f"""
    <table class="b-bottom header f-s">
        {head}
        <tr >
            <td >
                 Patient Name
            </td>
            <td class="width-35">
                : <span class="red rtl">{ test_doc.patient_name }</span>
            </td>
            <td>Age</td>
            <td class="width-35">: {test_doc.patient_age}</td>
        <tr>
         <tr>
            <td >
                 File No.
            </td>
            <td >
                : { test_doc.get_patient_file() }
            </td>
            <td >Gender</td>
            <td >: {test_doc.patient_sex}</td>
        <tr>
        <tr>
            <td >
                 Visit No.
            </td>
            <td >
                : { test_doc.sales_invoice }
            </td>
            <td >Sample Date</td>
            <td >: {  frappe.utils.get_datetime(test_doc.creation).strftime("%d/%m/%Y %r",)   }</td>
        <tr>
    </table>
    """

import pyqrcode

def qrcode_gen(value, scale=3):
    qr = pyqrcode.create(value, error='M')
    return qr.png_as_base64_str(scale)


def get_break():
    return "<div class='break'> </div>"
def get_print_style():
    return """
    <style>
    .blue{
        color: #0000ff !important;
    }
    .header td{
        font-size: 17px;
    }
              table {
        width: 100%;
        text-align:left;
    }
    .fh-2{
        font-size: 20px;
    }
     .fh-1{
        font-size: 1.05em;
    }
    .fb-1{
        font-size: 1.05em;
    }
    td{
        padding-bottom: 4px;
    }
    .width-50{
        width:50%;
    }
    .width-5{
        width:5%;
    }
    .width-25{
        width: 25%;
    }
    .width-20{
        width: 20%;
    }
    .width-45{
        width: 45%;
    }
    .width-33{
        width: 33%;
    }
    .width-15{
         width: 15%;
    }
    .width-10{
         width: 10%;
    }
    .width-35{
         width: 35%;
    }
    .width-30{
         width: 30%;
    }
    .width-40{
         width: 40%;
    }
    .width-75{
         width: 75%;
    }
    .width-100{
        width: 100%;
    }
    .fb{
        font-weight: bold;
    }
    .red{
        color: red;
    }
    .header .red{
        font-size: 1.3em;
    }
    .b-bottom{
        border-bottom: 1px solid;
    }
    .norm-line p{
       margin: 5px;
    }
    .f-s{
         
            font-family: 'serif';
            font-size: .9em;
    }
    .f-r{
        text-align: right;
    }
    .title{
        font-size: 24px;
        padding: 0 !important;
    }
    .border-line{
        border-bottom: 1px solid;
        border-top: 1px solid;
        padding: 5px 0 2px 0 !important;
    }
    .center{
        text-align: center;
    }

            thead{
                display: table-header-group;
            }
            tfoot{
                display: table-footer-group;
            }
        .break {
            display:block; 
        clear:both; 
        page-break-after:always;
        
    }
    @media screen {
        body{
            padding: 10px 30px;
        }
    }
    .diff{
        text-decoration: underline;
    font-weight: bold;
    }
    .b-top{
        border-top: 1px solid;
    }
    
     .mt-20{
        margin-top: 20px;
     }
     .highlight-result{
        font-weight: bold;
        color: red;
     }
        </style>
    """

