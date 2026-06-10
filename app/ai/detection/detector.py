# app/ai/detection/detector.py
# Object detection with YOLOv8n — agricultural focus
# Enhanced with comprehensive debug logging for troubleshooting

import cv2
import numpy as np
import os
import time
import traceback

from app.services.data_logger import data_logger

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
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear",
        "zebra", "giraffe",
        # Vehicles/obstacles
        "bicycle", "motorcycle", "truck", "bus",
        # Produce / vegetation
        "potted plant", "broccoli", "carrot", "apple", "banana", "orange",
        "bowl",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.net = None
        return cls._instance

    def load(self):
        if self.net is not None:
            data_logger.debug("ObjectDetector: model already loaded, skipping", component="detector")
            return

        data_logger.info(f"ObjectDetector: loading YOLOv8n ONNX from {MODEL_PATH}", component="detector")

        if not os.path.exists(MODEL_PATH):
            data_logger.critical(
                f"ObjectDetector: ONNX model not found at {MODEL_PATH}. "
                f"Export yolov8n.pt to ONNX and copy to project root.",
                component="detector"
            )
            raise FileNotFoundError(
                f"ONNX model not found at {MODEL_PATH}. "
                f"Export yolov8n.pt to ONNX on your laptop and copy it to the project root."
            )

        t0 = time.time()
        try:
            self.net = cv2.dnn.readNetFromONNX(MODEL_PATH)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            elapsed = (time.time() - t0) * 1000
            data_logger.info(
                f"ObjectDetector: model loaded successfully in {elapsed:.0f}ms",
                component="detector"
            )
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            data_logger.error(
                f"ObjectDetector: model load failed after {elapsed:.0f}ms: {e}",
                component="detector",
                details=traceback.format_exc()
            )
            raise

    def _resize_if_needed(self, frame):
        """Resize frame if it exceeds MAX_DIMENSION to prevent OOM."""
        h, w = frame.shape[:2]
        max_dim = max(h, w)
        if max_dim > MAX_DIMENSION:
            scale = MAX_DIMENSION / max_dim
            new_w = int(w * scale)
            new_h = int(h * scale)
            data_logger.debug(
                f"ObjectDetector: resizing frame from {w}x{h} to {new_w}x{new_h} "
                f"(max_dim={max_dim} > {MAX_DIMENSION})",
                component="detector"
            )
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return frame

    def detect(self, frame, conf_threshold=0.35, nms_threshold=0.4):
        t_start = time.time()
        data_logger.debug(
            f"ObjectDetector.detect: input frame shape={frame.shape}, "
            f"dtype={frame.dtype}, conf={conf_threshold}, nms={nms_threshold}",
            component="detector"
        )

        # Load model
        try:
            self.load()
        except Exception as e:
            data_logger.error(
                f"ObjectDetector.detect: model load failed: {e}",
                component="detector",
                details=traceback.format_exc()
            )
            raise

        # Resize large frames
        t_resize = time.time()
        frame = self._resize_if_needed(frame)
        resized_h, resized_w = frame.shape[:2]
        data_logger.debug(
            f"ObjectDetector.detect: after resize {resized_w}x{resized_h} "
            f"({(time.time()-t_resize)*1000:.1f}ms)",
            component="detector"
        )

        orig_h, orig_w = frame.shape[:2]

        # Preprocess
        t_preprocess = time.time()
        try:
            blob = cv2.dnn.blobFromImage(frame,
                                         1 / 255.0, (640, 640),
                                         swapRB=True,
                                         crop=False)
            self.net.setInput(blob)
            data_logger.debug(
                f"ObjectDetector.detect: blob shape={blob.shape}, "
                f"preprocess took {(time.time()-t_preprocess)*1000:.1f}ms",
                component="detector"
            )
        except Exception as e:
            data_logger.error(
                f"ObjectDetector.detect: preprocess failed: {e}",
                component="detector",
                details=traceback.format_exc()
            )
            raise

        # Forward pass
        t_forward = time.time()
        try:
            output = self.net.forward()[0]  # (84, 8400)
            output = output.T  # (8400, 84)
            forward_ms = (time.time() - t_forward) * 1000
            data_logger.debug(
                f"ObjectDetector.detect: forward pass output shape={output.shape}, "
                f"took {forward_ms:.1f}ms",
                component="detector"
            )
        except Exception as e:
            data_logger.error(
                f"ObjectDetector.detect: forward pass failed: {e}",
                component="detector",
                details=traceback.format_exc()
            )
            raise

        # Parse detections
        t_parse = time.time()
        boxes = []
        confidences = []
        class_ids = []
        raw_candidates = 0
        skipped_low_conf = 0
        skipped_non_agri = 0

        for det in output:
            scores = det[4:]  # 80 class scores
            cls_id = int(scores.argmax())
            confidence = float(scores[cls_id])

            if confidence < conf_threshold:
                skipped_low_conf += 1
                continue

            label = self.CLASSES[cls_id]
            if label not in self.AGRICULTURAL_CLASSES:
                skipped_non_agri += 1
                continue

            raw_candidates += 1

            # Box coordinates are center-x, center-y, width, height (normalized to 640)
            cx, cy, w, h = det[:4]
            x1 = int((cx - w / 2) * orig_w / 640)
            y1 = int((cy - h / 2) * orig_h / 640)
            bw = int(w * orig_w / 640)
            bh = int(h * orig_h / 640)

            boxes.append([x1, y1, bw, bh])
            confidences.append(confidence)
            class_ids.append(cls_id)

        parse_ms = (time.time() - t_parse) * 1000
        data_logger.debug(
            f"ObjectDetector.detect: parsed {raw_candidates} agri candidates "
            f"(skipped {skipped_low_conf} low-conf, {skipped_non_agri} non-agri) "
            f"in {parse_ms:.1f}ms",
            component="detector"
        )

        # Apply NMS
        detections = []
        if boxes:
            t_nms = time.time()
            try:
                indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold,
                                           nms_threshold)
                nms_ms = (time.time() - t_nms) * 1000
                nms_count = len(indices) if len(indices) > 0 else 0
                data_logger.debug(
                    f"ObjectDetector.detect: NMS reduced {len(boxes)} -> {nms_count} "
                    f"detections in {nms_ms:.1f}ms",
                    component="detector"
                )
                if nms_count > 0:
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
            except Exception as e:
                nms_ms = (time.time() - t_nms) * 1000
                data_logger.error(
                    f"ObjectDetector.detect: NMS failed after {nms_ms:.1f}ms: {e}. "
                    f"Boxes count={len(boxes)}, confidences count={len(confidences)}",
                    component="detector",
                    details=traceback.format_exc()
                )
                raise
        else:
            data_logger.debug(
                "ObjectDetector.detect: no boxes to run NMS on",
                component="detector"
            )

        total_ms = (time.time() - t_start) * 1000
        data_logger.info(
            f"ObjectDetector.detect: completed in {total_ms:.1f}ms — "
            f"{len(detections)} detections: "
            f"{[d['label'] + '(' + str(d['confidence']) + ')' for d in detections]}",
            component="detector"
        )

        return detections