// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %};
frappe.provide("erpnext.accounts");


erpnext.accounts.SalesInvoiceController = erpnext.selling.SellingController.extend({
	setup: function (frm) {
		this.setup_posting_date_time_check();
		this._super(frm);

	},

	company: function () {
		erpnext.accounts.dimensions.update_dimension(this.frm, this.frm.doctype);
		let me = this;
		if (this.frm.doc.company) {
			frappe.call({
				method:
					"erpnext.accounts.party.get_party_account",
				args: {
					party_type: 'Customer',
					party: this.frm.doc.customer,
					company: this.frm.doc.company
				},
				callback: (response) => {
					if (response) me.frm.set_value("debit_to", response.message);
				},
			});
			//ibrahim
			if (this.frm.doc.insurance_party_type){
				if (this.frm.doc.insurance_party){
					frappe.call({
						method:
							"erpnext.accounts.party.get_party_account",
						args: {
							party_type: 'Customer',
							party: this.frm.doc.insurance_party,
							company: this.frm.doc.company
						},
						callback: (response) => {
							if (response) me.frm.set_value("insurancepayer_account", response.message);
						},
					});
				}
			}
		}
		// ibrahim
		frappe.db.get_single_value("Accounts Settings", "enable_discount_accounting").then(enable_discount => {
			if(enable_discount){
				frappe.db.get_value("Company", this.frm.doc.company, "default_discount_account").then(result => {
					if(result.message && result.message.default_discount_account){
						me.frm.set_value("additional_discount_account", result.message.default_discount_account)
					}else{
						me.frm.set_value("additional_discount_account", "")
					}
				})
			}else{
				me.frm.set_value("additional_discount_account", "")
			}
		})
	},

	onload: function () {
		var me = this;
		this._super();

		this.frm.ignore_doctypes_on_cancel_all = ['POS Invoice', 'Timesheet', 'POS Invoice Merge Log', 'POS Closing Entry'];
		if (!this.frm.doc.__islocal && !this.frm.doc.customer && this.frm.doc.debit_to) {
			// show debit_to in print format
			this.frm.set_df_property("debit_to", "print_hide", 0);
		}

		erpnext.queries.setup_queries(this.frm, "Warehouse", function () {
			return erpnext.queries.warehouse(me.frm.doc);
		});

		if (this.frm.doc.__islocal && this.frm.doc.is_pos) {
			//Load pos profile data on the invoice if the default value of Is POS is 1

			me.frm.script_manager.trigger("is_pos");
			me.frm.refresh_fields();
		}
		erpnext.queries.setup_warehouse_query(this.frm);
		erpnext.accounts.dimensions.setup_dimension_filters(this.frm, this.frm.doctype);


	},

	refresh: function (doc, dt, dn) {
		const me = this;
		this._super();
		if (cur_frm.msgbox && cur_frm.msgbox.$wrapper.is(":visible")) {
			// hide new msgbox
			cur_frm.msgbox.hide();
		}

		this.frm.toggle_reqd("due_date", !this.frm.doc.is_return);

		if (this.frm.doc.is_return) {
			this.frm.return_print_format = "Sales Invoice Return";
		}

		this.show_general_ledger();

		//ibrahim
		cur_frm.add_custom_button(__('Claim Print'), function () {
			print_claim_report(cur_frm);
		});


		if (doc.update_stock) this.show_stock_ledger();

		if (doc.docstatus == 1 && doc.outstanding_amount != 0
			&& !(cint(doc.is_return) && doc.return_against)) {
			cur_frm.add_custom_button(__('Payment'),
				this.make_payment_entry);
			cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if (doc.docstatus == 1 && !doc.is_return) {

			var is_delivered_by_supplier = false;

			is_delivered_by_supplier = cur_frm.doc.items.some(function (item) {
				return item.is_delivered_by_supplier ? true : false;
			})

			if (doc.outstanding_amount >= 0 || Math.abs(flt(doc.outstanding_amount)) < flt(doc.grand_total)) {
				cur_frm.add_custom_button(__('Return / Credit Note'),
					this.make_sales_return, __('Create'));
				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
			}

			if (cint(doc.update_stock) != 1) {
				// show Make Delivery Note button only if Sales Invoice is not created from Delivery Note
				var from_delivery_note = false;
				from_delivery_note = cur_frm.doc.items
					.some(function (item) {
						return item.delivery_note ? true : false;
					});

				if (!from_delivery_note && !is_delivered_by_supplier) {
					cur_frm.add_custom_button(__('Delivery'),
						cur_frm.cscript['Make Delivery Note'], __('Create'));
				}
			}

			if (doc.outstanding_amount > 0) {
				cur_frm.add_custom_button(__('Payment Request'), function () {
					me.make_payment_request();
				}, __('Create'));

				cur_frm.add_custom_button(__('Invoice Discounting'), function () {
					cur_frm.events.create_invoice_discounting(cur_frm);
				}, __('Create'));

				if (doc.due_date < frappe.datetime.get_today()) {
					cur_frm.add_custom_button(__('Dunning'), function () {
						cur_frm.events.create_dunning(cur_frm);
					}, __('Create'));
				}
			}

			if (doc.docstatus === 1) {
				cur_frm.add_custom_button(__('Maintenance Schedule'), function () {
					cur_frm.cscript.make_maintenance_schedule();
				}, __('Create'));
			}

			if (!doc.auto_repeat) {
				cur_frm.add_custom_button(__('Subscription'), function () {
					erpnext.utils.make_subscription(doc.doctype, doc.name)
				}, __('Create'))
			}
		}

		// Show buttons only when pos view is active
		if (cint(doc.docstatus == 0) && cur_frm.page.current_view_name !== "pos" && !doc.is_return) {
			this.frm.cscript.sales_order_btn();
			this.frm.cscript.delivery_note_btn();
			this.frm.cscript.quotation_btn();
		}

		this.set_default_print_format();
		if (doc.docstatus == 1 && !doc.inter_company_invoice_reference) {
			let internal = me.frm.doc.is_internal_customer;
			if (internal) {
				let button_label = (me.frm.doc.company === me.frm.doc.represents_company) ? "Internal Purchase Invoice" :
					"Inter Company Purchase Invoice";

				me.frm.add_custom_button(button_label, function () {
					me.make_inter_company_invoice();
				}, __('Create'));
			}
		}


	},

	make_maintenance_schedule: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_maintenance_schedule",
			frm: cur_frm
		})
	},

	on_submit: function (doc, dt, dn) {
		var me = this;

		if (frappe.get_route()[0] != 'Form') {
			return
		}

		$.each(doc["items"], function (i, row) {
			if (row.delivery_note) frappe.model.clear_doc("Delivery Note", row.delivery_note)
		})
	},

	set_default_print_format: function () {
		// set default print format to POS type or Credit Note
		if (cur_frm.doc.is_pos) {
			if (cur_frm.pos_print_format) {
				cur_frm.meta._default_print_format = cur_frm.meta.default_print_format;
				cur_frm.meta.default_print_format = cur_frm.pos_print_format;
			}
		} else if (cur_frm.doc.is_return && !cur_frm.meta.default_print_format) {
			if (cur_frm.return_print_format) {
				cur_frm.meta._default_print_format = cur_frm.meta.default_print_format;
				cur_frm.meta.default_print_format = cur_frm.return_print_format;
			}
		} else {
			if (cur_frm.meta._default_print_format) {
				cur_frm.meta.default_print_format = cur_frm.meta._default_print_format;
				cur_frm.meta._default_print_format = null;
			} else if (in_list([cur_frm.pos_print_format, cur_frm.return_print_format], cur_frm.meta.default_print_format)) {
				cur_frm.meta.default_print_format = null;
				cur_frm.meta._default_print_format = null;
			}
		}
	},

	sales_order_btn: function () {
		var me = this;
		this.$sales_order_btn = this.frm.add_custom_button(__('Sales Order'),
			function () {
				erpnext.utils.map_current_doc({
					method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
					source_doctype: "Sales Order",
					target: me.frm,
					setters: {
						customer: me.frm.doc.customer || undefined,
					},
					get_query_filters: {
						docstatus: 1,
						status: ["not in", ["Closed", "On Hold"]],
						per_billed: ["<", 99.99],
						company: me.frm.doc.company
					}
				})
			}, __("Get Items From"));
	},

	quotation_btn: function () {
		var me = this;
		this.$quotation_btn = this.frm.add_custom_button(__('Quotation'),
			function () {
				erpnext.utils.map_current_doc({
					method: "erpnext.selling.doctype.quotation.quotation.make_sales_invoice",
					source_doctype: "Quotation",
					target: me.frm,
					setters: [{
						fieldtype: 'Link',
						label: __('Customer'),
						options: 'Customer',
						fieldname: 'party_name',
						default: me.frm.doc.customer,
					}],
					get_query_filters: {
						docstatus: 1,
						status: ["!=", "Lost"],
						company: me.frm.doc.company
					}
				})
			}, __("Get Items From"));
	},

	delivery_note_btn: function () {
		var me = this;
		this.$delivery_note_btn = this.frm.add_custom_button(__('Delivery Note'),
			function () {
				erpnext.utils.map_current_doc({
					method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
					source_doctype: "Delivery Note",
					target: me.frm,
					date_field: "posting_date",
					setters: {
						customer: me.frm.doc.customer || undefined
					},
					get_query: function () {
						var filters = {
							docstatus: 1,
							company: me.frm.doc.company,
							is_return: 0
						};
						if (me.frm.doc.customer) filters["customer"] = me.frm.doc.customer;
						return {
							query: "erpnext.controllers.queries.get_delivery_notes_to_be_billed",
							filters: filters
						};
					}
				});
			}, __("Get Items From"));
	},

	tc_name: function () {
		this.get_terms();
	},
	customer: function () {
		if (this.frm.doc.is_pos) {
			var pos_profile = this.frm.doc.pos_profile;
		}
		var me = this;
		if (this.frm.updating_party_details) return;
		erpnext.utils.get_party_details(this.frm,
			"erpnext.accounts.party.get_party_details", {
			posting_date: this.frm.doc.posting_date,
			party: this.frm.doc.customer,
			party_type: "Customer",
			account: this.frm.doc.debit_to,
			price_list: this.frm.doc.selling_price_list,
			pos_profile: pos_profile
		}, function () {
			me.apply_pricing_rule();
		});

		if (this.frm.doc.customer) {
			frappe.call({
				"method": "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_loyalty_programs",
				"args": {
					"customer": this.frm.doc.customer
				},
				callback: function (r) {
					if (r.message && r.message.length > 1) {
						select_loyalty_program(me.frm, r.message);
					}
				}
			});
		}
	},

	make_inter_company_invoice: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_inter_company_purchase_invoice",
			frm: me.frm
		});
	},

	debit_to: function () {
		var me = this;
		if (this.frm.doc.debit_to) {
			me.frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Account",
					fieldname: "account_currency",
					filters: { name: me.frm.doc.debit_to },
				},
				callback: function (r, rt) {
					if (r.message) {
						me.frm.set_value("party_account_currency", r.message.account_currency);
						me.set_dynamic_labels();
					}
				}
			});
		}
	},

	// ibrahim
	insurancepayer_account: function () {
		var me = this;
		if (this.frm.doc.insurancepayer_account) {
			me.frm.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Account",
					fieldname: "account_currency",
					filters: { name: me.frm.doc.insurancepayer_account },
				},
				callback: function (r, rt) {
					if (r.message) {
						me.frm.set_value("payer_account_currency", r.message.account_currency);
						me.set_dynamic_labels();
					}
				}
			});
		}
	},

	allocated_amount: function () {
		this.calculate_total_advance();
		this.frm.refresh_fields();
	},

	write_off_outstanding_amount_automatically() {
		if (cint(this.frm.doc.write_off_outstanding_amount_automatically)) {
			frappe.model.round_floats_in(this.frm.doc, ["grand_total", "paid_amount"]);
			// this will make outstanding amount 0
			this.frm.set_value("write_off_amount",
				flt(this.frm.doc.grand_total - this.frm.doc.paid_amount - this.frm.doc.total_advance, precision("write_off_amount"))
			);
		}

		this.calculate_outstanding_amount(false);
		this.frm.refresh_fields();
	},

	write_off_amount: function () {
		this.set_in_company_currency(this.frm.doc, ["write_off_amount"]);
		this.write_off_outstanding_amount_automatically();
	},

	items_add: function (doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["income_account", "discount_account", "cost_center"]);
	},

	set_dynamic_labels: function () {
		this._super();
		this.frm.events.hide_fields(this.frm)
	},

	items_on_form_rendered: function () {
		erpnext.setup_serial_or_batch_no();
	},

	packed_items_on_form_rendered: function (doc, grid_row) {
		erpnext.setup_serial_or_batch_no();
	},

	make_sales_return: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_sales_return",
			frm: cur_frm
		})
	},

	asset: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.asset) {
			frappe.call({
				method: erpnext.assets.doctype.asset.depreciation.get_disposal_account_and_cost_center,
				args: {
					"company": frm.doc.company
				},
				callback: function (r, rt) {
					frappe.model.set_value(cdt, cdn, "income_account", r.message[0]);
					frappe.model.set_value(cdt, cdn, "cost_center", r.message[1]);
				}
			})
		}
	},

	is_pos: function (frm) {
		this.set_pos_data();
	},

	pos_profile: function () {
		this.frm.doc.taxes = []
		this.set_pos_data();
	},

	set_pos_data: function () {
		if (this.frm.doc.is_pos) {
			this.frm.set_value("allocate_advances_automatically", 0);
			if (!this.frm.doc.company) {
				this.frm.set_value("is_pos", 0);
				frappe.msgprint(__("Please specify Company to proceed"));
			} else {
				var me = this;
				return this.frm.call({
					doc: me.frm.doc,
					method: "set_missing_values",
					callback: function (r) {
						if (!r.exc) {
							if (r.message && r.message.print_format) {
								me.frm.pos_print_format = r.message.print_format;
							}
							me.frm.trigger("update_stock");
							if (me.frm.doc.taxes_and_charges) {
								me.frm.script_manager.trigger("taxes_and_charges");
							}

							frappe.model.set_default_values(me.frm.doc);
							me.set_dynamic_labels();
							me.calculate_taxes_and_totals();
						}
					}
				});
			}
		}
		else this.frm.trigger("refresh");
	},

	amount: function () {
		this.write_off_outstanding_amount_automatically()
	},

	change_amount: function () {
		if (this.frm.doc.paid_amount > this.frm.doc.grand_total) {
			this.calculate_write_off_amount();
		} else {
			this.frm.set_value("change_amount", 0.0);
			this.frm.set_value("base_change_amount", 0.0);
		}

		this.frm.refresh_fields();
	},

	loyalty_amount: function () {
		this.calculate_outstanding_amount();
		this.frm.refresh_field("outstanding_amount");
		this.frm.refresh_field("paid_amount");
		this.frm.refresh_field("base_paid_amount");
	},

	currency() {
		var me = this;
		this._super();
		if (this.frm.doc.timesheets) {
			this.frm.doc.timesheets.forEach((d) => {
				let row = frappe.get_doc(d.doctype, d.name)
				set_timesheet_detail_rate(row.doctype, row.name, me.frm.doc.currency, row.timesheet_detail)
			});
			frm.trigger("calculate_timesheet_totals");
		}
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.accounts.SalesInvoiceController({ frm: cur_frm }));

