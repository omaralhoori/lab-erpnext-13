# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.model.meta import get_field_precision
from frappe.model.document import Document
from frappe.utils import  flt ,getdate ,nowdate,get_datetime, cint, cstr , now_datetime ,datetime
from datetime import timedelta
from frappe.core.doctype.sms_settings.sms_settings import send_sms
import requests

class SendBulkMOH(Document):
	def __init__(self, *args, **kwargs):
		super(SendBulkMOH, self).__init__(*args, **kwargs)



	def on_submit(self):
		#pass;
		self.check_collect_sample_flage()
		self.update_collect_sample_flage()




	def on_cancel(self):
		pass;		





	def check_collect_sample_flage (self):
				
		for sample in self.get("moh_child"):
			old_flage = frappe.db.get_value("COVID Analysis Form",	{"company": sample.company,"name":sample.covid_form_serial}, "sample_collect_flag")
			if old_flage == "0":
				frappe.msgprint(_(sample.covid_form_serial))
				frappe.throw(_('Form {0} / {1} not collected before ').format(sample.covid_form_serial,sample.full_name))

			old_resflage = frappe.db.get_value("COVID Analysis Form",	{"company": sample.company,"name":sample.covid_form_serial}, "result_flage")
			if old_resflage == "0":
				frappe.msgprint(_(sample.covid_form_serial))
				frappe.throw(_('Form {0} / {1} not released before ').format(sample.covid_form_serial,sample.full_name))





	def update_collect_sample_flage (self, cancel=0):
		for sample in self.get("moh_child"):
			if cancel:
				pass;
			else:
				if sample.nationality[0:1]=="J":
					sample.nationality="J"
				else:
					sample.nationality="N"
				
				
				if sample.result[0:1]=="N":
					sample.result="N"
				else:
					sample.result="P"
				msg_body = {  "AppUserName":"sondos","AppPassword":"sondos@123","AddressDetails":sample.address_details,"Location":sample.address_details ,"FullName":sample.full_name, "Age" :sample.age,"Telephone":sample.telephone,"NationalID":sample.national_id,"SampleEntryDate":sample.sample_entry_date,"SampleEntryTime":sample.sample_entry_time,"Nationality":sample.nationality,
"Result":sample.result,"RecieveAmanNotification":sample.receive_aman_notification,"AmanNotificationType":sample.aman_notification_type,
"Barcode":sample.covid_form_serial,"AnotherTelephone":sample.another_telephone,"Government":sample.government,"ResultDate":sample.result_date,
"ResultTime":sample.result_time,"UserCode":"JO Sante"}
				api_url = 'https://api.covid19survey.moh.gov.jo/AppAPI/Sondos/PrivateLab/InsertTransaction'
				r = requests.post(api_url,data= msg_body, verify = False)
				print("*" * 100)				
				print(r.text)
				y=frappe.db.set_value("MOH Child", {"company": sample.company,"covid_form_serial": sample.covid_form_serial}, "t_check", r.text)
				y=r.text[11:16]
				if y=="false":
					frappe.db.set_value("MOH Child", {"company": sample.company,"covid_form_serial": sample.covid_form_serial}, "correct", y)
					frappe.db.set_value("MOH Child", {"company": sample.company,"covid_form_serial": sample.covid_form_serial}, "docstatus", "2")
				else:
					frappe.db.set_value("MOH Child", {"company": sample.company,"covid_form_serial": sample.covid_form_serial}, "correct", "true")
				self.reload()

	@frappe.whitelist()
	def get_form_received_bydate(self):
		company = self.company
		form_received_date = self.form_received_date
		medical_direction = self.medical_direction
		analysis_result = self.analysis_result
		#frappe.msgprint(_(form_received_date))
		self.set("moh_child", [])
		if analysis_result:
			if medical_direction:
				gr_sample = frappe.db.sql("""
select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result, SUBSTRING(mobile_no,4,12) as mobile_no, 
`tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.another_mobile_no, `tabCOVID Analysis Form`.nationality, 
 `tabCOVID Analysis Form`.national_id,
 `tabCOVID Analysis Form`.age, `tabCOVID Analysis Form`.receive_aman_notification,`tabCOVID Analysis Form`.aman_notification_type,`tabCOVID Analysis Form`.governorate,
`tabCOVID Analysis Form`.address_details,`tabCOVID Analysis Form`.result_date,`tabCOVID Analysis Form`.result_time

from `tabCOVID Analysis Form`

where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and `tabCOVID Analysis Form`.analysis_result = '{1}' and  DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{2}' and `tabCOVID Analysis Form`.medical_direction<> '{3}' 
and `tabCOVID Analysis Form`.name not in(
select covid_form_serial from `tabMOH Child` where docstatus = 1
)""".format(company,analysis_result,form_received_date,medical_direction), as_dict=True)
			else:
				gr_sample = frappe.db.sql("""
select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result, SUBSTRING(mobile_no,4,12) as mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.another_mobile_no, `tabCOVID Analysis Form`.nationality, 
 `tabCOVID Analysis Form`.national_id,
 `tabCOVID Analysis Form`.age, `tabCOVID Analysis Form`.receive_aman_notification,`tabCOVID Analysis Form`.aman_notification_type,`tabCOVID Analysis Form`.governorate,
`tabCOVID Analysis Form`.address_details,`tabCOVID Analysis Form`.result_date,`tabCOVID Analysis Form`.result_time

from `tabCOVID Analysis Form`

where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and `tabCOVID Analysis Form`.analysis_result = '{1}' and  DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{2}' and `tabCOVID Analysis Form`.name not in(
select covid_form_serial from `tabMOH Child` where docstatus = 1
)""".format(company,analysis_result,form_received_date), as_dict=True)

	
		else:
			if medical_direction:
				gr_sample = frappe.db.sql("""
select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result, SUBSTRING(mobile_no,4,12) as mobile_no, 
`tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.another_mobile_no, `tabCOVID Analysis Form`.nationality, 
 `tabCOVID Analysis Form`.national_id,
 `tabCOVID Analysis Form`.age, `tabCOVID Analysis Form`.receive_aman_notification,`tabCOVID Analysis Form`.aman_notification_type,`tabCOVID Analysis Form`.governorate,
`tabCOVID Analysis Form`.address_details,`tabCOVID Analysis Form`.result_date,`tabCOVID Analysis Form`.result_time

from `tabCOVID Analysis Form`

where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and  DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{2}' and `tabCOVID Analysis Form`.medical_direction<> '{3}' and `tabCOVID Analysis Form`.name not in(
select covid_form_serial from `tabMOH Child` where docstatus = 1
) """.format(company,analysis_result,form_received_date,medical_direction), as_dict=True)
			else:
				gr_sample = frappe.db.sql("""
select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result,SUBSTRING(mobile_no,4,12) as mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.another_mobile_no, `tabCOVID Analysis Form`.nationality, 
 `tabCOVID Analysis Form`.national_id,
 `tabCOVID Analysis Form`.age, `tabCOVID Analysis Form`.receive_aman_notification,`tabCOVID Analysis Form`.aman_notification_type,`tabCOVID Analysis Form`.governorate,
`tabCOVID Analysis Form`.address_details,`tabCOVID Analysis Form`.result_date,`tabCOVID Analysis Form`.result_time

from `tabCOVID Analysis Form`

where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and  DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{2}' and `tabCOVID Analysis Form`.name not in(
select covid_form_serial from `tabMOH Child` where docstatus = 1
)""".format(company,analysis_result,form_received_date), as_dict=True)


		counter = 0
		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("moh_child")
			group_sample.covid_form_serial = d.name
			group_sample.full_name = d.custmer_name
			group_sample.result = d.analysis_result

			group_sample.age = d.age
			group_sample.telephone = d.mobile_no
			group_sample.national_id = d.national_id

			group_sample.sample_entry_date = d.collection_date
			group_sample.sample_entry_time = d.collection_time
			group_sample.nationality = d.nationality
			group_sample.address_details = d.address_details

			group_sample.receive_aman_notification = d.receive_aman_notification
			group_sample.aman_notification_type = d.aman_notification_type

			group_sample.another_telephone = d.another_mobile_no
			group_sample.government = d.governorate
			group_sample.result_date = d.result_date
			group_sample.result_time = d.result_time



	
	@frappe.whitelist()
	def get_form_received_byserial(self):
		company = self.company
		medical_direction = self.medical_direction
		analysis_result = self.analysis_result
		from_serial = self.from_serial
		to_serial = self.to_serial
		

		self.set("moh_child", [])
	

		if analysis_result : 
			if medical_direction :
				gr_sample = frappe.db.sql("""
select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result, SUBSTRING(mobile_no,4,12) as mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.another_mobile_no, `tabCOVID Analysis Form`.nationality, 
 `tabCOVID Analysis Form`.national_id,
 `tabCOVID Analysis Form`.age, `tabCOVID Analysis Form`.receive_aman_notification,`tabCOVID Analysis Form`.aman_notification_type,`tabCOVID Analysis Form`.governorate,
`tabCOVID Analysis Form`.address_details,`tabCOVID Analysis Form`.result_date,`tabCOVID Analysis Form`.result_time

from `tabCOVID Analysis Form`

where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and `tabCOVID Analysis Form`.analysis_result = '{1}' and  `tabCOVID Analysis Form`.daily_serial between {3} and {4} and `tabCOVID Analysis Form`.medical_direction<>'{2}' and `tabCOVID Analysis Form`.name not in(
select covid_form_serial from `tabMOH Child` where docstatus = 1
) """.format(company,analysis_result,medical_direction,from_serial,to_serial), as_dict=True)




			else:
				gr_sample = frappe.db.sql("""
select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result,SUBSTRING(mobile_no,4,12) as mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.another_mobile_no, `tabCOVID Analysis Form`.nationality, 
 `tabCOVID Analysis Form`.national_id,
 `tabCOVID Analysis Form`.age, `tabCOVID Analysis Form`.receive_aman_notification,`tabCOVID Analysis Form`.aman_notification_type,`tabCOVID Analysis Form`.governorate,
`tabCOVID Analysis Form`.address_details,`tabCOVID Analysis Form`.result_date,`tabCOVID Analysis Form`.result_time

from `tabCOVID Analysis Form`

where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and `tabCOVID Analysis Form`.analysis_result = '{1}' and  `tabCOVID Analysis Form`.daily_serial between {2} and {3} and `tabCOVID Analysis Form`.name not in(
select covid_form_serial from `tabMOH Child` where docstatus = 1
) """.format(company,analysis_result,from_serial,to_serial), as_dict=True)




		else:
			
			if medical_direction :
				gr_sample = frappe.db.sql("""
select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result,SUBSTRING(mobile_no,4,12) as mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.another_mobile_no, `tabCOVID Analysis Form`.nationality, 
 `tabCOVID Analysis Form`.national_id,
 `tabCOVID Analysis Form`.age, `tabCOVID Analysis Form`.receive_aman_notification,`tabCOVID Analysis Form`.aman_notification_type,`tabCOVID Analysis Form`.governorate,
`tabCOVID Analysis Form`.address_details,`tabCOVID Analysis Form`.result_date,`tabCOVID Analysis Form`.result_time

from `tabCOVID Analysis Form`

where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and  `tabCOVID Analysis Form`.daily_serial between {3} and {4} and `tabCOVID Analysis Form`.medical_direction<>'{2}' and `tabCOVID Analysis Form`.name not in(
select covid_form_serial from `tabMOH Child` where docstatus = 1
) """.format(company,analysis_result,medical_direction,from_serial,to_serial), as_dict=True)




			else:
				gr_sample = frappe.db.sql("""
select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result,SUBSTRING(mobile_no,4,12) as mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.collection_time,`tabCOVID Analysis Form`.another_mobile_no, `tabCOVID Analysis Form`.nationality, 
 `tabCOVID Analysis Form`.national_id,
 `tabCOVID Analysis Form`.age, `tabCOVID Analysis Form`.receive_aman_notification,`tabCOVID Analysis Form`.aman_notification_type,`tabCOVID Analysis Form`.governorate,
`tabCOVID Analysis Form`.address_details,`tabCOVID Analysis Form`.result_date,`tabCOVID Analysis Form`.result_time

from `tabCOVID Analysis Form`

where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and `tabCOVID Analysis Form`.daily_serial between {2} and {3}  and `tabCOVID Analysis Form`.name not in(
select covid_form_serial from `tabMOH Child` where docstatus = 1
)""".format(company,analysis_result,from_serial,to_serial), as_dict=True)



		counter = 0
		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("moh_child")
			group_sample.covid_form_serial = d.name
			group_sample.full_name = d.custmer_name
			group_sample.result = d.analysis_result

			group_sample.age = d.age
			group_sample.telephone = d.mobile_no
			group_sample.national_id = d.national_id

			group_sample.sample_entry_date = d.collection_date
			group_sample.sample_entry_time = d.collection_time
			group_sample.nationality = d.nationality
			group_sample.address_details = d.address_details

			group_sample.receive_aman_notification = d.receive_aman_notification
			group_sample.aman_notification_type = d.aman_notification_type

			group_sample.another_telephone = d.another_mobile_no
			group_sample.government = d.governorate
			group_sample.result_date = d.result_date
			group_sample.result_time = d.result_time			

		

			
@frappe.whitelist()
def get_covid_form_serial_for_sms(doctype, txt, searchfield, start, page_len, filters):
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
			`tabCOVID Analysis Form`.result_flage = %(link_result_flag)s 
		order by `tabCOVID Analysis Form`.name desc
		limit %(start)s, %(page_len)s """.format(**{
			'field': fields,
			'key': frappe.db.escape(searchfield)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'link_company': link_company,
			'link_sample_flag': link_sample_flag,
			'link_result_flag': link_result_flag
		})
	



@frappe.whitelist()
def get_covid_form_data(company, covid_form_serial):
	custmer_name = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "custmer_name")

	mobile_no = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "mobile_no")

	analysis_result = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "analysis_result")

	customer_password = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "customer_password")

	party_list = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "party_list")

	collection_date = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "collection_date")



	return {
		"custmer_name": custmer_name,
		"mobile_no": mobile_no,
		"analysis_result": analysis_result,
		"collection_date": collection_date,
		"customer_password":customer_password,
		"party_list":party_list
	}





