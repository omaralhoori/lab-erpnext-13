# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from functools import partial

import frappe
from frappe import _, log
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate

from frappe.core.doctype.sms_settings.sms_settings import send_sms
from erpnext.healthcare.doctype.patient.patient import validate_invoice_paid

import re
from .lab_test_print import get_lab_test_result

class LabTest(Document):
	def validate(self):
		if not self.is_new():
			self.set_secondary_uom_result()

	def on_submit(self):
		self.validate_sample_released()
		#validate_invoice_paid(self.patient, self.sales_invoice)
		self.validate_result_values()
		self.db_set('submitted_date', getdate())
		self.db_set('status', 'Completed')

		if not frappe.local.conf.is_embassy and (not self.sms_sent or self.sms_sent == 0):
			self.send_result_sms()
	
	def validate_sample_released(self):
		if not self.status == "Released":
			frappe.throw(_("You didn't release the sample!"))
	
	def validate_invoice_paid(self):
		if frappe.db.get_value("Sales Invoice", self.sales_invoice, "outstanding_amount") != 0:
			frappe.throw(_("Invoice is not paid"))
	
	def send_result_sms(self):
		send_to_payer = False
		receiver_number = None
		invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)

		if invoice:
			if invoice.sms_to_payer and invoice.sms_to_payer == 1:
				send_to_payer= True
				
		result_msg = frappe.db.get_single_value("Healthcare Settings", "result_sms_message")
		if not result_msg or result_msg == "":
			frappe.msgprint(_("Failed to send sms. Result sms message is empty in Healthcare Settings."))
			return

		if send_to_payer:
			receiver_number = frappe.db.get_value("Customer", invoice.insurance_party, "customer_mobile_no")
		else:
			receiver_number = frappe.db.get_value("Customer", invoice.customer, "customer_mobile_no")
		if not receiver_number or receiver_number == "":
			frappe.msgprint(_("Failed to send sms. Receiver mobile number is empty."))
			return

		result_url = frappe.db.get_single_value("Healthcare Settings", "result_url")
		if not result_url or result_url == "":
			frappe.msgprint(_("Failed to send sms. Result url is empty in Healthcare Settings."))
			return

		if result_url[-1] != "/":
			result_url += '/'
		patient_info = frappe.db.get_value("Patient", invoice.patient, ["patient_password", "patient_number"])
		if not patient_info:
			frappe.msgprint(_("Failed to send sms. Patient information is incomplete."))
			return
		patient_password, patient_number = patient_info
		result_url += "test-result?usercode=" + patient_password + "_" + patient_number.replace(" ", "%20")
		result_msg += "\n"  + result_url

		send_sms(msg=result_msg, receiver_list=[receiver_number])

	def before_save(self):
		for lab_test in self.normal_test_items:
			if lab_test.control_type == 'Formula':
				result = self.check_formula_result(lab_test.template)
				if result:
					if result[0]:
						lab_test.result_value = result[0]
					if result[1]:
						lab_test.secondary_uom_result = result[1]
	def get_lab_test_print(self):
		results = get_lab_test_result(self.patient, False, f"WHERE lt.name='{self.name}'")
		if len(results) > 0:
			html = frappe.render_template('templates/test_result/test_result.html', results[0])
			return html
		return "Unable to render template"
	def check_formula_result(self, test_name):
		try:
			formula = frappe.db.get_value("Lab Test Template", test_name, ["formula"])
			if not formula: return
			#formula = formula[0][0]
			items = re.findall('\[(.+?)\]', formula)
			if len(items) == 0: return
			si_result, conv_result = {}, {}
			result_si, result_conv= None, None
			for lab_test in self.normal_test_items:
				if lab_test.test_symbol and lab_test.test_symbol in items:
					#result[lab_test.symbol] = {}
					if lab_test.result_value:
						conv_result[lab_test.test_symbol] = lab_test.result_value
					if lab_test.secondary_uom_result:
						si_result[lab_test.test_symbol] = lab_test.secondary_uom_result
			if len(si_result.keys()) == len(items):
				formula_val = formula
				for res in si_result:
					formula_val = formula_val.replace(f'[{res}]', str(si_result[res]))
				result_si = eval(formula_val)
			if len(conv_result.keys()) == len(items):
				for res in conv_result:
					formula = formula.replace(f'[{res}]', str(conv_result[res]))
				result_conv = eval(formula)
			return  result_conv, result_si
		except:
			frappe.msgprint("Couldn't calculate formula result for test: " + test_name)

	def on_cancel(self):
		self.db_set('status', 'Cancelled')
		self.reload()

	def on_update(self):
		if self.sensitivity_test_items:
			sensitivity = sorted(self.sensitivity_test_items, key=lambda x: x.antibiotic_sensitivity)
			for i, item in enumerate(sensitivity):
				item.idx = i + 1
			self.sensitivity_test_items = sensitivity
		self.set_test_status()
		old_doc = self.get_doc_before_save()
		if old_doc:
			added_items, removed_items = self.get_created_or_deleted_items(old_doc.template, self.template)
			add_test_from_template(self, added_items)
	def get_created_or_deleted_items(self, old_items, new_items):
		old_items_code, new_items_code = [item.template for item in old_items], [item.template for item in new_items]
		added_items = [x for x in new_items if x.template not in old_items_code]
		removed_items =  [x for x in old_items if x.template not in new_items_code]
		return added_items, removed_items

	def set_test_status(self):
		status = self.status
		all_finalized, all_released = True, True
		partially_finalized, partially_released = False, False
		for item in self.normal_test_items:
			if item.status!='Finalized': all_finalized=False
			if item.status!='Released': all_released= False
			if item.status=='Finalized': partially_finalized=True
			if item.status=='Released': partially_released= True
		if all_finalized: status = 'Finalized'
		elif partially_finalized: status='Partially Finalized'
		elif all_released: status='Released'
		elif partially_released: status='Partially Released'
		self.db_set('status', status)
	def after_insert(self):
		if self.prescription:
			frappe.db.set_value('Lab Prescription', self.prescription, 'lab_test_created', 1)
			if frappe.db.get_value('Lab Prescription', self.prescription, 'invoiced'):
				self.invoiced = True
		if self.template:
			self.load_test_from_template()
			self.reload()

	def load_test_from_template(self):
		lab_test = self
		create_test_from_template(lab_test)
		self.reload()

	def set_secondary_uom_result(self):
		for item in self.normal_test_items:
			if item.result_value and item.control_type != 'Formula' and item.secondary_uom and item.conversion_factor:
				try:
					item.secondary_uom_result = float(item.result_value) * float(item.conversion_factor)
				except Exception:
					item.secondary_uom_result = ''
					frappe.msgprint(_('Row #{0}: Result for Secondary UOM not calculated').format(item.idx), title = _('Warning'))

	def validate_result_values(self):
		if self.normal_test_items:
			for item in self.normal_test_items:
				if not item.result_value and not item.allow_blank and item.require_result_value:
					frappe.throw(_('Row #{0}: Please enter the result value for {1}').format(
						item.idx, frappe.bold(item.lab_test_name)), title=_('Mandatory Results'))

		if self.descriptive_test_items:
			for item in self.descriptive_test_items:
				if not item.result_value and not item.allow_blank and item.require_result_value:
					frappe.throw(_('Row #{0}: Please enter the result value for {1}').format(
						item.idx, frappe.bold(item.lab_test_particulars)), title=_('Mandatory Results'))

	def get_patient_file(self):
		return frappe.db.get_value("Patient", self.patient, ["patient_number"])

