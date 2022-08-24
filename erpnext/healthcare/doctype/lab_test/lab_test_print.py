from __future__ import unicode_literals
from asyncore import write

import frappe
from frappe.permissions import get_valid_perms
from frappe.utils.pdf import get_file_data_from_writer

def get_lab_test_result(patient_name, show_all_results, where_stmt=None):
    show_all_results = True if show_all_results == 1 else False
    if not where_stmt:
        where_stmt = "WHERE p.name='{patient_name}' AND lt.docstatus=1".format(patient_name=patient_name)
    limit_stmt = "" if show_all_results else "LIMIT 1"
    fields = [
        "p.patient_name", "lt.patient_age", "p.patient_number", "p.sex as patient_gender", 
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
            SELECT ntr.lab_test_name, ntr.result_value, ntr.result_percentage, ltu1.lab_test_uom, ntr.secondary_uom_result, ltu2.si_unit_name, 
            ntr.lab_test_comment, ntr.template, ltt.normal_range_label, ntr.report_code
            FROM `tabNormal Test Result` as ntr
            INNER JOIN `tabLab Test Template` as ltt
            ON ltt.name=ntr.template
            LEFT JOIN `tabLab Test UOM` as ltu1
            ON ltu1.name=ntr.lab_test_uom
            LEFT JOIN `tabLab Test UOM` as ltu2
            ON ltu2.name=ntr.secondary_uom
            WHERE ntr.parent='{test_name}' AND ntr.parenttype='Lab Test' AND ntr.status IN ('Finalized', 'Released')
        """.format(test_name=test["test_name"]), as_dict=True)

        results = {}
        for result in test["results"]:
            result['template'] = filter_ranges(get_normal_ranges(result['template']), patient)
            if result['report_code']:
                if not results.get(result['report_code']):
                    results[result['report_code']] = []
                results[result['report_code']].append(result)
        test["results"] = results
    return lab_tests

def map_test_report_code(test_results):
    results = {}
    return results

def get_normal_ranges(lab_test_template):
    return frappe.db.sql("""
    SELECT nr.range_type, nr.gender, nr.criteria_text, nr.range_text, nr.si_range_text, 
    nr.age_range, nr.from_age, nr.from_age_period, nr.to_age, nr.to_age_period
    FROM `tabAttribute Normal Range` as anr
    INNER JOIN `tabNormal Range` as nr ON nr.name = anr.normal_range_id
    WHERE anr.parent="{lab_test_template}" AND anr.parenttype='Lab Test Template' AND anr.range_type!='Machine Edge' AND (nr.effective_date IS NULL OR now() >nr.effective_date) AND (nr.expiry_date IS NULL OR now() < nr.expiry_date)
    """.format(lab_test_template=lab_test_template), as_dict=True)

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
    frappe.local.response.filename = "Test.pdf"
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
            reader = PdfFileReader(io.BytesIO(xray))
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
    head = f'<img class="img-header" src="http://{url}/files/josante-logo.png" />' if with_header else None
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
    frappe.local.response.filename = "Test.pdf"
    frappe.local.response.filecontent = pdfkit.from_string(html, False, options)  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"


@frappe.whitelist()
def lab_test_result(lab_test):
    # f = open("test-print.html", "r")
    # html  = f.read()
    # f.close()
    if frappe.local.conf.is_embassy:
        embassy_test_result(lab_test)
        return
    test_doc = frappe.get_doc("Lab Test", lab_test)
    if not test_doc:
        frappe.throw("Lab Test not found")
    html = get_print_html_base()
    header = get_print_header(test_doc)
    tbody = get_print_tbody(test_doc, header)
    body = get_print_body(header, tbody)
    html = html.format(body=body,style=get_print_style())
    footer = get_lab_result_footer(test_doc)
    options = {"--margin-top" : "45mm", "--margin-left" : "0","--margin-right" : "0","--margin-bottom": "25mm", 
   "--footer-html" : footer, "footer-center": "Page [page]/[topage]",
    "quiet":""}
    frappe.local.response.filename = "Test.pdf"
    frappe.local.response.filecontent = pdfkit.from_string(html, False, options)  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"


@frappe.whitelist()
def embassy_test_result(lab_test, return_html = False):
    test_doc = frappe.get_doc("Lab Test", lab_test)
    if not test_doc:
        frappe.throw("Lab Test not found")
    html = get_print_html_base()
    header = get_print_header_embassy(test_doc)
    tbody = get_print_tbody_embassy(test_doc, header)
    body = get_print_body(header, tbody)
    html = html.format(body=body,style=get_print_style())
    footer = get_lab_result_footer(test_doc)
    options = {"--margin-top" : "50mm", "--margin-left" : "0","--margin-right" : "0","--margin-bottom": "30mm", 
   "--footer-html" : footer,
    "quiet":""}
    pdf_content =  pdfkit.from_string( html, False, options)  or ''
    if return_html: return pdf_content
    frappe.local.response.filename = "Test.pdf"
    frappe.local.response.filecontent = pdf_content#get_pdf(html)
    frappe.local.response.type = "pdf"

def get_lab_result_footer(test_doc):
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
                : { test_doc.patient_name }
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
        <tr>
            <td >
                 Consultant
            </td>
            <td >
                : { consultant }
            </td>
            <td >{payer_label}</td>
            <td >{payer_name}</td>
        <tr>
    </table>
    """

def get_print_body(header, tbody):
    "        <thead>{header}</thead>"
    return f"""
    <table>
        <tbody>{tbody}</tbody>
    </table>
    """

def get_print_tbody(test_doc, header, only_finalized=False):
    body = ""
    hematology_tests = get_hematology_tests(test_doc, only_finalized)
    if len(hematology_tests) > 0:
        if len(body) > 0: body += get_break()
        body +=  format_hematology_tests(hematology_tests, header)
    chemistry_tests = get_chemistry_tests(test_doc, only_finalized)
    if len(chemistry_tests) > 0:
        if len(body) > 0: body += get_break()
        chemistry_table = format_chemistry_tests(chemistry_tests, header)
        body += chemistry_table
    routine_tests = get_routine_tests(test_doc, only_finalized)
    if len(routine_tests) > 0:
        if len(body) > 0: body += get_break()
        body +=  format_routine_tests(routine_tests, header)
    if only_finalized:
        uploaded_tests = get_uploaded_tests(test_doc, only_finalized)
        if len(uploaded_tests) > 0:
            
            html = format_uploaded_tests(test_doc,uploaded_tests, header)
            if len(body) > 0 and len(html) > 0: body += get_break()
            body +=  html
    return body

def get_print_tbody_embassy(test_doc, header, only_finalized=False):
    body = ""
    embassy_tests = get_embassy_tests(test_doc, only_finalized)
    
    if len(embassy_tests) > 0:
        embassy_table = format_embassy_tests(embassy_tests, header)
        body += embassy_table

    return body

def get_embassy_tests(test_doc, only_finalized=False):
    tests = get_embassy_tests_items(test_doc.name, only_finalized)
    previous_tests = get_embassy_previous_tests(test_doc.name, test_doc.patient)
    #tests.sort(key=lambda x: x['order'])
    patient = frappe.get_doc("Patient", test_doc.patient)
    if patient:
        for test in tests:
            test['previous'] = previous_tests.get(test['template'])
            test['template'] = filter_ranges(get_normal_ranges(test['template']), patient)
    else: test['template'] = []
    return tests


def format_embassy_tests(tests, header, previous_tests={}):
    tests_html = ""
    test_num = 1
    for test in tests:
        normal_crit = ''
        normal_range = ''
        #previous_test = previous_tests.get()
        #print(test['template'])
        if test['template'] and len(test['template']) > 0:
            
            if len(test['template']) == 1:
                normal_crit = test['template'][0]['criteria_text'] or ''
            normal_range = test['template'][0]['range_text']
        if test['conv_result']:
            result = format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
            test_html = f"""
                <tr >
                <td class="width-40">{test['lab_test_name']}</td>
                <td class="width-5 f-s "></td>
                <td class="width-10 ">{result} </td>
                <td class="width-10 f-s ">{test['conv_uom'] or ''}</td>
                <td class="f-s width-10">{normal_crit}</td>
                <td class="f-s width-10">{normal_range}</td>
                <td class="width-15 center">{test.get('previous') or ''}</td>
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
             <td class="width-15 center">Previous Test</td>
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


    
def get_routine_tests(test_doc, only_finalized=False):
    tests = get_tests_by_item_group(test_doc.name, "Routine", only_finalized)
    patient = frappe.get_doc("Patient", test_doc.patient)
    if patient:
        for test in tests:
            test['template'] = filter_ranges(get_normal_ranges(test['template']), patient)
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
    tests.sort(key=lambda x: x['order'])
    microscopt_tests = ""
    normal_test, test_count = "", 0
    for test in tests:
        if test['conv_result']:
            if test['is_microscopy']:
                test_percentage = '<strong>' + format_float_result(test['result_percentage']) + "</strong> % &emsp;" if test['result_percentage'] else ""
                test_html = f"""
                    <tr>
                    <td class="width-20">{test['lab_test_name']}</td>
                    <td class="{'width-15' if test['conv_uom'] else 'width-40'} red"><strong>{format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])}</strong></td>
                    <td class="width-10"> {test['conv_uom'] or ''} </td>
                     <td class="width-50"> {test['template'][0]['range_text'] if test['template'] else ''} </td>
                    </tr>
                """
                test_html = "<tr><td><table>" + test_html + "</table></td></tr>"
                microscopt_tests += test_html
            else:
                test_count += 1
                normal_test += f"""
                    <td class="width-20">{test['lab_test_name']}</td>
                    <td class="width-30"><strong>: {test['conv_result']}</strong></td>
                """
                if test_count == 2:
                    normal_test = "<tr>" + normal_test + "</tr>"
                    normal_test = "<tr><td><table>" + normal_test + "</table></td></tr>"
                    tests_html+= normal_test
                    normal_test = ""
                    test_count = 0
    if test_count == 1:
        normal_test = "<tr>" + normal_test + "<td class='width-20'></td><td class='width-30'></td></tr>"
        normal_test = "<tr><td><table>" + normal_test + "</table></td></tr>"
        tests_html+= normal_test

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
    return html

def get_hematology_tests(test_doc, only_finalized=False):
    tests = get_tests_by_item_group(test_doc.name, "Hematology", only_finalized)
    patient = frappe.get_doc("Patient", test_doc.patient)
    if patient:
        for test in tests:
            test['template'] = filter_ranges(get_normal_ranges(test['template']), patient)
    else: test['template'] = []
    return tests


def format_hematology_tests(tests, header):
    tests_html = ""
    tests.sort(key=lambda x: x['order'])
    diff= 0
    for test in tests:
        if test['conv_result']:
            result = format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
            precentage = ""
            secondary_result = ""
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
            elif diff == 2:
                result = format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])
            test_class = ""
            if test['lab_test_name'] == "Leukocytes":
                test_class = "border-line"
                diff = 1
            if test['control_type'] == "Free Text":
                test_html = f"""
                    <tr>
                        <td class="width-25 hema-test">{test['lab_test_name']}</td>
                        <td class="f-s">{result} </td>
                    </tr>
                """
            else:
                test_html = f"""
                    <tr >
                    <td class="width-25 hema-test">{test['lab_test_name']}</td>
                    <td class="f-s width-10 fb">{result} </td>
                    <td class="width-5 f-s ">{precentage}</td>
                    <td class="width-10 f-s fb">{secondary_result}</td>
                    <td class="width-10 f-s ">{test['conv_uom'] or test['si_uom'] or ''}</td>
                    <td class="f-s width-40">&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;{test['template'][0]['range_text'] if test['template'] else ''}</td>

                    </tr>
                """
            test_html = f"{test_title}<tr><td class='{test_class}'><table>" + test_html + "</table></td></tr>"
            tests_html+= test_html
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
    return html


def get_chemistry_tests(test_doc, only_finalized=False):
    tests = get_tests_by_item_group(test_doc.name, "Chemistry", only_finalized)
    tests.sort(key=lambda x: x['order'])
    patient = frappe.get_doc("Patient", test_doc.patient)
    if patient:
        for test in tests:
            if test['print_all_normal_ranges']:
                test['template'] =  get_normal_ranges(test['template'])
            else:
                test['template'] = filter_ranges(get_normal_ranges(test['template']), patient)
    else: test['template'] = []
    return tests
    
def get_uploaded_tests(test_doc, only_finalized=False):
    where_stmt = " lt.status IN ('Finalized', 'Released')"
    if only_finalized: where_stmt = " lt.status IN ('Finalized')"
    tests = frappe.db.sql("""
        SELECT  lt.name as test_id, lt.lab_test_name, lt.result_value , lt.lab_test_comment as comment 
        FROM `tabNormal Test Result` as lt
         WHERE lt.parent='{test_name}' AND lt.parenttype='Lab Test' AND {where_stmt} AND lt.result_value != "" AND lt.result_value IS NOT NULL AND lt.control_type='Upload File'
    """.format(test_name=test_doc.name, where_stmt=where_stmt), as_dict=True)
    return tests


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

def format_chemistry_tests(tests, header=""):
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
                if idx == 0:
                    test_html = f"<tr><td colspan='3' >{child_test['parent_template']}</td></tr>" +test_html
                si = ""
                conv = ""
                if child_test['si_result'] and child_test['si_uom']:
                    si =str(format_float_result(child_test['si_result'], child_test['si_round_digits'], child_test['round_si_digits']))+ ' ' + child_test['si_uom']
                if child_test['conv_result'] and child_test['conv_uom']:
                    conv = str(format_float_result(child_test['conv_result'], child_test['conventional_round_digits'], child_test['round_conventional_digits'])) + ' ' + child_test['conv_uom']
                if (child_test['si_result'] or child_test['conv_result'] ):

                    test_html += f"""
                        <tr>
                            <td class="width-50">
                            &emsp;&emsp;{child_test['lab_test_name']}
                            </td>
                            <td class="width-25">{si}</td>
                            <td class="width-25">{conv}</td>
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
            test_html = ""
            si = ""
            conv = ""
            if test['si_result'] and test['si_uom']:
                si =str(format_float_result(test['si_result'], test['si_round_digits'], test['round_si_digits']))+ ' ' + test['si_uom']
            if test['conv_result'] and test['conv_uom']:
                conv = str(format_float_result(test['conv_result'], test['conventional_round_digits'], test['round_conventional_digits'])) + ' ' + test['conv_uom']
            if (test['si_result'] or test['conv_result'] ):

                test_html += f"""
                    <tr>
                        <td class="width-50">
                        &emsp;{test['lab_test_name']}
                        </td>
                        <td class="width-25">{si}</td>
                        <td class="width-25">{conv}</td>
                    </tr>
                """
                for idx, normal in enumerate(test["template"]):
                    si_range = normal['si_range_text'] if test['si_uom'] else ''
                    conv_range = normal['range_text'] if test['conv_uom'] else ''
                    if idx == 0:
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

