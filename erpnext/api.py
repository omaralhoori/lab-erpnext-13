import frappe
from erpnext.healthcare.doctype.lab_test.lab_test_print import lab_test_result
@frappe.whitelist(allow_guest=True)
def patient_results(invoice, password):
    patient = frappe.db.get_value("Lab Test", invoice, ['patient'])
    if not patient: return
    if frappe.db.get_value("Patient", patient, 'patient_password') != password: return
    #lab_test = frappe.db.get_value("Lab Test", {"sales_invoice": invoice}, "name")
    return lab_test_result(invoice, only_finilized=True, head=True, previous=True)

# from erpnext.accounts.report.general_ledger.general_ledger import execute as test_ledger

# @frappe.whitelist()
# def test_performance():
#     return test_ledger(frappe._dict(frappe.form_dict))

# from frappe import auth
# from frappe.core.doctype.user.user import update_password

# @frappe.whitelist( allow_guest=True )
# def login(usr, pwd):
#     try:
#         login_manager = frappe.auth.LoginManager()
#         login_manager.authenticate(user=usr, pwd=pwd)
#         login_manager.post_login()
#     except frappe.exceptions.AuthenticationError:
#         frappe.clear_messages()
#         frappe.local.response["message"] = {
#             "success_key":0,
#             "message":"Authentication Error!"
#         }

#         return
#     user = frappe.get_doc('User', frappe.session.user)
#     #if not user.api_secret:
#     # else:
#     #     api_generate = user.api_secret
    
#     frappe.response["message"] = {
#         "success_key":1,
#         "message":"Authentication success",
#         "sid":frappe.session.sid,
#         "username":user.username,
#         "fullname": user.full_name,
#         "image": user.user_image,
#         "gender": user.gender,
#         "address": user.location,
#         "birth_date": user.birth_date,
#         "mobile_no": user.mobile_no,
#         "email":user.email,
#     }