@frappe.whitelist()
def send_patient_result_sms(lab_test):
	lab_test = frappe.get_doc("Lab Test", lab_test)
	if not lab_test:
		frappe.throw("Test not found")
	lab_test.send_result_sms()


def create_test_from_template(lab_test):
	templates = lab_test.template if isinstance(lab_test.template, list) else [lab_test.template]
	sample_created = False
	for template_name in templates:
		if template_name.get("template"):
			template_name = template_name.get("template")
		template = frappe.get_doc('Lab Test Template', template_name)
		patient = frappe.get_doc('Patient', lab_test.patient)

		lab_test.lab_test_name = template.lab_test_name
		lab_test.result_date = getdate()
		lab_test.department = template.department
		lab_test.lab_test_group = template.lab_test_group
		lab_test.legend_print_position = template.legend_print_position
		lab_test.result_legend = template.result_legend
		lab_test.worksheet_instructions = template.worksheet_instructions

		lab_test = create_sample_collection(lab_test, template, patient, lab_test.sales_invoice, sample_created=sample_created)
		sample_created = True
		lab_test = load_result_format(lab_test, template, None, None)



def add_test_from_template(lab_test,  added_items):
	templates = added_items
	if lab_test.sample:
		frappe.db.set_value("Sample Collection", lab_test.sample, {"docstatus": 0})
	for template_name in templates:
		template = frappe.get_doc('Lab Test Template', template_name.template)
		patient = frappe.get_doc('Patient', lab_test.patient)
		lab_test = create_sample_collection(lab_test, template, patient, lab_test.sales_invoice, sample_created=True)
		lab_test = load_result_format(lab_test, template, None, None)

@frappe.whitelist()
def update_status(status, name):
	if name and status:
		frappe.db.set_value('Lab Test', name, {
			'status': status,
			'approved_date': getdate()
		})

@frappe.whitelist()
def create_multiple(doctype, docname):
	if not doctype or not docname:
		frappe.throw(_('Sales Invoice or Patient Encounter is required to create Lab Tests'), title=_('Insufficient Data'))

	lab_test_created = False
	if doctype == 'Sales Invoice':
		lab_test_created = create_lab_test_from_invoice(docname)
	elif doctype == 'Patient Encounter':
		lab_test_created = create_lab_test_from_encounter(docname)

	if lab_test_created:
		frappe.msgprint(_('Lab Test(s) {0} created successfully').format(lab_test_created), indicator='green')
	else:
		frappe.msgprint(_('No Lab Tests created'))

@frappe.whitelist()
def create_or_delete_items(sales_invoice, removed_item, added_items):
	# if lab not created create lab test
	lab_test = frappe.db.exists("Lab Test", {"sales_invoice": sales_invoice.name}, "name")
	if not lab_test:
		create_lab_test_from_invoice(sales_invoice.name)
		return
	# else delete or add new items
	add_new_items_lab_test(lab_test, added_items, sales_invoice)

