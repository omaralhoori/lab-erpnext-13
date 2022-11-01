// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Balance Confirmation Statement', {
	refresh: function(frm) {
		
		frm.add_custom_button('Prepare Statements',function(){

			frappe.call({
				method: "erpnext.accounts.doctype.balance_confirmation_statement.balance_confirmation_statement.prepare_statements",
				args: {
					"docname": frm.doc.name
				},
				callback: function(res){
					frm.reload_doc()
				}
			})
		});

		if(frm.doc.status == 'In Progress'){
			$('button[data-label="Prepare%20Statements"]').prop('disabled', true);
		}
	},
	fetch_customers: function(frm){
		if(frm.doc.collection_name){
			frappe.call({
				method: "erpnext.accounts.doctype.balance_confirmation_statement.balance_confirmation_statement.fetch_customers",
				args: {
					'customer_collection': frm.doc.customer_collection,
					'collection_name': frm.doc.collection_name
				},
				callback: function(r) {
					if(!r.exc) {
						if(r.message.length){
							frm.clear_table('customers');
							var customer_type = 'Customer';
							if(frm.doc.customer_collection == 'Supplier Group') customer_type = 'Supplier';
							for (const customer of r.message){
								var row = frm.add_child('customers');
								
								row.customer_type = customer_type;
								row.customer = customer.name;
								row.primary_email = customer.primary_email;
							}
							frm.refresh_field('customers');
						}
						else{
							frappe.throw(__('No Customers found with selected options.'));
						}
					}
				}
			});
		}
		else {
			frappe.throw('Enter ' + frm.doc.customer_collection + ' name.');
		}
	},
	get_template: async function(frm) {
		if(frm.doc.print_format_template){
			var res = await frappe.db.get_value("Balance Confirmation Statement Print Format", frm.doc.print_format_template, ["print_format"]);
			if(res.message.print_format){
				frm.set_value("print_format", res.message.print_format);
			}
		}else{
			frappe.throw('Enter print format template name.');
		}
	},
	download_statements: function(frm){
		var url  = frappe.urllib.get_full_url(
			'/api/method/erpnext.accounts.doctype.balance_confirmation_statement.balance_confirmation_statement.download_statements?'
			+ 'download_link='+encodeURIComponent(frm.doc.download_link));

			$.ajax({
				url: url,
				type: 'GET',
				success: function(result) {
					if(jQuery.isEmptyObject(result)){
						frappe.msgprint(__('No Records for these settings.'));
					}
					else{
						window.location = url;
					}
				}
			});
	}
});
