# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DataClean(Document):
	pass

@frappe.whitelist()
def clean_data_enque(to_date):
	frappe.enqueue('clean_data', queue='long', timeout=20000,to_date=to_date)
	#clean_data(to_date=to_date)
	#clean_data_query(to_date)
@frappe.whitelist()
def clean_data(to_date):
	try:
		patients = frappe.db.get_all("Patient", {"creation": ["<=", to_date]}, ["name", "customer"])
		
		
		for patient in patients:
			# delete contact
			frappe.db.set_single_value("Data Clean", "current_patient", patient.name)
			for contact in frappe.db.get_all("Dynamic Link", {"link_doctype": "Patient", "link_name": patient.name, "parenttype": "Contact"}, "parent"):
				frappe.delete_doc("Contact", contact.parent)

			try:
				#delete patient
				frappe.delete_doc("Patient", patient.name)
				frappe.delete_doc("Customer", patient.customer)
			except:
				
				# delete lab test
				tests = frappe.db.get_all("Lab Test", {"patient": patient.name}, "name")
				for lab_test in tests:
					frappe.delete_doc("Lab Test", lab_test.name)
				# cancel and delete sample collection
				collections = frappe.db.get_all("Sample Collection", {"patient": patient.name}, "name")
				for collection in collections:
					#frappe.delete_doc("Sample Collection", collection.name)
					sc = frappe.get_doc("Sample Collection", collection.name)
					try:
						sc.cancel()
					except:
						pass
					sc.delete()
				# delete Embassy Report
				reports = frappe.db.get_all("Embassy Report", {"patient": patient.name}, "name")
				for report in reports:
					frappe.delete_doc("Embassy Report", report.name)
				# delete Radiology Test
				for radiology in frappe.db.get_all("Radiology Test", {"patient": patient.name}, "name"):
					frappe.delete_doc("Radiology Test", radiology.name)
				# cancel gl enties against pe

				# cancel and delete payment entry
				for payment_entry in frappe.db.get_all("Payment Entry", {"party": patient.name}, "name"):
					pe = frappe.get_doc("Payment Entry", payment_entry.name)
					try:
						pe.cancel()
					except:
						pass
					pe.delete()

				for sales_invoice in frappe.db.get_all("Sales Invoice", {"patient": patient.name}, "name"):
					# cancel all gl entries against si and party patient
					#for gl_entry in frappe.db.get_all("GL Entry"# cancel gl enties against pe
					reports = frappe.db.get_all("Embassy Report", {"sales_invoice": sales_invoice.name}, "name")
					for report in reports:
						frappe.delete_doc("Embassy Report", report.name)
					si = frappe.get_doc("Sales Invoice", sales_invoice.name)
					try:
						si.cancel()
					except:
						pass
					si.delete()
			# cancel and delete payment entry, ""):
				# cancel and delete sales invoice

			# # delete contact
			# for contact in frappe.db.get_all("Dynamic Link", {"link_doctype": "Patient", "link_name": patient.name, "parenttype": "Contact"}, "parent"):
			# 	frappe.delete_doc("Contact", contact.parent)

				#delete patient
				frappe.delete_doc("Patient", patient.name)
				frappe.delete_doc("Customer", patient.customer)
			frappe.db.commit()
		frappe.db.set_single_value("Data Clean", "status", "Success")
	except Exception as e:
		frappe.db.set_single_value("Data Clean", "status", "Error")
		frappe.db.set_single_value("Data Clean", "error", repr(e))

def clean_data_query(to_date):
	print("start deleting -----------------------")
	frappe.db.set_single_value("Data Clean", "status", "In Progress")
	# try:
	# delete all lab tests
	frappe.db.sql("""delete from `tabLab Test` where creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabLab Test Template Table` where parenttype='Lab Test' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabNormal Test Result` where parenttype='Lab Test' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabDescriptive Test Result` where parenttype='Lab Test' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabOrganism Test Result` where parenttype='Lab Test' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabSensitivity Test Result` where parenttype='Lab Test' and creation<=%(to_date)s""", {"to_date": to_date})

	# delete sample collection
	frappe.db.sql("""delete from `tabSample Collection` where creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabLab Test Template Table` where parenttype='Sample Collection' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabSample Collection Detail` where parenttype='Sample Collection' and creation<=%(to_date)s""", {"to_date": to_date})

	# Embassy Report
	frappe.db.sql("""delete from `tabEmbassy Report` where creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabEmbassy Report Attribute Result` where parenttype='Embassy Report' and creation<=%(to_date)s""", {"to_date": to_date})

	# Radiology Test
	frappe.db.sql("""delete from `tabRadiology Test` where creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabLab Test Template Table` where parenttype='Radiology Test' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabRadiology Test Result` where parenttype='Radiology Test' and creation<=%(to_date)s""", {"to_date": to_date})

	# GL Entry
	frappe.db.sql("""delete from `tabGL Entry` where creation<=%(to_date)s""", {"to_date": to_date})
	# Payment Entry
	frappe.db.sql("""delete from `tabPayment Entry` where creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabCheque Info` where parenttype='Payment Entry' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabIssue Cheque Info` where parenttype='Payment Entry' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabPayment Entry Reference` where parenttype='Payment Entry' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabAdvance Taxes and Charges` where parenttype='Payment Entry' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabPayment Entry Deduction` where parenttype='Payment Entry' and creation<=%(to_date)s""", {"to_date": to_date})

	# Sales Invoice
	frappe.db.sql("""delete from `tabSales Invoice` where creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabSales Invoice Item` where parenttype='Sales Invoice' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabPricing Rule Detail` where parenttype='Sales Invoice' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabPacked Item` where parenttype='Sales Invoice' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabSales Invoice Timesheet` where parenttype='Sales Invoice' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabSales Taxes and Charges` where parenttype='Sales Invoice' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabSales Invoice Advance` where parenttype='Sales Invoice' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabPayment Schedule` where parenttype='Sales Invoice' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabSales Invoice Payment` where parenttype='Sales Invoice' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabSales Team` where parenttype='Sales Invoice' and creation<=%(to_date)s""", {"to_date": to_date})

	# Contact
	frappe.db.sql("""delete from `tabContact` where creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabContact Email` where parenttype='Contact' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabContact Phone` where parenttype='Contact' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabDynamic Link` where parenttype='Contact' and creation<=%(to_date)s""", {"to_date": to_date})

	# Patient
	frappe.db.sql("""delete from `tabPatient` where creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabPatient Fingerprint` where parenttype='Patient' and creation<=%(to_date)s""", {"to_date": to_date})
	frappe.db.sql("""delete from `tabPatient Relation` where parenttype='Patient' and creation<=%(to_date)s""", {"to_date": to_date})

	frappe.db.set_single_value("Data Clean", "status", "Success")
	# except Exception as e:
	# 	frappe.db.set_single_value("Data Clean", "status", "Error")
	# 	frappe.db.set_single_value("Data Clean", "error", repr(e))
	frappe.db.commit()
	frappe.msgprint("The data has been erased successfully")