def add_new_items_lab_test(lab_test, new_items, invoice):
	add_new_items_lab_test_joined(invoice, new_items)


def create_lab_test_from_encounter(encounter):
	lab_test_created = False
	encounter = frappe.get_doc('Patient Encounter', encounter)

	if encounter and encounter.lab_test_prescription:
		patient = frappe.get_doc('Patient', encounter.patient)
		for item in encounter.lab_test_prescription:
			if not item.lab_test_created:
				template = get_lab_test_template(item.lab_test_code)
				if template:
					lab_test = create_lab_test_doc(item.invoiced, encounter.practitioner, patient, template, encounter.company)
					lab_test.save(ignore_permissions = True)
					frappe.db.set_value('Lab Prescription', item.name, 'lab_test_created', 1)
					if not lab_test_created:
						lab_test_created = lab_test.name
					else:
						lab_test_created += ', ' + lab_test.name
	return lab_test_created


def create_lab_test_from_invoice(sales_invoice):
	lab_tests_created = False
	separate = frappe.db.get_single_value("Healthcare Settings", "create_lab_test_separated")
	if not separate or separate == 0:
		lab_tests_created = create_lab_test_joined(sales_invoice)
	else:
		lab_tests_created = create_lab_test_separated(sales_invoice)
	return lab_tests_created

def create_lab_test_joined(sales_invoice):
	lab_tests_created = False
	invoice = frappe.get_doc('Sales Invoice', sales_invoice)
	lab_test = None
	rad_test = None
	if invoice and invoice.patient:
		patient = frappe.get_doc('Patient', invoice.patient)
		test_created = False
		rad_created = False
		for item in invoice.items:
			template = get_lab_test_template(item.item_code)
			if template:
				if template.lab_test_group == "Radiology Services":
					if not rad_created:
						rad_test = create_rad_test_doc(patient, template, invoice)
						rad_created = True
					else:
						template_row = lab_test.append("template")
						template_row.template = template.name
				elif template.lab_test_group == "Lab Test Packages" and template.has_radiology():
					if not rad_created:
						rad_test = create_rad_test_doc(patient, template, invoice)
						rad_created = True
					else:
						template_row = lab_test.append("template")
						template_row.template = template.name
					if not test_created:
						lab_test = create_lab_test_doc(True, invoice.ref_practitioner, patient, template, invoice.company)
						test_created = True
					else:
						template_row = lab_test.append("template")
						template_row.template = template.name
				else:
					if not test_created:
						lab_test = create_lab_test_doc(True, invoice.ref_practitioner, patient, template, invoice.company)
						test_created = True
					else:
						template_row = lab_test.append("template")
						template_row.template = template.name
		if lab_test:
			lab_test.sales_invoice = sales_invoice
			lab_test.save(ignore_permissions = True)
			lab_tests_created = lab_test.name
		if rad_test:
			rad_test.save(ignore_permissions = True)
	return lab_tests_created



def add_new_items_lab_test_joined(invoice, new_items):
	lab_test = None
	rad_test = None
	if invoice and invoice.patient:
		patient = frappe.get_doc('Patient', invoice.patient)
		for item in new_items:
			print(item.item_code)
			template = get_lab_test_template(item.item_code)
			if template:
				if template.lab_test_group == "Radiology Services":
					rad_test = add_or_create_rad_test_doc(patient, template, invoice)
						
				elif template.lab_test_group == "Lab Test Packages" and template.has_radiology():
					rad_test = add_or_create_rad_test_doc(patient, template, invoice)
					lab_test = add_or_create_lab_test_doc(True, invoice.ref_practitioner, patient, template, invoice.company, invoice.name)
						
				else:
					lab_test = add_or_create_lab_test_doc(True, invoice.ref_practitioner, patient, template, invoice.company, invoice.name)
		if lab_test:
			lab_test.sales_invoice = invoice.name
			lab_test.save(ignore_permissions = True)
		if rad_test:
			rad_test.save(ignore_permissions = True)

def create_lab_test_separated(sales_invoice):
	lab_tests_created = False
	invoice = frappe.get_doc('Sales Invoice', sales_invoice)
	if invoice and invoice.patient:
		patient = frappe.get_doc('Patient', invoice.patient)
		for item in invoice.items:
			lab_test_created = 0
			if item.reference_dt == 'Lab Prescription':
				lab_test_created = frappe.db.get_value('Lab Prescription', item.reference_dn, 'lab_test_created')
			elif item.reference_dt == 'Lab Test':
				lab_test_created = 1
			if lab_test_created != 1:
				template = get_lab_test_template(item.item_code)
				if template:
					lab_test = create_lab_test_doc(True, invoice.ref_practitioner, patient, template, invoice.company)
					if item.reference_dt == 'Lab Prescription':
						lab_test.prescription = item.reference_dn
					lab_test.sales_invoice = sales_invoice
					lab_test.save(ignore_permissions = True)
					if item.reference_dt != 'Lab Prescription':
						frappe.db.set_value('Sales Invoice Item', item.name, 'reference_dt', 'Lab Test')
						frappe.db.set_value('Sales Invoice Item', item.name, 'reference_dn', lab_test.name)
					if not lab_tests_created:
						lab_tests_created = lab_test.name
					else:
						lab_tests_created += ', ' + lab_test.name
	return lab_tests_created

