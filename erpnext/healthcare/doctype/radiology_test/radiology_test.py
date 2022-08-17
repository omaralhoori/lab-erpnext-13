# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RadiologyTest(Document):
	def after_insert(self):
		if self.template:
			self.load_test_from_template()
	
	def load_test_from_template(self):
		rad_test = self
		create_rad_test_from_template(rad_test)
		self.reload()


def create_rad_test_from_template(rad_test):
	templates = rad_test.template if isinstance(rad_test.template, list) else [rad_test.template]
	for template_name in templates:
		if template_name.get("template"):
			template_name = template_name.get("template")
		template = frappe.get_doc('Lab Test Template', template_name)

		rad_test = load_result_format(rad_test, template)


def load_result_format(lab_test, template, depth=1):
	if depth > 3 : return lab_test
	if template.lab_test_template_type == 'Single'  and template.lab_test_group == "Radiology Services":
		create_results(template, lab_test)

	elif template.lab_test_template_type == 'Multiline':
		create_multiline_normals(template, lab_test)

	elif template.lab_test_template_type == 'Grouped':
		# Iterate for each template in the group and create one result for all.
		for lab_test_group in template.lab_test_groups:
			if lab_test_group.lab_test_template:
				template_in_group = frappe.get_doc('Lab Test Template', lab_test_group.lab_test_template)
				#create_multiline_normals(template_in_group, lab_test)
				lab_test = load_result_format(lab_test, template_in_group, depth + 1)

	lab_test.save(ignore_permissions=True) # Insert the result
	return lab_test

def create_multiline_normals(template, lab_test):
		if len(template.lab_test_groups)> 0:
			for lab_test_group in template.lab_test_groups:
				# Template_in_group = None
				if lab_test_group.lab_test_template:
					template_in_group = frappe.get_doc('Lab Test Template', lab_test_group.lab_test_template)
					if template_in_group:
						if template_in_group.lab_test_template_type == 'Single' and template_in_group.lab_test_group == "Radiology Services":
							create_results(template_in_group, lab_test)
		else:
			if template.lab_test_group == "Radiology Services" :
				create_results(template, lab_test)


def create_results(template, lab_test):
	result = lab_test.append('test_results')
	result.test_template = template.name
	result.test_result = template.result_legend


import json
@frappe.whitelist()
def finalize_selected(tests):
	tests = json.loads(tests)
	frappe.db.sql("""
	UPDATE `tabRadiology Test` SET record_status="Finalized"
	WHERE name in ({tests}) AND record_status IN ('Released')
	""".format(tests=",".join(tests)))

@frappe.whitelist()
def definalize_selected(tests):
	tests = json.loads(tests)
	frappe.db.sql("""
	UPDATE `tabRadiology Test` SET record_status="Released"
	WHERE name in ({tests}) AND record_status IN ('Finalized')
	""".format(tests=",".join(tests)))


@frappe.whitelist()
def unrelease_selected(tests):
	tests = json.loads(tests)
	frappe.db.sql("""
	UPDATE `tabRadiology Test` SET record_status="Draft"
	WHERE name in ({tests}) AND record_status IN ('Released')
	""".format(tests=",".join(tests)))