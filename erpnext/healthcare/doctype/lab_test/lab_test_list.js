/*
(c) ESS 2015-16
*/
frappe.listview_settings['Lab Test'] = {
	add_fields: ['name', 'status', 'invoiced'],
	filters: [['docstatus', '=', '1']],
	get_indicator: function (doc) {
		if (doc.status === 'Approved') {
			return [__('Approved'), 'green', 'status, =, Approved'];
		} else if (doc.status === 'Rejected') {
			return [__('Rejected'), 'orange', 'status, =, Rejected'];
		} else if (doc.status === 'Completed') {
			return [__('Completed'), 'green', 'status, =, Completed'];
		} else if (doc.status === 'Cancelled') {
			return [__('Cancelled'), 'red', 'status, =, Cancelled'];
		}
	},
	onload: function (listview) {
		listview.page.add_menu_item(__('Create Multiple'), function () {
			create_multiple_dialog(listview);
		});

		let disabled = false;
		let query = "";
		let url = location.href;
		document.body.addEventListener('click', ()=>{
			requestAnimationFrame(()=>{
			if(url!==location.href){
				//$(document).find('*').off('keydown');
				disabled = true;
				query = "";
				url = location.href
			}

			let urls = location.href.split("/");
			if(urls[urls.length - 1] === "lab-test"){
				disabled = false;
			}
			});
		}, true);
		
		$(document).keydown(function(e) {
			if(abandonedChars(e.which) || disabled ) return; // || !frm.is_dirty()
			query += String.fromCharCode(switchedChars(e.which));
			//console.log(e.which)
			if(e.which == 13) {
				// ctrl+b pressed
				frappe.call({
					method: "erpnext.healthcare.barcode_query.find_lab_test",
					args: {
						"test_code": query
					},
					callback: (res) => {
						if(res.message != null && res.message != ""){
							window.location.href =  res.message;
						}
					}
				})
				query = "";
			}
			
		});
			
	}
};

var create_multiple_dialog = function (listview) {
	var dialog = new frappe.ui.Dialog({
		title: 'Create Multiple Lab Tests',
		width: 100,
		fields: [
			{ fieldtype: 'Link', label: 'Patient', fieldname: 'patient', options: 'Patient', reqd: 1 },
			{
				fieldtype: 'Select', label: 'Invoice / Patient Encounter', fieldname: 'doctype',
				options: '\nSales Invoice\nPatient Encounter', reqd: 1
			},
			{
				fieldtype: 'Dynamic Link', fieldname: 'docname', options: 'doctype', reqd: 1,
				get_query: function () {
					return {
						filters: {
							'patient': dialog.get_value('patient'),
							'docstatus': 1
						}
					};
				}
			}
		],
		primary_action_label: __('Create'),
		primary_action: function () {
			frappe.call({
				method: 'erpnext.healthcare.doctype.lab_test.lab_test.create_multiple',
				args: {
					'doctype': dialog.get_value('doctype'),
					'docname': dialog.get_value('docname')
				},
				callback: function (data) {
					if (!data.exc) {
						if (!data.message) {
							frappe.msgprint(__('No Lab Tests created'));
						}
						listview.refresh();
					}
				},
				freeze: true,
				freeze_message: __('Creating Lab Tests...')
			});
			dialog.hide();
		}
	});

	dialog.show();
};



function abandonedChars(charCode){
	if(charCode == 16){
		return true;
	}
	return false;
}

function switchedChars(charCode){
    if(charCode == 189){
		return 45;
	}
	return charCode;
}
