import cv2
import numpy as np
import matplotlib.pyplot as plt
import pytictoc

def process_frame_watershed(frame):
    """
    Xử lý frame và trả về markers, tọa độ markers và bán kính
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Ngưỡng để phân tách đối tượng
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Áp dụng morphology để tách các đối tượng chạm nhau
    kernel = np.ones((3,3), np.uint8)
    opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)
    
    # Background rõ ràng
    sure_bg = cv2.dilate(opening, kernel, iterations=3)
    
    # Foreground rõ ràng
    dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist_transform, 0.4 * dist_transform.max(), 255, 0)
    sure_fg = np.uint8(sure_fg)
    
    # Vùng không chắc chắn
    unknown = cv2.subtract(sure_bg, sure_fg)
    
    # Gán nhãn cho vùng foreground
    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0
    
    # Áp dụng watershed
    markers = cv2.watershed(frame, markers)
    
    # Lấy unique markers (bỏ qua background (-1) và unknown (0))
    unique_markers = np.unique(markers)[2:]
    
    # Tạo mask cho từng đối tượng
    masks = []
    centroids = []
    radii = []
    
    for marker in unique_markers:
        mask = np.uint8(markers == marker)
        masks.append(mask)
        
        # Tính centroid và bán kính
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        M = cv2.moments(contours[0])
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            centroids.append((cx, cy))
            
            # Tính bán kính gần đúng từ contour
            radius = np.sqrt(cv2.contourArea(contours[0])/np.pi)
            radii.append(radius)
    
    return markers, masks, centroids, radii

def check_collision(masks):
    """
    Kiểm tra va chạm giữa các đối tượng
    """
    collision_detected = False
    min_distance = float('inf')
    
    if len(masks) == 2:
        # Tìm contour cho mỗi mask
        contours1, _ = cv2.findContours(masks[0], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours2, _ = cv2.findContours(masks[1], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Tìm khoảng cách nhỏ nhất giữa các điểm contour
        for pt1 in contours1[0]:
            for pt2 in contours2[0]:
                dist = np.sqrt((pt1[0][0] - pt2[0][0])**2 + (pt1[0][1] - pt2[0][1])**2)
                min_distance = min(min_distance, dist)

        # Nếu khoảng cách nhỏ hơn ngưỡng, coi như va chạm
        collision_detected = min_distance < 4
        
    return collision_detected, min_distance

def check_collision_watershed_video(video_path):
    # Đọc video đầu vào
    cap = cv2.VideoCapture(video_path)
    frame_number = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Xử lý frame
        markers, masks, centroids, radii = process_frame_watershed(frame)
        
        # Kiểm tra va chạm
        collision_detected, min_distance = check_collision(masks)
        
        if collision_detected:
            result_image = frame.copy()
            result_image[markers == -1] = [255, 0, 0]  # Đánh dấu va chạm
            
            # Hiển thị kết quả
            plt.imshow(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
            plt.title(f"Kết quả: Va chạm\nKhung hình: {frame_number}\n"
                     f"Số đối tượng: {len(masks)}\nKhoảng cách nhỏ nhất: {min_distance:.2f}")
            plt.axis('off')
            plt.show()
        
        frame_number += 1

    cap.release()