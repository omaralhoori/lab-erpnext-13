# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe , random
import os 
from frappe.utils import now_datetime, cint, cstr,flt,date_diff,nowdate

from frappe import _, throw
from frappe.model.document import Document
import re
from six import string_types

class COVIDAnalysisFormDup(Document):
	def __init__(self, *args, **kwargs):
		super(COVIDAnalysisFormDup, self).__init__(*args, **kwargs)

	def validate(self):
		print ('33333333333333333333333333')

		if self.party_list:
			pass;
		else:
			self.analysis_default_amount_org= self.government_amount
		
		if flt(self.analysis_amount) < flt(self.analysis_default_amount_org):
			if self.amount_change_approved_by == None or self.amount_change_approved_by == "":
				frappe.throw(_("The default amount has been changed , you have to set whose accepted that!"))
			
		if self.visit_type == "Home Visit" and (self.collector_name == None or self.collector_name == ""):	
			frappe.throw(_("Collector name must be entered for visit type of home visit"))

		if self.visit_type == "In Centre":	
			self.collector_name = None
			
		if self.customer_password == None or self.customer_password == "":	
			self.customer_password= random.randrange(1234567, 9876543)

		if self.date_of_birth:
			number_of_days = date_diff(nowdate(), self.date_of_birth) + 1;
			self.age=number_of_days/365;

		if self.party_list=="" or self.party_list == None:
			self.party_list = "NA"


		if len(self.name) > 0:
			serialcov = self.name.split("-")
			if len(serialcov) > 2:
				serialdaily = serialcov[2]
				serialmmdd = serialcov[1]
				self.daily_serial = cint(serialdaily) + (cint(serialmmdd) * 10000);
				self.barcode = get_barcode(self.company,self.medical_direction,self.custmer_name,self.date,self.daily_serial);
				#frappe.msgprint(_(cstr(tracking_number)));

	#def on_update(self):
		#frappe.msgprint(_("sdsd"));
		#xx = len(self.name);
		#frappe.msgprint(_(cstr(yy)));
		#self.daily_serial = self.name[len(self.name) - 5 :len(self.name)]

	#	self.daily_serial = get_transaction_count(self.company,self.date);
	#	self.barcode = get_barcode(self.company,self.medical_direction,self.custmer_name,self.date);	
		

	#	if not self.barcode:
	#		#self.barcode = self.name;
			
	#		#self.barcode = get_barcode(self.company,self.medical_direction,self.custmer_name,self.date);
	#		frappe.db.set_value("COVID Analysis Form Dup", {"company": self.company,"custmer_name": self.custmer_name}, "barcode", self.barcode)
	#		frappe.db.set_value("COVID Analysis Form Dup", {"company": self.company,"custmer_name": self.custmer_name}, "daily_serial", self.daily_serial)

@frappe.whitelist()
def get_barcode(company,medical_direction,customer_name,date,daily_serial):
	#2020-09-19
	#0123456789
	dayval=date[8:10]
	monval=date[5:7]
	
	daystr = dayval
	
	monstr = monval

	medical_direction_code = get_medical_direction_code(medical_direction)
	
	#transaction_count = get_transaction_count(company,date)

	#barcode = medical_direction_code + "-" + daystr + monstr + "-" + transaction_count 	#self.date[8:10]+":"+self.date[5:7]
	barcode = medical_direction_code + "-" + daystr + monstr + "-" + cstr(daily_serial) 	#self.date[8:10]+":"+self.date[5:7]
	
	return	barcode

