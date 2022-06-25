// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient', {
	refresh: function (frm) {
		frm.set_query('patient', 'patient_relation', function () {
			return {
				filters: [
					['Patient', 'name', '!=', frm.doc.name]
				]
			};
		});
		frm.set_query('customer_group', { 'is_group': 0 });
		frm.set_query('default_price_list', { 'selling': 1 });

		if (frappe.defaults.get_default('patient_name_by') != 'Naming Series') {
			frm.toggle_display('naming_series', false);
		} else {
			erpnext.toggle_naming_series();
		}

		if (frappe.defaults.get_default('collect_registration_fee') && frm.doc.status == 'Disabled') {
			frm.add_custom_button(__('Invoice Patient Registration'), function () {
				invoice_registration(frm);
			});
		}

		if (frm.doc.patient_name && frappe.user.has_role('Physician')) {
			frm.add_custom_button(__('Patient Progress'), function () {
				frappe.route_options = { 'patient': frm.doc.name };
				frappe.set_route('patient-progress');
			}, __('View'));

			frm.add_custom_button(__('Patient History'), function () {
				frappe.route_options = { 'patient': frm.doc.name };
				frappe.set_route('patient_history');
			}, __('View'));
		}

		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Patient' };
		frm.toggle_display(['address_html', 'contact_html'], !frm.is_new());

		if (!frm.is_new()) {
			if ((frappe.user.has_role('Nursing User') || frappe.user.has_role('Physician'))) {
				frm.add_custom_button(__('Medical Record'), function () {
					create_medical_record(frm);
				}, 'Create');
				frm.toggle_enable(['customer'], 0);
			}
			frm.add_custom_button(__('Add Fingerprint'), function () {
				let d = new frappe.ui.Dialog({
					title: 'Add Fingerprint',
					fields: [
						{
							label: 'Finger Name',
							fieldname: 'finger_name',
							fieldtype: 'Select',
							selected: 0,
							options: [
								"Unknown finger",
								"Right thumb",
								"Right index finger",
								"Right middle finger",
								"Right ring finger",
								"Right little finger",
								"Left thumb",
								"Left index finger",
								"Left middle finger",
								"Left ring finger",
								"Left little finger"
							]
						},
					],
					primary_action_label: 'Capture',
					async primary_action(values) {
						const capture_finger = async () => {
							frappe.show_progress('Capturing..', 0, 100, 'Please wait');
							var url = await frappe.db.get_single_value("Healthcare Settings", "fingerprint_scanner_url");
							if(!url){
								frappe.throw(__("Fingerprint scanner url is not set!"));
								return;
							}
							frappe.show_progress('Capturing..', 10, 100, 'Please wait');
							fetch(url).
								then(response => response.blob())
								.then(blob => {
									frappe.show_progress('Capturing..', 50, 100, 'Please wait');
									// xhr.open('POST', '/api/method/erpnext.healthcare.doctype.patient.patient.upload_fingerprint', true);
									let xhr = new XMLHttpRequest();
	
									xhr.open('POST', '/api/method/erpnext.healthcare.doctype.patient.patient.upload_fingerprint', true);
									xhr.setRequestHeader('Accept', 'application/json');
	
									xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);
	
									// let form_data = new FormData();
	
									// //var file = document.getElementById(‘id of the input file’).files[0];
	
									// form_data.append('file', blob, frm.doc.name + "_" + (values.finger_name || "Unknown finger") + ".raw");
	
									// xhr.send(form_data);
	
									// xhr.open('POST', '/api/method/upload_file', true);
									// xhr.setRequestHeader('Accept', 'application/json');
									// xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);
	
									let form_data = new FormData();
									if (blob) {
										form_data.append('file', blob, frm.doc.name + "_" + (values.finger_name || "Unknown finger"));
									}
									form_data.append('docname', frm.doc.name);
									form_data.append('finger_name', values.finger_name || "Unknown finger");
									form_data.append('filename', frm.doc.name + "_" + (values.finger_name || "Unknown finger"));
	
									xhr.send(form_data);
	
									xhr.addEventListener("load", (res) => {
										var progress = frappe.show_progress('Capturing..', 100, 100, 'Please wait');
										progress.hide();
										frappe.msgprint({
											title: __('Capturing status'),
											indicator: 'green',
											message: __('Successfully captured')
										});
										d.hide();
									})
								})
								.catch(err => {
									console.error(err);
									var progress = frappe.show_progress('Capturing..', 100, 100, 'Please wait');
									progress.hide();
									frappe.msgprint({
										title: __('Capturing status'),
										indicator: 'red',
										message: __('Fail to capture')
									});
								})
						}
						
						var found = false;
						for(var row in frm.doc.fingerprints){
							if(frm.doc.fingerprints[row].finger === values.finger_name){
								found = true;
								frappe.confirm(values.finger_name + ' already exists. Are you sure you want to proceed?',
									() => {
										capture_finger();
									}, () => {
										// action to perform if No is selected
									})
								break;
							}
							
						}
						if(!found){
							capture_finger();
						}
						

						// then(async res => {
						// 	const reader = res.body.getReader();
						// 	console.log(res);
						// 	while (true) {
						// 		const {image, done} = await reader.read();
						// 		console.log(image);
						// 		if(image){
						// 			console.log(image);
						// 		}else{
						// 			break;

						// 		}
						// 		if(done) break;
						// 	}
						// 	d.hide();
						// })*/
					}
				});

				d.show();
			});
			frappe.contacts.render_address_and_contact(frm);
			erpnext.utils.set_party_dashboard_indicators(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}
	},

	onload: function (frm) {
		if (frm.doc.dob) {
			$(frm.fields_dict['age_html'].wrapper).html(`${__('AGE')} : ${get_age(frm.doc.dob)}`);
		} else {
			$(frm.fields_dict['age_html'].wrapper).html('');
		}
	}
});

