import frappe

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
    fields = ["p.patient_name", "lt.patient_age", "p.patient_number", "p.sex as patient_gender", "lt.sales_invoice", "sc.modified as sample_date", "lt.practitioner_name", "lt.name as test_name"] # p.dob
    query = """
        SELECT {fields}
        FROM `tabLab Test` AS lt
        INNER JOIN `tabPatient` AS p ON lt.patient=p.name
        INNER JOIN `tabSample Collection` AS sc ON lt.sample=sc.name
        {where_stmt}
        ORDER BY lt.creation DESC
        {limit_stmt}
    """.format(fields=",".join(fields), where_stmt=where_stmt, limit_stmt=limit_stmt)

    lab_tests = frappe.db.sql(query, as_dict=True)

    for test in lab_tests:
        test["results"] = frappe.db.sql("""
            SELECT lab_test_name, result_value, lab_test_uom, secondary_uom_result, secondary_uom, lab_test_comment
            FROM `tabNormal Test Result`
            WHERE parent='{test_name}' AND parenttype='Lab Test'
        """.format(test_name=test["test_name"]), as_dict=True)

    return lab_tests


def print_error_message(msg):
    return {
            "body": """<h1>Error</h1>
                <p>{msg}</p>
                """.format(msg=msg)
        }