@frappe.whitelist()
def get_barcode_old(company,medical_direction,customer_name,date,daily_serial):
	#2020-09-19
	#0123456789
	dayval=date[8:10]
	monval=date[5:7]
	
	daystr = ""
	if dayval=="01":
		daystr = "A"
	if dayval=="02":
		daystr = "B"
	if dayval=="03":
		daystr = "C"
	if dayval=="04":
		daystr = "D"
	if dayval=="05":
		daystr = "E"
	if dayval=="06":
		daystr = "F"
	if dayval=="07":
		daystr = "G"
	if dayval=="08":
		daystr = "H"
	if dayval=="09":
		daystr = "I"
	if dayval=="10":
		daystr = "J"
	if dayval=="11":
		daystr = "K"
	if dayval=="12":
		daystr = "L"
	if dayval=="13":
		daystr = "M"
	if dayval=="14":
		daystr = "N"
	if dayval=="15":
		daystr = "O"
	if dayval=="16":
		daystr = "P"
	if dayval=="17":
		daystr = "Q"
	if dayval=="18":
		daystr = "R"
	if dayval=="19":
		daystr = "S"
	if dayval=="20":
		daystr = "T"
	if dayval=="21":
		daystr = "U"
	if dayval=="22":
		daystr = "V"
	if dayval=="23":
		daystr = "W"
	if dayval=="24":
		daystr = "X"
	if dayval=="25":
		daystr = "Y"
	if dayval=="26":
		daystr = "Z"
	if dayval=="27":
		daystr = "AG"
	if dayval=="28":
		daystr = "AK"
	if dayval=="29":
		daystr = "AL"
	if dayval=="30":
		daystr = "AM"
	if dayval=="31":
		daystr = "AN"
	
	monstr = ""
	if monval=="01":
		monstr = "JA"
	if monval=="02":
		monstr = "F"
	if monval=="03":
		monstr = "M"
	if monval=="04":
		monstr = "A"
	if monval=="05":
		monstr = "M"
	if monval=="06":
		monstr = "J"
	if monval=="07":
		monstr = "JU"
	if monval=="08":
		monstr = "O"
	if monval=="09":
		monstr = "S"
	if monval=="10":
		monstr = "O"
	if monval=="11":
		monstr = "N"
	if monval=="12":
		monstr = "D"

	medical_direction_code = get_medical_direction_code(medical_direction)
	
	transaction_count = get_transaction_count(company,date)

	barcode = medical_direction_code + "-" + daystr + "-" + transaction_count + "-" + monstr	#self.date[8:10]+":"+self.date[5:7]
	
	return	barcode 

@frappe.whitelist()
def get_transaction_count(company,date):

	res = frappe.db.sql(
			'select '
			'count(*) as transaction_count '
			'from '
			'`tabCOVID Analysis Form Dup` '
			'where '
			'`tabCOVID Analysis Form Dup`.company = %s and '
			'`tabCOVID Analysis Form Dup`.date = %s ',
			(company,date), as_dict=1
		)

	transaction_count = res[0].get('transaction_count', 0) if res else 0
	
	transaction_count = transaction_count 

	return cstr(transaction_count)


@frappe.whitelist()
def get_medical_direction_code(medical_direction):

	res = frappe.db.sql(
			'select '
			'`tabMedical Analysis Direction`.direction_code as direction_code '
			'from '
			'`tabMedical Analysis Direction` '
			'where '
			'`tabMedical Analysis Direction`.name = %s ',
			(medical_direction), as_dict=1
		)

	direction_code = res[0].get('direction_code', "0") if res else "0"

	return direction_code

@frappe.whitelist()
def get_party_list_data(party_list):
	analysis_amount = frappe.db.get_value("Third Party",
		{"name": party_list}, "default_amount")

	fees_amount = frappe.db.get_value("Third Party",
		{"name": party_list}, "fees_amount")

	payment_type = frappe.db.get_value("Third Party",
		{"name": party_list}, "payment_type")
	
	if payment_type == None:
		payment_type="Cash"

	return {
		"analysis_amount": analysis_amount,
		"fees_amount": fees_amount,
		"payment_type":payment_type
	}