frappe.ui.form.on('Patient', 'dob', function (frm) {
	if (frm.doc.dob) {
		let today = new Date();
		let birthDate = new Date(frm.doc.dob);
		if (today < birthDate) {
			frappe.msgprint(__('Please select a valid Date'));
			frappe.model.set_value(frm.doctype, frm.docname, 'dob', '');
		} else {
			let age_str = get_age(frm.doc.dob);
			$(frm.fields_dict['age_html'].wrapper).html(`${__('AGE')} : ${age_str}`);
		}
	} else {
		$(frm.fields_dict['age_html'].wrapper).html('');
	}
});

frappe.ui.form.on('Patient Relation', {
	patient_relation_add: function (frm) {
		frm.fields_dict['patient_relation'].grid.get_field('patient').get_query = function (doc) {
			let patient_list = [];
			if (!doc.__islocal) patient_list.push(doc.name);
			$.each(doc.patient_relation, function (idx, val) {
				if (val.patient) patient_list.push(val.patient);
			});
			return { filters: [['Patient', 'name', 'not in', patient_list]] };
		};
	}
});

let create_medical_record = function (frm) {
	frappe.route_options = {
		'patient': frm.doc.name,
		'status': 'Open',
		'reference_doctype': 'Patient Medical Record',
		'reference_owner': frm.doc.owner
	};
	frappe.new_doc('Patient Medical Record');
};

let get_age = function (birth) {
	let ageMS = Date.parse(Date()) - Date.parse(birth);
	let age = new Date();
	age.setTime(ageMS);
	let years = age.getFullYear() - 1970;
	return years + ' Year(s) ' + age.getMonth() + ' Month(s) ' + age.getDate() + ' Day(s)';
};

let create_vital_signs = function (frm) {
	if (!frm.doc.name) {
		frappe.throw(__('Please save the patient first'));
	}
	frappe.route_options = {
		'patient': frm.doc.name,
	};
	frappe.new_doc('Vital Signs');
};

let create_encounter = function (frm) {
	if (!frm.doc.name) {
		frappe.throw(__('Please save the patient first'));
	}
	frappe.route_options = {
		'patient': frm.doc.name,
	};
	frappe.new_doc('Patient Encounter');
};

let invoice_registration = function (frm) {
	frappe.call({
		doc: frm.doc,
		method: 'invoice_patient_registration',
		callback: function (data) {
			if (!data.exc) {
				if (data.message.invoice) {
					frappe.set_route('Form', 'Sales Invoice', data.message.invoice);
				}
				cur_frm.reload_doc();
			}
		}
	});
};
