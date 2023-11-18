# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from erpnext.healthcare.doctype.lab_test.lab_test_print import get_pdf_writer, format_patient_result_link, get_asset_file,get_xray_report, get_print_asset, get_print_body, get_print_header, get_print_html_base, get_print_style, get_print_tbody, get_uploaded_tests, get_uploaded_tests_with_content, remove_asset, lab_test_result
import frappe
import json
import pdfkit
from frappe.utils.pdf import get_file_data_from_writer
from PyPDF2 import PdfFileReader, PdfFileWriter
import io
from frappe.model.document import Document

class ClinicalTesting(Document):
	def after_insert(self):
		clnc_test =self
	def load_test_from_templates(self):
		create_test_from_template(self)
		#self.save(ignore_permissions=True)
		#self.reload()
	def on_update(self):
		self.set_test_status()
	def set_test_status(self):
		status = self.status
		all_finalized, all_released, all_rejected = True, True, True
		partially_finalized, partially_released = False, False
		for item in self.normal_test_items:
			if item.status!='Finalized' and not item.allow_blank and item.status != "Rejected": all_finalized=False
			if item.status!='Released' and not item.allow_blank and item.status != "Rejected": all_released= False
			if item.status=='Finalized': partially_finalized=True
			if item.status=='Released': partially_released= True
			if item.status != 'Rejected': all_rejected = False
		if all_rejected:status = 'Cancelled'	
		elif all_finalized: status = 'Finalized'
		elif partially_finalized: status='Partially Finalized'
		elif all_released: status='Released'
		elif partially_released: status='Partially Released'
		if len(self.normal_test_items) == 0: status = 'Draft'
		print(all_finalized, all_released, all_rejected, partially_finalized, partially_released)
		self.db_set('status', status)

	def get_patient_file(self):
		return frappe.db.get_value("Patient", self.patient, ["patient_number"])

	def add_test_from_template(self,  added_items):
		for item in added_items:
			lab_test = load_result_format(self, item['template'], None, None, item=item['item'])

def create_test_from_template(lab_test):
	templates = lab_test.template if isinstance(lab_test.template, list) else [lab_test.template]
	for template_name in templates:
		item = None
		if template_name.get("item"):
			item = template_name.get("item")
		if template_name.get("template"):
			template_name = template_name.get("template")
		template = frappe.get_doc('Lab Test Template', template_name)

		lab_test.lab_test_name = template.lab_test_name
		lab_test = load_result_format(lab_test, template, None, None, item=item)

def load_result_format(lab_test, template, prescription, invoice, depth=1,item=None):
	if depth > 3 : return lab_test
	if template.lab_test_template_type == 'Single':
		create_normals(template, lab_test, item=item)
	elif template.lab_test_template_type == 'Multiline' and template.lab_test_group =='Clinical Services':
		create_multiline_normals(template, lab_test, item=item)

	elif template.lab_test_template_type == 'Grouped' and (template.lab_test_group =='Clinical Services' or template.lab_test_group == "Lab Test Packages" or template.lab_test_group == "Package"):
		# Iterate for each template in the group and create one result for all.
		for lab_test_group in template.lab_test_groups:
			if lab_test_group.lab_test_template:
				template_in_group = frappe.get_doc('Lab Test Template', lab_test_group.lab_test_template)
				#create_multiline_normals(template_in_group, lab_test)
				lab_test = load_result_format(lab_test, template_in_group, prescription, invoice, depth + 1, item=item)

	return lab_test

def create_multiline_normals(template, lab_test, item=None):
	for lab_test_group in template.lab_test_groups:
		# Template_in_group = None
		if lab_test_group.lab_test_template:
			template_in_group = frappe.get_doc('Lab Test Template', lab_test_group.lab_test_template)
			if template_in_group:
				if template_in_group.lab_test_template_type == 'Single':
					create_normals(template_in_group, lab_test, template, item=item)
		else: # Lab Test Group - Add New Line
			normal = lab_test.append('normal_test_items')
			normal.lab_test_name = lab_test_group.group_event
			normal.lab_test_uom = lab_test_group.group_test_uom
			normal.secondary_uom = lab_test_group.secondary_uom
			normal.conversion_factor = lab_test_group.conversion_factor
			normal.normal_range = lab_test_group.group_test_normal_range
			normal.allow_blank = lab_test_group.allow_blank
			normal.require_result_value = 1
			normal.template = template.name
			normal.status = "Received"
			if item:
				normal.item= item


