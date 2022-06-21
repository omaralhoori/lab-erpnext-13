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
from frappe.core.doctype.sms_settings.sms_settings import send_sms

class SendBulkSMS(Document):
	def __init__(self, *args, **kwargs):
		super(SendBulkSMS, self).__init__(*args, **kwargs)

	def on_submit(self):
		#pass;
		self.check_collect_sample_flage()
		self.update_collect_sample_flage()

	def on_cancel(self):
		pass;		
		#self.update_collect_sample_flage(cancel=1)

	def check_collect_sample_flage (self):
		for sample in self.get("group_sms_form_table"):
			old_flage = frappe.db.get_value("COVID Analysis Form",	{"company": sample.company,"name":sample.covid_form_serial}, "sample_collect_flag")
			if old_flage != "1":
				frappe.msgprint(_(sample.covid_form_serial))
				frappe.throw(_('Form {0} / {1} not collected before ').format(sample.covid_form_serial,sample.customer_name))

			old_resflage = frappe.db.get_value("COVID Analysis Form",	{"company": sample.company,"name":sample.covid_form_serial}, "result_flage")
			if old_resflage != "1":
				frappe.msgprint(_(sample.covid_form_serial))
				frappe.throw(_('Form {0} / {1} not released before ').format(sample.covid_form_serial,sample.customer_name))

	def update_collect_sample_flage (self, cancel=0):
		for sample in self.get("group_sms_form_table"):
			if cancel:
				pass;
			else:
				if sample.analysis_result=="Not Detected (Negative)":
					msg_res = "سلبية(غير مصاب)."
				
				if sample.analysis_result=="Detected (Positive)":
					msg_res = "إيجابية( مصاب)."

				mesgg = """السيد/ة : {0} \n نشكركم لزيارة مختبرات جوسانتي الطبية \n نتيجة فحصك للكورونا بتاريخ {1}  \n{2}\n لطباعة التقرير اضغط على الرابط ادناه \n (To print result click following URL \n /http://94.142.51.110:1952/resultview?name={3}&password={4} \n) \n 	لفحوصات الدم و الزيارات المنزلية يرجى الاتصال على 065804444. \nسلامتك تهمنا\nمجموعة عيادات ومختبرات جوسانتي الطبية العالمية""".format(sample.customer_name,sample.collection_date,msg_res,sample.covid_form_serial,sample.customer_password)

				#mesgg = """Dear {0} \nYour COVID-19  test result for the sample collected on {1} is {2} \n (To print result click following URL \n/http://94.142.51.110:1952/resultview?name={3}&password={4} \n) \nPlease consult your doctor for interpretation and advice in particular circumstances.\nThanks alot\nJoSante-Clinics health""".format(sample.customer_name,sample.collection_date,sample.analysis_result,sample.covid_form_serial,sample.customer_password)


				receiver_list = [sample.mobile_no] #['962798228664']
				send_sms(receiver_list,cstr(mesgg))

				#frappe.db.sql(""" UPDATE `tabProjects References` SET total_reference_received = `total_reference_received` + %s
				#	WHERE reference_no = %s and company = %s """, (flt(reference.received_amount), reference.reference_no,self.company))

	@frappe.whitelist()
	def get_form_received_bydate(self):
		company = self.company
		form_received_date = self.form_received_date
		party_list = self.party_list
		send_sms_using_party_mobile = self.send_sms_using_party_mobile
		party_mobile_no = self.party_mobile_no

		analysis_result = self.analysis_result
		#frappe.msgprint(_(form_received_date))
		self.set("group_sms_form_table", [])

		if party_list:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result, `tabCOVID Analysis Form`.mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.customer_password, `tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and `tabCOVID Analysis Form`.analysis_result = '{1}' and  DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{2}' and `tabCOVID Analysis Form`.party_list='{3}' """.format(company,analysis_result,form_received_date,party_list), as_dict=True)
		else:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result, `tabCOVID Analysis Form`.mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.customer_password, `tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and `tabCOVID Analysis Form`.analysis_result = '{1}' and  DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{2}' """.format(company,analysis_result,form_received_date), as_dict=True)

		#frappe.msgprint(_("555"))
		counter = 0
		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("group_sms_form_table")
			group_sample.covid_form_serial = d.name
			group_sample.customer_name = d.custmer_name
			group_sample.analysis_result = d.analysis_result
			if send_sms_using_party_mobile:
				group_sample.mobile_no = party_mobile_no
			else:
				group_sample.mobile_no = d.mobile_no
			group_sample.party_list = d.party_list
			group_sample.collection_date = d.collection_date
			group_sample.customer_password = d.customer_password

			
	@frappe.whitelist()
	def get_form_received_byserial(self):
		company = self.company
		party_list = self.party_list
		send_sms_using_party_mobile = self.send_sms_using_party_mobile
		party_mobile_no = self.party_mobile_no

		from_serial = self.from_serial
		to_serial = self.to_serial
		analysis_result = self.analysis_result

		self.set("group_sms_form_table", [])

		if party_list:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result, `tabCOVID Analysis Form`.mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.customer_password, `tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}'  and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and `tabCOVID Analysis Form`.analysis_result = '{1}' and `tabCOVID Analysis Form`.party_list='{2}' and  `tabCOVID Analysis Form`.daily_serial between {3} and {4} """.format(company,analysis_result,party_list,from_serial,to_serial), as_dict=True)
		else:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.analysis_result, `tabCOVID Analysis Form`.mobile_no, `tabCOVID Analysis Form`.collection_date, `tabCOVID Analysis Form`.customer_password, `tabCOVID Analysis Form`.party_list  from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}'  and `tabCOVID Analysis Form`.sample_collect_flag = 1 and `tabCOVID Analysis Form`.result_flage = 1 and `tabCOVID Analysis Form`.analysis_result = '{1}' and  `tabCOVID Analysis Form`.daily_serial between {2} and {3} """.format(company,analysis_result,from_serial,to_serial), as_dict=True)

		counter = 0
		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("group_sms_form_table")
			group_sample.covid_form_serial = d.name
			group_sample.customer_name = d.custmer_name
			group_sample.analysis_result = d.analysis_result
			group_sample.party_list = d.party_list
			if send_sms_using_party_mobile:
				group_sample.mobile_no = party_mobile_no
			else:
				group_sample.mobile_no = d.mobile_no
			group_sample.collection_date = d.collection_date
			group_sample.customer_password = d.customer_password


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
def get_party_list_data(party_list):
	party_mobile_no = frappe.db.get_value("Third Party",{"name": party_list}, "mobile_no")

	return {
		"party_mobile_no": party_mobile_no
	}

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

