# app/ai/detection/detector.py
# Singleton object detector using YOLOv8m for efficient inference across the application.

from ultralytics import YOLO

class ObjectDetector:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            
            print("Loading YOLOv8 model...")
            cls._instance.model = YOLO("yolov8m.pt")
            
        return cls._instance
    
    def detect(self, image_path):
        results = self.model(image_path)
        
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
    
detector = ObjectDetector()