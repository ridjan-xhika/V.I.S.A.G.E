import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

ret, frame = cap.read()

cv2.imshow('Camera Feed', frame)

cv2.waitKey(0)
cap.release()
cv2.destroyAllWindows()
