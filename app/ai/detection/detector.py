# app/ai/detection/detector.py
# Singleton object detector using YOLOv8n (NCNN) for efficient inference on Raspberry Pi.

import os
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "yolov8n_ncnn_model")


class ObjectDetector:
    """Singleton class for object detection using YOLOv8n (NCNN)"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model = None  # don't load yet
        return cls._instance
    
    def load(self):
        if self.model is None:
            print(f"Loading YOLOv8n NCNN model from {MODEL_PATH}...")
            self.model = YOLO(MODEL_PATH)
            print("Model loaded.")
    
    def detect(self, frame):
        self.load()
        
        results = self.model(frame, verbose=False)
        
        detections = []
        
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                detections.append({
                    "label": result.names[cls_id],
                    "confidence": round(confidence, 3)
                })
                
        return detections