#--------------------------------------------------------------------------------------------------------------------------anas
@frappe.whitelist()
def get_customer(cus_info):
	customer_name = frappe.db.get_value("Customer information",{"name": cus_info}, "customer_name")
	party_list = frappe.db.get_value("Customer information",{"name": cus_info}, "party_list")
	visit_type = frappe.db.get_value("Customer information",{"name": cus_info}, "visit_type")
	collector_name = frappe.db.get_value("Customer information",{"name": cus_info}, "collector_name")

	mobile_number = frappe.db.get_value("Customer information",{"name": cus_info}, "mobile_number")
	mobile_2 = frappe.db.get_value("Customer information",{"name": cus_info}, "mobile_2")
	customer_nationality = frappe.db.get_value("Customer information",{"name": cus_info}, "customer_nationality")
	national_id = frappe.db.get_value("Customer information",{"name": cus_info}, "national_id")
	pass_id = frappe.db.get_value("Customer information",{"name": cus_info}, "pass_id")
	gender = frappe.db.get_value("Customer information",{"name": cus_info}, "gender")
	birth_date = frappe.db.get_value("Customer information",{"name": cus_info}, "birth_date")
	recive_aman = frappe.db.get_value("Customer information",{"name": cus_info}, "recive_aman")
	email_add = frappe.db.get_value("Customer information",{"name": cus_info}, "email_add")
	governorate = frappe.db.get_value("Customer information",{"name": cus_info}, "governorate")
	address_details = frappe.db.get_value("Customer information",{"name": cus_info}, "address_details")
	note = frappe.db.get_value("Customer information",{"name": cus_info}, "note")
	destination_country=frappe.db.get_value("Customer information",{"name": cus_info}, "destination_country")
	return {
		"customer_name": customer_name,
		"party_list": party_list,
		"visit_type": visit_type,
		"collector_name": collector_name,
		"mobile_number":mobile_number,
		"mobile_2":mobile_2,
		"customer_nationality":customer_nationality,
		"national_id":national_id,
		"pass_id":pass_id,
		"gender":gender,
		"birth_date":birth_date,		
		"recive_aman":recive_aman,
		"email_add":email_add,
		"governorate":governorate,
		"address_details":address_details,
		"note":note,
		"destination_country":destination_country,


	}

#------------------------------------------------------------------------------------------------------------------anas
@frappe.whitelist()
def set_rcv_flag(cus_info):
	
	frappe.db.set_value("Customer information", {"name": cus_info}, "rcv_flag", "1")

#---------------------------------------------------------------------------------------------------------------------------

@frappe.whitelist()
def qrcode_gen_dup(customer_password,docname):
	codname = customer_password + '_' + docname 

	nyear= now_datetime().strftime('%Y')
	nmonth= now_datetime().strftime('%m')
	qrpath = '/public/files/covidqrcode/' + nyear + '/' + nmonth + '/'
	qrpath_db = 'files/covidqrcode/' + nyear + '/' + nmonth + '/'

	frappe.utils.generate_qrcode_dup("94.142.51.110:1952",codname,qrpath)
	frappe.db.set_value("COVID Analysis Form Dup", {"name": docname}, "qrcode_path", qrpath_db)

		
@frappe.whitelist()
def get_medical_direction_data(medical_direction):
	medical_direction = frappe.db.get_value("Medical Analysis Direction",
		{"direction_name": medical_direction}, "direction_code")


	return {
		"medical_direction": medical_direction
	}

@frappe.whitelist()
def update_collect_sample_flag(company,medical_direction,custmer_name,collection_date,collection_time,collection_users):
	
	res = 1
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "sample_collect_flag", "1")
	#frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "barcode", barcode)
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "collection_date", collection_date)
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "collection_time", collection_time)
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "collection_users", collection_users)
	
	return {
		"res": res
	}

@frappe.whitelist()
def set_result_data(company,custmer_name,result_date,result_time,result_user):
	
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "result_flage", "1")
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "result_date", result_date)
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "result_time", result_time)
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "result_user", result_user)
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "analysis_result", "Not Detected (Negative)")
	frappe.db.set_value("COVID Analysis Form Dup", {"company": company,"custmer_name": custmer_name}, "analysis_result_ref_range", "Not Detected (Negative)")

	#frappe.db.set_value("COVID Analysis Form", {"company": company,"custmer_name": custmer_name}, "result_user", frappe.db.get_value("Analysis Result", old, "parent_account"))


	return {
		"res": "1"
	}

