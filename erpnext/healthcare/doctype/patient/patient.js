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
						// Fingerprint Functions

					const uploadFP = (frm, image, values) => {
						frappe.show_progress('Capturing..', 50, 100, 'Please wait');
						let xhr = new XMLHttpRequest();
						
						xhr.open('POST', '/api/method/erpnext.healthcare.doctype.patient.patient.upload_fingerprint', true);
						xhr.setRequestHeader('Accept', 'application/json');

						xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);
						let form_data = new FormData();
						if (image) {
							form_data.append('file', image, frm.doc.name + "_" + (values.finger_name || "Unknown finger"));
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
						})
					}

					const  SuccessFunc = (frm, values, result)=> {
						if (result.ErrorCode == 0) {
							if (result != null && result.BMPBase64.length > 0) {
								uploadFP(frm, b64toBlob(result.BMPBase64, "image/bmp"), values)
							}else{
								frappe.throw("Fingerprint Capture Fail");
							}
						}
						else {
							frappe.throw("Fingerprint Capture Error Code: " + result.ErrorCode )
						}
					}

					const ErrorFunc = (status) =>{
						console.error(status);
						var progress = frappe.show_progress('Capturing..', 100, 100, 'Please wait');
						progress.hide();
						frappe.msgprint({
							title: __('Capturing status'),
							indicator: 'red',
							message: __('Fail to capture; Status =') + status
						});
					}

					const CallSGIFPGetData = async (frm, values, successCall, failCall) => {
						frappe.show_progress('Capturing..', 0, 100, 'Please wait');
						var uri = await frappe.db.get_single_value("Healthcare Settings", "fingerprint_scanner_url");
						if(!uri){
							frappe.throw(__("Fingerprint scanner url is not set!"));
							return;
						}
						var license = await frappe.db.get_single_value("Healthcare Settings", "web_api_licence");

						var xmlhttp = new XMLHttpRequest();
						xmlhttp.onreadystatechange = function () {
							if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
								var fpobject = JSON.parse(xmlhttp.responseText);
								successCall(frm, values, fpobject);
							}
							else if (xmlhttp.status == 404) {
								failCall(xmlhttp.status)
							}
						}
						var params = "Timeout=" + "10000";
						params += "&Quality=" + "50";
						params += "&licstr=" + encodeURIComponent(license || "");
						params += "&templateFormat=" + "ISO";
						params += "&imageWSQRate=" + "0.75";
						xmlhttp.open("POST", uri, true);
						xmlhttp.send(params);

						xmlhttp.onerror = function () {
							failCall(xmlhttp.statusText);
						}
					}

						var found = false;
						for(var row in frm.doc.fingerprints){
							if(frm.doc.fingerprints[row].finger === values.finger_name){
								found = true;
								frappe.confirm(values.finger_name + ' already exists. Are you sure you want to proceed?',
									() => {
										CallSGIFPGetData(frm, values, SuccessFunc, ErrorFunc);
									}, () => {
										// action to perform if No is selected
									})
								break;
							}
							
						}
						if(!found){
							CallSGIFPGetData(frm, values, SuccessFunc, ErrorFunc);
						}
						
			
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



function b64toBlob (b64Data, contentType='', sliceSize=512) {
	const byteCharacters = atob(b64Data);
	const byteArrays = [];
  
	for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
	  const slice = byteCharacters.slice(offset, offset + sliceSize);
  
	  const byteNumbers = new Array(slice.length);
	  for (let i = 0; i < slice.length; i++) {
		byteNumbers[i] = slice.charCodeAt(i);
	  }
  
	  const byteArray = new Uint8Array(byteNumbers);
	  byteArrays.push(byteArray);
	}
  
	const blob = new Blob(byteArrays, {type: contentType});
	return blob;
  }