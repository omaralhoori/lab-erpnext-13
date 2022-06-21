# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.model.meta import get_field_precision
from frappe.model.document import Document
from frappe.utils import  flt ,getdate ,nowdate,get_datetime, cint, cstr , now_datetime ,datetime
from datetime import timedelta

class GroupSetResult(Document):
	def __init__(self, *args, **kwargs):
		super(GroupSetResult, self).__init__(*args, **kwargs)

	def on_submit(self):
		if self.set_analysis_result_to == "Not Collected":
			frappe.throw(_('Not Collected result not allowed here '))
		else:
			self.check_resutl_flage()
			self.update_resutl_flage()
		 

	def on_cancel(self):
		self.update_resutl_flage(cancel=1)

	def check_resutl_flage (self):
		for sample in self.get("group_result_table"):
			if  sample.analysis_result == "Not Collected":
				frappe.throw(_('Not Collected result or empty result for form {0} / {1} not allowed  ').format(sample.covid_form_serial,sample.customer_name))	
		
			if  sample.analysis_result == None :
				frappe.throw(_('Empty result for form {0} / {1} not allowed  ').format(sample.covid_form_serial,sample.customer_name))	
		
			old_flage = frappe.db.get_value("COVID Analysis Form",	{"company": sample.company,"name":sample.covid_form_serial}, "Result_Flage")
			if old_flage == "1":
				frappe.msgprint(_(sample.covid_form_serial))
				frappe.throw(_('Form {0} / {1} was released before ').format(sample.covid_form_serial,sample.customer_name))


	def update_resutl_flage (self, cancel=0):
		for sample in self.get("group_result_table"):
			if cancel:
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "result_flage", "0")
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "result_date", None)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "result_time", None)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "result_user", None)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "analysis_result", "Not Collected")
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "analysis_result_ref_range", "Not Detected (Negative)")

			else:
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "result_flage", "1")
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "result_date", sample.result_date)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "result_time", sample.result_time)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "result_user", frappe.session.user)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "analysis_result", sample.analysis_result)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "analysis_result_ref_range", "Not Detected (Negative)")


	def get_form_received_bydate(self):
		company = self.company
		form_received_date = self.form_received_date
		party_list = self.party_list
		#frappe.msgprint(_(form_received_date))
		self.set("group_result_table", [])

		if party_list:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.date, `tabCOVID Analysis Form`.medical_direction , `tabCOVID Analysis Form`.mobile_no, `tabCOVID Analysis Form`.national_id, `tabCOVID Analysis Form`.email_address, `tabCOVID Analysis Form`.date_of_birth, `tabCOVID Analysis Form`.passport_id, `tabCOVID Analysis Form`.gender, `tabCOVID Analysis Form`.medical_direction_code, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and (`tabCOVID Analysis Form`.result_flage is null or `tabCOVID Analysis Form`.result_flage = 0) and DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{1}' and `tabCOVID Analysis Form`.party_list='{2}' """.format(company,form_received_date,party_list), as_dict=True)
		else:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.date, `tabCOVID Analysis Form`.medical_direction , `tabCOVID Analysis Form`.mobile_no, `tabCOVID Analysis Form`.national_id, `tabCOVID Analysis Form`.email_address, `tabCOVID Analysis Form`.date_of_birth, `tabCOVID Analysis Form`.passport_id, `tabCOVID Analysis Form`.gender, `tabCOVID Analysis Form`.medical_direction_code, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and (`tabCOVID Analysis Form`.result_flage is null or `tabCOVID Analysis Form`.result_flage = 0) and DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{1}' """.format(company,form_received_date), as_dict=True)

		#frappe.msgprint(_("555"))
		counter = 0
		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("group_result_table")
			group_sample.covid_form_serial = d.name
			group_sample.customer_name = d.custmer_name
			group_sample.party_list = d.party_list
			group_sample.received_date = d.date
			group_sample.medical_analysis_direction = d.medical_direction
			group_sample.mobile_no = d.mobile_no
			group_sample.national_id = d.national_id
			group_sample.email_address = d.email_address
			group_sample.date_of_birth = d.date_of_birth
			group_sample.passport_id = d.passport_id
			group_sample.gender = d.gender
			group_sample.medical_direction_code = d.medical_direction_code
			group_sample.collection_date = d.collection_date
			group_sample.collection_time = d.collection_time

			group_sample.result_date = getdate(nowdate())
			timecol = now_datetime() + datetime.timedelta(seconds=(60 * counter))
			group_sample.result_time =  timecol.strftime('%H:%M:%S')
			group_sample.analysis_result =  self.set_analysis_result_to
			group_sample.analysis_result_ref_range =  "Not Detected (Negative)"
			

	def get_form_received_byserial(self):
		company = self.company
		party_list = self.party_list
		from_serial = self.from_serial
		to_serial = self.to_serial
		self.set("group_result_table", [])

		if party_list:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.date, `tabCOVID Analysis Form`.medical_direction , `tabCOVID Analysis Form`.mobile_no, `tabCOVID Analysis Form`.national_id, `tabCOVID Analysis Form`.email_address, `tabCOVID Analysis Form`.date_of_birth, `tabCOVID Analysis Form`.passport_id, `tabCOVID Analysis Form`.gender, `tabCOVID Analysis Form`.medical_direction_code, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}'  and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.party_list='{1}' and (`tabCOVID Analysis Form`.result_flage is null or `tabCOVID Analysis Form`.result_flage = 0) and  (`tabCOVID Analysis Form`.name between (select name from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.name like '%{2}%') and (select name from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.name like '%{3}%') or `tabCOVID Analysis Form`.name >= (select name from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.name like '%{2}%') )  """.format(company,party_list,from_serial,to_serial), as_dict=True)

		else:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.date, `tabCOVID Analysis Form`.medical_direction , `tabCOVID Analysis Form`.mobile_no, `tabCOVID Analysis Form`.national_id, `tabCOVID Analysis Form`.email_address, `tabCOVID Analysis Form`.date_of_birth, `tabCOVID Analysis Form`.passport_id, `tabCOVID Analysis Form`.gender, `tabCOVID Analysis Form`.medical_direction_code, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}'  and `tabCOVID Analysis Form`.sample_collect_flag = 1 and (`tabCOVID Analysis Form`.result_flage is null or `tabCOVID Analysis Form`.result_flage = 0) and (`tabCOVID Analysis Form`.name between (select name from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.name like '%{1}%') and (select name from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.name like '%{2}%') or `tabCOVID Analysis Form`.name >= (select name from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.name like '%{1}%') )  """.format(company,from_serial,to_serial), as_dict=True)

		counter = 0
		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("group_result_table")
			group_sample.covid_form_serial = d.name
			group_sample.customer_name = d.custmer_name
			group_sample.received_date = d.date
			group_sample.party_list = d.party_list
			group_sample.medical_analysis_direction = d.medical_direction
			group_sample.mobile_no = d.mobile_no
			group_sample.national_id = d.national_id
			group_sample.email_address = d.email_address
			group_sample.date_of_birth = d.date_of_birth
			group_sample.passport_id = d.passport_id
			group_sample.gender = d.gender
			group_sample.medical_direction_code = d.medical_direction_code
			group_sample.collection_date = d.collection_date
			group_sample.collection_time = d.collection_time

			group_sample.result_date = getdate(nowdate())
			timecol = now_datetime() + datetime.timedelta(seconds=(60 * counter))
			group_sample.result_time =  timecol.strftime('%H:%M:%S')
			group_sample.analysis_result =  self.set_analysis_result_to
			group_sample.analysis_result_ref_range =  "Not Detected (Negative)"


