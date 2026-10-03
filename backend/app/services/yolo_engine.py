import os
import time
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
import onnxruntime as ort

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.responses import BoundingBox


# Standard COCO 80 Class Names
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush"
]

# Examination Surveillance Specific Mapping
EXAM_OBJECT_MAPPING = {
    "cell phone": "MOBILE_PHONE",
    "laptop": "LAPTOP",
    "book": "BOOK",
    "backpack": "UNAUTHORIZED_OBJECT",
    "handbag": "UNAUTHORIZED_OBJECT",
    "scissors": "UNAUTHORIZED_OBJECT",
    "person": "PERSON"
}


class DetectedObject:
    def __init__(
        self,
        class_id: int,
        label: str,
        detection_type: str,
        confidence: float,
        bbox_norm: BoundingBox,
        bbox_abs: Tuple[int, int, int, int]
    ):
        self.class_id = class_id
        self.label = label
        self.detection_type = detection_type
        self.confidence = float(confidence)
        self.bbox = bbox_norm
        self.raw_box = bbox_abs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_type": self.detection_type,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "bounding_box": {
                "x": self.bbox.x,
                "y": self.bbox.y,
                "width": self.bbox.width,
                "height": self.bbox.height
            },
            "raw_box": {
                "x": self.raw_box[0],
                "y": self.raw_box[1],
                "width": self.raw_box[2],
                "height": self.raw_box[3]
            }
        }


class YoloEngine:
    """
    High-Performance YOLOv8 Object Detection Engine for Examination Surveillance.
    Executes ONNX Runtime inference targeting observable exam-relevant objects:
    Mobile phones, laptops, books/notes, and persons.
    Strictly reports factual observations without declaring subjective intent.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.YOLO_MODEL_PATH
        self.session: Optional[ort.InferenceSession] = None
        self.input_name: str = "images"
        self.output_name: str = "output0"
        self.input_size: int = settings.YOLO_INPUT_SIZE
        self._init_session()

    def _init_session(self):
        if not os.path.exists(self.model_path):
            logger.warning(f"YOLO ONNX model not found at {self.model_path}. Running in mock/fallback mode.")
            return

        try:
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=opts,
                providers=["CPUExecutionProvider"]
            )
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            logger.info(f"YOLO ONNX model initialized from {self.model_path} on CPUExecutionProvider.")
        except Exception as e:
            logger.error(f"Failed to initialize YOLO ONNX Runtime session: {str(e)}")
            self.session = None

    def letterbox(
        self,
        img: np.ndarray,
        new_shape: Tuple[int, int] = (640, 640),
        color: Tuple[int, int, int] = (114, 114, 114)
    ) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        """Resizes and pads image to preserve aspect ratio for YOLO."""
        shape = img.shape[:2]  # [height, width]
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
        dw = (new_shape[1] - new_unpad[0]) / 2.0
        dh = (new_shape[0] - new_unpad[1]) / 2.0

        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        return img, r, (dw, dh)

    def detect_objects(
        self,
        img: np.ndarray,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None,
        target_classes: Optional[List[str]] = None
    ) -> List[DetectedObject]:
        """
        Executes YOLO forward pass on decoded image.
        Extracts candidate objects and applies Non-Maximum Suppression (NMS).
        """
        if self.session is None or img is None or img.size == 0:
            return []

        conf_thresh = conf_threshold if conf_threshold is not None else settings.YOLO_CONFIDENCE_THRESHOLD
        iou_thresh = iou_threshold if iou_threshold is not None else settings.YOLO_IOU_THRESHOLD

        orig_h, orig_w = img.shape[:2]

        # 1. Preprocessing (Letterbox & Normalization)
        padded_img, ratio, (dw, dh) = self.letterbox(img, (self.input_size, self.input_size))
        blob = cv2.dnn.blobFromImage(padded_img, 1.0 / 255.0, (self.input_size, self.input_size), swapRB=True)

        # 2. Forward Inference
        outputs = self.session.run([self.output_name], {self.input_name: blob})
        # Output shape is [1, 84, 8400] -> transpose to [8400, 84]
        preds = np.transpose(outputs[0][0])

        boxes = []
        confidences = []
        class_ids = []

        # 3. Box Decoding & Confidence Filtering
        for row in preds:
            cx, cy, w, h = row[0:4]
            scores = row[4:]
            cid = int(np.argmax(scores))
            confidence = float(scores[cid])

            if confidence < conf_thresh:
                continue

            raw_label = COCO_CLASSES[cid] if cid < len(COCO_CLASSES) else f"class_{cid}"
            if target_classes and raw_label not in target_classes and cid not in [67, 63, 73, 0]:
                continue

            # Convert center (cx, cy, w, h) to corner (x1, y1, w, h) on unpadded image
            x1 = (cx - w / 2.0 - dw) / ratio
            y1 = (cy - h / 2.0 - dh) / ratio
            box_w = w / ratio
            box_h = h / ratio

            # Clamp coordinates to original image bounds
            x1 = max(0, min(orig_w - 1, x1))
            y1 = max(0, min(orig_h - 1, y1))
            box_w = max(1, min(orig_w - x1, box_w))
            box_h = max(1, min(orig_h - y1, box_h))

            boxes.append([int(x1), int(y1), int(box_w), int(box_h)])
            confidences.append(confidence)
            class_ids.append(cid)

        if len(boxes) == 0:
            return []

        # 4. Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_thresh, iou_thresh)
        if len(indices) == 0:
            return []

        results: List[DetectedObject] = []
        for idx in indices.flatten():
            bx, by, bw, bh = boxes[idx]
            cid = class_ids[idx]
            conf = confidences[idx]
            label = COCO_CLASSES[cid] if cid < len(COCO_CLASSES) else f"class_{cid}"
            det_type = EXAM_OBJECT_MAPPING.get(label, "OTHER")

            rel_box = BoundingBox(
                x=round(max(0.0, bx / orig_w), 3),
                y=round(max(0.0, by / orig_h), 3),
                width=round(min(1.0, bw / orig_w), 3),
                height=round(min(1.0, bh / orig_h), 3)
            )

            results.append(
                DetectedObject(
                    class_id=cid,
                    label=label,
                    detection_type=det_type,
                    confidence=conf,
                    bbox_norm=rel_box,
                    bbox_abs=(bx, by, bw, bh)
                )
            )

        return results


yolo_engine = YoloEngine()