cur_frm.cscript['Make Delivery Note'] = function () {
	frappe.model.open_mapped_doc({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.make_delivery_note",
		frm: cur_frm
	})
}

cur_frm.fields_dict.cash_bank_account.get_query = function (doc) {
	return {
		filters: [
			["Account", "account_type", "in", ["Cash", "Bank"]],
			["Account", "root_type", "=", "Asset"],
			["Account", "is_group", "=", 0],
			["Account", "company", "=", doc.company]
		]
	}
}

cur_frm.fields_dict.write_off_account.get_query = function (doc) {
	return {
		filters: {
			'report_type': 'Profit and Loss',
			'is_group': 0,
			'company': doc.company
		}
	}
}

// Write off cost center
//-----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function (doc) {
	return {
		filters: {
			'is_group': 0,
			'company': doc.company
		}
	}
}

// project name
//--------------------------
cur_frm.fields_dict['project'].get_query = function (doc, cdt, cdn) {
	return {
		query: "erpnext.controllers.queries.get_project_name",
		filters: { 'customer': doc.customer }
	}
}

// Income Account in Details Table
// --------------------------------
cur_frm.set_query("income_account", "items", function (doc) {
	return {
		query: "erpnext.controllers.queries.get_income_account",
		filters: { 'company': doc.company }
	}
});

