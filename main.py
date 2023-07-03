import cv2
import math
import threading
import time
from helper_functions import *
from ultralytics import YOLO
from sort import *

# Failide asukohad
VIDEO_FILE = "./Videod/six_lane_traffic.mp4"
VIDEO_MASK_FILE = "./Masks/six_lane_traffic_mask.png"
YOLOV8_WEIGHT_FILE = "./Yolo_Weights/yolov8m.pt"
OUTPUT_FILE_PATH = "./Logs/"

SAVE_INTERVAL = 10 # Sõidukite andmete salvestamise interval sekundites
STOP_FLAG = False # Konstant, mis annab teada, kas lõimumine tuleks lõpetada

# Videosalvestuse, mask pildi ja masinnägemise mudeli defineerimine
cap = cv2.VideoCapture(VIDEO_FILE)
mask = cv2.imread(VIDEO_MASK_FILE)
model = YOLO(YOLOV8_WEIGHT_FILE)

# Objektide jälitajad
truck_tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)
car_tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)

# Loendus joonte asukoht kaamerapildis [startX, startY, endX, endY]
outgoing_line_dimensions = [200,450,600,475]
incoming_line_dimensions = [675,475,1100,470]

vehicles = create_vehicle_dictionary()

# Masinnägemise treenimis mudeli klassifikatsioonide nimetused --- Hetkel kasutuses COCO mudel
classNames = ['person', 'bicycle', 'car', 'motorbike', 'aeroplane', 'bus',
             'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 
             'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 
             'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 
             'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 
             'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 
             'baseball glove', 'skateboard', 'surfboard', 'tennis racket', 
             'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 
             'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 
             'hot dog', 'pizza', 'donut', 'cake', 'chair', 'sofa', 
             'pottedplant', 'bed', 'diningtable', 'toilet', 'tvmonitor', 
             'laptop', 'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 
             'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 
             'scissors', 'teddy bear', 'hair drier', 'toothbrush']

# Andmete salvestamine andmebaasi teises lõimus
#save_thread = threading.Thread(target=insert_data_periodically, args=(vehicles, STOP_FLAG, SAVE_INTERVAL), daemon=True).start()

# Andmete salvestamine teksti faili teises lõimus
save_thread = threading.Thread(target=save_text_periodically, args=(OUTPUT_FILE_PATH, vehicles, STOP_FLAG, SAVE_INTERVAL), daemon=True).start()

# Andmete salvestamine json faili teises lõimus
#save_thread = threading.Thread(target=save_json_periodically, args=(OUTPUT_FILE_PATH, vehicles, STOP_FLAG, SAVE_INTERVAL), daemon=True).start()

# Programmi põhiosa
if __name__ == '__main__':


    while True:
        # Videopildi kaadrist mitte vajaliku tausta eemaldamine ja olemasolevast
        # kaadrist objektide tuvastamine
        success, img = cap.read()

        img_region = cv2.bitwise_and(img, mask)

        results = model(img_region, stream=True)

        detections = {'car': np.empty((0, 5)), 'truck': np.empty((0, 5))}

        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # Usaldusväärsus
                conf = math.ceil((box.conf[0]*100))/100

                # Klassi nimi
                cls = int(box.cls[0])
                current_class = classNames[cls]
              
                # Otsitava klassi lisamine sõnastikku(auto ja veoauto)
                if current_class in detections and conf > 0.4:
                    current_array = np.array([x1, y1, x2, y2, conf])
                    detections[current_class] = np.vstack((detections[current_class], current_array))

        # Unikaalse ID lisamine tuvastatud objektidele
        car_tracker_results = car_tracker.update(detections['car'])
        truck_tracker_results = truck_tracker.update(detections['truck'])

        '''Joonte joonistamine kaadrisse, mida kasutame sõidukite lugemiseks, kui
        sõidetakse sellest läbi.'''
        # Lahkuvate sõidukite joon
        cv2.line(img, (outgoing_line_dimensions[0], outgoing_line_dimensions[1]), 
                (outgoing_line_dimensions[2], outgoing_line_dimensions[3]), 
                (255,0,0), 5)

        # Sissetulevate sõidukite joon
        cv2.line(img, (incoming_line_dimensions[0], incoming_line_dimensions[1]), 
                (incoming_line_dimensions[2], incoming_line_dimensions[3]), 
                (255,0,0), 5)

        # VEOAUTODE jälgimine
        for truck_tracker_result in truck_tracker_results:
            x1, y1, x2, y2, truck_tracking_id = truck_tracker_result
        
            center_x, center_y = draw_tracked_object(img,x1,y1,x2,y2,truck_tracking_id,(255,0,0), 1)
        
            check_and_append_tracking_id(outgoing_line_dimensions, 15, 
                                        vehicles['outgoing']['truck'], 'truck', center_x,
                                        center_y, truck_tracking_id, img)
            
            check_and_append_tracking_id(incoming_line_dimensions, 15, 
                                        vehicles['incoming']['truck'], 'truck', center_x,
                                        center_y, truck_tracking_id, img)

        # SÕIDUAUTODE jälgimine
        for car_tracker_result in car_tracker_results:
                x1, y1, x2, y2, car_tracking_id = car_tracker_result
                
                center_x, center_y = draw_tracked_object(img,x1,y1,x2,y2,car_tracking_id,(255,0,0), 1)

                check_and_append_tracking_id(outgoing_line_dimensions, 15, 
                                        vehicles['outgoing']['car'], 'car', center_x,
                                        center_y, car_tracking_id, img)
                
                check_and_append_tracking_id(incoming_line_dimensions, 15, 
                                        vehicles['incoming']['car'], 'car', center_x,
                                        center_y, car_tracking_id, img)

        # Näitab loendatud sõidukite arvu kaadris
        display_vehicle_count(img, f'Lahkuvate veoautode arv: {len(vehicles["outgoing"]["truck"])}', (50, 100))
        display_vehicle_count(img, f'Sissetulevate veoautode arv: {len(vehicles["incoming"]["truck"])}', (950, 100))
        display_vehicle_count(img, f'Lahkuvate autode arv: {len(vehicles["outgoing"]["car"])}', (50, 50))
        display_vehicle_count(img, f'Sissetulevate autode arv: {len(vehicles["incoming"]["car"])}', (950, 50))

        # Näitab videoedastus ekraanil
        cv2.imshow("Image", img)

        # Videoedastuse lõpetamine Q klahviga
        q = cv2.waitKey(1) & 0xFF
        if q == ord('q'):
            stop_flag = True
            break

