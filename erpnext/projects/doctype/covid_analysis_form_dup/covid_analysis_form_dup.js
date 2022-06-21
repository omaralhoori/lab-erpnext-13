// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('COVID Analysis Form Dup', {
	onload: function(frm) {
		
		if (frm.doc.date == null) {
			frm.set_value('date', frappe.datetime.now_date()); 
		}
		if (frm.doc.mobile_no == null) {
			frm.set_value('mobile_no', "962"); 
		}
		frm.set_query("cus_info", function() {
			return {
				filters: {
					'rcv_flag': 0, 
				}
			}
		});

		
		//if (frm.doc.new_customer_flage == "0"){
		//	frm.set_value('collection_date', frappe.datetime.now_date()); 
		//	frm.set_value('collection_time', frappe.datetime.now_time()); 
		//	frm.set_value('result_date', frappe.datetime.now_date()); 
		//	frm.set_value('result_time', frappe.datetime.now_time()); 
		//}
		//else
		//{
		//	frm.set_value('collection_date', ""); 
		//	frm.set_value('collection_time', ""); 
		//	frm.set_value('result_date', ""); 
		//	frm.set_value('result_time', ""); 
		//}

		//if (frm.doc.sample_collect_flag == "1"){
		//	frm.toggle_display("collect_sample",false);
		//	frm.toggle_enable("collection_date",false);
		//	frm.toggle_enable("collection_time",false);
		//}
		//else{
		//	frm.doc.sample_collect_flag="0"
		//}
		//if (frm.doc.result_flage == "1"){
		//	frm.toggle_display("set_result",false);
		//	frm.toggle_enable("result_date",false);
		//	frm.toggle_enable("result_time",false);
		//}
		//else{
		//frm.doc.result_flage="0"
		//}

		
		if (frm.doc.analysis_result != null){
			
		}
		else{
			frm.doc.analysis_result="Not Collected"
			frm.doc.analysis_result_ref_range="Not Collected"
		}
		//if (frm.doc.custmer_name != null || frm.doc.medical_direction != null){
		//	frappe.new_doc("COVID Analysis Form")
		//	frm.enable_save();
		//	//frm.reload_doc();
		//}
		//if (frm.doc.custmer_name == null && frm.doc.medical_direction == null){
		frm.enable_save();
		//	//frm.reload_doc();
		//}
	},
	after_save:function(frm) {
		frappe.show_alert('Record added successfully')
		frappe.msgprint(__("Record added successfully"));
		frappe.call({
			method: "erpnext.projects.doctype.covid_analysis_form_dup.covid_analysis_form_dup.qrcode_gen_dup",
			args: {
				customer_password:frm.doc.customer_password,
				docname:frm.doc.name
			},
			callback: function(r, rt) {
			}
		})
		if(frm.doc.cus_info != null) {
			frappe.call({
				method: "erpnext.projects.doctype.covid_analysis_form_dup.covid_analysis_form_dup.set_rcv_flag",
				args: {
					cus_info:frm.doc.cus_info
				},
				callback: function(r, rt) {
				}
			})
		}

		frm.disable_save();
		//frappe.new_doc("COVID Analysis Form")
		//frm.fields.forEach(function(l){ frm.set_df_property(l.df.fieldname, "read_only", 1); })

	},


	collect_sample: function(frm) {
		frappe.call({
			method: "erpnext.projects.doctype.covid_analysis_form_dup.covid_analysis_form_dup.update_collect_sample_flag",
			args: {
				company:frm.doc.company,
				medical_direction:frm.doc.medical_direction,
				custmer_name:frm.doc.custmer_name,
				collection_date:frm.doc.collection_date,
				collection_time:frm.doc.collection_time,
				collection_users:frappe.session.user
			},
			callback: function(r, rt) {
				//frm.set_value("barcode", r.message.barcode);	
				frm.set_value("sample_collect_flag", "1");	
				frm.toggle_display("collect_sample",false);
				frm.toggle_display("collection_date",false);
				frm.toggle_display("collection_time",false);
				frappe.msgprint(__("Sample Collected"));
			}
		})
	},

	set_result: function(frm) {
		if (frm.doc.sample_collect_flag != "1"){
			frappe.throw(__("Sample not colected"));
		}

		frappe.call({
			method: "erpnext.projects.doctype.covid_analysis_form_dup.covid_analysis_form_dup.set_result_data",
			args: {
				company:frm.doc.company,
				custmer_name:frm.doc.custmer_name,
				result_date:frm.doc.result_date,
				result_time:frm.doc.result_time,
				result_user:frappe.session.user
			},
			callback: function(r, rt) {
				frm.toggle_display("set_result",false);
				frm.toggle_display("result_date",false);
				frm.toggle_display("result_time",false);
				frappe.msgprint(__("Done"));
			}
		})
	},
	send_sms_message:function(frm) {
		//frappe.msgprint(__("sds"));
		//Dear ( PT name ) 

		//Your COVID-19  test result for the sample collected on < date > is NEGATIVE 

		//Please consult your doctor for interpretation and advice in particular circumstances. 

		//Please log in to review information about you result online: 
		//<Link> 

		//Thanks alot 
		//JoSante-Clinics health
		
		var msg_res
		if (frm.doc.analysis_result =="Not Detected (Negative)" ){
			msg_res = "سلبية(غير مصاب).";
		}
		if (frm.doc.analysis_result =="Detected (Positive)" ){
			msg_res = "إيجابية( مصاب).";
		}

		var msgg = "السيد/ة " + frm.doc.custmer_name + "\n" + "نشكركم لزيارة مختبرات جوسانتي الطبية " + "\n" + "نتيجة فحصك للكورونا بتاريخ ";
		msgg += frm.doc.date  + "\n" + msg_res +  "\n";
		msgg += "لطباعة التقرير اضغط على الرابط ادناه " +  "\n";
		msgg += "(To print result click following URL "+ "\n";
		msgg += "http://94.142.51.110:1952/resultv?name="+ frm.doc.name +"&password="+ frm.doc.customer_password +  "\n";
		msgg += ")" +  "\n";
		msgg += "لفحوصات الدم و الزيارات المنزلية يرجى الاتصال على 065804444. " +  "\n";
		msgg += "سلامتك تهمنا" +  "\n";
		msgg += "مجموعة عيادات ومختبرات جوسانتي الطبية العالمية" +  "\n";


		//var msgg = "Dear " + frm.doc.custmer_name + "\n" + "Your COVID-19  test result for the sample collected on ";
		//msgg += frm.doc.date + " is " + frm.doc.analysis_result +  "\n";
		//msgg += "Please consult your doctor for interpretation and advice in particular circumstances." +  "\n";
		//msgg += "To print result click following URL:"+ "\n";
		//msgg += "http://94.142.51.110:1952/resultv?name="+ frm.doc.name +"&password="+ frm.doc.customer_password +  "\n";
		//msgg += "Thanks alot" +  "\n";
		//msgg += "JoSante-Clinics health" +  "\n";


		//frappe.msgprint(__(msgg));
		frappe.call({
			method: "frappe.core.doctype.sms_settings.sms_settings.send_sms",
			args: {
				receiver_list: [frm.doc.mobile_no],
				msg:msgg,
			},
			callback: function(r, rt) {
				if (r.exc) {
                       			msgprint(r.exc);
                       			return;
                   		}
				frappe.msgprint(__("SMS Meesage Send"));
			}
		})
	},
	party_list: function(frm) {
		frm.doc.analysis_default_amount_org=frm.doc.government_amount
		if(frm.doc.party_list != null) {
			frappe.call({
				method: "erpnext.projects.doctype.covid_analysis_form_dup.covid_analysis_form_dup.get_party_list_data",
				args: {
					party_list:frm.doc.party_list
				},
				callback: function(r, rt) {
					frm.set_value("analysis_amount", r.message.analysis_amount);
					frm.set_value("analysis_default_amount_org", r.message.analysis_amount);
					frm.set_value("fees_amount", r.message.fees_amount);
					frm.set_value("payment_type", r.message.payment_type);
				}
			})
		}
	},
	custmer_name: function(frm) {
		frm.set_value("new_customer_flage", "0");
	},
	medical_direction: function(frm) {
		if(frm.doc.medical_direction != null) {
			frappe.call({
				method: "erpnext.projects.doctype.covid_analysis_form_dup.covid_analysis_form_dup.get_medical_direction_data",
				args: {
					medical_direction:frm.doc.medical_direction
				},
				callback: function(r, rt) {
					frm.set_value("medical_direction_code", r.message.medical_direction);
				}
			})
		}
	},
	cus_info: function(frm) {
		if(frm.doc.cus_info != null) {
			frappe.call({
				method: "erpnext.projects.doctype.covid_analysis_form_dup.covid_analysis_form_dup.get_customer",
				args: {
					cus_info:frm.doc.cus_info
				},
				callback: function(r, rt) {
					frm.set_value("custmer_name", r.message.customer_name);
					frm.set_value("party_list", r.message.party_list);
					frm.set_value("visit_type", r.message.visit_type);
					frm.set_value("collector_name", r.message.collector_name);
					frm.set_value("mobile_no", r.message.mobile_number);
					frm.set_value("another_mobile_no", r.message.mobile_2);
					frm.set_value("nationality", r.message.customer_nationality);
					frm.set_value("national_id", r.message.national_id);
					frm.set_value("passport_id", r.message.pass_id);
					frm.set_value("gender", r.message.gender);
					frm.set_value("date_of_birth", r.message.birth_date);
					frm.set_value("receive_aman_notification", r.message.recive_aman);
					frm.set_value("email_address", r.message.email_add);
					frm.set_value("governorate", r.message.governorate);
					frm.set_value("address_details", r.message.address_details);
					frm.set_value("notes", r.message.note);
					frm.set_value("destination_country", r.message.destination_country);

				}
			})
		}
	},


});