// Cost Center in Details Table
// -----------------------------
cur_frm.fields_dict["items"].grid.get_field("cost_center").get_query = function (doc) {
	return {
		filters: {
			'company': doc.company,
			"is_group": 0
		}
	}
}

cur_frm.cscript.income_account = function (doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "income_account");
}

cur_frm.cscript.expense_account = function (doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "expense_account");
}

cur_frm.cscript.discount_account = function (doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "discount_account");
}

cur_frm.cscript.cost_center = function (doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_rows(doc, cdt, cdn, "items", "cost_center");
}

cur_frm.set_query("debit_to", function (doc) {
	return {
		filters: {
			'account_type': 'Receivable',
			'is_group': 0,
			'company': doc.company
		}
	}
});

//ibrahim
cur_frm.set_query("insurancepayer_account", function (doc) {
	return {
		filters: {
			'account_type': 'Receivable',
			'is_group': 0,
			'company': doc.company
		}
	}
});

cur_frm.set_query("asset", "items", function (doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return {
		filters: [
			["Asset", "item_code", "=", d.item_code],
			["Asset", "docstatus", "=", 1],
			["Asset", "status", "in", ["Submitted", "Partially Depreciated", "Fully Depreciated"]],
			["Asset", "company", "=", doc.company]
		]
	}
});

