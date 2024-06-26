# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc


class LabTestTemplate(Document):
	def after_insert(self):
		if not self.item:
			create_item_from_template(self)

	def validate(self):
		if self.is_billable and (not self.lab_test_rate or self.lab_test_rate <= 0.0):
			frappe.throw(_('Standard Selling Rate should be greater than zero.'))

		self.validate_conversion_factor()
		self.enable_disable_item()

	def has_radiology(self):
		rad_tests = frappe.db.sql("""SELECT count(tltt2.name)  FROM `tabLab Test Group Template` tltgt 
   		INNER JOIN `tabLab Test Template` tltt ON tltgt.lab_test_template =tltt.name
   		INNER JOIN `tabLab Test Template` tltt2 ON tltt2.name=tltgt.parent
   		WHERE tltt.lab_test_group ='Radiology Services' AND tltt2.name='{template_name}'""".format(template_name=self.name))[0][0]
		return rad_tests > 0

	def has_clinical(self):
		clnc_tests = frappe.db.sql("""SELECT count(tltt2.name)  FROM `tabLab Test Group Template` tltgt 
   		INNER JOIN `tabLab Test Template` tltt ON tltgt.lab_test_template =tltt.name
   		INNER JOIN `tabLab Test Template` tltt2 ON tltt2.name=tltgt.parent
   		WHERE tltt.lab_test_group ='Clinical Services' AND tltt2.name='{template_name}'""".format(template_name=self.name))[0][0]
		return clnc_tests > 0

	def on_update(self):
		# If change_in_item update Item and Price List
		options = ["<option>" + item.form_attribute_description + "</option>" for item in self.lab_test_attribute]
		self.db_set("attribute_options", "".join(options))
		if self.change_in_item and self.is_billable and self.item:
			self.update_item()
			item_price = self.item_price_exists()
			if not item_price:
				if self.lab_test_rate and self.lab_test_rate > 0.0:
					price_list_name = frappe.db.get_value('Selling Settings', None, 'selling_price_list') or frappe.db.get_value('Price List', {'selling': 1})
					make_item_price(self.lab_test_code, price_list_name, self.lab_test_rate)
			else:
				frappe.db.set_value('Item Price', item_price, 'price_list_rate', self.lab_test_rate)

			self.db_set('change_in_item', 0)

		elif not self.is_billable and self.item:
			frappe.db.set_value('Item', self.item, 'disabled', 1)
		old_doc = self.get_doc_before_save()
		if not self.expected_tat_seconds or (old_doc and (old_doc.expected_tat != self.expected_tat or old_doc.expected_tat_unit != self.expected_tat_unit)):
			self.set_tat_seconds()
		self.reload()
	def set_tat_seconds(self):
		if self.expected_tat and self.expected_tat_unit:
				self.expected_tat_seconds = self.get_tat_time_seconds(self.expected_tat, self.expected_tat_unit)
				self.db_set("expected_tat_seconds", self.expected_tat_seconds)
	def get_tat_time_seconds(self, tat, tat_unit):
		import datetime
		if tat_unit == 'Minute':
			return datetime.timedelta(minutes=tat).total_seconds()
		if tat_unit == 'Hour':
			return datetime.timedelta(hours=tat).total_seconds()
		if tat_unit == 'Day':
			return datetime.timedelta(days=tat).total_seconds()
		if tat_unit == 'Month':
			return datetime.timedelta(days= tat * 30).total_seconds()
		return tat
	def on_trash(self):
		# Remove template reference from item and disable item
		if self.item:
			try:
				item = self.item
				self.db_set('item', '')
				frappe.delete_doc('Item', item)
			except Exception:
				frappe.throw(_('Not permitted. Please disable the Lab Test Template'))

	def enable_disable_item(self):
		if self.is_billable:
			if self.disabled:
				frappe.db.set_value('Item', self.item, 'disabled', 1)
			else:
				frappe.db.set_value('Item', self.item, 'disabled', 0)

	def update_item(self):
		item = frappe.get_doc('Item', self.item)
		if item:
			item.update({
				'item_name': self.lab_test_name,
				'item_group': self.lab_test_group,
				'disabled': 0,
				'standard_rate': self.lab_test_rate,
				'description': self.lab_test_description
			})
			item.flags.ignore_mandatory = True
			item.save(ignore_permissions=True)

	def item_price_exists(self):
		item_price = frappe.db.exists({'doctype': 'Item Price', 'item_code': self.lab_test_code})
		if item_price:
			return item_price[0][0]
		return False

	def validate_conversion_factor(self):
		if self.lab_test_template_type == 'Single' and self.secondary_uom and not self.conversion_factor:
			frappe.throw(_('Conversion Factor is mandatory'))
		if self.lab_test_template_type == 'Compound':
			for item in self.normal_test_templates:
				if item.secondary_uom and not item.conversion_factor:
					frappe.throw(_('Row #{0}: Conversion Factor is mandatory').format(item.idx))
		if self.lab_test_template_type == 'Grouped':
			for group in self.lab_test_groups:
				if group.template_or_new_line == 'Add New Line' and group.secondary_uom and not group.conversion_factor:
					frappe.throw(_('Row #{0}: Conversion Factor is mandatory').format(group.idx))