def get_lab_test_template(item):
	template_id = frappe.db.exists('Lab Test Template', {'item': item})
	if template_id:
		return frappe.get_doc('Lab Test Template', template_id)
	return False

def create_rad_test_doc(patient, template, invoice):
	rad_test = frappe.new_doc('Radiology Test')
	rad_test.patient = patient.name
	rad_test.patient_age = patient.get_age()
	rad_test.patient_sex = patient.sex
	template_row = rad_test.append("template")
	template_row.template = template.name
	rad_test.company = invoice.company
	rad_test.sales_invoice = invoice.name
	rad_test.physician = invoice.ref_practitioner
	return rad_test


def add_or_create_rad_test_doc(patient, template, invoice):
	rad_test = frappe.db.get_value("Radiology Test", {"sales_invoice": invoice.name}, ["name"])
	if not rad_test: return create_rad_test_doc(patient, template, invoice)
	rad_test = frappe.get_doc("Radiology Test", rad_test)
	template_row = rad_test.append("template")
	template_row.template = template.name
	return rad_test

def create_lab_test_doc(invoiced, practitioner, patient, template, company):
	lab_test = frappe.new_doc('Lab Test')
	lab_test.invoiced = invoiced
	lab_test.practitioner = practitioner
	lab_test.patient = patient.name
	lab_test.patient_age = patient.get_age()
	lab_test.patient_sex = patient.sex
	lab_test.email = patient.email
	lab_test.mobile = patient.mobile
	lab_test.report_preference = patient.report_preference
	lab_test.department = template.department
	#lab_test.template = template.name
	template_row = lab_test.append("template")
	template_row.template = template.name
	lab_test.lab_test_group = template.lab_test_group
	lab_test.result_date = getdate()
	lab_test.company = company
	return lab_test


def add_or_create_lab_test_doc(invoiced, practitioner, patient, template, company, sales_invoice):
	lab_test = frappe.db.get_value('Lab Test', {"sales_invoice": sales_invoice}, ['name'])
	if not lab_test: return create_lab_test_doc(invoiced, practitioner, patient, template, company)
	lab_test = frappe.get_doc('Lab Test', {"sales_invoice": sales_invoice})
	template_row = lab_test.append("template")
	template_row.template = template.name
	return lab_test

def create_normals(template, lab_test, group_template=None):
	lab_test.normal_toggle = 1
	normal = lab_test.append('normal_test_items')
	normal.lab_test_name = template.lab_test_name

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
	normal.allow_blank = 0
	normal.template = template.name
	normal.report_code = template.name
	if group_template :
		normal.report_code = group_template.name
	if group_template.default_comment or template.default_comment:
		normal.lab_test_comment = group_template.default_comment or template.default_comment
	normal.control_type = template.control_type
	test_code = None
	query = """
		SELECT mtt.parent, mtt.host_code FROM `tabMachine Type Lab Test Template` AS mtt
		INNER JOIN `tabMachine Type` AS mt
		ON mt.name=mtt.parent
		WHERE mt.disable=0 AND mtt.lab_test_template="{template}"
		"""
	try:
		if group_template:
			test_code = frappe.db.sql(query.format(template=group_template.name), as_dict=True)
			#test_code = frappe.db.get_value("Machine Type Lab Test Template", {"lab_test_template": group_template.name}, ["parent", "host_code"])
			if len(test_code) == 0:
				test_code = frappe.db.sql(query.format(template=template.name), as_dict=True)
		else:
			test_code = frappe.db.sql(query.format(template=template.name), as_dict=True)
	except:
		print(query.format(template=template.name))
	# print("888888888888888888888888888888888888888")
	# print(template.name)
	# print(test_code)
	if len(test_code) > 0:
		
		machine_name,host_code = test_code[0]['parent'], test_code[0]['host_code']
		if host_code and machine_name:
			normal.host_code=host_code
			normal.host_name=machine_name
	if group_template.alias and template.symbol:
		normal.test_symbol = group_template.alias + "." + template.symbol
	elif template.alias and template.symbol:
		normal.test_symbol = template.alias + "." + template.symbol

def create_compounds(template, lab_test, is_group):
	lab_test.normal_toggle = 1
	for normal_test_template in template.normal_test_templates:
		normal = lab_test.append('normal_test_items')
		if is_group:
			normal.lab_test_event = normal_test_template.lab_test_event
		else:
			normal.lab_test_name = normal_test_template.lab_test_event

		normal.lab_test_uom = normal_test_template.lab_test_uom
		normal.secondary_uom = normal_test_template.secondary_uom
		normal.conversion_factor = normal_test_template.conversion_factor
		normal.normal_range = normal_test_template.normal_range
		normal.require_result_value = 1
		normal.allow_blank = normal_test_template.allow_blank
		normal.template = template.name

def create_descriptives(template, lab_test):
	lab_test.descriptive_toggle = 1
	if template.sensitivity:
		lab_test.sensitivity_toggle = 1
	for descriptive_test_template in template.descriptive_test_templates:
		descriptive = lab_test.append('descriptive_test_items')
		descriptive.lab_test_particulars = descriptive_test_template.particulars
		descriptive.require_result_value = 1
		descriptive.allow_blank = descriptive_test_template.allow_blank
		descriptive.template = template.name