frappe.ui.form.on('Sales Invoice', {
	setup: function (frm) {
		frm.add_fetch('customer', 'tax_id', 'tax_id');
		frm.add_fetch('payment_term', 'invoice_portion', 'invoice_portion');
		frm.add_fetch('payment_term', 'description', 'description');

		frm.set_df_property('packed_items', 'cannot_add_rows', true);
		frm.set_df_property('packed_items', 'cannot_delete_rows', true);

		frm.set_query("account_for_change_amount", function () {
			return {
				filters: {
					account_type: ['in', ["Cash", "Bank"]],
					company: frm.doc.company,
					is_group: 0
				}
			};
		});

		frm.set_query("unrealized_profit_loss_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
					root_type: "Liability",
				}
			};
		});

		frm.set_query("adjustment_against", function () {
			return {
				filters: {
					company: frm.doc.company,
					customer: frm.doc.customer,
					docstatus: 1
				}
			};
		});

		frm.set_query("additional_discount_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
					report_type: "Profit and Loss",
				}
			};
		});

		frm.custom_make_buttons = {
			'Delivery Note': 'Delivery',
			'Sales Invoice': 'Return / Credit Note',
			'Payment Request': 'Payment Request',
			'Payment Entry': 'Payment'
		},
			frm.fields_dict["timesheets"].grid.get_field("time_sheet").get_query = function (doc, cdt, cdn) {
				return {
					query: "erpnext.projects.doctype.timesheet.timesheet.get_timesheet",
					filters: { 'project': doc.project }
				}
			}

		// expense account
		frm.fields_dict['items'].grid.get_field('expense_account').get_query = function (doc) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						'report_type': 'Profit and Loss',
						'company': doc.company,
						"is_group": 0
					}
				}
			}
		}

		// discount account
		frm.fields_dict['items'].grid.get_field('discount_account').get_query = function (doc) {
			return {
				filters: {
					'report_type': 'Profit and Loss',
					'company': doc.company,
					"is_group": 0
				}
			}
		}

		frm.fields_dict['items'].grid.get_field('deferred_revenue_account').get_query = function (doc) {
			return {
				filters: {
					'root_type': 'Liability',
					'company': doc.company,
					"is_group": 0
				}
			}
		}

		frm.set_query('company_address', function (doc) {
			if (!doc.company) {
				frappe.throw(__('Please set Company'));
			}

			return {
				query: 'frappe.contacts.doctype.address.address.address_query',
				filters: {
					link_doctype: 'Company',
					link_name: doc.company
				}
			};
		});

		frm.set_query('pos_profile', function (doc) {
			if (!doc.company) {
				frappe.throw(_('Please set Company'));
			}

			return {
				query: 'erpnext.accounts.doctype.pos_profile.pos_profile.pos_profile_query',
				filters: {
					company: doc.company
				}
			};
		});

		// set get_query for loyalty redemption account
		frm.fields_dict["loyalty_redemption_account"].get_query = function () {
			return {
				filters: {
					"company": frm.doc.company,
					"is_group": 0
				}
			}
		};

		// set get_query for loyalty redemption cost center
		frm.fields_dict["loyalty_redemption_cost_center"].get_query = function () {
			return {
				filters: {
					"company": frm.doc.company,
					"is_group": 0
				}
			}
		};
	},
	// When multiple companies are set up. in case company name is changed set default company address
	company: function (frm) {
		if (frm.doc.company) {
			frappe.call({
				method: "erpnext.setup.doctype.company.company.get_default_company_address",
				args: { name: frm.doc.company, existing_address: frm.doc.company_address || "" },
				debounce: 2000,
				callback: function (r) {
					if (r.message) {
						frm.set_value("company_address", r.message)
					}
					else {
						frm.set_value("company_address", "")
					}
				}
			})
		}
	},

	onload: function (frm) {
		frm.redemption_conversion_factor = null;
	},

	update_stock: function (frm, dt, dn) {
		frm.events.hide_fields(frm);
		frm.fields_dict.items.grid.toggle_reqd("item_code", frm.doc.update_stock);
		frm.trigger('reset_posting_time');
	},

	redeem_loyalty_points: function (frm) {
		frm.events.get_loyalty_details(frm);
	},

	loyalty_points: function (frm) {
		if (frm.redemption_conversion_factor) {
			frm.events.set_loyalty_points(frm);
		} else {
			frappe.call({
				method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_redeemption_factor",
				args: {
					"loyalty_program": frm.doc.loyalty_program
				},
				callback: function (r) {
					if (r) {
						frm.redemption_conversion_factor = r.message;
						frm.events.set_loyalty_points(frm);
					}
				}
			});
		}
	},

	hide_fields: function (frm) {
		let doc = frm.doc;
		var parent_fields = ['project', 'due_date', 'is_opening', 'source', 'total_advance', 'get_advances',
			'advances', 'from_date', 'to_date'];

		if (cint(doc.is_pos) == 1) {
			hide_field(parent_fields);
		} else {
			for (var i in parent_fields) {
				var docfield = frappe.meta.docfield_map[doc.doctype][parent_fields[i]];
				if (!docfield.hidden) unhide_field(parent_fields[i]);
			}
		}

		// India related fields
		if (frappe.boot.sysdefaults.country == 'India') unhide_field(['c_form_applicable', 'c_form_no']);
		else hide_field(['c_form_applicable', 'c_form_no']);

		frm.refresh_fields();
	},
	apply_item_discount: function(frm){
		var selected_items = frm.get_selected()["items"]
		if (selected_items){
			var discount = frm.doc.additional_item_discount || 0
			selected_items.forEach(item => {
				frappe.model.set_value("Sales Invoice Item", item, "discount_percentage", discount)
			})
		}
	},

	get_loyalty_details: function (frm) {
		if (frm.doc.customer && frm.doc.redeem_loyalty_points) {
			frappe.call({
				method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_loyalty_program_details",
				args: {
					"customer": frm.doc.customer,
					"loyalty_program": frm.doc.loyalty_program,
					"expiry_date": frm.doc.posting_date,
					"company": frm.doc.company
				},
				callback: function (r) {
					if (r) {
						frm.set_value("loyalty_redemption_account", r.message.expense_account);
						frm.set_value("loyalty_redemption_cost_center", r.message.cost_center);
						frm.redemption_conversion_factor = r.message.conversion_factor;
					}
				}
			});
		}
	},

	set_loyalty_points: function (frm) {
		if (frm.redemption_conversion_factor) {
			let loyalty_amount = flt(frm.redemption_conversion_factor * flt(frm.doc.loyalty_points), precision("loyalty_amount"));
			var remaining_amount = flt(frm.doc.grand_total) - flt(frm.doc.total_advance) - flt(frm.doc.write_off_amount);
			if (frm.doc.grand_total && (remaining_amount < loyalty_amount)) {
				let redeemable_points = parseInt(remaining_amount / frm.redemption_conversion_factor);
				frappe.throw(__("You can only redeem max {0} points in this order.", [redeemable_points]));
			}
			frm.set_value("loyalty_amount", loyalty_amount);
		}
	},
	coverage_percentage: function(frm){
		if(frm.doc.coverage_percentage || frm.doc.coverage_percentage == 0){
			frm.set_value("charged_percentage", 100 - frm.doc.coverage_percentage)
		}
		
	},
	charged_percentage: function(frm){
		if(frm.doc.charged_percentage || frm.doc.charged_percentage == 0){
			frm.set_value("coverage_percentage", 100 - frm.doc.charged_percentage)
		}
	},

	//ibrahim
	discount_amount: function(frm) {
		if (frm.doc.discount_amount >= 0){
			$.each(frm.doc["items"] || [], function(i, item) {
				if ((!item.qty) && frm.doc.is_return) {
					item.contract_discount = flt(item.rate * item.qty  * (frm.doc.additional_discount_percentage/100) * -1, precision("contract_discount", item));
					if (item.discount_amount == 0){
						item.contract_discount = 0
						item.base_contract_discount = 0
					}
				
				} else {
					
					item.contract_discount = flt(item.rate * item.qty * (frm.doc.additional_discount_percentage/100), precision("contract_discount", item));
					if (item.discount_amount == 0){
						item.contract_discount = 0
						item.base_contract_discount = 0
					}
			}
				//frappe.model.set_value(item.doctype, item.name, "margin_type", 'Percentage');
				});
		}

	},

	insurance_party_type: function (frm) {


		if (frm.doc.insurance_party_type == "Insurance Company" ) {
			frappe.db.get_single_value("Selling Settings", "default_insurance_price_list").then(default_pl => {
				if(default_pl){
					frm.set_value("selling_price_list", default_pl)
				}else{
					frm.set_value("selling_price_list", "")
				}
			})
		}else if (frm.doc.insurance_party_type == "Payer" ) {
			frappe.db.get_single_value("Selling Settings", "selling_price_list").then(default_pl => {
				if(default_pl){
					frm.set_value("selling_price_list", default_pl)
				}else{
					frm.set_value("selling_price_list", "")
				}
			})
		}else{
			frm.set_value("additional_discount_percentage", 0)
			frm.set_value("discount_amount", 0)
			frm.set_value("base_discount_amount", 0)
			frm.set_value("insurance_party", "")
			frm.set_value("insurance_party_child", "")
			frm.set_value("coverage_percentage", 0)
			frm.set_value("charged_percentage", 0)
			frm.set_value("coverage_type", "")

			frappe.db.get_single_value("Selling Settings", "selling_price_list").then(default_pl => {
				if(default_pl){
					frm.set_value("selling_price_list", default_pl)
				}else{
					frm.set_value("selling_price_list", "")
				}
			})
		}
	},
	insurance_party: function (frm) {
		//ibrahim
		if (frm.doc.insurance_party){
			frappe.call({
				method:	"erpnext.accounts.party.get_party_account",
				args: {
					party_type: 'Customer',
					party: frm.doc.insurance_party,
					company: frm.doc.company
				},
				callback: function (res) {
					if (res.message) frm.set_value("insurancepayer_account", res.message);
				},
			});
		}

		if (frm.doc.insurance_party && frm.doc.insurance_party != "") {
			frappe.call({
				method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.is_customer_parent",
				args: {
					customer: frm.doc.insurance_party
				},
				callback: function (res) {
					if (res.message) {
						frm.set_query("insurance_party_child", function (doc) {
							return {
								filters: {
									'parent_customer': frm.doc.insurance_party,
								}
							}
						});

						frm.toggle_display("insurance_party_child", true)

					} else {
						frm.set_value("insurance_party_child", "")
						frm.toggle_display("insurance_party_child", false)
					}
				}
			})
			
			if (frm.doc.insurance_party_child) {
				frappe.db.get_value("Customer", frm.doc.insurance_party_child, "default_price_list").then(result => {
					if(result.message && result.message.default_price_list){
						frm.set_value("selling_price_list", result.message.default_price_list)
					}else{
						if (frm.doc.insurance_party_type == "Insurance Company" ) {
							frappe.db.get_single_value("Selling Settings", "default_insurance_price_list").then(default_pl => {
								if(default_pl){
									frm.set_value("selling_price_list", default_pl)
								}else{
									frm.set_value("selling_price_list", "")
								}
							})
						}else if (frm.doc.insurance_party_type == "Payer" ) {
							frappe.db.get_single_value("Selling Settings", "selling_price_list").then(default_pl => {
								if(default_pl){
									frm.set_value("selling_price_list", default_pl)
								}else{
									frm.set_value("selling_price_list", "")
								}
							})
						}else{
							frappe.db.get_single_value("Selling Settings", "selling_price_list").then(default_pl => {
								if(default_pl){
									frm.set_value("selling_price_list", default_pl)
								}else{
									frm.set_value("selling_price_list", "")
								}
							})
						}
										
					}
				})
	
			}else {
				frappe.db.get_value("Customer", frm.doc.insurance_party, "default_price_list").then(result => {
					if(result.message && result.message.default_price_list){
						frm.set_value("selling_price_list", result.message.default_price_list)
					}else{
						frappe.db.get_single_value("Selling Settings", "default_insurance_price_list").then(default_pl => {
							if(default_pl){
								frm.set_value("selling_price_list", default_pl)
							}else{
								if (frm.doc.insurance_party_type == "Insurance Company" ) {
									frappe.db.get_single_value("Selling Settings", "default_insurance_price_list").then(default_pl => {
										if(default_pl){
											frm.set_value("selling_price_list", default_pl)
										}else{
											frm.set_value("selling_price_list", "")
										}
									})
								}else if (frm.doc.insurance_party_type == "Payer" ) {
									frappe.db.get_single_value("Selling Settings", "selling_price_list").then(default_pl => {
										if(default_pl){
											frm.set_value("selling_price_list", default_pl)
										}else{
											frm.set_value("selling_price_list", "")
										}
									})
								}else{
									frappe.db.get_single_value("Selling Settings", "selling_price_list").then(default_pl => {
										if(default_pl){
											frm.set_value("selling_price_list", default_pl)
										}else{
											frm.set_value("selling_price_list", "")
										}
									})
								}
							}
						})
						
					}
				})
	
			}
		}

		if(frm.doc.coverage_type !='Cash'){
			$.each(frm.doc["items"] || [], function(i, item) {
				frappe.model.set_value(item.doctype, item.name, "margin_type", 'Percentage');
				frappe.model.set_value(item.doctype, item.name, "discount_percentage",frm.doc.coverage_percentage);
				});
		}else{
			$.each(frm.doc["items"] || [], function(i, item) {
				frappe.model.set_value(item.doctype, item.name, "margin_type", 'Percentage');
				frappe.model.set_value(item.doctype, item.name, "discount_percentage", 0);
				});
		}

		frappe.db.get_value('Customer', frm.doc.insurance_party, ["additional_discount_percentage"]).then(result => {
			if (result.message){
				if(result.message.additional_discount_percentage){
					frm.set_value("additional_discount_percentage", result.message.additional_discount_percentage)
				}else{
					frm.set_value("additional_discount_percentage", 0)
				}
			}
		})
	},
	insurance_party_child: function(frm){
		if (frm.doc.insurance_party_child && frm.doc.insurance_party_child != "") {
			frappe.db.get_value("Customer", frm.doc.insurance_party_child, "default_price_list").then(result => {
				if(result.message && result.message.default_price_list){
					frm.set_value("selling_price_list", result.message.default_price_list)
				}else{
					frappe.db.get_single_value("Selling Settings", "default_insurance_price_list").then(default_pl => {
						if(default_pl){
							frm.set_value("selling_price_list", default_pl)
						}else{
							frm.set_value("selling_price_list", "")
						}
					})
				}
			})
		}
	},

	apply_coverage_on_item:function(frm) {
		//ibrahim
		
	},
	// Healthcare
	patient: function (frm) {
		if (frappe.boot.active_domains.includes("Healthcare")) {
			if (frm.doc.patient) {
				frappe.call({
					method: "frappe.client.get_value",
					args: {
						doctype: "Patient",
						filters: {
							"name": frm.doc.patient
						},
						fieldname: "customer"
					},
					callback: function (r) {
						if (r && r.message.customer) {
							frm.set_value("customer", r.message.customer);
						}
					}
				});
			}
		}
	},

	project: function (frm) {
		if (frm.doc.project) {
			frm.events.add_timesheet_data(frm, {
				project: frm.doc.project
			});
		}
	},

	async add_timesheet_data(frm, kwargs) {
		if (kwargs === "Sales Invoice") {
			// called via frm.trigger()
			kwargs = Object();
		}

		if (!kwargs.hasOwnProperty("project") && frm.doc.project) {
			kwargs.project = frm.doc.project;
		}

		const timesheets = await frm.events.get_timesheet_data(frm, kwargs);
		return frm.events.set_timesheet_data(frm, timesheets);
	},

	async get_timesheet_data(frm, kwargs) {
		return frappe.call({
			method: "erpnext.projects.doctype.timesheet.timesheet.get_projectwise_timesheet_data",
			args: kwargs
		}).then(r => {
			if (!r.exc && r.message.length > 0) {
				return r.message
			} else {
				return []
			}
		});
	},

	set_timesheet_data: function (frm, timesheets) {
		frm.clear_table("timesheets")
		timesheets.forEach(timesheet => {
			if (frm.doc.currency != timesheet.currency) {
				frappe.call({
					method: "erpnext.setup.utils.get_exchange_rate",
					args: {
						from_currency: timesheet.currency,
						to_currency: frm.doc.currency
					},
					callback: function (r) {
						if (r.message) {
							exchange_rate = r.message;
							frm.events.append_time_log(frm, timesheet, exchange_rate);
						}
					}
				});
			} else {
				frm.events.append_time_log(frm, timesheet, 1.0);
			}
		});
	},

	append_time_log: function (frm, time_log, exchange_rate) {
		const row = frm.add_child("timesheets");
		row.activity_type = time_log.activity_type;
		row.description = time_log.description;
		row.time_sheet = time_log.time_sheet;
		row.from_time = time_log.from_time;
		row.to_time = time_log.to_time;
		row.billing_hours = time_log.billing_hours;
		row.billing_amount = flt(time_log.billing_amount) * flt(exchange_rate);
		row.timesheet_detail = time_log.name;
		row.project_name = time_log.project_name;

		frm.refresh_field("timesheets");
		frm.trigger("calculate_timesheet_totals");
	},

	calculate_timesheet_totals: function (frm) {
		frm.set_value("total_billing_amount",
			frm.doc.timesheets.reduce((a, b) => a + (b["billing_amount"] || 0.0), 0.0));
		frm.set_value("total_billing_hours",
			frm.doc.timesheets.reduce((a, b) => a + (b["billing_hours"] || 0.0), 0.0));
	},

	refresh: function (frm) {
		frm.get_field("items").grid.set_multiple_add("item_code");

		if (frm.doc.docstatus === 0 && !frm.doc.is_return) {
			frm.add_custom_button(__("Fetch Timesheet"), function () {
				let d = new frappe.ui.Dialog({
					title: __("Fetch Timesheet"),
					fields: [
						{
							"label": __("From"),
							"fieldname": "from_time",
							"fieldtype": "Date",
							"reqd": 1,
						},
						{
							fieldtype: "Column Break",
							fieldname: "col_break_1",
						},
						{
							"label": __("To"),
							"fieldname": "to_time",
							"fieldtype": "Date",
							"reqd": 1,
						},
						{
							"label": __("Project"),
							"fieldname": "project",
							"fieldtype": "Link",
							"options": "Project",
							"default": frm.doc.project
						},
					],
					primary_action: function () {
						const data = d.get_values();
						frm.events.add_timesheet_data(frm, {
							from_time: data.from_time,
							to_time: data.to_time,
							project: data.project
						});
						d.hide();
					},
					primary_action_label: __("Get Timesheets")
				});
				d.show();
			});
		}

		if (frm.doc.is_debit_note) {
			frm.set_df_property('return_against', 'label', 'Adjustment Against');
		}

		if (frappe.boot.active_domains.includes("Healthcare")) {
			frm.set_df_property("patient", "hidden", 0);
			frm.set_df_property("patient_name", "hidden", 0);
			frm.set_df_property("ref_practitioner", "hidden", 0);
			if (cint(frm.doc.docstatus == 0) && cur_frm.page.current_view_name !== "pos" && !frm.doc.is_return) {
				frm.add_custom_button(__('Healthcare Services'), function () {
					get_healthcare_services_to_invoice(frm);
				}, "Get Items From");
				frm.add_custom_button(__('Prescriptions'), function () {
					get_drugs_to_invoice(frm);
				}, "Get Items From");
			}
		}
		else {
			frm.set_df_property("patient", "hidden", 1);
			frm.set_df_property("patient_name", "hidden", 1);
			frm.set_df_property("ref_practitioner", "hidden", 1);
		}



		frappe.call({
			method: "erpnext.healthcare.utils.is_embassy",
			callback: (res) => {
				if (res.message) {

					if (!frm.is_new() && frm.doc.patient && frm.doc.patient != "") {
						frappe.db.get_value("Country", frm.doc.destination_country, "has_cover").then(res => {
							if (res.message.has_cover){
								frm.add_custom_button(__('Create Cover'), function(){
									frappe.db.get_value("Embassy Report", {sales_invoice: frm.doc.name}, "name").then(res => {
										if (res.message.name){
											frappe.set_route('Form', 'Embassy Report', res.message.name)
										}else{
											frappe.new_doc("Embassy Report", {
											
												sales_invoice: frm.doc.name})
										}
									})
								})
							}
						})
						
						var patient_name = frm.doc.patient;
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
									const uploadFP = (frm, image, values) => {
										frappe.show_progress('Capturing..', 50, 100, 'Please wait');
										let xhr = new XMLHttpRequest();

										xhr.open('POST', '/api/method/erpnext.healthcare.doctype.patient.patient.upload_fingerprint', true);
										xhr.setRequestHeader('Accept', 'application/json');

										xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);
										let form_data = new FormData();
										if (image) {
											form_data.append('file', image, patient_name + "_" + (values.finger_name || "Unknown finger"));
										}
										form_data.append('docname', patient_name);
										form_data.append('finger_name', values.finger_name || "Unknown finger");
										form_data.append('filename', patient_name + "_" + (values.finger_name || "Unknown finger"));

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

									const SuccessFunc = (frm, values, result) => {
										if (result.ErrorCode == 0) {
											if (result != null && result.BMPBase64.length > 0) {
												
												var d = new frappe.ui.Dialog({
													'fields': [
														{'fieldname': 'ht', 'fieldtype': 'HTML'},
												
													],
													primary_action: function(){
														d.hide();
														uploadFP(frm, b64toBlob(result.BMPBase64, "image/bmp"), values)
														//show_alert(d.get_values());
													}
												});
												d.fields_dict.ht.$wrapper.html(`<img src="data:image/bmp;base64,${result.BMPBase64}"/>`);
												d.show();
											} else {
												frappe.throw("Fingerprint Capture Fail");
											}
										}
										else {
											frappe.throw("Fingerprint Capture Error Code: " + result.ErrorCode)
										}
									}

									const ErrorFunc = (status) => {
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
										if (!uri) {
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
									var res = await frappe.call({ "method": "erpnext.healthcare.doctype.patient.patient.get_fingerprints", args: { "patient": patient_name } })
									var fingerprints = res.message
									for (var row in fingerprints) {
										if (fingerprints[row].finger === values.finger_name) {
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
									if (!found) {
										CallSGIFPGetData(frm, values, SuccessFunc, ErrorFunc);
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
					}
					let embassy_fields = ["passport_no", "passport_issue_date", "passport_expiry_date", "destination_country", "social_status", "passport_place"];
					frm.toggle_display(embassy_fields, true);
					frm.toggle_reqd(embassy_fields, true)
					// for (var field in embassy_fields ){
					// 	frm.set_df_property(field, "reqd", true);
					// }
					// frm.set_df_property("ref_practitioner", "reqd", false);
					//frm.toggle_reqd("ref_practitioner", false)
				}
			}

		})
	},

	create_invoice_discounting: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.create_invoice_discounting",
			frm: frm
		});
	},
	get_items_from_party: async function (frm) {
		const include_items = (items) => {
			items = items.map(item => item.item_code);
			var existing_items = [];
			for (var item of frm.doc.items) {
				if (items.includes(item.item_code)) {
					existing_items.push(item.item_code)
					frappe.msgprint(__("Item exists: ") + item.item_code);
				}
			}
			var last_row = frm.doc.items[frm.doc.items.length - 1];
			if (last_row.item_code == null || last_row.item_code == "") {
				frm.doc.items.splice(last_row, 1)

			}
			items = items.filter(item => !existing_items.includes(item))
			for (var item of items) {

				var row = cur_frm.add_child("items");
				frappe.model.set_value(row.doctype, row.name, "item_code", item);
				//row.item_code = item.item_code;
			}

			frm.refresh_fields("items");
		}

		if (frm.doc.selling_price_list == "" || frm.doc.selling_price_list == 'Standard Selling') {
			frappe.msgprint(__("Please select selling price list"));
		} else {
			var items = await frappe.db.get_list("Item Price", { filters: { "price_list": frm.doc.selling_price_list }, fields: ["item_code"] , limit: 'NULL'});
			if (items.length > 100){
						frappe.confirm(__(`There are ${items.length} items in this price list. Are you sure you want to proceed?`),
			() => {
				include_items(items);
			}, () => {
				// action to perform if No is selected
			})
			}else{
				include_items(items)
			}
	
			
		}
	},
	create_dunning: function (frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.create_dunning",
			frm: frm
		});
	}
});


