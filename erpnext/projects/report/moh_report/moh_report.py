# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr 

value_fields = ("custmer_name", "mobile_no", "gender")


def execute(filters=None):
	validate_filters(filters)
	data = get_data(filters)
	columns = get_columns()
	return columns, data

def validate_filters(filters):
	if not filters.from_date:
		filters.from_date = filters.year_start_date

	if not filters.to_date:
		filters.to_date = filters.year_end_date

	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

def get_data(filters):
	additional_conditions = ""

	if filters.party_list:
		additional_conditions += " and party_list = %(party_list)s "

	
	if filters.get("analysis_result"): additional_conditions += " and analysis_result in %(analysis_result)s "
	
	if filters.get("direction_name"): additional_conditions += " and medical_direction in %(direction_name)s "

	#if filters.analysis_result:
	#	additional_conditions += " and analysis_result = %(analysis_result)s "

	query_filters = {
		"company": filters.company,
		"from_date": filters.from_date,
		"to_date": filters.to_date,
		"party_list": filters.party_list,
		"analysis_result": filters.analysis_result,
		"direction_name": filters.direction_name
	}


	covid_date = frappe.db.sql("""select visit_type,collection_date,collection_time,medical_direction,payment_type,custmer_name,age,case when nationality='Jordan' then 'J' else 'N' end as nationality,national_id, case when (mobile_no is not null and Length(mobile_no )> 10) then SUBSTRING(mobile_no, 4, LENGTH(mobile_no)-3) else "" end as mobile_no  , case when analysis_result='Detected (Positive)' then 'P' when analysis_result='Not Detected (Negative)' then 'N' else 'O' end as analysis_result,receive_aman_notification,aman_notification_type,party_list, `date`,name,governorate,address_details, case when (another_mobile_no is not null and Length(another_mobile_no )> 10) then SUBSTRING(another_mobile_no, 4, LENGTH(another_mobile_no)-3) else "" end as another_mobile_no,result_time,date_format(result_date, '%%m/%%d/%%y') as result_date from `tabCOVID Analysis Form` where company=%(company)s {additional_conditions} and `date` between %(from_date)s and %(to_date)s order by `date` """.format(additional_conditions=additional_conditions), query_filters , as_dict=True)

	if not covid_date:
		return None


	data = prepare_data(covid_date, filters)

	return data

def change_date_format(string_date):
	DATE_FORMAT = "%m/%d/%y"
	TIME_FORMAT = "%H:%M:%S.%f"
	DATETIME_FORMAT = DATE_FORMAT + " " + TIME_FORMAT

	date = getdate(string_date)
	formatted_date = date.strftime(DATE_FORMAT)
	formatted_date = formatted_date.replace("0", "")

	return formatted_date

def change_time_format(string_time):
	DATE_FORMAT = "%m/%d/%y"
	TIME_FORMAT = "%H24:%M"
	DATETIME_FORMAT = DATE_FORMAT + " " + TIME_FORMAT

	formatted_time="00:00"
	if string_time:
		if len(string_time) == 8:
			formatted_time=string_time[0:5]
		else:
			formatted_time= "0" + string_time[0:4]

	return formatted_time

def prepare_data(covid_date, filters):
	data = []

	for d in covid_date:

		has_value = False

		if d.address_details:
			address_details = d.address_details
		else:
			address_details = d.governorate	
		
		if d.another_mobile_no:
			another_mobile_no = d.another_mobile_no
		else:
			another_mobile_no = "0"

		row = {
			"visit_type": d.visit_type,
			"collection_date": change_date_format(cstr(d.collection_date))  ,  #d.collection_date,
			"collection_time": change_time_format(cstr(d.collection_time)),  #d.collection_time,
			"custmer_name": d.custmer_name,
			"age": d.age,
			"nationality": d.nationality,
			"national_id": d.national_id,
			"mobile_no": d.mobile_no,
			"analysis_result": d.analysis_result,
			"another_mobile_no": another_mobile_no, #d.another_mobile_no,
			"address_details": address_details, #d.address_details,
			"governorate": d.governorate,
			"result_date": change_date_format(cstr(d.result_date))  ,  #d.result_date,
			"result_time": change_time_format(cstr(d.result_time)),  #d.result_time,
			"receive_aman_notification": d.receive_aman_notification,
			"aman_notification_type": d.aman_notification_type,
			"party_list": d.party_list,
			"date": change_date_format(cstr(d.date))  ,  #d.date,
			"name": d.name,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"medical_direction": d.medical_direction,
			"payment_type":d.payment_type,
		}

		has_value = True

		row["has_value"] = has_value
		data.append(row)

	data.extend([{}])

	return data

def get_columns():
	return [
		{
			"fieldname": "governorate",
			"label": _("Government"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "address_details",
			"label": _("Address Details"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "collection_date",
			"label": _("Entry Date"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "collection_time",
			"label": _("Entry Time"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "custmer_name",
			"label": _("Customer Name"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "age",
			"label": _("Age"),
			"fieldtype": "Data",
			"width": 50
		},
		{
			"fieldname": "nationality",
			"label": _("Nationality"),
			"fieldtype": "Link",
			"options": "Country",
			"width": 100
		},
		{
			"fieldname": "national_id",
			"label": _("Nationality ID"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "mobile_no",
			"label": _("Telephone"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "analysis_result",
			"label": _("Result"),
			"fieldtype": "Link",
			"options": "Analysis Result",
			"width": 120
		},
		{
			"fieldname": "receive_aman_notification",
			"label": _("Receive Aman Notification"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "aman_notification_type",
			"label": _("Aman Notification Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "name",
			"label": _("Barcode"),
			"fieldtype": "Link",
			"options": "COVID Analysis Form",
			"width": 100
		},
		{
			"fieldname": "another_mobile_no",
			"label": _("Another Telephone"),
			"fieldtype": "Link",
			"options": "COVID Analysis Form",
			"width": 100
		},
		{
			"fieldname": "result_date",
			"label": _("Result Date"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "result_time",
			"label": _("Result Time"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "party_list",
			"label": _("Party List"),
			"fieldtype": "Link",
			"options": "Third Party",
			"width": 120
		},
		{
			"fieldname": "date",
			"label": _("Visit Date"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "medical_direction",
			"label": _("Medical Direction"),
			"fieldtype": "Link",
			"options": _("Medical Analysis Direction"),
			"width": 120
		},
		{
			"fieldname": "payment_type",
			"label": _("Payment Type"),
			"fieldtype": "Data",
			"width": 120
		},
	
	]