def create_sample_doc(template, patient, invoice, company = None):
	if template.sample:
		sample_exists = frappe.db.exists({
			'doctype': 'Sample Collection',
			'patient': patient.name,
			'docstatus': 0,
			'sales_invoice': invoice
			# 'sample': template.sample
		})
		if sample_exists:
			# update sample collection by adding quantity
			sample_collection = frappe.get_doc('Sample Collection', sample_exists[0][0])

			if template.lab_test_template_type == "Single":
				add_template_sample(template, sample_collection)
			elif template.lab_test_template_type == "Multiline": 
				create_multiple_sample(template, sample_collection, add=True)
			elif template.lab_test_template_type == "Grouped":
				for group_item in template.lab_test_groups:
					group_template = frappe.get_doc("Lab Test Template", group_item.lab_test_template)
					if group_template.lab_test_template_type == "Single":
						add_template_sample(group_template, sample_collection)
					elif group_template.lab_test_template_type == "Multiline": 
						create_multiple_sample(group_template, sample_collection, add=True)
	
			test_template = sample_collection.append("lab_test_templates")
			test_template.template = template.name

			if template.sample_details:
				sample_details = sample_collection.sample_details + '\n-\n' + _('Test :')
				sample_details += (template.get('lab_test_name') or template.get('template')) +	'\n'
				sample_details += _('Collection Details:') + '\n\t' + template.sample_details
				frappe.db.set_value('Sample Collection', sample_collection.name, 'sample_details', sample_details)

			#frappe.db.set_value('Sample Collection', sample_collection.name, {'sales_invoice': invoice})
			sample_collection.save(ignore_permissions=True)
		else:
			# Create Sample Collection for template, copy vals from Invoice
			sample_collection = frappe.new_doc('Sample Collection')
			if invoice:
				sample_collection.invoiced = True

			sample_collection.patient = patient.name
			sample_collection.patient_age = patient.get_age()
			sample_collection.patient_sex = patient.sex

			# sample_collection.sample = template.sample
			# sample_collection.sample_uom = template.sample_uom 
			# sample_collection.sample_qty = template.sample_qty
			test_template = sample_collection.append("lab_test_templates")
			test_template.template = template.name
			if template.lab_test_template_type == "Single":
				create_template_sample(template, sample_collection)
			elif template.lab_test_template_type == "Multiline":
				create_multiple_sample(template, sample_collection, add=True)
			elif template.lab_test_template_type == "Grouped":
				for group_item in template.lab_test_groups:
					group_template = frappe.get_doc("Lab Test Template", group_item.lab_test_template)
					if group_template.lab_test_template_type == "Single":
						create_template_sample(group_template, sample_collection)
					elif group_template.lab_test_template_type == "Multiline":
						create_multiple_sample(group_template, sample_collection, add=True)

			sample_collection.company = company
			sample_collection.sales_invoice = invoice

			if template.sample_details:
				sample_collection.sample_details = _('Test :') + (template.get('lab_test_name') or template.get('template')) + '\n' + 'Collection Detials:\n\t' + template.sample_details
			sample_collection.save(ignore_permissions=True)

		return sample_collection
	
def create_multiple_sample(template, sample_collection, add=False):
	for group_item in template.lab_test_groups:
		group_template = frappe.get_doc("Lab Test Template", group_item.lab_test_template)
		if group_template.sample and group_template.sample != "":
			if add:
				add_template_sample(group_template, sample_collection)
			else:
				create_template_sample(group_template, sample_collection)
		elif template.sample and template.sample != "":
			if add:
				add_template_sample(template, sample_collection)
			else:
				create_template_sample(template, sample_collection)
		

def create_template_sample(template, sample_collection):
	sample_detail = sample_collection.append("sample_collection_detail")
	sample_detail.sample = template.sample
	sample_detail.sample_uom = template.sample_uom
	qty = template.sample_qty or 1
	sample_detail.sample_qty = qty
	sample_collection.num_print = int(sample_collection.num_print) + 1

def add_template_sample(template, sample_collection):
	template_found = False
	if sample_collection.get("sample_collection_detail"):
		for sample_detail in sample_collection.sample_collection_detail:
			if template.sample == sample_detail.sample:
				qty = template.sample_qty or 1
				quantity = int(sample_detail.sample_qty) + int(qty)
				sample_detail.sample_qty = quantity
				sample_detail.num_print = int(sample_detail.num_print or 1) + 1
				# sample_collection.num_print = int(sample_collection.num_print or 1) + 1
				template_found = True
				break
	if not template_found:
		sample_detail = sample_collection.append("sample_collection_detail")
		sample_detail.sample = template.sample
		sample_detail.sample_uom = template.sample_uom
		sample_detail.sample_qty = template.sample_qty or 1
		sample_collection.num_print = int(sample_collection.num_print) + 1

