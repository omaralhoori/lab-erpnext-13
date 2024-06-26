# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os

import dateutil
import frappe, random
from frappe import _
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import cint, cstr, getdate
from frappe.utils.nestedset import get_root_of
from frappe.model.naming import make_autoname
from erpnext import get_default_currency
from erpnext.accounts.party import get_dashboard_info
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import (
	get_income_account,
	get_receivable_account,
	send_registration_sms,
)

from erpnext.healthcare.doctype.embassy_report.embassy_report import calculate_patient_age

class Patient(Document):
	def onload(self):
		'''Load address and contacts in `__onload`'''
		load_address_and_contact(self)
		self.load_dashboard_info()

	def validate(self):
		self.set_full_name()

	def before_insert(self):
		self.create_random_password()
		format_ser = "PTN" + ".####"
		prg_serial = make_autoname(format_ser)
		self.patient_number = prg_serial
		self.set_missing_customer_details()

	def after_insert(self):
		self.generate_qrcode()
		if frappe.db.get_single_value('Healthcare Settings', 'collect_registration_fee'):
			frappe.db.set_value('Patient', self.name, 'status', 'Disabled')
		else:
			send_registration_sms(self)
		self.reload()
	def create_random_password(self):
		if not self.patient_password or self.patient_password == "":
			self.patient_password = random.randrange(1234567, 9876543)

	def generate_qrcode(self):
		if not self.patient_password:
			self.create_random_password()
		qrcode_gen(str(self.patient_password), self.name)
		frappe.db.commit()

	def on_update(self):
		if frappe.db.get_single_value('Healthcare Settings', 'link_customer_to_patient'):
			if self.customer:
				customer = frappe.get_doc('Customer', self.customer)
				if self.customer_group:
					customer.customer_group = self.customer_group
				if self.territory:
					customer.territory = self.territory

				customer.customer_name = self.patient_name
				customer.default_price_list = self.default_price_list
				customer.default_currency = self.default_currency
				customer.language = self.language
				customer.customer_mobile_no = self.mobile
				customer.ignore_mandatory = True
				customer.save(ignore_permissions=True)
			else:
				create_customer(self)

		self.set_contact() # add or update contact
		self.update_patient_fields()
		if not self.user_id and self.email and self.invite_user:
			self.create_website_user()

	
	def update_patient_fields(self):
		old_doc = self.get_doc_before_save()
		if not old_doc: return
		if old_doc.patient_name != self.patient_name: self.update_patient_name()
		if old_doc.social_status != self.social_status: self.update_social_status()
		if old_doc.passport_no != self.passport_no: self.update_passport_no()
		if old_doc.passport_issue_date != self.passport_issue_date: self.update_passport_issue_date()
		if old_doc.passport_place != self.passport_place: self.update_passport_place()
		if old_doc.passport_expiry_date != self.passport_expiry_date: self.update_passport_expiry_date()
		if old_doc.mobile != self.mobile: self.update_mobile()
		if old_doc.dob != self.dob: self.update_dob()
		if old_doc.sex != self.sex: self.update_gender()
		if old_doc.country != self.country: self.update_country()

	def update_country(self):
		frappe.db.set_value("Embassy Report", {"patient": self.name}, "nationality", self.country)
	
	
	def update_gender(self):
		frappe.db.set_value("Lab Test", {"patient": self.name}, "patient_sex", self.sex)
		frappe.db.set_value("Radiology Test", {"patient": self.name}, "patient_sex", self.sex)
		frappe.db.set_value("Sample Collection", {"patient": self.name}, "patient_sex", self.sex)
		frappe.db.set_value("Embassy Report", {"patient": self.name}, "gender", self.sex)

	def update_dob(self):
		frappe.db.set_value("Lab Test", {"patient": self.name}, "patient_age", self.get_age())
		frappe.db.set_value("Radiology Test", {"patient": self.name}, "patient_age", self.get_age())
		frappe.db.set_value("Sample Collection", {"patient": self.name}, "patient_age", self.get_age())
		frappe.db.set_value("Embassy Report", {"patient": self.name}, "age", calculate_patient_age(self))

	def update_mobile(self):
		frappe.db.set_value("Sales Invoice", {"patient": self.name}, "mobile_no", self.mobile)
		frappe.db.set_value("Customer", self.name, "customer_mobile_no", self.mobile)
		frappe.db.set_value("Lab Test", {"patient": self.name}, "patient_mobile", self.mobile)
		frappe.db.set_value("Radiology Test", {"patient": self.name}, "patient_mobile", self.mobile)

	def update_passport_expiry_date(self):
		frappe.db.set_value("Sales Invoice", {"patient": self.name}, "passport_expiry_date", self.passport_expiry_date)

	def update_passport_place(self):
		frappe.db.set_value("Sales Invoice", {"patient": self.name}, "passport_place", self.passport_place)
		frappe.db.set_value("Embassy Report", {"patient": self.name}, "passport_place_of_issue", self.passport_place)

	def update_passport_issue_date(self):
		frappe.db.set_value("Sales Invoice", {"patient": self.name}, "passport_issue_date", self.passport_issue_date)
		frappe.db.set_value("Embassy Report", {"patient": self.name}, "passport_date_of_issue", self.passport_issue_date)

	def update_passport_no(self):
		frappe.db.set_value("Sales Invoice", {"patient": self.name}, "passport_no", self.passport_no)
		frappe.db.set_value("Embassy Report", {"patient": self.name}, "passport_no", self.passport_no)

	def update_social_status(self):
		frappe.db.set_value("Sales Invoice", {"patient": self.name}, "social_status", self.social_status)
		frappe.db.set_value("Embassy Report", {"patient": self.name}, "status", self.social_status)

	def update_patient_name(self):
		old_name = self.name
		frappe.db.set_value("Sales Invoice", {"patient": old_name}, "patient_name", self.patient_name)
		frappe.db.set_value("Sales Invoice", {"patient": old_name}, "customer_name", self.patient_name)
		frappe.db.set_value("Sales Invoice", {"patient": old_name}, "title", self.patient_name)
		frappe.db.set_value("Customer", old_name, "customer_name", self.patient_name)
		frappe.db.set_value("Lab Test", {"patient": old_name}, "patient_name", self.patient_name)
		frappe.db.set_value("Sample Collection", {"patient":old_name}, "patient_name", self.patient_name)
		frappe.db.set_value("Radiology Test", {"patient": old_name}, "patient_name", self.patient_name)
		frappe.db.set_value("Embassy Report", {"patient":old_name}, "patient_name", self.patient_name)
		frappe.db.set_value("GL Entry", {"against":old_name}, "against", self.patient_name)
		frappe.db.set_value("Payment Entry", {"party":old_name}, "party_name", self.patient_name)
		frappe.db.set_value("Payment Entry", {"party":old_name}, "title", self.patient_name)
		frappe.rename_doc("Patient", old_name, self.patient_name)
		frappe.rename_doc("Customer", old_name, self.patient_name)

	def load_dashboard_info(self):
		if self.customer:
			info = get_dashboard_info('Customer', self.customer, None)
			self.set_onload('dashboard_info', info)

	def set_full_name(self):
		if self.last_name:
			self.patient_name = ' '.join(filter(None, [self.first_name, self.middle_name , self.third_name ,self.last_name]))
		else:
			self.patient_name = self.first_name

	def set_missing_customer_details(self):
		if not self.customer_group:
			self.customer_group = frappe.db.get_single_value('Selling Settings', 'default_patient_group') or get_root_of('Customer Group')
		if not self.territory:
			self.territory = frappe.db.get_single_value('Selling Settings', 'territory') or get_root_of('Territory')
		if not self.default_price_list:
			self.default_price_list = frappe.db.get_single_value('Selling Settings', 'selling_price_list')

		if not self.customer_group or not self.territory or not self.default_price_list:
			frappe.msgprint(_('Please set defaults for Customer Group, Territory and Selling Price List in Selling Settings'), alert=True)

		if not self.default_currency:
			self.default_currency = get_default_currency()
		if not self.language:
			self.language = frappe.db.get_single_value('System Settings', 'language')

	def create_website_user(self):
		users = frappe.db.get_all('User', fields=['email', 'mobile_no'], or_filters={'email': self.email, 'mobile_no': self.mobile})
		if users and users[0]:
			frappe.throw(_("User exists with Email {}, Mobile {}<br>Please check email / mobile or disable 'Invite as User' to skip creating User")
				.format(frappe.bold(users[0].email), frappe.bold(users[0].mobile_no)), frappe.DuplicateEntryError)

		user = frappe.get_doc({
			'doctype': 'User',
			'first_name': self.first_name,
			'last_name': self.last_name,
			'email': self.email,
			'user_type': 'Website User',
			'gender': self.sex,
			'phone': self.phone,
			'mobile_no': self.mobile,
			'birth_date': self.dob
		})
		user.flags.ignore_permissions = True
		user.enabled = True
		user.send_welcome_email = True
		user.add_roles('Patient')
		self.db_set('user_id', user.name)

	def autoname(self):
		patient_name_by = frappe.db.get_single_value('Healthcare Settings', 'patient_name_by')
		if patient_name_by == 'Patient Name':
			self.name = self.get_patient_name()
		else:
			set_name_by_naming_series(self)

	def get_patient_name(self):
		self.set_full_name()
		name = self.patient_name
		if frappe.db.get_value('Patient', name):
			count = frappe.db.sql("""select ifnull(MAX(CAST(SUBSTRING_INDEX(name, ' ', -1) AS UNSIGNED)), 0) from tabPatient
				 where name like %s""", "%{0} - %".format(name), as_list=1)[0][0]
			count = cint(count) + 1
			return "{0} - {1}".format(name, cstr(count))

		return name

	@property
	def age(self):
		if not self.dob:
			return
		dob = getdate(self.dob)
		age = dateutil.relativedelta.relativedelta(getdate(), dob)
		return age

	def get_age(self):
		age = self.age
		if not age:
			return
		age_str = str(age.years) + ' ' + _("Years(s)") + ' ' + str(age.months) + ' ' + _("Month(s)") + ' ' + str(age.days) + ' ' + _("Day(s)")
		return age_str

	@frappe.whitelist()
	def invoice_patient_registration(self):
		if frappe.db.get_single_value('Healthcare Settings', 'collect_registration_fee'):
			company = frappe.defaults.get_user_default('company')
			if not company:
				company = frappe.db.get_single_value('Global Defaults', 'default_company')

			sales_invoice = make_invoice(self.name, company)
			sales_invoice.save(ignore_permissions=True)
			frappe.db.set_value('Patient', self.name, 'status', 'Active')
			send_registration_sms(self)

			return {'invoice': sales_invoice.name}

	def set_contact(self):
		contact = get_default_contact(self.doctype, self.name)

		if contact:
			old_doc = self.get_doc_before_save()
			if not old_doc:
				return

			if old_doc.email != self.email or old_doc.mobile != self.mobile or old_doc.phone != self.phone:
				self.update_contact(contact)
		else:
			if self.customer:
				# customer contact exists, link patient
				contact = get_default_contact('Customer', self.customer)

			if contact:
				self.update_contact(contact)
			else:
				self.reload()
				if self.email or self.mobile or self.phone:
					contact = frappe.get_doc({
						'doctype': 'Contact',
						'first_name': self.first_name,
						'middle_name': self.middle_name,
						'last_name': self.last_name,
						'gender': self.sex,
						'is_primary_contact': 1
					})
					contact.append('links', dict(link_doctype='Patient', link_name=self.name))
					if self.customer:
						contact.append('links', dict(link_doctype='Customer', link_name=self.customer))

					contact.insert(ignore_permissions=True)
					self.update_contact(contact.name)

	def update_contact(self, contact):
		contact = frappe.get_doc('Contact', contact)

		if not contact.has_link(self.doctype, self.name):
			contact.append('links', dict(link_doctype=self.doctype, link_name=self.name))

		if self.email and self.email != contact.email_id:
			for email in contact.email_ids:
				email.is_primary = True if email.email_id == self.email else False
			contact.add_email(self.email, is_primary=True)
			contact.set_primary_email()

		if self.mobile and self.mobile != contact.mobile_no:
			for mobile in contact.phone_nos:
				mobile.is_primary_mobile_no = True if mobile.phone == self.mobile else False
			contact.add_phone(self.mobile, is_primary_mobile_no=True)
			contact.set_primary('mobile_no')

		if self.phone and self.phone != contact.phone:
			for phone in contact.phone_nos:
				phone.is_primary_phone = True if phone.phone == self.phone else False
			contact.add_phone(self.phone, is_primary_phone=True)
			contact.set_primary('phone')

		contact.flags.skip_patient_update = True
		contact.save(ignore_permissions=True)