frappe.ui.form.on("Sales Invoice Timesheet", {
	timesheets_remove(frm) {
		frm.trigger("calculate_timesheet_totals");
	}
});


var set_timesheet_detail_rate = function (cdt, cdn, currency, timelog) {
	frappe.call({
		method: "erpnext.projects.doctype.timesheet.timesheet.get_timesheet_detail_rate",
		args: {
			timelog: timelog,
			currency: currency
		},
		callback: function (r) {
			if (!r.exc && r.message) {
				frappe.model.set_value(cdt, cdn, 'billing_amount', r.message);
			}
		}
	});
}

var select_loyalty_program = function (frm, loyalty_programs) {
	var dialog = new frappe.ui.Dialog({
		title: __("Select Loyalty Program"),
		fields: [
			{
				"label": __("Loyalty Program"),
				"fieldname": "loyalty_program",
				"fieldtype": "Select",
				"options": loyalty_programs,
				"default": loyalty_programs[0]
			}
		]
	});

	dialog.set_primary_action(__("Set"), function () {
		dialog.hide();
		return frappe.call({
			method: "frappe.client.set_value",
			args: {
				doctype: "Customer",
				name: frm.doc.customer,
				fieldname: "loyalty_program",
				value: dialog.get_value("loyalty_program"),
			},
			callback: function (r) { }
		});
	});

	dialog.show();
}