def get_tests_by_item_group(test_name, item_group, only_finalized=False):
    where_stmt = " lt.status IN ('Finalized', 'Released')"
    if only_finalized: where_stmt = " lt.status IN ('Finalized')"
    order = "tltt.order"
    if item_group == "Chemistry":
        item_group = "NOT IN ('Routine', 'Hematology')"
        order = "ltt.order"
    else:
        item_group = f"IN ('{item_group}')"
    return frappe.db.sql("""
        SELECT  
        lt.template, tltt.control_type, tltt.print_all_normal_ranges, tltt.lab_test_name,ltt.group_tests, lt.result_value as conv_result, lt.result_percentage ,ctu.lab_test_uom as conv_uom, {order},
        lt.secondary_uom_result as si_result, stu.si_unit_name as si_uom, tltt.round_conventional_digits, tltt.round_si_digits, tltt.conventional_round_digits, tltt.si_round_digits,  lt.lab_test_comment as comment, ltt.lab_test_name as parent_template, tltt.is_microscopy
         FROM `tabNormal Test Result` as lt
        LEFT JOIN `tabLab Test Template` as ltt
        ON ltt.name=lt.report_code
        INNER JOIN `tabLab Test Template` as tltt
        ON tltt.name=lt.template
        LEFT JOIN `tabLab Test UOM` as ctu
        ON ctu.name=lt.lab_test_uom
        LEFT JOIN `tabLab Test UOM` as stu
        ON stu.name=lt.secondary_uom

        WHERE lt.parent='{test_name}' AND lt.parenttype='Lab Test' AND ltt.lab_test_group {item_group}  AND {where_stmt} AND lt.result_value IS NOT NULL  AND lt.control_type !='Upload File'
        """.format(test_name=test_name, order= order, item_group=item_group, where_stmt=where_stmt), as_dict=True)