def create_sample_collection(lab_test, template, patient, invoice, depth=1, sample_created=True):
	if depth < 4 and frappe.get_cached_value('Healthcare Settings', None, 'create_sample_collection_for_lab_test'):
		sample_collection = None
		if template.lab_test_template_type == "Grouped":
			for group_item in template.lab_test_groups:
				group_template = frappe.get_doc("Lab Test Template", group_item.lab_test_template)
				lab_test = create_sample_collection(lab_test, group_template, patient, invoice, depth + 1, sample_created=sample_created)#create_sample_doc(group_template, patient, invoice, lab_test.company)
				#sample_created = True
		else:
			sample_collection = create_sample_doc(template, patient, invoice, lab_test.company)
		if sample_collection:
			lab_test.sample = sample_collection.name
			sample_collection_doc = get_link_to_form('Sample Collection', sample_collection.name)
			if not sample_created:
				frappe.msgprint(_('Sample Collection {0} has been created').format(sample_collection_doc),
					title=_('Sample Collection'), indicator='green')
	return lab_test

def load_result_format(lab_test, template, prescription, invoice, depth=1):
	if depth > 3 : return lab_test
	if template.lab_test_template_type == 'Single':
		create_normals(template, lab_test)

	elif template.lab_test_template_type == 'Compound':
		create_compounds(template, lab_test, False)

	elif template.lab_test_template_type == 'Descriptive':
		create_descriptives(template, lab_test)
	elif template.lab_test_template_type == 'Multiline':
		create_multiline_normals(template, lab_test)

	elif template.lab_test_template_type == 'Grouped':
		# Iterate for each template in the group and create one result for all.
		for lab_test_group in template.lab_test_groups:
			if lab_test_group.lab_test_template:
				template_in_group = frappe.get_doc('Lab Test Template', lab_test_group.lab_test_template)
				#create_multiline_normals(template_in_group, lab_test)
				lab_test = load_result_format(lab_test, template_in_group, prescription, invoice, depth + 1)

	if template.lab_test_template_type != 'No Result':
		if prescription:
			lab_test.prescription = prescription
			if invoice:
				frappe.db.set_value('Lab Prescription', prescription, 'invoiced', True)
		lab_test.save(ignore_permissions=True) # Insert the result
		return lab_test

def create_multiline_normals(template, lab_test):
		for lab_test_group in template.lab_test_groups:
			# Template_in_group = None
			if lab_test_group.lab_test_template:
				template_in_group = frappe.get_doc('Lab Test Template', lab_test_group.lab_test_template)
				if template_in_group:
					if template_in_group.lab_test_template_type == 'Single':
						create_normals(template_in_group, lab_test, template)

					elif template_in_group.lab_test_template_type == 'Compound':
						normal_heading = lab_test.append('normal_test_items')
						normal_heading.lab_test_name = template_in_group.lab_test_name
						normal_heading.require_result_value = 0
						normal_heading.allow_blank = 1
						normal_heading.template = template_in_group.name
						create_compounds(template_in_group, lab_test, True)

					elif template_in_group.lab_test_template_type == 'Descriptive':
						descriptive_heading = lab_test.append('descriptive_test_items')
						descriptive_heading.lab_test_name = template_in_group.lab_test_name
						descriptive_heading.require_result_value = 0
						descriptive_heading.allow_blank = 1
						descriptive_heading.template = template_in_group.name
						create_descriptives(template_in_group, lab_test)

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

@frappe.whitelist()
def get_employee_by_user_id(user_id):
	emp_id = frappe.db.exists('Employee', { 'user_id': user_id })
	if emp_id:
		return frappe.get_doc('Employee', emp_id)
	return None


@frappe.whitelist()
def get_lab_test_prescribed(patient):
	return frappe.db.sql(
		'''
			select
				lp.name,
				lp.lab_test_code,
				lp.parent,
				lp.invoiced,
				pe.practitioner,
				pe.practitioner_name,
				pe.encounter_date
			from
				`tabPatient Encounter` pe, `tabLab Prescription` lp
			where
				pe.patient=%s
				and lp.parent=pe.name
				and lp.lab_test_created=0
		''', (patient))

from erpnext.healthcare.socket_communication import send_infinty_msg_order

@frappe.whitelist()
def get_receive_sample(sample, test_name=None):
	print("receiving--------------------------------")
	sample_docstatus = frappe.db.get_value("Sample Collection",{"name": sample}, "docstatus")

	if str(sample_docstatus) == '0':
		frappe.throw(_("Sample not collected / not submitted. {0}").format(sample), title=_("Sample Collection"))
	
	if test_name:
		send_received_msg_order(sample, test_name)
	# 	tests = frappe.db.get_all("Normal Test Result", {"parent": test_name}, ["host_code", "host_name"])
	# 	tests = list(set([code['host_code'] for code in tests if code['host_name'] == "Inifinty" ]))
	# 	print(tests)
	# 	if len(tests) > 0:
	# 		lab_test = frappe.get_doc("Lab Test", test_name)
	# 		patient = frappe.get_doc("Patient", lab_test.patient)
	# 		if not patient: frappe.throw("Patient not defiend")
	# 		dob = "19710101"
	# 		if patient.dob: dob = str(patient.dob).replace("-", "")
	# 		gender = "M" if patient.sex == "Male" else "F"
	# 		sample = frappe.get_doc("Sample Collection", sample)
	# 		print(patient.patient_number, dob, gender, sample.collection_serial.split("-")[-1], sample.creation.strftime("%Y%m%d%H%M%S"), tests, 107)
	# 		sent = send_msg_order(patient.patient_number, dob, gender, sample.collection_serial.split("-")[-1], sample.creation.strftime("%Y%m%d%H%M%S"), tests, 107)
		#print(patient.patient_number, dob, gender, sample.collection_serial.split("-")[-1], sample.modified.strftime("%Y%m%d%H%M%S"), tests, 107)
	frappe.db.sql("""
				UPDATE `tabNormal Test Result` SET status='Received'
			WHERE parent='{test_name}' AND status NOT IN ('Released', 'Finalized')
			""".format(test_name=test_name))
	return str(sample_docstatus)