def get_covid_form_serial_for_result(doctype, txt, searchfield, start, page_len, filters):
	link_company = filters.pop('link_company')
	link_sample_flag = filters.pop('link_sample_flag')
	link_result_flag = filters.pop('link_result_flag')

	fields = ["`tabCOVID Analysis Form`.name", "`tabCOVID Analysis Form`.custmer_name"]
	fields = ", ".join(fields)

	return frappe.db.sql("""select
			{field} 
		from
			`tabCOVID Analysis Form`
		where	(name like %(txt)s
				or custmer_name like %(txt)s) and 
			`tabCOVID Analysis Form`.company = %(link_company)s and
			`tabCOVID Analysis Form`.sample_collect_flag = %(link_sample_flag)s and
			`tabCOVID Analysis Form`.result_flage <> %(link_result_flag)s 
		order by `tabCOVID Analysis Form`.date desc
		limit %(start)s, %(page_len)s """.format(**{
			'field': fields,
			'key': frappe.db.escape(searchfield)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'link_company': link_company,
			'link_sample_flag': link_sample_flag
		})


def get_set_analysis_result(doctype, txt, searchfield, start, page_len):

	return frappe.db.sql("""select
			`tabAnalysis Result`.name 
		from
			`tabAnalysis Result`
		where
			`tabAnalysis Result`.name not in ("Not Collected")
		order by `tabAnalysis Result`.name desc """)




@frappe.whitelist()
def get_covid_form_data(company, covid_form_serial):
	custmer_name = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "custmer_name")

	date = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "date")

	party_list = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "party_list")

	medical_direction = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "medical_direction")

	mobile_no = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "mobile_no")

	national_id = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "national_id")

	email_address = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "email_address")

	national_id = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "national_id")

	date_of_birth = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "date_of_birth")

	passport_id = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "passport_id")

	gender = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "gender")

	medical_direction_code = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "medical_direction_code")

	collection_date = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "collection_date")

	collection_time = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "collection_time")


	return {
		"custmer_name": custmer_name,
		"date": date,
		"party_list": party_list,
		"medical_direction": medical_direction,	
		"mobile_no": mobile_no,
		"national_id": national_id,
		"email_address": email_address,
		"date_of_birth": date_of_birth,
		"passport_id": passport_id,
		"gender": gender,
		"medical_direction_code": medical_direction_code,
		"collection_date": collection_date,
		"collection_time": collection_time
	}