def get_embassy_previous_tests(test_name, patient):
    tests =  frappe.db.sql(f"""
        SELECT GROUP_CONCAT(lt.template SEPARATOR "/;/") as templates , GROUP_CONCAT(IFNULL(lt.result_value, '')  SEPARATOR "/;/") as results FROM `tabNormal Test Result` as lt
        INNER JOIN `tabLab Test` AS lt1 ON lt1.name=lt.parent
        WHERE lt.parent !='{test_name}' AND lt1.patient='{patient}'
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
def get_embassy_tests_items(test_name, only_finalized=False):
    where_stmt = " lt.status IN ('Finalized', 'Released')"
    if only_finalized: where_stmt = " lt.status IN ('Finalized')"
    order = "tltt.order"
    
    return frappe.db.sql("""
        SELECT  
        lt.template, tltt.lab_test_name, lt.result_value as conv_result, lt.result_percentage ,ctu.lab_test_uom as conv_uom, {order},
        lt.secondary_uom_result as si_result, stu.si_unit_name as si_uom, tltt.round_si_digits, tltt.round_conventional_digits,tltt.conventional_round_digits, tltt.si_round_digits, lt.lab_test_comment as comment, ltt.lab_test_name as parent_template, tltt.is_microscopy
         FROM `tabNormal Test Result` as lt
        LEFT JOIN `tabLab Test Template` as ltt
        ON ltt.name=lt.report_code
        INNER JOIN `tabLab Test Template` as tltt
        ON tltt.name=lt.template
        LEFT JOIN `tabLab Test UOM` as ctu
        ON ctu.name=lt.lab_test_uom
        LEFT JOIN `tabLab Test UOM` as stu
        ON stu.name=lt.secondary_uom
        WHERE lt.parent='{test_name}' AND lt.parenttype='Lab Test' AND {where_stmt} AND lt.result_value IS NOT NULL  AND lt.control_type !='Upload File'
        ORDER BY ltt.order,tltt.order
        """.format(test_name=test_name, order= order, where_stmt=where_stmt), as_dict=True)

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

from PyPDF2 import PdfFileReader, PdfFileWriter
import io

def get_pdf_writer(filedata):
    reader = PdfFileReader(io.BytesIO(filedata))
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
        reader = PdfFileReader(io.BytesIO(xray))
        writer.appendPagesFromReader(reader)
    if cover and cover != "":
        reader = PdfFileReader(io.BytesIO(cover))
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
        reports = { result.test_name: result.test_result for result in xray_test.test_results }
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
        pdf_content =  pdfkit.from_string( html, False, options)  or ''
        if return_html : return pdf_content
        frappe.local.response.filename = "Test.pdf"
        frappe.local.response.filecontent = pdf_content#get_pdf(html)
        frappe.local.response.type = "pdf"
    except:
        return ""

def format_xray_header(xray_test, with_header=False, url=""):
    visit_date = frappe.db.get_value("Sales Invoice", xray_test.sales_invoice, "creation")
    header= ""
    if with_header:
        header = f"""
            <tr>
            <td colspan="6" style="text-align: center"><img class="img-header" src="http://{url}/files/josante-logo.png" /></td>
        </tr>
        """
    return f"""
    <table class="b-bottom header f-s">
        {header}
        <tr class="center fb"><td colspan="6">Radiology Report</td> </tr>
        <tr class="fb">
            <td >
                 Patient Name
            </td>
            <td >
                : <span class="red">{ xray_test.patient_name }</span>
            </td>
            <td>Age</td>
            <td >: {" ".join(xray_test.patient_age.split(" ")[:2])}</td>
            <td>Gender</td>
            <td>: {xray_test.patient_sex}</td>
        <tr>
         <tr>
            <td >
                 Visit Date
            </td>
            <td >
                : { frappe.utils.get_datetime(visit_date).strftime("%d/%m/%Y %r",) }
            </td>
            <td >Referring Physician</td>
            <td colspan="3">: {xray_test.practitioner_name or "" }</td>
        <tr>
        <tr>
            <td >
                Report Date
            </td>
            <td colspan="5">: {  frappe.utils.get_datetime().strftime("%d/%m/%Y %r",)   }</td>
        <tr>
    </table>
    """


def get_normal_xray_tbody(reports, header):
    html = ""
    for report in reports:
        if len(html) > 0:
            html += get_break()
        body = f"""
        <tr class="center fb"><td> {report} </td></tr>
            <tr><td>
                {reports[report]}
            </td></tr>
        """
        html += f"""
            <table>
            <thead>
                <tr><td>{header}</td></tr>
            </thead>
            <tbody class="fh-2">
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
                : <span class="red">{ test_doc.patient_name }</span>
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

def get_break():
    return "<div class='break'> </div>"
def get_print_style():
    return """
    <style>
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
        </style>
    """