def create_item_from_template(doc):
	uom = frappe.db.exists('UOM', 'Unit') or frappe.db.get_single_value('Stock Settings', 'stock_uom')
	# Insert item
	item =  frappe.get_doc({
		'doctype': 'Item',
		'item_code': doc.lab_test_code,
		'item_name':doc.lab_test_name,
		'item_group': doc.lab_test_group,
		'description':doc.lab_test_description,
		'is_sales_item': 1,
		'is_service_item': 1,
		'is_purchase_item': 0,
		'is_stock_item': 0,
		'include_item_in_manufacturing': 0,
		'show_in_website': 0,
		'is_pro_applicable': 0,
		'disabled': 0 if doc.is_billable and not doc.disabled else doc.disabled,
		'stock_uom': uom
	}).insert(ignore_permissions=True, ignore_mandatory=True)

	# Insert item price
	if doc.is_billable and doc.lab_test_rate != 0.0:
		price_list_name = frappe.db.get_value('Selling Settings', None, 'selling_price_list') or frappe.db.get_value('Price List', {'selling': 1})
		if doc.lab_test_rate:
			make_item_price(item.name, price_list_name, doc.lab_test_rate)
		else:
			make_item_price(item.name, price_list_name, 0.0)
	# Set item in the template
	frappe.db.set_value('Lab Test Template', doc.name, 'item', item.name)

	doc.reload()

def make_item_price(item, price_list_name, item_price):
	frappe.get_doc({
		'doctype': 'Item Price',
		'price_list': price_list_name,
		'item_code': item,
		'price_list_rate': item_price
	}).insert(ignore_permissions=True, ignore_mandatory=True)

@frappe.whitelist()
def change_test_code_from_template(lab_test_code, doc):
	doc = frappe._dict(json.loads(doc))

	if frappe.db.exists({'doctype': 'Item', 'item_code': lab_test_code}):
		frappe.throw(_('Lab Test Item {0} already exist').format(lab_test_code))
	else:
		rename_doc('Item', doc.name, lab_test_code, ignore_permissions=True)
		frappe.db.set_value('Lab Test Template', doc.name, 'lab_test_code', lab_test_code)
		frappe.db.set_value('Lab Test Template', doc.name, 'lab_test_name', lab_test_code)
		rename_doc('Lab Test Template', doc.name, lab_test_code, ignore_permissions=True)
	return lab_test_code


@frappe.whitelist()
def get_package_items(test_template):
	#template = frappe.get_doc("Lab Test Template", lab_test_template)
	return frappe.db.sql(f"""
		   SELECT ltt.lab_test_code as item FROM `tabLab Test Group Template` as ntt 
		LEFT JOIN `tabLab Test Template` as ltt ON ntt.lab_test_template =ltt.name
		WHERE ntt.parent='{test_template}' AND ltt.is_billable=1

	""", as_dict=True)


@frappe.whitelist()
def get_package_templates(test_template):
	#template = frappe.get_doc("Lab Test Template", lab_test_template)
	return frappe.db.sql(f"""
		   SELECT ntt.lab_test_template as template FROM `tabLab Test Group Template` as ntt 
		WHERE ntt.parent='{test_template}'
	""", as_dict=True)

def enable_disable_templates():
	frappe.db.sql("""
		update 
		`tabItem` ti
		INNER JOIN 
		`tabLab Test Template` tltt
		ON tltt.item=ti.name
		set ti.disabled=0, tltt.disabled=0
		WHERE tltt.effective_date <= now()
		;
	""")
	frappe.db.sql("""
		update 
		`tabItem` ti
		INNER JOIN 
		`tabLab Test Template` tltt
		ON tltt.item=ti.name
		set ti.disabled=1, tltt.disabled=1
		WHERE tltt.expiry_date  < now()
		;
	""")

	frappe.db.commit()