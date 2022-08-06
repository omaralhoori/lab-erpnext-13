// Copyright (c) 2016, ESS and contributors
// For license information, please see license.txt

cur_frm.cscript.custom_refresh = function (doc) {
	cur_frm.toggle_display('sb_sensitivity', doc.sensitivity_toggle);
	cur_frm.toggle_display('organisms_section', doc.descriptive_toggle);
	cur_frm.toggle_display('sb_descriptive', doc.descriptive_toggle);
	cur_frm.toggle_display('sb_normal', doc.normal_toggle);
};

const create_tests_result_type =  (childTest, options) => {
	var result_type = undefined;
	if (["Numeric", "Formula", "Ratio"].includes(childTest['control_type'])){
		result_type = `<label>
		Conv Result
	</label>
	<input ${disable_input(childTest['status'])}  class="input test-input-control" name="${childTest['name']}" value="${childTest['result_value'] || ""}"/>
	<label>
		SI Result
	</label>
	<input class="test-input-control" disabled name="${childTest['name']}" value="${childTest['secondary_uom_result'] || ""}"/>
`
	}
	else if (["Drop Down List"].includes(childTest['control_type'])){
		
		// var attributes_list = await frappe.db.get_list("Lab Test Template Attribute", {filters: {"parent": childTest['template']}, fields: ["form_attribute_description"]})
		// var attributes = attributes_list.map((attr) => {
		// 	return `
		// 	<option>${attr['form_attribute_description']}</option>
		// 	`;
		// })
		// var attributes_list = await frappe.db.get_value("Lab Test Template", childTest['template'],  ["attribute_options"])
		// var attributes = attributes_list['attribute_options']
		result_type = `
		<label>
			Select Result
		</label>
		<select ${disable_input(childTest['status'])}  class="test-input-control freetext-select">
			<option></option>
			${options}
	</select>
		<label>
		Result
		</label>
	<input class="input test-input-control" disabled name="${childTest['name']}" value="${childTest['result_value'] || ""}"/>

	
		`
	}
	else if (["Free Text"].includes(childTest['control_type'])){
		// var attributes_list = await frappe.db.get_value("Lab Test Template", childTest['template'],  ["attribute_options"])
		// var attributes = attributes_list['attribute_options']
		result_type = `
		<label>
		Result
		</label>
	<input ${disable_input(childTest['status'])}  class="input test-input-control" name="${childTest['name']}" value="${childTest['result_value'] || ""}"/>

	<label>Default Option</label>
	<select ${disable_input(childTest['status'])} class="test-input-control freetext-select">
			<option></option>
			${options}
	</select>
		`
	}else if (["Upload File"].includes(childTest['control_type'])){
		result_type = `
		<label>
		Upload Result File
		</label>
		
		<div  ${disable_input(childTest['status'])}  class="upload-btn" name="${childTest['name']}" value="${childTest['result_value'] || ''}"></div>
		`
		
	}

	return result_type;
}
const disable_input = (status) => {
	return status == "Rejected" || status == "Finalized" ? 'disabled' : ''; 
}
const format_tests_html = (tests, attr_options) => {
	var html = "";
	if (frappe.user.has_role('LabTest Approver')){
		html = `<div> 
	<button class='btn test-selected-btn' name='Finalized' disabled>Finalize Selected</button>
	<button class='btn test-selected-btn' name='Rejected' disabled>Reject Selected</button>
	</div>`
	}else{
		html = `<div> 
		<button class='btn test-selected-btn' name='Received' disabled>Receive Selected</button>
		<button class='btn test-selected-btn' name='Released' disabled>Release Selected</button>
		</div>`
	}
	html = html = `<div> 
	<button class='btn test-selected-btn' name='Received' disabled>Receive Selected</button>
	<button class='btn test-selected-btn' name='Released' disabled>Release Selected</button>
	<button class='btn test-selected-btn' name='Finalized' disabled>Finalize Selected</button>
	<button class='btn test-selected-btn' name='Rejected' disabled>Reject Selected</button>
	</div>`
	var options = attr_options.reduce((obj, item) => (obj[item.template] = item.attribute_options, obj) ,{});
	for (var testTemplate in tests){
		var child_tests_html = "";
		for (var childTest of tests[testTemplate]){
			var result_type = undefined;
			result_type = create_tests_result_type(childTest, options[childTest['template']])
			if (result_type){
				child_tests_html += `
				<div class="child-test-container ${childTest['status']}">
					<label> <strong>${childTest['lab_test_name']} </strong></label>
					<div class="test_result_container">
					${result_type}
					<input type="checkbox" value="${childTest['name']}" class="result-checkbox" />
					${childTest['status'] || ""}
					</div>
				</div>
			`;
			}
			
		}
		
		html += `
		<div class="test-container">
			<h4>${testTemplate}</h4>
			<div class="child-tests">
			${child_tests_html}
			</div>
		</div>`
	}
	return html
}
const setup_input_listeners = (frm) => {
	$('.child-tests .input').change(function(value) {
		//console.log($(this).attr('name'), $(this).val());
		frappe.model.set_value('Normal Test Result',$(this).attr('name'), "result_value", $(this).val());
	})
	$('.child-tests .freetext-select').change(function(value) {
		//console.log($(this).attr('name'), $(this).val());
		$(this).parent().find(".input").val($(this).val())
		frappe.model.set_value('Normal Test Result',$(this).parent().find(".input").attr('name'), "result_value", $(this).val());
	})
	$('.child-tests .upload-btn').each(function(){
		let me = this;
		let input = frappe.ui.form.make_control({
			df: {
				"fieldtype": "Attach",
				"label": "Item",
				"fieldname": "file_url",
				onchange: function () {
					frappe.model.set_value('Normal Test Result',$(me).attr('name'), "result_value", this.value);
				}
			},
			parent: this//$('.child-tests .upload-btn'),
		});
		input.set_value($(this).attr("value"))
	input.make_input()
	})
	$('.result-checkbox').change(function() {
		if ($(".result-checkbox:checked").length > 0)
			{
				toggle_test_selected_buttons(true);
			}
			else
			{
				toggle_test_selected_buttons(false);
			}
	});

	$('.test-selected-btn').click(function() {
		let button = $(this).attr("name");
		var searchIDs = $(".result-checkbox:checked").map(function(){
			//frappe.model.set_value('Normal Test Result', $(this).val(), "status", button) ;
			return $(this).val();
		  }).get();
		frappe.call({
			method: "erpnext.healthcare.doctype.lab_test.lab_test.apply_test_button_action",
			args: {
				action: button,
				tests: searchIDs,
				sample: frm.doc.sample,
				test_name: frm.doc.name
			},
			callback: () =>
			{
				frm.reload_doc();
			}
		})
	})
	
}
const toggle_test_selected_buttons = (value) => {
	$('.test-selected-btn').prop('disabled', !value);
}
frappe.ui.form.on('Lab Test', {
	setup: function (frm) {
		frm.get_field('normal_test_items').grid.editable_fields = [
			{ fieldname: 'lab_test_name', columns: 3 },
			{ fieldname: 'lab_test_event', columns: 2 },
			{ fieldname: 'result_value', columns: 2 },
			{ fieldname: 'lab_test_uom', columns: 1 },
			{ fieldname: 'normal_range', columns: 2 }
		];
		frm.get_field('descriptive_test_items').grid.editable_fields = [
			{ fieldname: 'lab_test_particulars', columns: 3 },
			{ fieldname: 'result_value', columns: 7 }
		];
	},
	refresh: function (frm) {
		if (!frm.is_new()){
			frm.add_custom_button(__('Print'), function(){
				//let url = `/printview?doctype=Lab%20Test&name=${frm.doc.name}&trigger_print=1&format=Lab%20Test%20Print&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en-US`;
				let url = `/api/method/erpnext.healthcare.doctype.lab_test.lab_test_print.lab_test_result?lab_test=${frm.doc.name}`
				window. open(url, '_blank')
			})
			var tests = {};
			
			cur_frm.doc.normal_test_items.forEach(item => {
				if (! tests[item['report_code']]) {
					tests[item['report_code']] = [];
				}
				tests[item['report_code']].push(item);
			})
			frappe.call({
				method: "erpnext.healthcare.doctype.lab_test.lab_test.get_test_attribute_options",
				args: {
					lab_test: frm.doc.name
				},
			}).then(res => {
				$(frm.fields_dict.lab_test_html.wrapper).html( format_tests_html(tests, res.message))
				setup_input_listeners(frm);
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
		refresh_field('normal_test_items');
		refresh_field('descriptive_test_items');
		if (frm.doc.__islocal) {
			frm.add_custom_button(__('Get from Patient Encounter'), function () {
				get_lab_test_prescribed(frm);
			});
		}
		if (frappe.user.has_role('LabTest Approver')) {
			frm.add_custom_button(__('Reject Sample'), function () {
				get_rejects_sample(frm);
			});
			frm.add_custom_button(__('Finalize'), function () {
				get_finalize_test(frm);
			});
		}
		

		frm.add_custom_button(__('Release Sample'), function () {
			get_release_sample(frm);
		});

		frm.add_custom_button(__('Receive Sample'), function () {
			get_receive_sample(frm);
		});

		if (frappe.defaults.get_default('lab_test_approval_required') && frappe.user.has_role('LabTest Approver')) {
			if (frm.doc.docstatus === 1 && frm.doc.status !== 'Approved' && frm.doc.status !== 'Rejected') {
				frm.add_custom_button(__('Approve'), function () {
					status_update(1, frm);
				}, __('Actions'));
				frm.add_custom_button(__('Reject'), function () {
					status_update(0, frm);
				}, __('Actions'));
			}
		}

		if (frm.doc.docstatus === 1 && frm.doc.sms_sent === 0 && frm.doc.status !== 'Rejected' ) {
			frm.add_custom_button(__('Send SMS'), function () {
				frappe.call({
					method: 'erpnext.healthcare.doctype.healthcare_settings.healthcare_settings.get_sms_text',
					args: { doc: frm.doc.name },
					callback: function (r) {
						if (!r.exc) {
							var emailed = r.message.emailed;
							var printed = r.message.printed;
							make_dialog(frm, emailed, printed);
						}
					}
				});
			});
		}

	}
});

frappe.ui.form.on('Lab Test', 'patient', function (frm) {
	if (frm.doc.patient) {
		frappe.call({
			'method': 'erpnext.healthcare.doctype.patient.patient.get_patient_detail',
			args: { patient: frm.doc.patient },
			callback: function (data) {
				var age = null;
				if (data.message.dob) {
					age = calculate_age(data.message.dob);
				}
				let values = {
					'patient_age': age,
					'patient_sex': data.message.sex,
					'email': data.message.email,
					'mobile': data.message.mobile,
					'report_preference': data.message.report_preference
				};
				frm.set_value(values);
			}
		});
	}
});

frappe.ui.form.on('Normal Test Result', {
	normal_test_items_remove: function () {
		frappe.msgprint(__('Not permitted, configure Lab Test Template as required'));
		cur_frm.reload_doc();
	}
});

frappe.ui.form.on('Descriptive Test Result', {
	descriptive_test_items_remove: function () {
		frappe.msgprint(__('Not permitted, configure Lab Test Template as required'));
		cur_frm.reload_doc();
	}
});
//ibrahim
var status_update = function (approve, frm) {
	var doc = frm.doc;
	var status = null;
	if (approve == 2) {
		status = 'Received';
	}
	else if (approve == 3) {
		status = 'Released';
	}
	else if (approve == 4) {
		status = 'Rejected';
	}
	else if (approve == 1) {
		status = 'Approved';
	}
	else {
		status = 'Rejected';
	}
	frappe.call({
		method: 'erpnext.healthcare.doctype.lab_test.lab_test.update_status',
		args: { status: status, name: doc.name },
		callback: function () {
			cur_frm.reload_doc();
		}
	});
};

var get_lab_test_prescribed = function (frm) {
	if (frm.doc.patient) {
		frappe.call({
			method: 'erpnext.healthcare.doctype.lab_test.lab_test.get_lab_test_prescribed',
			args: { patient: frm.doc.patient },
			callback: function (r) {
				show_lab_tests(frm, r.message);
			}
		});
	}
	else {
		frappe.msgprint(__('Please select Patient to get Lab Tests'));
	}
};
//ibrahim
var get_receive_sample = function (frm) {
	if (frm.doc.sample) {
		frappe.call({
			method: 'erpnext.healthcare.doctype.lab_test.lab_test.get_receive_sample',
			args: { 
				sample: frm.doc.sample,
				test_name: frm.doc.name 
			
			},
			callback: function (r) {
				if (r.message != '0') { // draft
					status_update(2, frm);
				}
			}
		});
	}
	else {
		frappe.msgprint(__('No sample collection found'));
	}
};
//ibrahim
var get_release_sample = function (frm) {
	if (frm.doc.status == 'Received' || frm.doc.status == 'Rejected') {
		let confirm = false;
		for(var item in  frm.doc.normal_test_items){
			if(!item.result_value){
				confirm = true;
				break;
			}
		}
		if (confirm){
			frappe.confirm('Not all test results have been entered. Are you sure you want to proceed?',
					() => {
						release_sample(frm);
					}, () => {
						// action to perform if No is selected
					})
		}else{
			release_sample(frm)
		}
		
	}
	else {
		frappe.msgprint(__('Sample not received or rejected'));
	}
};
const release_sample = function (frm){
	frappe.call({
		method: 'erpnext.healthcare.doctype.lab_test.lab_test.get_release_sample',
		args: { 
			doclab: frm.doc,
			docname: frm.doc.name
		},
		callback: function (r) {
			if (r.message == 'Received' || r.message == 'Rejected') { 
				status_update(3, frm);
			}
		}
	});
}
//ibrahim
var get_rejects_sample = function (frm) {
	if (frm.doc.status == 'Released'  ) {
		frappe.call({
			method: 'erpnext.healthcare.doctype.lab_test.lab_test.get_reject_sample',
			args: { 
				docname: frm.doc.name ,
			},
			callback: function (r) {
				if (r.message == 'Released') { // draft
					status_update(4, frm);
				}
			}
		});
	}
	else {
		frappe.msgprint(__('Sample not released'));
	}
};

var get_finalize_test = function(frm) {
	
}


var show_lab_tests = function (frm, lab_test_list) {
	var d = new frappe.ui.Dialog({
		title: __('Lab Tests'),
		fields: [{
			fieldtype: 'HTML', fieldname: 'lab_test'
		}]
	});
	var html_field = d.fields_dict.lab_test.$wrapper;
	html_field.empty();
	$.each(lab_test_list, function (x, y) {
		var row = $(repl(
			'<div class="col-xs-12" style="padding-top:12px;">\
				<div class="col-xs-3"> %(lab_test)s </div>\
				<div class="col-xs-4"> %(practitioner_name)s<br>%(encounter)s</div>\
				<div class="col-xs-3"> %(date)s </div>\
				<div class="col-xs-1">\
					<a data-name="%(name)s" data-lab-test="%(lab_test)s"\
					data-encounter="%(encounter)s" data-practitioner="%(practitioner)s"\
					data-invoiced="%(invoiced)s" href="#"><button class="btn btn-default btn-xs">Get</button></a>\
				</div>\
			</div><hr>',
			{ name: y[0], lab_test: y[1], encounter: y[2], invoiced: y[3], practitioner: y[4], practitioner_name: y[5], date: y[6] })
		).appendTo(html_field);

		row.find("a").click(function () {
			frm.doc.template = $(this).attr('data-lab-test');
			frm.doc.prescription = $(this).attr('data-name');
			frm.doc.practitioner = $(this).attr('data-practitioner');
			frm.set_df_property('template', 'read_only', 1);
			frm.set_df_property('patient', 'read_only', 1);
			frm.set_df_property('practitioner', 'read_only', 1);
			frm.doc.invoiced = 0;
			if ($(this).attr('data-invoiced') === 1) {
				frm.doc.invoiced = 1;
			}
			refresh_field('invoiced');
			refresh_field('template');
			d.hide();
			return false;
		});
	});
	if (!lab_test_list.length) {
		var msg = __('No Lab Tests found for the Patient {0}', [frm.doc.patient_name.bold()]);
		html_field.empty();
		$(repl('<div class="col-xs-12" style="padding-top:0px;" >%(msg)s</div>', { msg: msg })).appendTo(html_field);
	}
	d.show();
};

var make_dialog = function (frm, emailed, printed) {
	var number = frm.doc.mobile;

	var dialog = new frappe.ui.Dialog({
		title: 'Send SMS',
		width: 400,
		fields: [
			{ fieldname: 'result_format', fieldtype: 'Select', label: 'Result Format', options: ['Emailed', 'Printed'] },
			{ fieldname: 'number', fieldtype: 'Data', label: 'Mobile Number', reqd: 1 },
			{ fieldname: 'message', fieldtype: 'Small Text', label: 'Message', reqd: 1 }
		],
		primary_action_label: __('Send'),
		primary_action: function () {
			var values = dialog.fields_dict;
			if (!values) {
				return;
			}
			send_sms(values, frm);
			dialog.hide();
		}
	});
	if (frm.doc.report_preference === 'Print') {
		dialog.set_values({
			'result_format': 'Printed',
			'number': number,
			'message': printed
		});
	} else {
		dialog.set_values({
			'result_format': 'Emailed',
			'number': number,
			'message': emailed
		});
	}
	var fd = dialog.fields_dict;
	$(fd.result_format.input).change(function () {
		if (dialog.get_value('result_format') === 'Emailed') {
			dialog.set_values({
				'number': number,
				'message': emailed
			});
		} else {
			dialog.set_values({
				'number': number,
				'message': printed
			});
		}
	});
	dialog.show();
};

var send_sms = function (vals, frm) {
	var number = vals.number.value;
	var message = vals.message.last_value;

	if (!number || !message) {
		frappe.throw(__('Did not send SMS, missing patient mobile number or message content.'));
	}
	frappe.call({
		method: 'frappe.core.doctype.sms_settings.sms_settings.send_sms',
		args: {
			receiver_list: [number],
			msg: message
		},
		callback: function (r) {
			if (r.exc) {
				frappe.msgprint(r.exc);
			} else {
				frm.reload_doc();
			}
		}
	});
};

var calculate_age = function (dob) {
	var ageMS = Date.parse(Date()) - Date.parse(dob);
	var age = new Date();
	age.setTime(ageMS);
	var years = age.getFullYear() - 1970;
	return `${years} ${__('Years(s)')} ${age.getMonth()} ${__('Month(s)')} ${age.getDate()} ${__('Day(s)')}`;
};