// Healthcare
var get_healthcare_services_to_invoice = function (frm) {
	var me = this;
	let selected_patient = '';
	var dialog = new frappe.ui.Dialog({
		title: __("Get Items from Healthcare Services"),
		fields: [
			{
				fieldtype: 'Link',
				options: 'Patient',
				label: 'Patient',
				fieldname: "patient",
				reqd: true
			},
			{ fieldtype: 'Section Break' },
			{ fieldtype: 'HTML', fieldname: 'results_area' }
		]
	});
	var $wrapper;
	var $results;
	var $placeholder;
	dialog.set_values({
		'patient': frm.doc.patient
	});
	dialog.fields_dict["patient"].df.onchange = () => {
		var patient = dialog.fields_dict.patient.input.value;
		if (patient && patient != selected_patient) {
			selected_patient = patient;
			var method = "erpnext.healthcare.utils.get_healthcare_services_to_invoice";
			var args = { patient: patient, company: frm.doc.company };
			var columns = (["service", "reference_name", "reference_type"]);
			get_healthcare_items(frm, true, $results, $placeholder, method, args, columns);
		}
		else if (!patient) {
			selected_patient = '';
			$results.empty();
			$results.append($placeholder);
		}
	}
	$wrapper = dialog.fields_dict.results_area.$wrapper.append(`<div class="results"
		style="border: 1px solid #d1d8dd; border-radius: 3px; height: 300px; overflow: auto;"></div>`);
	$results = $wrapper.find('.results');
	$placeholder = $(`<div class="multiselect-empty-state">
				<span class="text-center" style="margin-top: -40px;">
					<i class="fa fa-2x fa-heartbeat text-extra-muted"></i>
					<p class="text-extra-muted">No billable Healthcare Services found</p>
				</span>
			</div>`);
	$results.on('click', '.list-item--head :checkbox', (e) => {
		$results.find('.list-item-container .list-row-check')
			.prop("checked", ($(e.target).is(':checked')));
	});
	set_primary_action(frm, dialog, $results, true);
	dialog.show();
};

