from __future__ import unicode_literals
import frappe

#import numpy as np
#import cv2
import os
from erpnext.sgfingerprint.pysgfplib import *
from ctypes import *
from PIL import Image

#import base64

# init
sgfplib = PYSGFPLib()
sgfplib.Create()
sgfplib.Init(SGFDxDeviceName.SG_DEV_FDU03)

def load_image(path):
    grayScale = Image.open(path).convert('L')
    img = grayScale.tobytes()
    # imageBuffer = (c_char*(260*300))()
    # imageBuffer.value = img
    return img


fingerprint_shape = (300, 260) # Height, Width
matching_score_accuracy = {
    "Basic": SGFDxSecurityLevel.SL_BELOW_NORMAL,
    "Normal": SGFDxSecurityLevel.SL_NORMAL,
    "High": SGFDxSecurityLevel.SL_HIGH,
    "Extreme": SGFDxSecurityLevel.SL_HIGHEST
}

def read_blob(blob):
    with open("temp.bmp", 'wb') as fw:
        fw.write(blob)
    #img = cv2.imread("temp.bmp", cv2.IMREAD_GRAYSCALE)
    img = load_image("temp.bmp")
    os.remove("temp.bmp")
    return img

def create_template(img):
    cMinutiaeBuffer1 = (c_char*sgfplib.constant_sg400_template_size)()
    result = sgfplib.CreateSG400Template(img, cMinutiaeBuffer1)
    return cMinutiaeBuffer1

def verify_fingerprint(fingerprint):
    paths = get_fingerprint_paths()
    best_score = 0
    patient = None
    print(paths)
    selecting_method = frappe.db.get_single_value("Healthcare Settings", "selecting_method")

    first_match = True if selecting_method == "First Match" else False

    matching_accuracy = frappe.db.get_single_value("Healthcare Settings", "matching_accuracy")
    security_level = matching_score_accuracy.get(matching_accuracy, SGFDxSecurityLevel.SL_NORMAL)

    
    img = read_blob(fingerprint)
    fingerprint_template = create_template(img)

    for path in paths:
        saved_fingerprint = load_image(path["file_path"])
        if saved_fingerprint is None:
            print("error reading: ", path)
            continue

        saved_fingerprint_template = create_template(saved_fingerprint)
        
        cMatched = c_bool(False)
        result = sgfplib.MatchTemplate(fingerprint_template, saved_fingerprint_template, security_level, byref(cMatched))
        
        if cMatched.value:
            if first_match:
                patient = path["parent"]
                return patient
            else:
                cScore = c_int(0)
                result = sgfplib.GetMatchingScore(fingerprint_template, saved_fingerprint_template,  byref(cScore))
                if cScore.value > best_score:
                    patient = path["parent"]
                    best_score = cScore.value
    return patient

def get_fingerprint_paths():
    #PATH = frappe.local.site + "/private/files/fingerprints"
    #result = [os.path.join(dp, f) for dp, dn, filenames in os.walk(PATH) for f in filenames]
    capture_date = frappe.db.get_single_value("Healthcare Settings", "match_fingerprints_only")
    capture_dict = {
        "Last day": "1 DAY",
        "Last two days": "2 DAY",
        "Last week": "1 WEEK",
        "Last Month": "1 MONTH",
        "Last two months": "2 MONTH"
    }
    where_clause = ""
    if capture_date and capture_date != "" and capture_date != "All time":
        where_clause = "WHERE  capture_date >= NOW() - INTERVAL " + capture_dict[capture_date]
    result = frappe.db.sql("""
        SELECT file_path, parent FROM `tabPatient Fingerprint`
        {where_clause}
        ORDER BY capture_date DESC
    """.format(where_clause=where_clause), as_dict=True)

    return result