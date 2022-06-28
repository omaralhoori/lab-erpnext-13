from __future__ import unicode_literals
import frappe

import numpy as np
import cv2
import os

import base64



fingerprint_shape = (300, 260) # Height, Width
matching_score_accuracy = {
    "Basic": 10,
    "Normal": 25,
    "High": 50,
    "Extreme": 80
}

def read_blob(blob):
    # nparray = np.frombuffer(blob,  dtype=np.uint8)
    # print(nparray)
    # print(nparray.shape)
    # return nparray.reshape(fingerprint_shape)
    with open("temp.bmp", 'wb') as fw:
        fw.write(blob)
    img = cv2.imread("temp.bmp", cv2.IMREAD_GRAYSCALE)
    os.remove("temp.bmp")
    return img
def read_fingerprint(path):
    try:
        # with open(path, "rb") as f:
        #     numpy_data = np.fromfile(f, np.dtype('B'))
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)#numpy_data.reshape(fingerprint_shape)
        return img
    except:
        print('Error while opening the file:', path)

def verify_fingerprint(fingerprint):
    paths = get_fingerprint_paths()
    best_score = 0
    patient = None
    
    selecting_method = frappe.db.get_single_value("Healthcare Settings", "selecting_method")

    first_match = True if selecting_method == "First Match" else False

    matching_accuracy = frappe.db.get_single_value("Healthcare Settings", "matching_accuracy")
    score_threshold = matching_score_accuracy.get(matching_accuracy, 90)

    sift = cv2.SIFT_create()
    #print(fingerprint)
    #np.frombuffer(fingerprint, np.dtype('B')).reshape(fingerprint_shape)
    img = read_blob(fingerprint)
    keypoints_1, descriptor_1 = sift.detectAndCompute(img, None)

    for path in paths:
        saved_fingerprint = read_fingerprint(path["file_path"])
        if saved_fingerprint is None:
            print("error reading: ", path)
            continue
        keypoints_2, descriptor_2 = sift.detectAndCompute(saved_fingerprint, None)

        matches = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 10}, {}).knnMatch(descriptor_1, descriptor_2, k=2)

        match_points = []
        for p, q in matches:
            if p.distance < 0.1 * q.distance:
                match_points.append(p)
        
        keypoints = 0
        if len(keypoints_1) < len(keypoints_2):
            keypoints = len(keypoints_1)
        else:
            keypoints = len(keypoints_2)
        
        if len(match_points) / keypoints * 100 > best_score:
            best_score = len(match_points) / keypoints * 100
            if best_score > score_threshold:
                patient = path["parent"]#path.split("/")[-1].split("_")[0]
                if first_match:
                    return patient
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