@frappe.whitelist()
def generate_patient_qrcode(patient_name):
	patinet = frappe.get_doc("Patient", patient_name)
	if patinet:
		patinet.generate_qrcode()

@frappe.whitelist()
def qrcode_gen(customer_password,docname):
	patient_number = frappe.db.get_value("Patient", docname, "patient_number")
	codname = customer_password + '_' + patient_number 

	nyear= frappe.utils.now_datetime().strftime('%Y')
	nmonth= frappe.utils.now_datetime().strftime('%m')
	qrpath = '/public/files/patientqrcode/' + nyear + '/' + nmonth + '/'
	qrpath_db = '/files/patientqrcode/' + nyear + '/' + nmonth + '/' + codname

	frappe.utils.generate_qrcode(frappe.db.get_single_value("Healthcare Settings", "result_url"),codname,qrpath, '', 'test-result')
	frappe.db.set_value("Patient", {"name": docname}, "qrcode_path", qrpath_db)

def create_customer(doc):
	customer = frappe.get_doc({
		'doctype': 'Customer',
		'customer_name': doc.patient_name,
		'customer_group': doc.customer_group or frappe.db.get_single_value('Selling Settings', 'customer_group'),
		'territory' : doc.territory or frappe.db.get_single_value('Selling Settings', 'territory'),
		'customer_type': 'Individual',
		'default_currency': doc.default_currency,
		'default_price_list': doc.default_price_list,
		'language': doc.language,
		'customer_mobile_no': doc.mobile,
		'country': doc.country,
		'customer_number': doc.patient_number,
		'national_id': doc.uid,
		'gender': doc.sex
	}).insert(ignore_permissions=True, ignore_mandatory=True)

	frappe.db.set_value('Patient', doc.name, 'customer', customer.name)
	frappe.msgprint(_('Customer {0} is created.').format(customer.name), alert=True)