def send_received_msg_order(sample, test_name):
	sent = False
	if frappe.get_cached_value("Healthcare Settings",None, "send_test_order"):
		tests = frappe.db.get_all("Normal Test Result", {"parent": test_name}, ["host_code", "host_name"])
		infinty_tests = list(set([code['host_code'] for code in tests if (code['host_name'] == "Inifinty" and  code['host_code'] and code['host_code'] != "") ]))
		print(infinty_tests)
		if len(infinty_tests) > 0:
			sent = send_infinty_msg_with_patient(test_name, sample, infinty_tests)
		#print(patient.patient_number, dob, gender, sample.collection_serial.split("-")[-1], sample.modified.strftime("%Y%m%d%H%M%S"), tests, 107)
	return sent

def send_infinty_msg_with_patient(test_name,sample, infinty_tests):
	lab_test = frappe.get_doc("Lab Test", test_name)
	patient = frappe.get_doc("Patient", lab_test.patient)
	if not patient: frappe.throw("Patient not defiend")
	dob = "19710101"
	if patient.dob: dob = str(patient.dob).replace("-", "")
	gender = "M" if patient.sex == "Male" else "F"
	sample = frappe.get_doc("Sample Collection", sample)
	print(patient.patient_number, dob, gender, sample.collection_serial.split("-")[-1], sample.creation.strftime("%Y%m%d%H%M%S"), infinty_tests, 107)
	sent = send_infinty_msg_order(patient.patient_number, dob, gender, sample.collection_serial.split("-")[-1], sample.creation.strftime("%Y%m%d%H%M%S"), infinty_tests, 107)
	return sent

@frappe.whitelist()
def get_release_sample(doclab,docname):

	sam_res = frappe.get_doc('Lab Test', docname)

	sample_status = frappe.db.get_value("Lab Test",{"name": docname}, "status")

	if sample_status != 'Received' and sample_status != 'Rejected':
		frappe.throw(_("Sample not received or rejected."), title=_("Sample Release"))
	
	# if sam_res.normal_test_items:
	# 	for item in sam_res.normal_test_items:
	# 		if not item.result_value and not item.allow_blank and item.require_result_value:
	# 			sample_status='Draft'
	# 			frappe.throw(_('Row #{0}: Please enter the result value for {1}').format(
	# 				item.idx, frappe.bold(item.lab_test_name)), title=_('Mandatory Results'))
	frappe.db.sql("""
				UPDATE `tabNormal Test Result` SET status='Released'
			WHERE parent='{test_name}' AND status='Received'
			""".format(test_name=docname))

	return sample_status

@frappe.whitelist()
def get_finalize_sample(doclab,docname):

	sam_res = frappe.get_doc('Lab Test', docname)

	sample_status = frappe.db.get_value("Lab Test",{"name": docname}, "status")

	if sample_status != 'Released':
		frappe.throw(_("Sample not released."), title=_("Sample Release"))
	
	frappe.db.sql("""
				UPDATE `tabNormal Test Result` SET status='Finalized'
			WHERE parent='{test_name}' AND status='Released'
			""".format(test_name=docname))

	return sample_status

@frappe.whitelist()
def get_reject_sample(docname):

	sample_status = frappe.db.get_value("Lab Test",{"name": docname}, "status")

	if sample_status != 'Released' :
		frappe.throw(_("Sample not released."), title=_("Sample Reject"))
	
	frappe.db.sql("""
				UPDATE `tabNormal Test Result` SET status='Rejected'
			WHERE parent='{test_name}' AND status='Released'
			""".format(test_name=docname))
	
	return sample_status

import json
@frappe.whitelist(allow_guest=True)
def receive_infinty_results():
	lab_tests = json.loads(frappe.request.data)
	print("results received---------------------------------------------")
	print(len(lab_tests))
	print(lab_tests)
	for lab_test in lab_tests:
		results = lab_test['results']
		for test in results:
			query = """ UPDATE `tabNormal Test Result` as ntr 
				INNER JOIN `tabLab Test` as lt ON lt.name=ntr.parent
				INNER JOIN `tabSample Collection` as sc ON sc.name=lt.sample
				INNER JOIN `tabPatient` as p ON p.name=lt.patient
				SET ntr.result_value='{result}'
				WHERE sc.collection_serial='bar-{order_id}' AND p.patient_number='{file_no}' AND ntr.host_code='{test_code}'
								""".format(result=test['result'], test_code=test['code'], order_id=lab_test['order_id'], file_no=lab_test['file_no'])
			frappe.db.sql(query)
	frappe.db.commit()
