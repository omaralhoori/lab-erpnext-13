# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import datetime
def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data


def get_data(filters):
	company = filters.get("company")
	if filters.get("filter_based_on") == "Date":
		condations = f" AND DATE(echk.time) ='{filters.get('log_date')}'"
	else:
		condations = f""" AND DATE(echk.time) >= "{filters.get('from_date')}" AND DATE(echk.time) <= "{filters.get('to_date')}" """ 

	checkins = frappe.db.sql("""
		select echk.name as checkin_name, echk.employee, 
			echk.time, echk.log_type, DATE(echk.time) ,
			tsa.start_date as shift_start_date, tsa.end_date as shift_end_date,
			tst.name  as shift, tst.start_time as shift_start_time,
			tst.end_time as shift_end_time,
			tst.begin_check_in_before_shift_start_time,
			tst.allow_check_out_after_shift_end_time,
			tst.enable_entry_grace_period,
			tst.enable_exit_grace_period,
			tst.late_entry_grace_period,
			tst.early_exit_grace_period,
			tst.holiday_list
		FROM `tabEmployee Checkin` as echk
		INNER JOIN `tabEmployee` as empl ON empl.name=echk.employee
		LEFT JOIN `tabShift Assignment` tsa ON tsa.employee=echk.employee
		LEFT JOIN `tabShift Type` tst ON tst.name=IFNULL(tsa.shift_type,empl.default_shift)
			WHERE empl.company=%(company)s AND 
			IF(tsa.end_date is not null , DATE(echk.time) <=tsa.end_date and DATE(echk.time) >= tsa.start_date and tsa.status='Active', True) {condations} 
			ORDER BY echk.time
	""".format(condations=condations), {"company": company}, as_dict=True)
	if filters.get("filter_based_on") == "Date":
		return get_data_for_single_day(checkins, filters.get("holiday_as_overtime"))
	else:
		return get_data_for_range_date(checkins,  filters.get("holiday_as_overtime"))

def get_data_for_range_date(checkins, holiday_as_overtime=False):
	data = []
	new_checkins = []
	for chk in checkins:
		if len(new_checkins) > 0 and new_checkins[0]['time'].date() == chk['time'].date():
			new_checkins.append(chk)
		else:
			data.extend(get_data_for_single_day(new_checkins, holiday_as_overtime))
			new_checkins = [chk]
	data.extend(get_data_for_single_day(new_checkins, holiday_as_overtime))
	return data	

def get_data_for_single_day(checkins, holiday_as_overtime=False):
	data = {}
	for chk in checkins:
		if data.get(chk['employee']):
			if chk['log_type'] == 'IN':
				if data[chk['employee']].get('enrty_datetime'):
					data[chk['employee']]['enrty_datetime_2'] =  chk['time']
				else:
					data[chk['employee']]['enrty_datetime'] =  chk['time']
					data[chk['employee']]['enrty_datetime_2'] =  chk['time']
			else:
				data[chk['employee']]['exit_datetime'] =  chk['time']
			if compare_two_dates(data[chk['employee']].get('exit_datetime'), data[chk['employee']].get('enrty_datetime_2')):
				data[chk['employee']]['total_work_hours'] += get_total_work_hours(data[chk['employee']].get('enrty_datetime_2'), data[chk['employee']].get('exit_datetime'))
				overtime = get_overtime(data[chk['employee']], chk)
				if holiday_as_overtime and is_date_holiday(data[chk['employee']]['enrty_datetime'], chk['holiday_list']):
					data[chk['employee']]['total_overtime_hours'] =  data[chk['employee']]['total_work_hours']
				else:
					data[chk['employee']]['total_overtime_hours'] = overtime[0]
					data[chk['employee']]['late_entry'] = overtime[1]
					data[chk['employee']]['early_exit'] = overtime[2]
		else:
			data[chk['employee']] = {
				"employee": chk['employee'],
				"total_overtime_hours": "00:00",
				"total_work_hours": datetime.timedelta(0),
				"late_entry": False,
				"early_exit": False,
				"total_shift_hours": get_hours_between_times(chk['shift_start_time'], chk['shift_end_time']),
			}
			if chk['log_type'] == 'IN':
				data[chk['employee']]['enrty_datetime'] = chk['time']
				data[chk['employee']]['enrty_datetime_2'] = chk['time']
			else:
				data[chk['employee']]['exit_datetime'] = chk['time']
	return list(data.values())