def make_invoice(patient, company):
	uom = frappe.db.exists('UOM', 'Nos') or frappe.db.get_single_value('Stock Settings', 'stock_uom')
	sales_invoice = frappe.new_doc('Sales Invoice')
	sales_invoice.customer = frappe.db.get_value('Patient', patient, 'customer')
	sales_invoice.due_date = getdate()
	sales_invoice.company = company
	sales_invoice.is_pos = 0
	sales_invoice.debit_to = get_receivable_account(company)

	item_line = sales_invoice.append('items')
	item_line.item_name = 'Registration Fee'
	item_line.description = 'Registration Fee'
	item_line.qty = 1
	item_line.uom = uom
	item_line.conversion_factor = 1
	item_line.income_account = get_income_account(None, company)
	item_line.rate = frappe.db.get_single_value('Healthcare Settings', 'registration_fee')
	item_line.amount = item_line.rate
	sales_invoice.set_missing_values()
	return sales_invoice

@frappe.whitelist()
def get_patient_detail(patient):
	patient_dict = frappe.db.sql("""select * from tabPatient where name=%s""", (patient), as_dict=1)
	if not patient_dict:
		frappe.throw(_('Patient not found'))
	vital_sign = frappe.db.sql("""select * from `tabVital Signs` where patient=%s
		order by signs_date desc limit 1""", (patient), as_dict=1)

	details = patient_dict[0]
	if vital_sign:
		details.update(vital_sign[0])
	return details

