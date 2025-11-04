import cv2
import numpy as np

TEMPLATE_FILENAME = 'image.png'  # Use your latest template file

car_template = cv2.imread(TEMPLATE_FILENAME, cv2.IMREAD_UNCHANGED)
if car_template is None:
    print("Error loading car template image.")
    exit()

if car_template.shape[2] == 4:
    car_template = car_template[:, :, :3]

h, w, _ = car_template.shape
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Webcam not detected.")
    exit()

# Define birds-eye region size as a fraction of template dimensions (adjust if needed)
region_width = w // 5
region_height = h // 5

while True:
    ret, webcam_img = cap.read()
    if not ret:
        print("Error reading webcam frame.")
        break

    webcam_img_resized = cv2.resize(webcam_img, (region_width, region_height))
    rh, rw, _ = webcam_img_resized.shape

    canvas = car_template.copy()

    # Place at the center-top (front)
    y1 = h // 11
    x1 = (w // 2) - (rw // 2)
    canvas[y1:y1+rh, x1:x1+rw] = webcam_img_resized

    # Place at the center-bottom (rear)
    y2 = h - rh - h // 11
    x2 = (w // 2) - (rw // 2)
    canvas[y2:y2+rh, x2:x2+rw] = webcam_img_resized

    # Place at the center-left (left)
    y3 = (h // 2) - (rh // 2)
    x3 = w // 24
    canvas[y3:y3+rh, x3:x3+rw] = webcam_img_resized

    # Place at the center-right (right)
    y4 = (h // 2) - (rh // 2)
    x4 = w - rw - w // 24
    canvas[y4:y4+rh, x4:x4+rw] = webcam_img_resized

    cv2.imshow('Birds-Eye 360 Placed Like Reference', canvas)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