def get_overtime(employee_data, checkin):
	overtime = 0
	entry_late = False
	exit_early = False
	if not employee_data['enrty_datetime'] or not employee_data['exit_datetime']: return overtime, entry_late, exit_early
	# begin_check_in_before_shift_start_time, allow_check_out_after_shift_end_time
	checkin_date = employee_data['enrty_datetime'].date()
	shift_start_datetime = datetime.datetime(checkin_date.year, checkin_date.month, checkin_date.day) + checkin['shift_start_time']
	if shift_start_datetime >= employee_data['enrty_datetime'] :
		diff = shift_start_datetime - employee_data['enrty_datetime']
		if checkin['begin_check_in_before_shift_start_time'] and \
		checkin['begin_check_in_before_shift_start_time'] > 0 and \
		(diff.seconds/60) > checkin['begin_check_in_before_shift_start_time'] :
			overtime += checkin['begin_check_in_before_shift_start_time']  * 60
		else:
			overtime += diff.seconds
	else:
		diff = employee_data['enrty_datetime']  - shift_start_datetime
		if checkin['enable_entry_grace_period'] and checkin['late_entry_grace_period'] > 0:
			diff_seconds = diff.seconds - (checkin['late_entry_grace_period'] * 60)
			if diff_seconds > 0:
				entry_late = True
				overtime -= diff_seconds
		else:
			entry_late = True
			overtime -= diff.seconds

	shift_end_datetime = datetime.datetime(checkin_date.year, checkin_date.month, checkin_date.day) + checkin['shift_end_time']
	if shift_end_datetime <= employee_data['exit_datetime'] :
		diff = employee_data['exit_datetime'] - shift_end_datetime
		if checkin['allow_check_out_after_shift_end_time'] and \
		checkin['allow_check_out_after_shift_end_time'] > 0 and \
		(diff.seconds/60) > checkin['allow_check_out_after_shift_end_time'] :
			overtime += checkin['allow_check_out_after_shift_end_time']  * 60
		else:
			overtime += diff.seconds
	else:
		diff = shift_end_datetime - employee_data['exit_datetime']
		if checkin['enable_exit_grace_period'] and checkin['early_exit_grace_period'] > 0:
			diff_seconds = diff.seconds - (checkin['early_exit_grace_period'] * 60)
			if diff_seconds > 0:
				exit_early = True
				overtime -= diff_seconds
		else:
			exit_early = True
			overtime -= diff.seconds
	
		
	return format_time_in_seconds(overtime), entry_late, exit_early

def is_date_holiday(date, holiday_list):
	if type(date) == datetime.datetime:
		date = date.date()
	return frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date})

def compare_two_dates(first_date, second_date):
	if not first_date or not second_date: return False
	# a = datetime.strptime(first_date, "%d-%m-%Y %H:%M:%S")
	# b = datetime.strptime(second_date, "%d-%m-%Y %H:%M:%S")
	return first_date > second_date

def get_total_work_hours(first_time, second_time):
	# start_time = datetime.strptime(first_time, '%Y-%m-%d %H:%M:%S')
	# end_time = datetime.strptime(second_time, '%Y-%m-%d %H:%M:%S')

	time_delta = second_time - first_time
	#hours = time_delta.total_seconds() / 60
	return time_delta#float("{:.1f}".format(hours))

def format_time_in_seconds(time):
	formated_time = ""
	if time < 0:
		formated_time = "-"
		time = 0 - time
	hours = int(time / 3600)
	time = time % 3600
	minutes = int(time / 60)
	formated_time = f"{formated_time}{str(hours).zfill(2)}:{str(minutes).zfill(2)}"
	return formated_time

def get_hours_between_times(first_time, second_time):
	# time_obj_1 = datetime.strptime(first_time, '%H:%M:%S').time()
	# time_obj_2 = datetime.strptime(second_time, '%H:%M:%S').time()
	# default_date = datetime.strptime('2000-01-01', '%Y-%m-%d').date()

	# if time_obj_2 < time_obj_1:
	# 	time_diff = datetime.combine(default_date, time_obj_2) + timedelta(days=1) - datetime.combine(default_date, time_obj_1)
	# else:
	# 	time_diff = datetime.combine(default_date, time_obj_2) - datetime.combine(default_date, time_obj_1)
	time_diff = second_time - first_time
	#hours = time_diff.total_seconds() / 60
	return time_diff#float("{:.1f}".format(hours))

def get_columns(filters=None):
	columns =  [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 300
		},
		{
			"fieldname": "enrty_datetime",
			"label": _("Entry Datetime"),
			"fieldtype": "Datetime",
			"width": 200
		},
		{
			"fieldname": "exit_datetime",
			"label": _("Exit Datetime"),
			"fieldtype": "Datetime",
			"width": 200
		},
		{
			"fieldname": "total_shift_hours",
			"label": _("Total Shift Hours"),
			"fieldtype": "float",
			"width": 120
		},
		{
			"fieldname": "total_work_hours",
			"label": _("Total Work Hours"),
			"fieldtype": "Time",
			"width": 120
		},
		{
			"fieldname": "total_overtime_hours",
			"label": _("Total Overtime Hours"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "late_entry",
			"label": _("Late Entry"),
			"fieldtype": "check",
			"width": 80
		},
		{
			"fieldname": "early_exit",
			"label": _("Early Exit"),
			"fieldtype": "check",
			"width": 80
		},
	]

	return columns