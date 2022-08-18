# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, cstr
from collections import defaultdict, OrderedDict
from frappe.utils.pdf import get_pdf

@frappe.whitelist()
def claimrep(sales_invoice):
	cur_doc = frappe.get_doc("Sales Invoice",sales_invoice)
	if cur_doc.insurance_party_type != 'Insurance Company' and cur_doc.insurance_party_type != 'Payer':
		return

	if cur_doc.items:
		values = get_formatted_result_for_invoice_items(cur_doc)

		formatted_result = values.get("formatted_result")
		item_group_dict = values.get("item_group_dict")
		result_items_name = values.get("result_items_name")

		#for result in result_items_name:
		#	frappe.msgprint(result)
		#add_score_and_recalculate_grade(result, result.assessment_criteria,academic_year_term_dict[result.academic_year,result.academic_term])

		template=""
		if cur_doc.insurance_party_type == 'Insurance Company':
			template = "erpnext/accounts/doctype/sales_invoice/insurance_insurd_claim.html"

		if cur_doc.insurance_party_type == 'Payer':
			template = "erpnext/accounts/doctype/sales_invoice/insurance_payer_claim.html"

		base_template_path = "frappe/www/printview.html"
		
		add_letterhead = frappe.db.get_value("Letter Head", {"is_default": 1}, ["content", "footer"], as_dict=True) or {}
		

		from frappe.www.printview import get_letter_head
		letterhead = get_letter_head(frappe._dict({"letter_head": cur_doc.letter_head}), not add_letterhead)
		
		html = frappe.render_template(template,
			{
				"doc": cur_doc,
				"letterhead": letterhead and letterhead.get('content', None),
				"add_letterhead": add_letterhead if add_letterhead else 0,
				"lab_test_result": formatted_result,
				"item_groups": item_group_dict,
				"result_items_name": result_items_name
			})

	
		final_template = frappe.render_template(base_template_path, {"body": html, "title": "Claim Card"})

		content = get_pdf(final_template)
		frappe.msgprint('content')
		frappe.response.filename = "Claim" + cur_doc.name + ".pdf"
		frappe.response.filecontent = content
		frappe.response.type = "pdf"