from erpnext.healthcare.socket_communication import log_result
@frappe.whitelist(allow_guest=True)
def receive_sysmex_results():
	lab_tests = json.loads(frappe.request.data)
	print("results received---------------------------------------------")
	log_result("sysmex", "results received--------------------")
	for lab_test in lab_tests:
		results = lab_test['results']
		for test in results:
			#if test['result'].isnumeric():
			set_stmt = 'ntr.result_value'
			if test['code'].endswith("%"):
				set_stmt = 'ntr.result_percentage'
			elif test['code'].endswith("#"):
				test['code'] = test['code'][:-1] + "%"
			query = """ UPDATE `tabNormal Test Result` as ntr 
				INNER JOIN `tabLab Test` as lt ON lt.name=ntr.parent
				INNER JOIN `tabSample Collection` as sc ON sc.name=lt.sample
				SET {set_stmt}='{result}'
				WHERE sc.collection_serial='bar-{order_id}' AND ntr.host_code='{test_code}'
								""".format(set_stmt = set_stmt, result=test['result'], test_code=test['code'], order_id=lab_test['order_id'])
			#log_result("sysmex", query)
			frappe.db.sql(query)
	frappe.db.commit()

@frappe.whitelist()
def get_test_attribute_options(lab_test):
	options = frappe.db.sql("""
	SELECT tntr.template, tltt.attribute_options  FROM `tabLab Test Template` tltt
		INNER JOIN `tabNormal Test Result` tntr
		ON tntr.template = tltt.name
		WHERE tntr.parent="{lab_test}" AND tltt.control_type IN ('Free Text', 'Drop Down List')
	""".format(lab_test=lab_test), as_dict=True)

	units = frappe.db.sql("""
		SELECT tntr.name,tltu.lab_test_uom as conv_unit, tltu2.si_unit_name as si_unit FROM `tabNormal Test Result` tntr 
		LEFT JOIN `tabLab Test UOM` tltu ON tltu.name=tntr.lab_test_uom
		LEFT JOIN `tabLab Test UOM` tltu2 ON tltu2.name=tntr.secondary_uom
		WHERE tntr.parent="{lab_test}"
	""".format(lab_test=lab_test),as_dict=True)

	orders = frappe.db.sql(f"""
		SELECT tmtltt.lab_test_template ,tmtltt.interface_order FROM `tabNormal Test Result` tntr 
		INNER JOIN `tabMachine Type Lab Test Template` tmtltt ON tmtltt.lab_test_template=tntr.template
		WHERE tntr.parent="{lab_test}"
	""", as_dict=True)
	return {
		"options": options,
		"units": units,
		"orders": orders
	}

@frappe.whitelist()
def get_lab_test_form_tests(lab_test):
	return frappe.db.sql(f"""
	SELECT tntr.name, tntr.template, tntr.report_code as parent_template, tltt.attribute_options, tntr.result_percentage,  tntr.control_type, 
		tltu.lab_test_uom as conv_unit, tltu2.si_unit_name as si_unit, tntr.lab_test_comment, tntr.status, tntr.lab_test_name, tntr.result_value,
		tntr.host_code, tntr.secondary_uom_result
		FROM `tabNormal Test Result` tntr 
		INNER JOIN `tabLab Test Template` tltt ON tntr.template=tltt.name
		LEFT JOIN `tabLab Test Template` tltt2 ON tntr.report_code=tltt2.name
		LEFT JOIN `tabLab Test UOM` tltu ON tltu.name=tntr.lab_test_uom
		LEFT JOIN `tabLab Test UOM` tltu2 ON tltu2.name=tntr.secondary_uom
		WHERE tntr.parent="{lab_test}"
		ORDER BY ISNULL(tltt2.printing_order), ISNULL(tltt.printing_order), cast(tltt2.printing_order as unsigned), cast(tltt.printing_order as unsigned)
		;
	""", as_dict=True)


@frappe.whitelist()
def apply_test_button_action(action, tests, test_name, sample):
	where_stmt = ""
	if action == "Received":
		if frappe.db.get_value("Sample Collection", sample, ["docstatus"]) != 1:
			frappe.throw("Sample is not collected")
		where_stmt = "(status is NULL or status not in ('Released', 'Finalized'))"
	elif action == "Released":
		where_stmt = "status='Received' AND result_value !='' AND result_value IS NOT NULL "
	elif action == 'Finalized':
		where_stmt = "status='Released'"
	elif action == 'Rejected':
		where_stmt = "status='Released'"
	elif action == 'definalize':
		where_stmt = "status='Finalized'"
		action = 'Released'
	else: frappe.throw("Undefined action: " + action)
	tests = json.loads(tests)
	tests = [f"'{s}'" for s in tests]
	query= """
	UPDATE `tabNormal Test Result` SET status='{action}'
	WHERE name in ({tests}) AND {where_stmt}
	""".format(action=action, tests=",".join(tests), where_stmt=where_stmt)
	frappe.db.sql(query)
	frappe.db.commit()
	lab_test = frappe.get_doc('Lab Test', test_name)
	if lab_test:
		lab_test.set_test_status()
	if action == "Received":
		infinty_tests = frappe.db.sql("""
			SELECT host_code FROM `tabNormal Test Result`
			WHERE name in ({tests}) AND status='Received' AND host_name='Inifinty'
		""".format(tests=",".join(tests)), as_dict=True)
		infinty_tests = list(set([test['host_code'] for test in infinty_tests if test['host_code'] and test['host_code'] !=""]))
		if len(infinty_tests) > 0:
			send_infinty_msg_with_patient(test_name, sample, infinty_tests)