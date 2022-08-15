
from __future__ import unicode_literals

import frappe
import json


@frappe.whitelist(allow_guest=True)
def get_invoice():
    invoice_data = json.loads(frappe.request.data)
    total = 0
    for item in invoice_data['items']:
        total += item['patient_share']
    invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": invoice_data['customer'],
        "patient": invoice_data['customer'],
        "company": invoice_data['company'],
        "total_patient": total,
        "selling_price_list": invoice_data['price_list'],
        "price_list_currency": invoice_data['currency']
    })
    
    for item_data in invoice_data["items"]:
        item = invoice.append("items")
        item.item_code = item_data['item_code']
        item.qty = 1
        item.patient_share= item_data['patient_share']
        item.patient_rate= item_data['patient_share']
    invoice.save(ignore_permissions=True)
    #invoice.submit()
    frappe.db.commit()
    return invoice.name

