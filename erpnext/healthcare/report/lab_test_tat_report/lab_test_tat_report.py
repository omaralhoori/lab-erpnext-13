# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			'label': _("Requested Date"),
			'fieldname': 'requested_date',
			'fieldtype': 'Datetime',
			'width': 120
		},
		{
			'label': _("Test Id"),
			'fieldname': 'test_id',
			'fieldtype': 'Link',
			"options": "Lab Test",
			'width': 120
		},
		{
			'label': _("Patient"),
			'fieldname': 'patient',
			'fieldtype': 'Link',
			"options": "Patient",
			'width': 120
		},
		
		{
			'label': _("Doctor Name"),
			'fieldname': 'doctor_name',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			"label": _('Test Code'),
			"fieldname": "test_code",
			"fieldtype": "Link",
			"options": "Lab Test Template",
		},
		{
			"label": _('Test Count'),
			"fieldname": "test_count",
			"fieldtype": "Int",
		},
		{
			"label": _('Collection Date'),
			"fieldname": "collection_time",
			"fieldtype": "Datetime",
			'width': 200
		},
		{
			"label": _('Release Date'),
			"fieldname": "release_time",
			"fieldtype": "Datetime",
			'width': 200
		},
		{
			"label": _('Finalized Date'),
			"fieldname": "finalize_time",
			"fieldtype": "Datetime",
			'width': 200
		},
		{
			"label": _('Expected TAT'),
			"fieldname": "expected_tat",
			"fieldtype": "Data",
			'width': 200
		},
		{
			"label": _('Actual TAT'),
			"fieldname": "actual_tat",
			"fieldtype": "Data",
			'width': 200
		},
		{
			"label": _('Delayed'),
			"fieldname": "tat_flag",
			"fieldtype": "Check",
			'width': 80
		},

		
	]

import datetime 

def get_data(filters=None):
	from_date = datetime.datetime.strptime(filters.get('from_date'), '%Y-%m-%d') 
	to_date = datetime.datetime.strptime(filters.get('to_date'), '%Y-%m-%d') + datetime.timedelta(days=1)
	lab_test = ''
	if filters.get('lab_test'):
		lab_test = ' AND res.template=%(lab_test)s'
	tests = frappe.db.sql("""
		SELECT res.creation as requested_date, res.parent as test_id,
		lab.patient, practitioner_name as doctor_name, res.template as test_code,
		res.collection_time, res.release_time, res.finalize_time,
		CONCAT(FORMAT(tmplt.expected_tat, 1), " " , tmplt.expected_tat_unit) as expected_tat,
		TIMEDIFF(res.finalize_time, res.collection_time) AS actual_tat,
		1 as test_count,
		CASE
   		 	WHEN TIMESTAMPDIFF(SECOND, res.collection_time, res.finalize_time) > tmplt.expected_tat_seconds THEN 1
			ELSE 0
		END AS tat_flag
		FROM `tabNormal Test Result` as res
		INNER JOIN `tabLab Test` as lab ON lab.name=res.parent
		INNER JOIN `tabLab Test Template` as tmplt ON tmplt.name=res.template
		WHERE lab.creation >= %(from_date)s AND lab.creation <= %(to_date)s {lab_test}
	""".format(lab_test=lab_test), {
		"lab_test": filters.get('lab_test'), 
		"from_date": from_date, "to_date":
		  to_date,}, as_dict=True)
	# invoice_tests = {}
	# for test in tests:
	# 	test_tat = frappe.db.get_value('Lab Test Template', test.get('test_code'), ['expected_tat', 'expected_tat_unit'])
	# 	if test_tat:
	# 		total_tat_seconds = get_tat_time_seconds(test_tat[0], test_tat[1])
	# 		# if not invoice_tests.get(test.get('test_id')):
	# 		# 	invoice_tests[test.get('test_id')] = {
	# 		# 		"test": test,
	# 		# 		"total_tat_seconds": total_tat_seconds
	# 		# 	}
	# 		test['expected_tat'] = str(test_tat[0]) + " " + str(test_tat[1])
	# 		if test['finalize_time'] and test['collection_time']:
	# 			time_difference = test['finalize_time'] - test['collection_time']
	# 			if time_difference.total_seconds() > total_tat_seconds:
	# 				test['tat_flag'] = 1
	return tests


 


def get_data_old(filters=None):
	from_date = datetime.datetime.strptime(filters.get('from_date'), '%Y-%m-%d') 
	to_date = datetime.datetime.strptime(filters.get('to_date'), '%Y-%m-%d') + datetime.timedelta(days=1)
	test_tat = frappe.db.get_value('Lab Test Template', filters.get('lab_test'), ['expected_tat', 'expected_tat_unit'])
	total_tat_seconds = get_tat_time_seconds(test_tat[0], test_tat[1])
	return frappe.db.sql("""
		SELECT res.creation as requested_date, res.parent as test_id,
		lab.patient, practitioner_name as doctor_name, res.template as test_code,
		res.collection_time, res.finalize_time, %(expected_tat)s as expected_tat, 
		TIMEDIFF(res.finalize_time, res.collection_time) AS actual_tat,
		CASE
   		 	WHEN TIMESTAMPDIFF(SECOND, collection_time, finalize_time) > {total_tat_seconds} THEN 1
			ELSE 0
		END AS tat_flag
		FROM `tabNormal Test Result` as res
		INNER JOIN `tabLab Test` as lab ON lab.name=res.parent
		WHERE lab.creation >= %(from_date)s AND lab.creation <= %(to_date)s AND res.template=%(lab_test)s
	""".format(total_tat_seconds=total_tat_seconds), {"lab_test": filters.get('lab_test'), "from_date": from_date, "to_date": to_date, "expected_tat": str(test_tat[0]) + " " + str(test_tat[1])}, as_dict=True)


def get_tat_time_seconds(tat, tat_unit):
	if tat_unit == 'Minute':
		return datetime.timedelta(minutes=tat).total_seconds()
	if tat_unit == 'Hour':
		return datetime.timedelta(hours=tat).total_seconds()
	if tat_unit == 'Day':
		return datetime.timedelta(days=tat).total_seconds()
	if tat_unit == 'Month':
		return datetime.timedelta(days= tat * 30).total_seconds()
	return tat