var get_healthcare_items = function (frm, invoice_healthcare_services, $results, $placeholder, method, args, columns) {
	var me = this;
	$results.empty();
	frappe.call({
		method: method,
		args: args,
		callback: function (data) {
			if (data.message) {
				$results.append(make_list_row(columns, invoice_healthcare_services));
				for (let i = 0; i < data.message.length; i++) {
					$results.append(make_list_row(columns, invoice_healthcare_services, data.message[i]));
				}
			} else {
				$results.append($placeholder);
			}
		}
	});
}

var make_list_row = function (columns, invoice_healthcare_services, result = {}) {
	var me = this;
	// Make a head row by default (if result not passed)
	let head = Object.keys(result).length === 0;
	let contents = ``;
	columns.forEach(function (column) {
		contents += `<div class="list-item__content ellipsis">
			${head ? `<span class="ellipsis">${__(frappe.model.unscrub(column))}</span>`

				: (column !== "name" ? `<span class="ellipsis">${__(result[column])}</span>`
					: `<a class="list-id ellipsis">
						${__(result[column])}</a>`)
			}
		</div>`;
	})

	let $row = $(`<div class="list-item">
		<div class="list-item__content" style="flex: 0 0 10px;">
			<input type="checkbox" class="list-row-check" ${result.checked ? 'checked' : ''}>
		</div>
		${contents}
	</div>`);

	$row = list_row_data_items(head, $row, result, invoice_healthcare_services);
	return $row;
};

