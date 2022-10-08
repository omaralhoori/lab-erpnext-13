// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include "erpnext/public/js/controllers/accounts.js" %}

frappe.ui.form.on('Cheque Entry', {
	onload: function(frm) {
		frm.events.Set_bank_account_list(frm);

		frm.set_query("chq_info_name","cheque_transaction",  function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				query: 'erpnext.accounts.doctype.cheque_entry.cheque_entry.get_chq_list',
				filters: {
					link_company: frm.doc.company,
					link_entry_type: frm.doc.entry_type,
					link_bank:frm.doc.bank
				}
			}
		});

	},

	bank_account:function(frm){
		frappe.db.get_value("Bank Account", {"name":frm.doc.bank_account}, "bank").then((res) => {
			frm.set_value('bank', res.message.bank)
			frappe.db.get_value("Bank Account",  {"bank":res.message.bank,"account_type":"Cheque Collection Account"}, "account").then((r) => {
				frm.set_value('collection_account', r.message.account)
			})
		})
	},

	entry_type: function(frm){
		frm.set_value('bank', '')
		frm.set_value('bank_account', '')
		frm.set_value('account_no', '')
		frm.set_value('collection_account', '')
		frm.set_value('document_reference_no', '')
		frm.set_value('document_date', '')
		frm.set_value('account_type', '')
		frm.events.Set_bank_account_list(frm);
	},
	refresh: function(frm){
		frm.events.show_general_ledger(frm);
	},
	show_general_ledger: function(frm) {
		if(frm.doc.docstatus > 0) {
			frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name,
					"from_date": frm.doc.posting_date,
					"to_date": moment(frm.doc.modified).format('YYYY-MM-DD'),
					"company": frm.doc.company,
					"group_by": "",
					"show_cancelled_entries": frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			}, "fa fa-table");
		}
	},
	Set_bank_account_list: function(frm) {
		if (frm.doc.entry_type=='Send Cheques'){
			frm.set_value('account_type', 'Cheque Collection Account')
			frm.set_query("bank_account", function() {
				return {
					filters: {
						'is_company_account': 1,
						'account_type':["in",["Cheque Collection Account"]] 
						//'account_type':["in",["Cheque Collection Account","Current Account","Cheque Return Account"]] 
					}
				}
			});
		}
		if (frm.doc.entry_type=='Paid Cheques'){
			frm.set_value('account_type', 'Current Account')
			frm.set_query("bank_account", function() {
				return {
					filters: {
						'is_company_account': 1,
						'account_type':["in",["Current Account"]] 
						//'account_type':["in",["Cheque Collection Account","Current Account","Cheque Return Account"]] 
					}
				}
			});
		}
		if (frm.doc.entry_type=='Returned Cheques'){
			frm.set_value('account_type', 'Cheque Return Account')
			frm.set_query("bank_account", function() {
				return {
					filters: {
						'is_company_account': 1,
						'account_type':["in",["Cheque Return Account"]] 
						//'account_type':["in",["Cheque Collection Account","Current Account","Cheque Return Account"]] 
					}
				}
			});
		}
	},

});

frappe.ui.form.on("Cheque Transaction", {

	cheque_paid_amount: function(frm, cdt, cdn) {
		cur_frm.cscript.update_chq_totals(frm.doc);
	},

	cheque_transaction_remove: function(frm, cdt, cdn) {
		cur_frm.cscript.update_chq_totals(frm.doc);
	},
	pcheque_transaction_add: function(frm, cdt, cdn) {
		cur_frm.cscript.update_chq_totals(frm.doc);
	},

	chq_info_name: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.chq_info_name != null) {
			frappe.call({
				method: 'erpnext.accounts.doctype.cheque_entry.cheque_entry.get_chq_info',
				args: {
					bank:frm.doc.bank,
					chq_info_name:row.chq_info_name
				},
				callback: function(r, rt) {
					frappe.model.set_value(cdt, cdn, "cheque_no",r.message.cheque_no);
					frappe.model.set_value(cdt, cdn, "cheque_date",r.message.cheque_date);
					frappe.model.set_value(cdt, cdn, "cheque_amount",r.message.cheque_amount);
					frappe.model.set_value(cdt, cdn, "cheque_bank",r.message.cheque_bank);
					frappe.model.set_value(cdt, cdn, "notes",r.message.notes);
					frappe.model.set_value(cdt, cdn, "cheque_paid_amount",r.message.cheque_amount);
					frappe.model.set_value(cdt, cdn, "chq_old_status",r.message.chq_status);
					frappe.model.set_value(cdt, cdn, "payment_entry_no",r.message.payment_entry_no);
					frappe.model.set_value(cdt, cdn, "party_type",r.message.party_type);
					frappe.model.set_value(cdt, cdn, "party",r.message.party);
					frappe.model.set_value(cdt, cdn, "account_paid_from",r.message.account_paid_from);
					frappe.model.set_value(cdt, cdn, "account_paid_to",r.message.account_paid_to);
					frappe.model.set_value(cdt, cdn, "company_bank",frm.doc.bank);

				}
			})
		}
	},

});
cur_frm.cscript.update_chq_totals = function(doc) {
	var amount_total=0.0;
	var cheque_transaction = doc.cheque_transaction || [];
	for(var i in cheque_transaction) {
		amount_total += flt(cheque_transaction[i].cheque_paid_amount);
	}
	var doc = locals[doc.doctype][doc.name];
	doc.total_amount = amount_total;
	refresh_many(['total_amount']);
}

