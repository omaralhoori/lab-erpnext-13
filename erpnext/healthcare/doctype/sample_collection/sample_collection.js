// Copyright (c) 2016, ESS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sample Collection', {
	refresh: function(frm) {
		if (frappe.defaults.get_default('create_sample_collection_for_lab_test')) {
			frm.add_custom_button(__('View Lab Tests'), function() {
				frappe.route_options = {'sample': frm.doc.name};
				frappe.set_route('List', 'Lab Test');
			});
		}
		if (!frm.is_new()){
			frm.add_custom_button(__('Print'), function(){
				//let url = `/printview?doctype=Lab%20Test&name=${frm.doc.name}&trigger_print=1&format=Lab%20Test%20Print&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en-US`;
				let url = `/printview?doctype=Sample%20Collection&name=${frm.doc.name}&trigger_print=1&format=Sample%20ID%20Print&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en`
				window. open(url, '_blank')
			})
		}
		if (!frm.is_new() && frm.doc.docstatus != 1){
			frm.add_custom_button(__('Send patient permitting message'), function() {
				let d = new frappe.ui.Dialog({
					title: 'Enter details',
					fields: [
						{
							label: 'Send to User',
							fieldname: 'to_user',
							fieldtype: 'Link',
							options: "User"
						},
					],
					primary_action_label: 'Send',
					primary_action(values) {
						frappe.call({
							method: "erpnext.healthcare.utils.publish_user_message",
							args: {
								user: values.to_user,
								msg: `Please allow patient: <a onclick="function hi(){frappe.set_route('permitted-patient', 'new-permitted-patient',{patient:'${frm.doc.patient}' })};hi()" >${frm.doc.patient}</a> to proceed without paying`
							}
						})

						d.hide();
					}
				});
				
				d.show();
				
				
			});
			
		}
	}
});

frappe.ui.form.on('Sample Collection', 'patient', function(frm) {
	if(frm.doc.patient){
		frappe.call({
			'method': 'erpnext.healthcare.doctype.patient.patient.get_patient_detail',
			args: {
				patient: frm.doc.patient
			},
			callback: function (data) {
				var age = null;
				if (data.message.dob){
					age = calculate_age(data.message.dob);
				}
				frappe.model.set_value(frm.doctype,frm.docname, 'patient_age', age);
				frappe.model.set_value(frm.doctype,frm.docname, 'patient_sex', data.message.sex);
			}
		});
	}
});

var calculate_age = function(birth) {
	var	ageMS = Date.parse(Date()) - Date.parse(birth);
	var	age = new Date();
	age.setTime(ageMS);
	var	years =  age.getFullYear() - 1970;
	return `${years} ${__('Years(s)')} ${age.getMonth()} ${__('Month(s)')} ${age.getDate()} ${__('Day(s)')}`;
};
