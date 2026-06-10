# app/ai/detection/detector.py

import cv2
import numpy as np
import os

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "yolov8n.onnx")

# Maximum image dimension to prevent OOM on Raspberry Pi
MAX_DIMENSION = 1280


class ObjectDetector:
    _instance = None

    # Full standard COCO classes
    CLASSES = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
        "truck", "boat", "traffic light", "fire hydrant", "stop sign",
        "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
        "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
        "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
        "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
        "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
        "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
        "couch", "potted plant", "bed", "dining table", "toilet", "tv",
        "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
        "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
        "scissors", "teddy bear", "hair drier", "toothbrush"
    ]

    AGRICULTURAL_CLASSES = {
        # Safety
        "person",

        # Livestock
        "bird",
        "cat",
        "dog",
        "horse",
        "sheep",
        "cow",
        "elephant",
        "bear",
        "zebra",
        "giraffe",

        # Vehicles/obstacles
        "bicycle",
        "motorcycle",
        "truck",
        "bus",

        # Produce / vegetation
        "potted plant",
        "broccoli",
        "carrot",
        "apple",
        "banana",
        "orange",
        "bowl",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.net = None
        return cls._instance

    def load(self):
        if self.net is None:
            print(f"Loading YOLOv8n ONNX from {MODEL_PATH}...")
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(
                    f"ONNX model not found at {MODEL_PATH}. "
                    f"Export yolov8n.pt to ONNX on your laptop and copy it to the project root."
                )
            self.net = cv2.dnn.readNetFromONNX(MODEL_PATH)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            print("Model loaded successfully.")

    def _resize_if_needed(self, frame):
        """Resize frame if it exceeds MAX_DIMENSION to prevent OOM."""
        h, w = frame.shape[:2]
        max_dim = max(h, w)
        if max_dim > MAX_DIMENSION:
            scale = MAX_DIMENSION / max_dim
            new_w = int(w * scale)
            new_h = int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return frame

    def detect(self, frame, conf_threshold=0.35, nms_threshold=0.4):
        self.load()

        # Resize large frames to prevent memory issues on Raspberry Pi
        frame = self._resize_if_needed(frame)

        orig_h, orig_w = frame.shape[:2]

        # Preprocess
        blob = cv2.dnn.blobFromImage(frame,
                                     1 / 255.0, (640, 640),
                                     swapRB=True,
                                     crop=False)
        self.net.setInput(blob)

        # Forward pass
        output = self.net.forward()[0]  # (84, 8400)
        output = output.T  # (8400, 84)

        boxes = []
        confidences = []
        class_ids = []

        for det in output:
            scores = det[4:]  # 80 class scores
            cls_id = int(scores.argmax())
            confidence = float(scores[cls_id])

            if confidence < conf_threshold:
                continue

            label = self.CLASSES[cls_id]
            if label not in self.AGRICULTURAL_CLASSES:
                continue

            # Box coordinates are center-x, center-y, width, height (normalized to 640)
            cx, cy, w, h = det[:4]
            x1 = int((cx - w / 2) * orig_w / 640)
            y1 = int((cy - h / 2) * orig_h / 640)
            bw = int(w * orig_w / 640)
            bh = int(h * orig_h / 640)

            boxes.append([x1, y1, bw, bh])
            confidences.append(confidence)
            class_ids.append(cls_id)

        # Apply NMS to remove overlapping boxes for the same object
        detections = []
        if boxes:
            indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold,
                                       nms_threshold)
            if len(indices) > 0:
                for i in indices.flatten():
                    detections.append({
                        "label": self.CLASSES[class_ids[i]],
                        "confidence": round(confidences[i], 3),
                        "box": {
                            "x": boxes[i][0],
                            "y": boxes[i][1],
                            "width": boxes[i][2],
                            "height": boxes[i][3],
                        }
                    })

        return detections