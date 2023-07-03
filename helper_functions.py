import cv2
import time
import json
import threading
import psycopg2
from os import path
from config import config

def check_and_append_tracking_id(
            line_list, line_list_offset, passed_vehicle_dict, vehicle_type,
            tracked_object_center_x, tracked_object_center_y, 
            tracked_object_id, frame
            ):
        '''Kontrollib, kas jälgitav objekt on joonistatud joone lähedal.
        Kui on piisavalt lähedal siis lisab objekti listi. Kui objekt lisatakse
        listi siis joonistakse joon üle rohelise värviga, mis annab märku, et
        objekt on lisatud.'''
        if line_list[0] < tracked_object_center_x < line_list[2] and \
            line_list[1] - line_list_offset < tracked_object_center_y < \
            line_list[3] + line_list_offset:
            if tracked_object_id not in passed_vehicle_dict:
                    passed_vehicle_dict.append(tracked_object_id)
                    passed_vehicle_dict.append({
                           'vehicle_type': str(vehicle_type),
                           'time': time.strftime("'%d-%m-%Y %H:%M:%S'")
                           })                 

                    cv2.line(frame, (line_list[0], line_list[1]), 
                    (line_list[2], line_list[3]), 
                    (0,255,0), 5)

def draw_tracked_object(img, x1, y1, x2, y2, tracking_id, color, line_thickness):
    '''Joonistab jälgitavale objektile ümbritseva kasti ja objekti keskele punkti.
    Tagastab objekti keskpunkti koordinaadid.'''
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    w, h = x2 - x1, y2 - y1

    # Jälgitava objekti ümbritsev kast ja selle ID näitamine
    cv2.rectangle(img, (x1, y1), (x2, y2), color, line_thickness)
    cv2.putText(img, str(int(tracking_id)),
                (max(0, x1), max(35, y2)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (36, 266, 12), 2)

    # Jälgitava objekti keskpunkti leidmine ning selle lisamine kaadrisse
    center_x, center_y = x1 + w // 2, y1 + h // 2
    cv2.circle(img, (center_x, center_y), 5, (255, 0, 255), cv2.FILLED)

    return center_x, center_y

def display_vehicle_count(img, count, position):
    '''Lisab kaadrisse loendatud sõidukite teksti.'''
    cv2.putText(img, count,
        position,
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
def create_file_path(output_path, file_format):
    '''Loob ajatempliga failile aadressi.'''
    file_path = output_path + "LOG-" + str(time.strftime("%d_%m_%Y") + file_format)
    return file_path 
         
def save_data_to_txt(output_path, vehicles_dict):
    '''Salvestab sõidukite liikumiste andmed teksti faili.'''
    text_file = create_file_path(output_path, '.txt')
    with open(text_file, 'w+') as file:
        for direction, vehicle_types in vehicles_dict.items():            
            # Sõiduki suunad
            file.write(f"{direction.capitalize()} vehicles:\n")
            for vehicle_type, data in vehicle_types.items():
                if isinstance(data, list):
                    for item in data:
                        # Sõiduki tüüp ja kellaaeg
                        if isinstance(item, dict):
                            file.write(f"    Vehicle type: {item['vehicle_type'].title()}\n")
                            file.write(f"    Time: {item['time']}\n")
                        else:
                            # Sõiduki ID 
                            file.write(f"  Vehicle ID: {int(item)}\n")
                file.write("\n")

def save_data_to_json(output_path, vehicles_dict):
    '''Salvestab sõidukite liikumiste andmed json faili'''
    json_file = create_file_path(output_path, '.json')
    json_data = json.dumps(vehicles_dict, indent=4)
    with open(json_file, 'w') as file:
            file.write(json_data)
            
def save_text_periodically(output_file_path, vehicles_dict, flag, interval = 60):
    '''Salvestab sõidukite liikumised teksti faili perioodiliselt. Kasutada
    eraldi lõimus.'''
    while not flag:
        save_data_to_txt(output_file_path, vehicles_dict)
        time.sleep(interval)
  
def save_json_periodically(output_file_path, vehicles_dict, flag, interval = 60):
    '''Salvestab sõidukite liikumised json faili perioodiliselt. Kasutada
    eraldi lõimus.'''
    while not flag:
        save_data_to_json(output_file_path, vehicles_dict)
        time.sleep(interval)

def insert_data_to_database(vehicles_dict):
    '''Salvestab sõidukite liikumised postgreSQL andmebaasi'''
    connection = None
    try:
        params = config()
        print("Connecting to the postgreSQL database...")
        connection = psycopg2.connect(**params)

        
        cur = connection.cursor()

        # Sõnastiku sisaldava informatsiooni edastamine andmebaasi
        for direction, vehicle_types in vehicles_dict.items():            
            for vehicle_type, data in vehicle_types.items():
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            _type = item['vehicle_type']
                            _datetime = item['time']
                        else:
                            _id = int(item)                   
                    insert_script = f"INSERT INTO vehicle (id, direction, vehicle_type, datetime)" "VALUES ({_id}, '{str(direction)}', '{str(_type)}', {_datetime}) ON CONFLICT DO NOTHING"
                    cur.execute(insert_script)

        connection.commit()
        cur.close()
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if connection is not None:
            connection.close()
            print("Database connection terminated.")

def insert_data_periodically(vehicle_dict, flag, interval = 60):
    '''Salvestab sõidukite liikumised andmebaasi perioodiliselt. Kasutada
    eraldi lõimus.'''
    while not flag:
        insert_data_to_database(vehicle_dict)
        time.sleep(interval)

def create_vehicle_dictionary():
    '''Loob sõidukite sõnastiku'''
    vehicle_dict = {
        'incoming': {
            'car': [],
            'truck': []
        },
        'outgoing': {
            'car': [],
            'truck': []
        }
    }

    return vehicle_dict
     