var set_primary_action = function (frm, dialog, $results, invoice_healthcare_services) {
	var me = this;
	dialog.set_primary_action(__('Add'), function () {
		let checked_values = get_checked_values($results);
		if (checked_values.length > 0) {
			if (invoice_healthcare_services) {
				frm.set_value("patient", dialog.fields_dict.patient.input.value);
			}
			frm.set_value("items", []);
			add_to_item_line(frm, checked_values, invoice_healthcare_services);
			dialog.hide();
		}
		else {
			if (invoice_healthcare_services) {
				frappe.msgprint(__("Please select Healthcare Service"));
			}
			else {
				frappe.msgprint(__("Please select Drug"));
			}
		}
	});
};

var get_checked_values = function ($results) {
	return $results.find('.list-item-container').map(function () {
		let checked_values = {};
		if ($(this).find('.list-row-check:checkbox:checked').length > 0) {
			checked_values['dn'] = $(this).attr('data-dn');
			checked_values['dt'] = $(this).attr('data-dt');
			checked_values['item'] = $(this).attr('data-item');
			if ($(this).attr('data-rate') != 'undefined') {
				checked_values['rate'] = $(this).attr('data-rate');
			}
			else {
				checked_values['rate'] = false;
			}
			if ($(this).attr('data-income-account') != 'undefined') {
				checked_values['income_account'] = $(this).attr('data-income-account');
			}
			else {
				checked_values['income_account'] = false;
			}
			if ($(this).attr('data-qty') != 'undefined') {
				checked_values['qty'] = $(this).attr('data-qty');
			}
			else {
				checked_values['qty'] = false;
			}
			if ($(this).attr('data-description') != 'undefined') {
				checked_values['description'] = $(this).attr('data-description');
			}
			else {
				checked_values['description'] = false;
			}
			return checked_values;
		}
	}).get();
};

var get_drugs_to_invoice = function (frm) {
	var me = this;
	let selected_encounter = '';
	var dialog = new frappe.ui.Dialog({
		title: __("Get Items from Prescriptions"),
		fields: [
			{ fieldtype: 'Link', options: 'Patient', label: 'Patient', fieldname: "patient", reqd: true },
			{
				fieldtype: 'Link', options: 'Patient Encounter', label: 'Patient Encounter', fieldname: "encounter", reqd: true,
				description: 'Quantity will be calculated only for items which has "Nos" as UoM. You may change as required for each invoice item.',
				get_query: function (doc) {
					return {
						filters: {
							patient: dialog.get_value("patient"),
							company: frm.doc.company,
							docstatus: 1
						}
					};
				}
			},
			{ fieldtype: 'Section Break' },
			{ fieldtype: 'HTML', fieldname: 'results_area' }
		]
	});
	var $wrapper;
	var $results;
	var $placeholder;
	dialog.set_values({
		'patient': frm.doc.patient,
		'encounter': ""
	});
	dialog.fields_dict["encounter"].df.onchange = () => {
		var encounter = dialog.fields_dict.encounter.input.value;
		if (encounter && encounter != selected_encounter) {
			selected_encounter = encounter;
			var method = "erpnext.healthcare.utils.get_drugs_to_invoice";
			var args = { encounter: encounter };
			var columns = (["drug_code", "quantity", "description"]);
			get_healthcare_items(frm, false, $results, $placeholder, method, args, columns);
		}
		else if (!encounter) {
			selected_encounter = '';
			$results.empty();
			$results.append($placeholder);
		}
	}
	$wrapper = dialog.fields_dict.results_area.$wrapper.append(`<div class="results"
		style="border: 1px solid #d1d8dd; border-radius: 3px; height: 300px; overflow: auto;"></div>`);
	$results = $wrapper.find('.results');
	$placeholder = $(`<div class="multiselect-empty-state">
				<span class="text-center" style="margin-top: -40px;">
					<i class="fa fa-2x fa-heartbeat text-extra-muted"></i>
					<p class="text-extra-muted">No Drug Prescription found</p>
				</span>
			</div>`);
	$results.on('click', '.list-item--head :checkbox', (e) => {
		$results.find('.list-item-container .list-row-check')
			.prop("checked", ($(e.target).is(':checked')));
	});
	set_primary_action(frm, dialog, $results, false);
	dialog.show();
};

var list_row_data_items = function (head, $row, result, invoice_healthcare_services) {
	if (invoice_healthcare_services) {
		head ? $row.addClass('list-item--head')
			: $row = $(`<div class="list-item-container"
				data-dn= "${result.reference_name}" data-dt= "${result.reference_type}" data-item= "${result.service}"
				data-rate = ${result.rate}
				data-income-account = "${result.income_account}"
				data-qty = ${result.qty}
				data-description = "${result.description}">
				</div>`).append($row);
	}
	else {
		head ? $row.addClass('list-item--head')
			: $row = $(`<div class="list-item-container"
				data-item= "${result.drug_code}"
				data-qty = ${result.quantity}
				data-description = "${result.description}">
				</div>`).append($row);
	}
	return $row
};

var add_to_item_line = function (frm, checked_values, invoice_healthcare_services) {
	if (invoice_healthcare_services) {
		frappe.call({
			doc: frm.doc,
			method: "set_healthcare_services",
			args: {
				checked_values: checked_values
			},
			callback: function () {
				frm.trigger("validate");
				frm.refresh_fields();
			}
		});
	}
	else {
		for (let i = 0; i < checked_values.length; i++) {
			var si_item = frappe.model.add_child(frm.doc, 'Sales Invoice Item', 'items');
			frappe.model.set_value(si_item.doctype, si_item.name, 'item_code', checked_values[i]['item']);
			frappe.model.set_value(si_item.doctype, si_item.name, 'qty', 1);
			if (checked_values[i]['qty'] > 1) {
				frappe.model.set_value(si_item.doctype, si_item.name, 'qty', parseFloat(checked_values[i]['qty']));
			}
		}
		frm.refresh_fields();
	}
};

//ibrahim
var print_claim_report = function (frm) {
	if (frm.doc.insurance_party_type == 'Insurance Company' || frm.doc.insurance_party_type == 'Payer'){
		if (frm.doc.items) {
			open_url_post(
				'/api/method/erpnext.accounts.api.claimrep',
				{
					sales_invoice: frm.doc.name,
				}, true
			);
		}
		else {
			frappe.msgprint(__('No lab test found'));
		}
	}
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