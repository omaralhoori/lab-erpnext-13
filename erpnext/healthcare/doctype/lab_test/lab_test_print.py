from __future__ import unicode_literals
from cgi import test
from imghdr import tests
from colorama import Style

import frappe
from frappe.permissions import get_valid_perms

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
    WHERE anr.parent='{lab_test_template}' AND anr.parenttype='Lab Test Template' AND anr.range_type!='Machine Edge' AND (nr.effective_date IS NULL OR now() >nr.effective_date) AND (nr.expiry_date IS NULL OR now() < nr.expiry_date)
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
                from_days =  int(range['from_age']) * 25
            else:
                from_days =  int(range['from_age']) * 330   
            if range['to_age_period'] == 'Day(s)':
                to_days = int(range['to_age'])
            elif range['to_age_period'] == 'Month(s)':
                to_days =  int(range['to_age']) * 25
            else:
                to_days =  int(range['to_age']) * 330
            return patient_days > from_days and patient_days < to_days
    return True

def compare_age(age_period, age_range, dob):
    pass

def filter_ranges(ranges, patient):
    ranges = list(filter(lambda range: filter_range_by_gender(range, patient), ranges ))
    ranges = list(filter(lambda range: filter_range_by_age(range, patient), ranges ))
    return ranges


import pdfkit
@frappe.whitelist(allow_guest=True)
def user_test_result(lab_test, get_html=True):
    # f = open("test-print.html", "r")
    # html  = f.read()
    # f.close()
    test_doc = frappe.get_doc("Lab Test", lab_test)
    if not test_doc:
        frappe.throw("Lab Test not found")
    html = get_print_html_base()
    header = get_print_header(test_doc)
    tbody = get_print_tbody(test_doc, header, True)
    body = get_print_body(header, tbody)
    html = html.format(body=body,style=get_print_style())

    if get_html:
        return html
    options = {"--margin-top" : "40mm", "--margin-bottom": "20mm", "quiet":""}
    frappe.local.response.filename = "Test.pdf"
    frappe.local.response.filecontent = pdfkit.from_string(html, False, options)  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"


@frappe.whitelist()
def lab_test_result(lab_test):
    # f = open("test-print.html", "r")
    # html  = f.read()
    # f.close()
    test_doc = frappe.get_doc("Lab Test", lab_test)
    if not test_doc:
        frappe.throw("Lab Test not found")
    html = get_print_html_base()
    header = get_print_header(test_doc)
    tbody = get_print_tbody(test_doc, header)
    body = get_print_body(header, tbody)
    html = html.format(body=body,style=get_print_style())
    options = {"--margin-top" : "40mm", "--margin-bottom": "20mm", "quiet":""}
    frappe.local.response.filename = "Test.pdf"
    frappe.local.response.filecontent = pdfkit.from_string(html, False, options)  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"

