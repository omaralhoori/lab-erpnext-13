// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Price List", {
	refresh: function(frm) {
		let me = this;
		frm.add_custom_button(__("Add / Edit Prices"), function() {
			frappe.route_options = {
				"price_list": frm.doc.name
			};
			frappe.set_route("Report", "Item Price");
		}, "fa fa-money");

		if(!frm.is_new())
		{
			frm.add_custom_button(__("Copy Items"), function() {
				// frm.copy_doc((doc, old) => {
				// 		console.log(doc, old);
				// }, frm.doc.name  )
				let d = new frappe.ui.Dialog({
					title: 'Enter details',
					fields: [
						{
							label: 'From Price List',
							fieldname: 'price_list',
							fieldtype: 'Link',
							options: "Price List"
						},
					],
					primary_action_label: 'Copy',
					primary_action(values) {
						frappe.call({
							method: "erpnext.stock.doctype.price_list.price_list.copy_items",
							args: {
								price_list: values.price_list,
								new_price_list: frm.doc.name
							},
							callback: (res) => {
								console.log(res);
								
							}
						})
						$('button[data-label="Copy%20Items"]').prop('disabled', true)
						d.hide();
					}
				});
				
				d.show();
			});

			if(frm.doc.is_copying == 1){
				$('button[data-label="Copy%20Items"]').prop('disabled', true)
			}else{
				$('button[data-label="Copy%20Items"]').prop('disabled', false)
			}
		}
	}
});