def get_formatted_result_for_invoice_items(doc):
	def get_lab_test_template(doc, item_code):
		template = frappe.get_doc("Lab Test Template", {"item": item_code})
		if not template: return False
		if not template.is_billable or len(template.lab_test_groups) == 0: return False

		results = frappe.db.sql("""
			SELECT tltt2.item as lab_test_name FROM `tabLab Test Group Template` tltgt 
			INNER JOIN `tabLab Test Template` tltt2 ON tltt2.name=tltgt.lab_test_template AND tltt2.is_billable=1 
			WHERE tltgt.parent="{template_name}";
		""".format(template_name=template.name), as_dict=True)
		if not results: return False
		return results

	formatted_result = defaultdict(dict)
	result_items_name = defaultdict(dict)
	item_group_dict = OrderedDict()

	for lab_test in doc.items:
		result = get_lab_test_template(doc,lab_test.item_code)
		if not result:
			item = frappe.get_doc("Item",lab_test.item_code)
			Claim_type = frappe.db.get_value("Item Group", {"name": item.item_group}, ["claim_type"]) or item.item_group
			item.item_group = Claim_type
			item_group_dict[item.item_group]=item.item_group

			if not formatted_result["item_group",item.item_group]:
				formatted_result["item_group",item.item_group] = defaultdict(dict)
				if not formatted_result["item_group",item.item_group]["amount"]:
					formatted_result["item_group",item.item_group]["amount"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["amount"] = 0
				if not formatted_result["item_group",item.item_group]["qty"]:
					formatted_result["item_group",item.item_group]["qty"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["qty"] = 0
				if not formatted_result["item_group",item.item_group]["patient_share"]:
					formatted_result["item_group",item.item_group]["patient_share"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["patient_share"] = 0
				if not formatted_result["item_group",item.item_group]["contract_discount"]:
					formatted_result["item_group",item.item_group]["contract_discount"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["contract_discount"] = 0
				if not formatted_result["item_group",item.item_group]["discount_amount"]:
					formatted_result["item_group",item.item_group]["discount_amount"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["discount_amount"] = 0

			if not result_items_name["item_name",lab_test.item_name]:
				result_items_name["item_name",lab_test.item_name] = defaultdict(dict)

			if not formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]:
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name] = defaultdict(dict)

			if not formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["item_des"]:
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["item_des"] = defaultdict(dict)
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["item_des"] = lab_test.item_name

			if not formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["amount"]:
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["amount"] = defaultdict(dict)
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["amount"] = 0
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["amount"] = lab_test.amount
				formatted_result["item_group",item.item_group]["amount"] += lab_test.amount
				#frappe.msgprint('44444')
				#frappe.msgprint(formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["amount"])
				#frappe.msgprint('5555')

			if not formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["qty"]:
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["qty"] = defaultdict(dict)
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["qty"] = 0
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["qty"] = lab_test.qty
				formatted_result["item_group",item.item_group]["qty"] += lab_test.qty

			if not formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["patient_share"]:
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["patient_share"] = defaultdict(dict)
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["patient_share"] = 0
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["patient_share"] = lab_test.patient_share + lab_test.cash_discount
				formatted_result["item_group",item.item_group]["patient_share"] += (lab_test.patient_share + lab_test.cash_discount)

			if not formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["contract_discount"]:
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["contract_discount"] = defaultdict(dict)
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["contract_discount"] = 0
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["contract_discount"] = lab_test.contract_discount
				formatted_result["item_group",item.item_group]["contract_discount"] += lab_test.contract_discount

			if not formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["contract_percentage"]:
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["contract_percentage"] = defaultdict(dict)
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["contract_percentage"] = 0
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["contract_percentage"] = lab_test.contract_percentage

			if not formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["discount_amount"]:
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["discount_amount"] = defaultdict(dict)
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["discount_amount"] = 0
				formatted_result["item_group",item.item_group]["item_name",lab_test.item_name]["discount_amount"] = lab_test.discount_amount
				formatted_result["item_group",item.item_group]["discount_amount"] += lab_test.discount_amount

		else:
			org_test_price = 0
			package_test_price = lab_test.amount
			for res in result:
				price_list_for_res = frappe.db.get_value("Item Price", {"price_list": doc.selling_price_list,"selling": 1,"item_code": res['lab_test_name']}, ["price_list_rate"]) or 0
				org_test_price += price_list_for_res
			
			diff_percentage = 0.0
			diff_percentage = package_test_price / org_test_price

			for res in result:
				lab_doc = frappe.get_doc("Lab Test Template", {"name": res['lab_test_name']})
				#frappe.msgprint(cstr(lab_doc))
				
				#item = frappe.get_doc("Item", {"name": lab_doc.item})
				#item_group_dict[item.item_group]=item.item_group

				item = frappe.get_doc("Item",lab_doc.item)
				Claim_type = frappe.db.get_value("Item Group", {"name": item.item_group}, ["claim_type"]) or item.item_group
				item.item_group = Claim_type
				item_group_dict[item.item_group]=item.item_group





				if not formatted_result["item_group",item.item_group]:
					formatted_result["item_group",item.item_group] = defaultdict(dict)
					if not formatted_result["item_group",item.item_group]["amount"]:
						formatted_result["item_group",item.item_group]["amount"] = defaultdict(dict)
						formatted_result["item_group",item.item_group]["amount"] = 0
					if not formatted_result["item_group",item.item_group]["qty"]:
						formatted_result["item_group",item.item_group]["qty"] = defaultdict(dict)
						formatted_result["item_group",item.item_group]["qty"] = 0
					if not formatted_result["item_group",item.item_group]["patient_share"]:
						formatted_result["item_group",item.item_group]["patient_share"] = defaultdict(dict)
						formatted_result["item_group",item.item_group]["patient_share"] = 0
					if not formatted_result["item_group",item.item_group]["contract_discount"]:
						formatted_result["item_group",item.item_group]["contract_discount"] = defaultdict(dict)
						formatted_result["item_group",item.item_group]["contract_discount"] = 0
					if not formatted_result["item_group",item.item_group]["discount_amount"]:
						formatted_result["item_group",item.item_group]["discount_amount"] = defaultdict(dict)
						formatted_result["item_group",item.item_group]["discount_amount"] = 0

				if not result_items_name["item_name",lab_test.item_name]:
					result_items_name["item_name",lab_doc.lab_test_name] = defaultdict(dict)

				if not formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]:
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name] = defaultdict(dict)

				if not formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["item_des"]:
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["item_des"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["item_des"] = lab_doc.lab_test_name

				price_list_for_res = frappe.db.get_value("Item Price", {"price_list": doc.selling_price_list,"selling": 1,"item_code": res['lab_test_name']}, ["price_list_rate"]) or 0
				new_amount =flt(price_list_for_res * diff_percentage, lab_test.precision("amount"))
				patient_share = flt(new_amount * doc.charged_percentage / 100 , lab_test.precision("patient_share"))
				contract_discount= flt(new_amount * doc.additional_discount_percentage / 100 , lab_test.precision("contract_discount"))
				discount_amount= flt(new_amount * doc.coverage_percentage / 100 , lab_test.precision("discount_amount"))

				new_amount = round(new_amount,3)
				patient_share = round(patient_share,3)
				contract_discount = round(contract_discount,3)
				discount_amount = round(discount_amount,3)

				if not formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["amount"]:
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["amount"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["amount"] = 0
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["amount"] = new_amount
					formatted_result["item_group",item.item_group]["amount"] += new_amount

				if not formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["qty"]:
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["qty"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["qty"] = 0
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["qty"] = lab_test.qty
					formatted_result["item_group",item.item_group]["qty"] += lab_test.qty


				if not formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["patient_share"]:
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["patient_share"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["patient_share"] = 0
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["patient_share"] = patient_share
					formatted_result["item_group",item.item_group]["patient_share"] += patient_share

				if not formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["contract_discount"]:
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["contract_discount"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["contract_discount"] = 0
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["contract_discount"] = contract_discount
					formatted_result["item_group",item.item_group]["contract_discount"] += contract_discount

				if not formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["contract_percentage"]:
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["contract_percentage"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["contract_percentage"] = 0
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["contract_percentage"] = new_amount

				if not formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["discount_amount"]:
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["discount_amount"] = defaultdict(dict)
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["discount_amount"] = 0
					formatted_result["item_group",item.item_group]["item_name",lab_doc.lab_test_name]["discount_amount"] = discount_amount
					formatted_result["item_group",item.item_group]["discount_amount"] += discount_amount


	#print('ffffffffffffffffffffffff')
	#print(formatted_result)

	return {
		"formatted_result": formatted_result,
		"item_group_dict": item_group_dict,
		"result_items_name": result_items_name
	}