def get_print_header(test_doc):
    consultant = test_doc.practitioner_name or "Outpatient Doctor"
    return f"""
    <table>
        <tr>
            <td class="width-15">
                 Patient Name
            </td>
            <td class="width-35">
                : <span class="red">{ test_doc.patient_name }</span>
            </td>
            <td class="width-15">Age</td>
            <td class="width-35">: {test_doc.patient_age}</td>
        <tr>
         <tr>
            <td class="width-15">
                 File No.
            </td>
            <td class="width-35">
                : { test_doc.get_patient_file() }
            </td>
            <td class="width-15">Gender</td>
            <td class="width-35">: {test_doc.patient_sex}</td>
        <tr>
        <tr>
            <td class="width-15">
                 Visit No.
            </td>
            <td class="width-35">
                : { test_doc.sales_invoice }
            </td>
            <td class="width-15">External No.</td>
            <td class="width-35">: </td>
        <tr>
        <tr>
            <td class="width-15">
                 Consultant
            </td>
            <td class="width-35">
                : { consultant }
            </td>
            <td class="width-15">Sample Date</td>
            <td class="width-35">: {  frappe.utils.get_datetime(test_doc.creation).strftime("%d/%m/%Y %r",)   }</td>
        <tr>
    </table>
    <hr / >
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
    chemistry_tests = get_chemistry_tests(test_doc, only_finalized)
    if len(chemistry_tests) > 0:
        chemistry_table = format_chemistry_tests(chemistry_tests, header)
        body += chemistry_table
    hematology_tests = get_hematology_tests(test_doc, only_finalized)
    if len(hematology_tests) > 0:
        if len(body) > 0: body += get_break()
        body +=  format_hematology_tests(hematology_tests, header)
    routine_tests = get_routine_tests(test_doc, only_finalized)
    if len(routine_tests) > 0:
        if len(body) > 0: body += get_break()
        body +=  format_routine_tests(routine_tests, header)
    return body

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
    for test in tests:
        if test['conv_result']:
            test_percentage = '<strong>' + format_float_result(test['result_percentage']) + "</strong> % &emsp;" if test['result_percentage'] else ""
            test_html = f"""
                <tr>
                <td class="width-25">{test['lab_test_name']}</td>
                <td class="width-75">{test_percentage}<strong>{format_float_result(test['conv_result'])}</strong>&emsp;{test['conv_uom'] or ''} &emsp;&emsp;{test['template'][0]['range_text'] if test['template'] else ''}</td>
                </tr>
            """
            test_html = "<tr><td><table>" + test_html + "</table></td></tr>"
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
            <th colspan="4" class="center"><strong>{test_name}</strong></th>

            </tr>
            <tr>
                <td colspan="4"><hr></td>
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
    for test in tests:
        if test['conv_result']:
            test_percentage = '<strong>' + format_float_result(test['result_percentage']) + "</strong> % &emsp;" if test['result_percentage'] else ""
            test_html = f"""
                <tr>
                <td class="width-33">{test['lab_test_name']}</td>
                <td class="width-33">{test_percentage}<strong>{format_float_result(test['conv_result'])}</strong>&emsp;{test['conv_uom'] or ''}</td>
                    <td class="width-33">&emsp;&emsp;{test['template'][0]['range_text'] if test['template'] else ''}</td>

                </tr>
            """
            test_html = "<tr><td><table>" + test_html + "</table></td></tr>"
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
            <th colspan="3" class="center"><strong>HEMATOLOGY</strong></th>

            </tr>
            <tr>
                <td colspan="3"><hr></td>
            </tr>
            <tr>
                <td class="width-33" ></td>
                <td class="width-33"></td>
                <td class="width-33 ">Normal Range( Age and Sex releated )</td>
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

def get_chemistry_tests(test_doc, only_finalized=False):
    tests = get_tests_by_item_group(test_doc.name, "Chemistry", only_finalized)
    patient = frappe.get_doc("Patient", test_doc.patient)
    if patient:
        for test in tests:
            test['template'] = filter_ranges(get_normal_ranges(test['template']), patient)
    else: test['template'] = []
    return tests
    
def format_float_result(result):
    try:
        return "%.2f" % float(result)
    except ValueError:
        return result

def format_chemistry_tests(tests, header=""):
    tests_html = ""
    for test in tests:
        test_html = ""
        si = ""
        conv = ""
        if test['si_result'] and test['si_uom']:
            si =format_float_result(test['si_result'])+ ' ' + test['si_uom']
        if test['conv_result'] and test['conv_uom']:
            conv = format_float_result(test['conv_result']) + ' ' + test['conv_uom']
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
                        <td>&emsp;&emsp;{normal['criteria_text']}</td>
                        <td>{si_range or ''}</td>
                        <td>{conv_range or ''}</td>
                    </tr>
                """
            if test['comment']:
                test_html += f"<tr><td colspan='3' class='red'><strong>Comment: </strong>{test['comment']}</td></tr>"
            test_html += "<tr><td colspan='3'><hr></td></tr>"
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
            <th class="width-50">Laboratory Result</th>
            <th class="width-25">SI Units</th>
            <th class="width-25">Conventional Units</th>
            </tr>
            <tr>
                <td colspan="3"><hr></td>
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

def get_tests_by_item_group(test_name, item_group, only_finalized=False):
    where_stmt = " lt.status IN ('Finalized', 'Released')"
    if only_finalized: where_stmt = " lt.status IN ('Finalized')"
    return frappe.db.sql("""
        SELECT  
        lt.template, lt.lab_test_name, lt.result_value as conv_result, lt.result_percentage ,ctu.lab_test_uom as conv_uom, tltt.order,
        lt.secondary_uom_result as si_result, stu.si_unit_name as si_uom, lt.lab_test_comment as comment, ltt.lab_test_name as parent_template
         FROM `tabNormal Test Result` as lt
        LEFT JOIN `tabLab Test Template` as ltt
        ON ltt.name=lt.report_code
        INNER JOIN `tabLab Test Template` as tltt
        ON tltt.name=lt.template
        LEFT JOIN `tabLab Test UOM` as ctu
        ON ctu.name=lt.lab_test_uom
        LEFT JOIN `tabLab Test UOM` as stu
        ON stu.name=lt.secondary_uom

        WHERE lt.parent='{test_name}' AND lt.parenttype='Lab Test' AND ltt.lab_test_group="{item_group}" AND {where_stmt}
        """.format(test_name=test_name, item_group=item_group, where_stmt=where_stmt), as_dict=True)

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
def get_break():
    return "<div class='break'> </div>"
def get_print_style():
    return """
    <style>
    
              table {
        width: 100%;
        text-align:left;
    }
    td{
        padding-bottom: 8px;
    }
    .width-50{
        width:50%;
    }
    .width-25{
        width: 25%;
    }
    .width-33{
        width: 33%;
    }
    .width-15{
         width: 15%;
    }
    .width-35{
         width: 35%;
    }
    .width-75{
         width: 75%;
    }
    .width-100{
        width: 100%;
    }
    .red{
        color: red;
    }
    .b-bottom{
        border-bottom: 1px solid;
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
        </style>
    """