def get_timeline_data(doctype, name):
	'''
	Return Patient's timeline data from medical records
	Also include the associated Customer timeline data
	'''
	patient_timeline_data = dict(frappe.db.sql('''
		SELECT
			unix_timestamp(communication_date), count(*)
		FROM
			`tabPatient Medical Record`
		WHERE
			patient=%s
			and `communication_date` > date_sub(curdate(), interval 1 year)
		GROUP BY communication_date''', name))

	customer = frappe.db.get_value(doctype, name, 'customer')
	if customer:
		from erpnext.accounts.party import get_timeline_data
		customer_timeline_data = get_timeline_data('Customer', customer)
		patient_timeline_data.update(customer_timeline_data)

	return patient_timeline_data

from datetime import datetime

@frappe.whitelist(allow_guest=True)
def upload_fingerprint():
	if frappe.request.files['file']:
		file = frappe.request.files['file']
		patient_name = frappe.form_dict.docname
		finger_name = frappe.form_dict.finger_name
		file_name = frappe.form_dict.filename
		file_content = file.stream.read()
		now_date = datetime.now()
		full_path = frappe.local.site + "/private/files/fingerprints/" + str(now_date.year) + "-" +str(now_date.month)
		file_no = frappe.db.get_value("Patient", file_name.split("_")[0], ["patient_number"])
		create_path(full_path)
		file_path = get_file_path(full_path, file_no + "_" + finger_name)

		with open(file_path, 'wb') as fw:
			fw.write(file_content)
		
		patient = frappe.get_doc("Patient", patient_name)
		row = patient.append("fingerprints")
		row.finger = finger_name
		row.capture_date = now_date
		row.file_path = file_path
		patient.save(ignore_permissions=True)
		frappe.db.commit()

	else:
		frappe.throw(_("Fingerprint image is not uploaded"))
	return "success"


