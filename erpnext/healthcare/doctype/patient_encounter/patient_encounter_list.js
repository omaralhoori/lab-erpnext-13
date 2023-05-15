/*
(c) ESS 2015-16
*/
frappe.listview_settings['Patient Encounter'] = {
	filters:[["docstatus","!=","2"]],
	onload: function (listview) {

		listview.page.add_button("Capture Fingerprint", async () => {

			// Fingerprint Functions

			const matchFP = (image) => {

				frappe.show_progress('Capturing..', 50, 100, 'Please wait');
				let xhr = new XMLHttpRequest();

				xhr.open('POST', '/api/method/erpnext.healthcare.doctype.patient.patient.match_fingerprint_encounter', true);
				xhr.setRequestHeader('Accept', 'application/json');

				xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);

				let form_data = new FormData();
				if (image) {
					form_data.append('file', image, "fingerprint");
				}
				xhr.send(form_data);

				xhr.addEventListener("load", (res) => {
					var progress = frappe.show_progress('Capturing..', 100, 100, 'Please wait');
					progress.hide();
					if (xhr.response && xhr.response != ""){
						var response = JSON.parse(xhr.response)
						if(response.message && response.message.path){
							window.location.href = response.message.path
						}else{
							frappe.msgprint({
								title: __('Matching status'),
								indicator: 'orange',
								message: __('Fingerprint did not match!')
							});
						}
					}else{
						frappe.throw(__("Something went wrong!"))
					}

				})
			}

			const  SuccessFunc = (result) => {
				if (result.ErrorCode == 0) {
					if (result != null && result.BMPBase64.length > 0) {
						matchFP(b64toBlob(result.BMPBase64, "image/bmp"))
					}else{
						frappe.throw("Fingerprint Capture Fail");
					}
				}
				else {
					frappe.throw("Fingerprint Capture Error Code: " + result.ErrorCode )
				}
			}

			const ErrorFunc= (status) => {
				console.error(status);
				var progress = frappe.show_progress('Capturing..', 100, 100, 'Please wait');
				progress.hide();
				frappe.msgprint({
					title: __('Capturing status'),
					indicator: 'red',
					message: __('Fail to capture; Status =') + status
				});
			}

			const CallSGIFPGetData = async (successCall, failCall) => {
				frappe.show_progress('Capturing..', 0, 100, 'Please wait');
				var uri = await frappe.db.get_single_value("Healthcare Settings", "fingerprint_scanner_url");
				if(!uri){
					frappe.throw(__("Fingerprint scanner url is not set!"));
					return;
				}
				var license = await frappe.db.get_single_value("Healthcare Settings", "web_api_licence");

				var xmlhttp = new XMLHttpRequest();
				xmlhttp.onreadystatechange = function () {
					if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
						var fpobject = JSON.parse(xmlhttp.responseText);
						successCall(fpobject);
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

			CallSGIFPGetData(SuccessFunc, ErrorFunc);
			
		})
	}
};


function b64toBlob (b64Data, contentType='', sliceSize=512)  {
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