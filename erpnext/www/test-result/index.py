import frappe
import pdfkit
import tempfile
import os
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

def get_lab_test_result(patient_name, show_all_results):
    show_all_results = True if show_all_results == 1 else False

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
            SELECT ntr.lab_test_name, ntr.result_value, ltu1.lab_test_uom, ntr.secondary_uom_result, ltu2.si_unit_name, 
            ntr.lab_test_comment, ntr.template, ltt.normal_range_label, ntr.report_code
            FROM `tabNormal Test Result` as ntr
            INNER JOIN `tabLab Test Template` as ltt
            ON ltt.name=ntr.template
            LEFT JOIN `tabLab Test UOM` as ltu1
            ON ltu1.name=ntr.secondary_uom
            LEFT JOIN `tabLab Test UOM` as ltu2
            ON ltu2.name=ntr.lab_test_uom
            WHERE ntr.parent='{test_name}' AND ntr.parenttype='Lab Test'
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
    SELECT anr.range_type, anr.gender, anr.criteria_text, anr.range_text, anr.si_range_text, 
    nr.age_range, nr.from_age, nr.from_age_period, nr.to_age, nr.to_age_period
    FROM `tabAttribute Normal Range` as anr
    INNER JOIN `tabNormal Range` as nr ON nr.name = anr.normal_range_id
    WHERE anr.parent='{lab_test_template}' AND anr.parenttype='Lab Test Template' AND anr.range_type!='Machine Edge'
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