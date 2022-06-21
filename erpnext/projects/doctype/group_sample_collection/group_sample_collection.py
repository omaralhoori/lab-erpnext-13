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

class GroupSampleCollection(Document):
	def __init__(self, *args, **kwargs):
		super(GroupSampleCollection, self).__init__(*args, **kwargs)

	def on_submit(self):
		self.check_collect_sample_flage()
		self.update_collect_sample_flage()

	def on_cancel(self):
		self.update_collect_sample_flage(cancel=1)

	def check_collect_sample_flage (self):
		for sample in self.get("group_sample_collection_table"):
			old_flage = frappe.db.get_value("COVID Analysis Form",	{"company": sample.company,"name":sample.covid_form_serial}, "sample_collect_flag")
			#frappe.msgprint(_(old_flage))
			if old_flage == "1":
				frappe.msgprint(_(sample.covid_form_serial))
				frappe.throw(_('Form {0} / {1} was collected before ').format(sample.covid_form_serial,sample.customer_name))

	def update_collect_sample_flage (self, cancel=0):
		for sample in self.get("group_sample_collection_table"):
			if cancel:
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "sample_collect_flag", "0")
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "collection_date", None )
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "collection_time", None)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "collection_users", None)
			else:
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "sample_collect_flag", "1")
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "collection_date", sample.collection_date)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "collection_time", sample.collection_time)
				frappe.db.set_value("COVID Analysis Form", {"company": sample.company,"name": sample.covid_form_serial}, "collection_users", frappe.session.user)
				#frappe.db.sql(""" UPDATE `tabProjects References` SET total_reference_received = `total_reference_received` + %s
				#	WHERE reference_no = %s and company = %s """, (flt(reference.received_amount), reference.reference_no,self.company))

	@frappe.whitelist()
	def get_form_received_bydate(self):
		company = self.company
		form_received_date = self.form_received_date
		party_list = self.party_list
		#frappe.msgprint(_(party_list))
		self.set("group_sample_collection_table", [])
		if party_list:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.date, `tabCOVID Analysis Form`.medical_direction,`tabCOVID Analysis Form`.party_list from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 0 and DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{1}' and `tabCOVID Analysis Form`.party_list='{2}' """.format(company,form_received_date,party_list), as_dict=True)
		else:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.date, `tabCOVID Analysis Form`.medical_direction,`tabCOVID Analysis Form`.party_list from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}' and `tabCOVID Analysis Form`.sample_collect_flag = 0 and DATE_FORMAT(`tabCOVID Analysis Form`.date,'%Y-%m-%d') = '{1}' """.format(company,form_received_date), as_dict=True)

		#frappe.msgprint(_("555"))
		counter = 0
		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("group_sample_collection_table")
			group_sample.covid_form_serial = d.name
			group_sample.customer_name = d.custmer_name
			group_sample.received_date = d.date
			group_sample.medical_analysis_direction = d.medical_direction
			group_sample.party_list = d.party_list
			group_sample.collection_date = getdate(nowdate())
			timecol = now_datetime() + datetime.timedelta(seconds=(60 * counter))
			group_sample.collection_time =  timecol.strftime('%H:%M:%S')
			#group_sample.collection_time = datetime.datetime.now() + datetime.timedelta(days=3)
			#group_sample.collection_time = now_datetime().strftime('%H:%M:%S')
			

	@frappe.whitelist()
	def get_form_received_byserial(self):
		company = self.company
		party_list = self.party_list
		from_serial = self.from_serial
		to_serial = self.to_serial
		self.set("group_sample_collection_table", [])

		if party_list:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.date, `tabCOVID Analysis Form`.medical_direction,`tabCOVID Analysis Form`.party_list from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}'  and `tabCOVID Analysis Form`.sample_collect_flag = 0 and `tabCOVID Analysis Form`.party_list='{1}' and  `tabCOVID Analysis Form`.daily_serial between {2} and {3}  """.format(company,party_list,from_serial,to_serial), as_dict=True)
		else:
			gr_sample = frappe.db.sql("""select `tabCOVID Analysis Form`.name, `tabCOVID Analysis Form`.custmer_name,`tabCOVID Analysis Form`.date, `tabCOVID Analysis Form`.medical_direction,`tabCOVID Analysis Form`.party_list from `tabCOVID Analysis Form` where `tabCOVID Analysis Form`.company = '{0}'  and `tabCOVID Analysis Form`.sample_collect_flag = 0 and  `tabCOVID Analysis Form`.daily_serial between {1} and {2}""".format(company,from_serial,to_serial), as_dict=True)





		counter = 0
		for d in gr_sample:
			counter = counter + 1
			group_sample = self.append("group_sample_collection_table")
			group_sample.covid_form_serial = d.name
			group_sample.customer_name = d.custmer_name
			group_sample.received_date = d.date
			group_sample.medical_analysis_direction = d.medical_direction
			group_sample.party_list = d.party_list
			group_sample.collection_date = getdate(nowdate())
			timecol = now_datetime() + datetime.timedelta(seconds=(60 * counter))
			group_sample.collection_time =  timecol.strftime('%H:%M:%S')
			#group_sample.collection_time = now_datetime().strftime('%H:%M:%S')


@frappe.whitelist()
def get_covid_form_serial_for_sample(doctype, txt, searchfield, start, page_len, filters):
	link_company = filters.pop('link_company')
	link_sample_flag = filters.pop('link_sample_flag')

	fields = ["`tabCOVID Analysis Form`.name", "`tabCOVID Analysis Form`.custmer_name"]
	fields = ", ".join(fields)

	return frappe.db.sql("""select
			{field} 
		from
			`tabCOVID Analysis Form`
		where	(name like %(txt)s
				or custmer_name like %(txt)s) and 
			`tabCOVID Analysis Form`.company = %(link_company)s and
			`tabCOVID Analysis Form`.sample_collect_flag = %(link_sample_flag)s 
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



@frappe.whitelist()
def get_covid_form_data(company, covid_form_serial):
	custmer_name = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "custmer_name")

	date = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "date")

	medical_direction = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "medical_direction")

	party_list = frappe.db.get_value("COVID Analysis Form",
		{"company": company, "name": covid_form_serial}, "party_list")

	return {
		"custmer_name": custmer_name,
		"date": date,
		"medical_direction": medical_direction,
		"party_list":party_list
	}

