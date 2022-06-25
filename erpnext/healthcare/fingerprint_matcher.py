from __future__ import unicode_literals
from fileinput import filename
import frappe

import numpy as np
import cv2
import os


fingerprint_shape = (300, 260) # Height, Width

def read_fingerprint(path):
    try:
        with open(path, "rb") as f:
            numpy_data = np.fromfile(f, np.dtype('B'))
        img = numpy_data.reshape(fingerprint_shape)
        return img
    except IOError:
        print('Error while opening the file:', path)

def verify_fingerprint(fingerprint):
    paths = get_fingerprint_paths()
    best_score = 0
    patient = None
    
    sift = cv2.SIFT_create()
    keypoints_1, descriptor_1 = sift.detectAndCompute(np.frombuffer(fingerprint, np.dtype('B')).reshape(fingerprint_shape), None)

    for path in paths:
        saved_fingerprint = read_fingerprint(path)
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
            patient = path.split("/")[-1].split("_")[0]
    return patient

def get_fingerprint_paths():
    PATH = frappe.local.site + "/private/files/fingerprints"
    result = [os.path.join(dp, f) for dp, dn, filenames in os.walk(PATH) for f in filenames]
    return result