def create_normals(template, lab_test, group_template=None, item=None):
	if template.company and template.company != lab_test.company: return
	lab_test.normal_toggle = 1
	normal = lab_test.append('normal_test_items')
	normal.lab_test_name = template.lab_test_name
	if item:
		normal.item = item
	# UOM CHANGE
	normal.lab_test_uom = template.secondary_uom
	if not template.secondary_uom and group_template:
		normal.lab_test_uom = group_template.secondary_uom
	
	normal.secondary_uom = template.lab_test_uom
	if not template.lab_test_uom and group_template:
		normal.secondary_uom = group_template.lab_test_uom
	

	normal.conversion_factor = template.conversion_factor
	if not template.conversion_factor and group_template:
		normal.conversion_factor = group_template.conversion_factor
	normal.normal_range = template.lab_test_normal_range
	normal.require_result_value = 1
	#normal.allow_blank = 0
	normal.template = template.name
	normal.report_code = template.name
	if group_template :
		normal.report_code = group_template.name
	if group_template.default_comment or template.default_comment:
		normal.lab_test_comment = group_template.default_comment or template.default_comment
	normal.control_type = template.control_type

	if group_template.alias and template.symbol:
		normal.test_symbol = group_template.alias + "." + template.symbol
	elif template.alias and template.symbol:
		normal.test_symbol = template.alias + "." + template.symbol
	normal.status = "Received"




@frappe.whitelist()
def apply_test_button_action(action, tests, test_name):
	where_stmt = ""
	if action == "Received":
		where_stmt = "(status is NULL or status not in ('Released', 'Finalized', 'Rejected'))"
	elif action == "Released":
		where_stmt = "status='Received' AND result_value !='' AND result_value IS NOT NULL "
	elif action == 'Finalized':
		where_stmt = "status='Released'"
	elif action == 'Rejected':
		where_stmt = "(status is NULL or status not in ('Finalized'))"
	elif action == 'definalize':
		where_stmt = "status='Finalized'"
		action = 'Released'
	elif action == 'unrelease':
		where_stmt = "status='Released'"
		action = 'Received'
	else: frappe.throw("Undefined action: " + action)
	tests = json.loads(tests)
	tests = [f"'{s}'" for s in tests]
	query= """
	UPDATE `tabNormal Test Result` SET status='{action}'
	WHERE name in ({tests}) AND {where_stmt}
	""".format(action=action, tests=",".join(tests), where_stmt=where_stmt)
	frappe.db.sql(query)
	frappe.db.commit()
	lab_test = frappe.get_doc('Clinical Testing', test_name)
	if lab_test:
		lab_test.set_test_status()
	# if action == "Received":
	# 	infinty_tests = frappe.db.sql("""
	# 		SELECT host_code FROM `tabNormal Test Result`
	# 		WHERE name in ({tests}) AND status='Received' AND host_name='Inifinty'
	# 	""".format(tests=",".join(tests)), as_dict=True)
	# 	infinty_tests = list(set([test['host_code'] for test in infinty_tests if test['host_code'] and test['host_code'] !=""]))
	# 	if len(infinty_tests) > 0:
	# 		send_infinty_msg_with_patient(test_name, sample, infinty_tests)



@frappe.whitelist()
def clnc_test_result(lab_test, previous=None, only_finilized=False, head=None, return_html=False):
    test_doc = frappe.get_doc("Clinical Testing", lab_test)
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
        footer = frappe.render_template(footer, {"username":frappe.utils.get_fullname(), "result_link": result_link})
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
    uploaded_tests = get_uploaded_tests(test_doc, True, parent_type='Clinical Testing')
    print(uploaded_tests)
    if not frappe.db.get_single_value("Healthcare Settings","print_empty_result"):
        if not tbody or tbody == "":
            output = None
    if len(uploaded_tests) > 0:
        output = get_uploaded_tests_with_content(uploaded_tests, output)
    remove_asset(footer_link)
    if return_html: return output
    frappe.local.response.filename = "Test.pdf"
    frappe.local.response.filecontent = output  or ''#get_pdf(html)
    frappe.local.response.type = "pdf"

@frappe.whitelist()
def print_all_reports(lab_test):
	sales_invoice = frappe.db.get_value("Lab Test", lab_test, "sales_invoice")
	clnc =None
	result = lab_test_result(lab_test, return_html=True)
	xray = get_xray_report(sales_invoice, return_html=True)
	clnc_doc = frappe.db.get_value("Clinical Testing", {"sales_invoice": sales_invoice}, "name")
	if clnc_doc:
		clnc = clnc_test_result(clnc_doc, return_html=True)
	writer = get_pdf_writer(result)
	if xray and xray != "":
		reader = PdfFileReader(io.BytesIO(xray))
		writer.appendPagesFromReader(reader)
	if clnc and clnc != "":
		reader = PdfFileReader(io.BytesIO(clnc))
		writer.appendPagesFromReader(reader)
	output = get_file_data_from_writer(writer)
	frappe.local.response.filename = "Test Result"
	frappe.local.response.filecontent = output #get_pdf(html)
	frappe.local.response.type = "pdf"