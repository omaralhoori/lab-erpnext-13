frappe.listview_settings['Sample Collection'] = {

	onload: function (listview) {
		let disabled = false;
		let query = "";
		let url = location.href;
		document.body.addEventListener('click', () => {
			requestAnimationFrame(() => {
				if (url !== location.href) {
					//$(document).find('*').off('keydown');
					disabled = true;
					query = "";
					url = location.href
				}
				let urls = location.href.split("/");
				if (urls[urls.length - 1] === "sample-collection") {
					disabled = false;
				}
			});
		}, true);

		$(document).keydown(function (e) {
			if (abandonedChars(e.which) || disabled) return; // || !frm.is_dirty()
			query += String.fromCharCode(switchedChars(e.which));
			//console.log(e.which)
			if (e.which == 13) {
				// ctrl+b pressed
				frappe.call({
					method: "erpnext.healthcare.barcode_query.find_sample_collection",
					args: {
						"test_code": query
					},
					callback: (res) => {
						if (res.message != null && res.message != "") {
							window.location.href = res.message;
						}
					}
				})
				query = "";
			}

		});

		listview.page.add_button("Capture Fingerprint", async () => {
			frappe.show_progress('Capturing..', 0, 100, 'Please wait');
			var url = await frappe.db.get_single_value("Healthcare Settings", "fingerprint_scanner_url");
			frappe.show_progress('Capturing..', 10, 100, 'Please wait');
			if (!url) {
				frappe.throw(__("Fingerprint scanner url is not set!"));
				return;
			}
			fetch(url).
				then(response => response.blob())
				.then(blob => {
					frappe.show_progress('Capturing..', 50, 100, 'Please wait');
					// xhr.open('POST', '/api/method/erpnext.healthcare.doctype.patient.patient.upload_fingerprint', true);
					let xhr = new XMLHttpRequest();

					xhr.open('POST', '/api/method/erpnext.healthcare.doctype.patient.patient.match_fingerprint', true);
					xhr.setRequestHeader('Accept', 'application/json');

					xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);

					let form_data = new FormData();
					if (blob) {
						form_data.append('file', blob, "fingerprint");
					}
					xhr.send(form_data);

					xhr.addEventListener("load", (res) => {
						var progress = frappe.show_progress('Capturing..', 100, 100, 'Please wait');
						progress.hide();
						if (xhr.response && xhr.response != ""){
							var response = JSON.parse(xhr.response)
							if(response.message && response.message.path){
								window.location.href = response.message.path
							}
						}

					})
				})
				.catch(err => {
					console.error(err);
					var progress = frappe.show_progress('Capturing..', 100, 100, 'Please wait');
					progress.hide();
					frappe.msgprint({
						title: __('Capturing status'),
						indicator: 'red',
						message: __('Fail to capture')
					});
				})
		})
	}
}



function abandonedChars(charCode) {
	if (charCode == 16) {
		return true;
	}
	return false;
}

function switchedChars(charCode) {
	if (charCode == 189) {
		return 45;
	}
	return charCode;
}
