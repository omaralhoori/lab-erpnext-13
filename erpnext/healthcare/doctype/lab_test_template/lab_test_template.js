// Copyright (c) 2016, ESS
// License: ESS license.txt

frappe.ui.form.on('Lab Test Template', {
	lab_test_name: function(frm) {
		if (!frm.doc.lab_test_code)
			frm.set_value('lab_test_code', frm.doc.lab_test_name);
		if (!frm.doc.lab_test_description)
			frm.set_value('lab_test_description', frm.doc.lab_test_name);
	},
	add_item_group_btn: function(frm){
		frappe.call({
			method: "erpnext.healthcare.doctype.lab_test_template.lab_test_template.get_package_templates",
			args:{
				test_template: frm.doc.custom_group_item
			},
			callback: (res) => {
				if (res.message){
					for (var item of res.message){
						var row = frm.add_child("lab_test_groups");
						frappe.model.set_value(row.doctype, row.name, "lab_test_template", item.template);
					}

					frm.set_value("custom_group_item", "")
					frm.refresh_fields("lab_test_groups");
				}
			}
		})
	},
	refresh : function(frm) {
		// Restrict Special, Grouped type templates in Child Test Groups
		if (frm.is_new()){
			frm.set_value("company", "")
		}
		if (frm.doc.lab_test_template_type == 'Multiline'){
			frm.set_query('lab_test_template', 'lab_test_groups', function() {
				return {
					filters: {
						 //lab_test_template_type: ['in', ['Single','Multiline','Compound']]
						lab_test_template_type: ['in', ['Single']]
					}
				};
			});
		}else if (frm.doc.lab_test_template_type == 'Grouped'){
			frm.set_query('lab_test_template', 'lab_test_groups', function() {
				return {
					filters: {
						 //lab_test_template_type: ['in', ['Single','Multiline','Compound']]
						lab_test_template_type: ['in', ['Multiline','Grouped']]
					}
				};
			});
		}else{
			frm.set_query('lab_test_template', 'lab_test_groups', function() {
				return {
					filters: {
						 //lab_test_template_type: ['in', ['Single','Multiline','Compound']]
						lab_test_template_type: ['in', ['Single','Multiline','Compound']]
					}
				};
			});
		}
	},
	medical_code: function(frm) {
		frm.set_query('medical_code', function() {
			return {
				filters: {
					medical_code_standard: frm.doc.medical_code_standard
				}
			};
		});
	},
	lab_test_template_type:function(frm) {
		// Restrict Special, Grouped type templates in Child Test Groups
		if (frm.doc.lab_test_template_type == 'Multiline'){
			frm.set_query('lab_test_template', 'lab_test_groups', function() {
				return {
					filters: {
						 //lab_test_template_type: ['in', ['Single','Multiline','Compound']]
						lab_test_template_type: ['in', ['Single']]
					}
				};
			});
		}else if (frm.doc.lab_test_template_type == 'Grouped'){
			frm.set_query('lab_test_template', 'lab_test_groups', function() {
				return {
					filters: {
						 //lab_test_template_type: ['in', ['Single','Multiline','Compound']]
						lab_test_template_type: ['in', ['Multiline','Grouped']]
					}
				};
			});
		}else{
			frm.set_query('lab_test_template', 'lab_test_groups', function() {
				return {
					filters: {
						 //lab_test_template_type: ['in', ['Single','Multiline','Compound']]
						lab_test_template_type: ['in', ['Single','Multiline','Compound']]
					}
				};
			});
		}
	},
	copy_normal_ranges: function(frm) {
		if (! frm.doc.normal_range_branch){
			return frappe.msgprint(__("Please fill branch field!"));
		}
		

		for (var range of frm.doc.branch_normal_ranges){
			 if (range.company == frm.doc.normal_range_branch){
				return frappe.confirm(__("There are Normal Ranges related to this branch. Do you want to proceed?"), ()=> {
					console.log('Test');
					add_normal_ranges(frm,frm.doc.normal_range_branch )
				}, () => {

				})
			}
		}
		add_normal_ranges(frm,frm.doc.normal_range_branch )
	}
});
const add_normal_ranges = (frm, branch) => {
	for(var range of frm.doc.attribute_normal_range) {
		// var rangeCopy = {...range}
		// delete rangeCopy.owner;delete rangeCopy.creation;delete rangeCopy.idx;
		// delete rangeCopy.name;delete rangeCopy.modified; delete rangeCopy.modified_by;
		
		// rangeCopy.parentfield='branch_normal_ranges';
		// rangeCopy.company = branch;
		// console.log(rangeCopy);
		var child = frm.add_child("branch_normal_ranges" );
		child.range_type= range.range_type;
		child.result_type= range.result_type;
		child.gender= range.gender;
		child.effective_date= range.effective_date;
		child.criteria_text= range.criteria_text;
		child.range_order= range.range_order;
		child.expiry_date= range.expiry_date;
		child.hide_normal_range= range.hide_normal_range;
		child.age_range= range.age_range;
		child.from_age_period= range.from_age_period;
		child.from_age= range.from_age;
		child.to_age_period= range.to_age_period;
		child.to_age= range.to_age;
		child.range_text= range.range_text;
		child.range_from= range.range_from;
		child.range_to= range.range_to;
		child.si_range_text= range.si_range_text;
		child.min_si_value= range.min_si_value;
		child.max_si_value= range.max_si_value;
		child.company= branch;
		frm.refresh_field("branch_normal_ranges");
		
	}
}
cur_frm.cscript.custom_refresh = function(doc) {
	cur_frm.set_df_property('lab_test_code', 'read_only', doc.__islocal ? 0 : 1);

	if (!doc.__islocal) {
		cur_frm.add_custom_button(__('Change Template Code'), function() {
			change_template_code(doc);
		});
	}
};

let change_template_code = function(doc) {
	let d = new frappe.ui.Dialog({
		title:__('Change Template Code'),
		fields:[
			{
				'fieldtype': 'Data',
				'label': 'Lab Test Template Code',
				'fieldname': 'lab_test_code',
				reqd: 1
			}
		],
		primary_action: function() {
			let values = d.get_values();
			if (values) {
				frappe.call({
					'method': 'erpnext.healthcare.doctype.lab_test_template.lab_test_template.change_test_code_from_template',
					'args': {lab_test_code: values.lab_test_code, doc: doc},
					callback: function (data) {
						frappe.set_route('Form', 'Lab Test Template', data.message);
					}
				});
			}
			d.hide();
		},
		primary_action_label: __('Change Template Code')
	});
	d.show();

	d.set_values({
		'lab_test_code': doc.lab_test_code
	});
};

frappe.ui.form.on('Lab Test Template', 'lab_test_name', function(frm) {
	frm.doc.change_in_item = 1;
});

frappe.ui.form.on('Lab Test Template', 'lab_test_rate', function(frm) {
	frm.doc.change_in_item = 1;
});

frappe.ui.form.on('Lab Test Template', 'lab_test_group', function(frm) {
	frm.doc.change_in_item = 1;
});

frappe.ui.form.on('Lab Test Template', 'lab_test_description', function(frm) {
	frm.doc.change_in_item = 1;
});

frappe.ui.form.on('Lab Test Groups', 'template_or_new_line', function (frm, cdt, cdn) {
	let child = locals[cdt][cdn];
	if (child.template_or_new_line == 'Add New Line') {
		frappe.model.set_value(cdt, cdn, 'lab_test_template', '');
		frappe.model.set_value(cdt, cdn, 'lab_test_description', '');
	}
});