def create_path(full_path):
	isExist = os.path.exists(full_path)
	if not isExist:
		os.makedirs(full_path)

def get_file_path(full_path, file_name):
	file_number = 0
	while True:
		if not os.path.exists(os.path.join(full_path, file_name + "_" + str(file_number))):
			return os.path.join(full_path, file_name + "_" + str(file_number))
		file_number += 1

@frappe.whitelist(allow_guest=True)
def get_fingerprints(patient):
	patient_doc = frappe.get_doc("Patient", patient)
	return patient_doc.fingerprints


from erpnext.healthcare.fingerprint_matcher import verify_fingerprint

@frappe.whitelist()
def match_fingerprint():
	if frappe.request.files['file']:
		file = frappe.request.files['file']
		file_content = file.stream.read()
		patient = verify_fingerprint(file_content)
		if patient and patient != "":
			sample = frappe.db.get_value("Sample Collection", {"patient": patient}, ["name"])
			if sample:
				frappe.db.set_value("Sample Collection", sample, "record_status", "Released")
			return {"path": "/app/sample-collection/" + str(sample)}
	return None

@frappe.whitelist()
def match_fingerprint_encounter():
	if frappe.request.files['file']:
		file = frappe.request.files['file']
		file_content = file.stream.read()
		patient = verify_fingerprint(file_content)
		if patient and patient != "":
			sample = frappe.db.get_value("Patient Encounter", {"patient": patient}, ["name"])
			return {"path": "/app/patient-encounter/" + str(sample)}
	return None

@frappe.whitelist()
def match_fingerprint_radiology():
	if frappe.request.files['file']:
		file = frappe.request.files['file']
		file_content = file.stream.read()
		patient = verify_fingerprint(file_content)
		if patient and patient != "":
			sample = frappe.db.get_value("Radiology Test", {"patient": patient}, ["name", "record_status"])
			if sample:
				if sample[1] != "Finalized":
					frappe.db.set_value("Radiology Test", sample[0], "record_status", "Released")
				return {"path": "/app/radiology-test/" + str(sample[0])}
	return None

@frappe.whitelist()
def match_fingerprint_cover():
	if frappe.request.files['file']:
		file = frappe.request.files['file']
		file_content = file.stream.read()
		patient = verify_fingerprint(file_content)
		if patient and patient != "":
			sample = frappe.db.get_value("Embassy Report", {"patient": patient}, ["name"])
			if sample:
				return {"path": "/app/embassy-report/" + str(sample)}
	return None

def validate_invoice_paid(patient, invoice):
	now = frappe.utils.now()
	res = frappe.db.sql("""
		SELECT patient FROM `tabPermitted Patient` WHERE patient='{patient}' and '{now}' > from_time AND '{now}' < to_time
	""".format(patient=patient, now=now))
	if len(res) > 0: return
	if frappe.db.get_value("Sales Invoice", invoice, "outstanding_amount") != 0:
		frappe.throw(_("Invoice is not paid"))