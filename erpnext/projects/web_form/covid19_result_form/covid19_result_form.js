frappe.ready(function() {
	var txt = frappe.utils.get_url_arg("new");
	frappe.msgprint(frappe.utils.get_url_arg("new"));
	var customer_password = document.getElementById("Customer Password");
	customer_password.value=txt;

	frappe.web_form.on('customer_password', (field, value) => {
	    if (value < '1000') {
		frappe.msgprint('Value must be more than 1000');
		field.set_value('0');
	    }
	});

	frappe.web_form.set_value('customer_name', txt);
	frappe.web_form.validate = () => {
	    	//let data = frappe.web_form.get_values();
	    //if (data.customer_password != '2') {
		frappe.web_form.set_value('customer_name', 'nn');
		frappe.web_form.set_value('analysis_result', 'Detected (Positive)');
	    //}
	}
})
