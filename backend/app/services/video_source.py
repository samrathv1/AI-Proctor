import abc
import asyncio
import os
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import cv2
import numpy as np

from backend.app.core.logging import logger
from backend.app.core.config import settings


class FramePacket:
    """
    Standardized Normalized Frame Container for Downstream AI Processing.
    Every video input source (Webcam, IP/CCTV RTSP, Recorded MP4) must wrap
    extracted imagery into this standardized data structure.
    """
    def __init__(
        self,
        frame: np.ndarray,
        source_id: str,
        source_type: str,  # WEBCAM | IP_CAMERA | RECORDED_VIDEO
        timestamp: Optional[datetime] = None,
        frame_number: Optional[int] = None,
        resolution: Optional[Tuple[int, int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.frame = frame
        self.source_id = source_id
        self.source_type = source_type
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.frame_number = frame_number
        if resolution is not None:
            self.resolution = resolution
        elif frame is not None and len(frame.shape) >= 2:
            self.resolution = (frame.shape[1], frame.shape[0])
        else:
            self.resolution = (0, 0)
        self.metadata = metadata or {}

    @property
    def width(self) -> int:
        return self.resolution[0]

    @property
    def height(self) -> int:
        return self.resolution[1]


class BoundedFrameBuffer:
    """
    Latest-Frame-Wins Dropping Queue / Ring Buffer.
    
    BACKPRESSURE ARCHITECTURE:
    When the camera streams at 30 FPS but CPU AI processing throughput is ~4.1 FPS (242 ms),
    storing all incoming frames causes queue explosion and minutes of observation latency.
    This bounded buffer holds strictly ONE latest frame.
    Whenever a newer frame arrives while the previous frame is still being processed,
    the stale intermediate frames are safely dropped, guaranteeing zero stale latency.
    """
    def __init__(self, capacity: int = 1):
        self.capacity = max(1, capacity)
        self._latest_packet: Optional[FramePacket] = None
        self._lock = asyncio.Lock()
        self.frames_captured: int = 0
        self.frames_processed: int = 0
        self.frames_dropped: int = 0
        self._last_capture_time: float = time.time()
        self._last_process_time: float = time.time()
        self.capture_fps: float = 0.0
        self.processing_fps: float = 0.0

    async def put(self, packet: FramePacket) -> bool:
        """Puts a frame packet into the buffer. Drops previous unprocessed packet if present."""
        async with self._lock:
            now = time.time()
            dt = now - self._last_capture_time
            if dt > 0:
                instant_fps = 1.0 / dt
                self.capture_fps = round(0.9 * self.capture_fps + 0.1 * instant_fps, 1)
            self._last_capture_time = now

            self.frames_captured += 1
            was_dropped = False
            if self._latest_packet is not None:
                self.frames_dropped += 1
                was_dropped = True

            self._latest_packet = packet
            return was_dropped

    async def get_latest(self) -> Optional[FramePacket]:
        """Pulls the latest available frame. Clears buffer."""
        async with self._lock:
            if self._latest_packet is None:
                return None
            pkt = self._latest_packet
            self._latest_packet = None

            now = time.time()
            dt = now - self._last_process_time
            if dt > 0:
                instant_fps = 1.0 / dt
                self.processing_fps = round(0.9 * self.processing_fps + 0.1 * instant_fps, 1)
            self._last_process_time = now
            self.frames_processed += 1
            return pkt

    def peek(self) -> Optional[FramePacket]:
        return self._latest_packet

    def get_stats(self) -> Dict[str, Any]:
        return {
            "frames_captured": self.frames_captured,
            "frames_processed": self.frames_processed,
            "frames_dropped": self.frames_dropped,
            "queue_depth": 1 if self._latest_packet is not None else 0,
            "capture_fps": self.capture_fps,
            "processing_fps": self.processing_fps,
        }

    def clear(self):
        self._latest_packet = None
        self.frames_captured = 0
        self.frames_processed = 0
        self.frames_dropped = 0


class VideoSource(abc.ABC):
    """
    Abstract Common Base Class for all video input modalities.
    """
    def __init__(self, source_id: str, source_type: str):
        self.source_id = source_id
        self.source_type = source_type
        self.status = "OFFLINE"  # CONNECTING | ONLINE | OFFLINE | ERROR | RECONNECTING
        self.last_seen_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.buffer = BoundedFrameBuffer(capacity=1)

    @abc.abstractmethod
    async def connect(self) -> bool:
        """Establish connection or initialize video capture."""
        pass

    @abc.abstractmethod
    async def read_frame(self) -> Optional[FramePacket]:
        """Read normalized frame packet from stream/source."""
        pass

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Release underlying hardware, network socket, or file descriptor."""
        pass

    def get_status(self) -> str:
        return self.status

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "status": self.status,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "error_message": self.error_message,
            "buffer_stats": self.buffer.get_stats()
        }


class WebcamSource(VideoSource):
    """
    Laptop/Desktop Browser Webcam Stream Ingestion.
    Supports either browser-transported Base64/JPEG frames (WebRTC / HTML5 Canvas),
    or local OpenCV VideoCapture hardware access (device index 0, 1, etc.).
    """
    def __init__(self, source_id: str = "webcam-01", device_index: Optional[int] = None):
        super().__init__(source_id, "WEBCAM")
        self.device_index = device_index
        self._cap: Optional[cv2.VideoCapture] = None
        self.frame_counter: int = 0

    async def connect(self) -> bool:
        self.status = "CONNECTING"
        if self.device_index is not None:
            try:
                # Local device capture
                self._cap = cv2.VideoCapture(self.device_index)
                if not self._cap.isOpened():
                    self.status = "ERROR"
                    self.error_message = f"Failed to open webcam device at index {self.device_index}"
                    return False
                self.status = "ONLINE"
                self.last_seen_at = datetime.now(timezone.utc)
                logger.info(f"Webcam hardware device {self.device_index} connected.")
                return True
            except Exception as e:
                self.status = "ERROR"
                self.error_message = str(e)
                return False
        else:
            # Client push / browser transport mode
            self.status = "ONLINE"
            self.last_seen_at = datetime.now(timezone.utc)
            return True

    async def ingest_client_frame(self, frame_bgr: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Ingests frame received from browser client into bounded buffer with backpressure."""
        self.frame_counter += 1
        self.last_seen_at = datetime.now(timezone.utc)
        packet = FramePacket(
            frame=frame_bgr,
            source_id=self.source_id,
            source_type=self.source_type,
            timestamp=self.last_seen_at,
            frame_number=self.frame_counter,
            metadata=metadata
        )
        return await self.buffer.put(packet)

    async def read_frame(self) -> Optional[FramePacket]:
        if self.device_index is not None and self._cap is not None:
            ret, frame = self._cap.read()
            if not ret or frame is None:
                self.status = "ERROR"
                self.error_message = "Webcam frame read returned false"
                return None
            self.frame_counter += 1
            self.last_seen_at = datetime.now(timezone.utc)
            packet = FramePacket(
                frame=frame,
                source_id=self.source_id,
                source_type=self.source_type,
                timestamp=self.last_seen_at,
                frame_number=self.frame_counter
            )
            await self.buffer.put(packet)
            return await self.buffer.get_latest()
        else:
            # Pull latest ingested frame from browser client
            return await self.buffer.get_latest()

    async def disconnect(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self.status = "OFFLINE"
        self.buffer.clear()
        logger.info(f"Webcam source {self.source_id} disconnected.")


class IPCameraSource(VideoSource):
    """
    RTSP / IP Camera / CCTV Stream Source Adapter.
    
    SECURITY ARCHITECTURE:
    RTSP connection credentials (username, password, port) are kept strictly on the backend.
    Never exposed to frontend browser clients or Next.js public variables.
    
    RESILIENCE:
    Implements bounded exponential backoff reconnection on network timeouts or RTSP packet drops.
    """
    def __init__(
        self,
        source_id: str,
        rtsp_url: str,
        reconnect_attempts: int = 5,
        base_backoff_seconds: float = 1.0
    ):
        super().__init__(source_id, "IP_CAMERA")
        self._rtsp_url = rtsp_url
        self.reconnect_attempts = reconnect_attempts
        self.base_backoff_seconds = base_backoff_seconds
        self._cap: Optional[cv2.VideoCapture] = None
        self._ingestion_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self.frame_counter: int = 0
        self.consecutive_failures: int = 0

    async def connect(self) -> bool:
        self.status = "CONNECTING"
        self.error_message = None
        logger.info(f"Connecting to IP Camera '{self.source_id}' at RTSP endpoint.")

        # OpenCV VideoCapture with TCP transport preference to avoid UDP packet loss
        try:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            self._cap = cv2.VideoCapture(self._rtsp_url, cv2.CAP_FFMPEG)
            if not self._cap.isOpened():
                self.status = "ERROR"
                self.error_message = "Failed to establish RTSP socket connection"
                logger.warning(f"IP Camera '{self.source_id}' connection failed: {self.error_message}")
                return False

            self.status = "ONLINE"
            self.last_seen_at = datetime.now(timezone.utc)
            self.consecutive_failures = 0
            self._running = True

            # Launch background ingestion loop to prevent internal RTSP buffer lag
            self._ingestion_task = asyncio.create_task(self._background_capture_loop())
            logger.info(f"IP Camera '{self.source_id}' successfully connected and online.")
            return True
        except Exception as e:
            self.status = "ERROR"
            self.error_message = str(e)
            logger.error(f"IP Camera '{self.source_id}' unexpected connect exception: {str(e)}")
            return False

    async def _background_capture_loop(self):
        """Continuously clears the hardware/OpenCV buffer and puts newest frame in buffer."""
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                await self._attempt_reconnect()
                continue

            try:
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    self.consecutive_failures += 1
                    logger.warning(
                        f"IP Camera '{self.source_id}' frame read dropped (consecutive: {self.consecutive_failures})"
                    )
                    if self.consecutive_failures >= 3:
                        await self._attempt_reconnect()
                    else:
                        await asyncio.sleep(0.05)
                    continue

                self.consecutive_failures = 0
                self.frame_counter += 1
                self.last_seen_at = datetime.now(timezone.utc)
                packet = FramePacket(
                    frame=frame,
                    source_id=self.source_id,
                    source_type=self.source_type,
                    timestamp=self.last_seen_at,
                    frame_number=self.frame_counter
                )
                await self.buffer.put(packet)
                # Yield control to event loop
                await asyncio.sleep(0.005)
            except Exception as e:
                logger.error(f"Error in IP camera background capture loop: {str(e)}")
                await asyncio.sleep(0.5)

    async def _attempt_reconnect(self):
        """Bounded exponential backoff reconnection."""
        self.status = "RECONNECTING"
        if self._cap is not None:
            self._cap.release()
            self._cap = None

        for attempt in range(1, self.reconnect_attempts + 1):
            if not self._running:
                break
            backoff = min(16.0, self.base_backoff_seconds * (2 ** (attempt - 1)))
            logger.info(
                f"IP Camera '{self.source_id}' reconnecting (attempt {attempt}/{self.reconnect_attempts}) in {backoff:.1f}s..."
            )
            await asyncio.sleep(backoff)

            try:
                self._cap = cv2.VideoCapture(self._rtsp_url, cv2.CAP_FFMPEG)
                if self._cap.isOpened():
                    self.status = "ONLINE"
                    self.last_seen_at = datetime.now(timezone.utc)
                    self.consecutive_failures = 0
                    logger.info(f"IP Camera '{self.source_id}' reconnected successfully.")
                    return
            except Exception as e:
                self.error_message = f"Reconnect attempt {attempt} error: {str(e)}"

        self.status = "OFFLINE"
        self.error_message = f"Max reconnection attempts ({self.reconnect_attempts}) exhausted."
        logger.error(f"IP Camera '{self.source_id}' went OFFLINE. {self.error_message}")

    async def read_frame(self) -> Optional[FramePacket]:
        """Pulls the latest available frame from the bounded dropping buffer."""
        return await self.buffer.get_latest()

    async def disconnect(self) -> None:
        self._running = False
        if self._ingestion_task is not None:
            self._ingestion_task.cancel()
            self._ingestion_task = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self.status = "OFFLINE"
        self.buffer.clear()
        logger.info(f"IP Camera '{self.source_id}' disconnected.")


class RecordedVideoSource(VideoSource):
    """
    Examination Recorded Video Reader (MP4, AVI, MOV).
    Supports offline examination review and asynchronous background proctoring.
    Tracks frame positions, total duration, processing percentage, and timestamps.
    """
    def __init__(self, source_id: str, file_path: str):
        super().__init__(source_id, "RECORDED_VIDEO")
        self.file_path = file_path
        self._cap: Optional[cv2.VideoCapture] = None
        self.total_frames: int = 0
        self.fps: float = 30.0
        self.duration_seconds: float = 0.0
        self.current_frame_index: int = 0
        self.start_wall_time: float = 0.0

    async def connect(self) -> bool:
        self.status = "CONNECTING"
        if not os.path.exists(self.file_path):
            self.status = "ERROR"
            self.error_message = f"Recorded video file not found at: {self.file_path}"
            logger.error(self.error_message)
            return False

        try:
            self._cap = cv2.VideoCapture(self.file_path)
            if not self._cap.isOpened():
                self.status = "ERROR"
                self.error_message = f"Failed to open recorded video file: {self.file_path}"
                return False

            self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = float(self._cap.get(cv2.CAP_PROP_FPS))
            if self.fps <= 0 or np.isnan(self.fps):
                self.fps = 30.0
            self.duration_seconds = round(self.total_frames / self.fps, 2) if self.fps > 0 else 0.0

            self.status = "ONLINE"
            self.current_frame_index = 0
            self.start_wall_time = time.time()
            self.last_seen_at = datetime.now(timezone.utc)
            logger.info(
                f"Recorded Video '{self.source_id}' opened: {self.total_frames} frames, "
                f"{self.fps:.1f} FPS, {self.duration_seconds}s duration."
            )
            return True
        except Exception as e:
            self.status = "ERROR"
            self.error_message = str(e)
            return False

    async def read_frame(self) -> Optional[FramePacket]:
        if self._cap is None or not self._cap.isOpened():
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            self.status = "COMPLETED"
            return None

        self.current_frame_index += 1
        self.last_seen_at = datetime.now(timezone.utc)
        current_msec = self._cap.get(cv2.CAP_PROP_POS_MSEC)
        current_timestamp_seconds = round(current_msec / 1000.0, 2)

        packet = FramePacket(
            frame=frame,
            source_id=self.source_id,
            source_type=self.source_type,
            timestamp=self.last_seen_at,
            frame_number=self.current_frame_index,
            metadata={
                "current_timestamp_seconds": current_timestamp_seconds,
                "duration_seconds": self.duration_seconds,
                "progress_percentage": round((self.current_frame_index / max(1, self.total_frames)) * 100, 1),
                "total_frames": self.total_frames
            }
        )
        return packet

    @property
    def progress_percentage(self) -> float:
        if self.total_frames <= 0:
            return 0.0
        return round((self.current_frame_index / self.total_frames) * 100.0, 2)

    @property
    def current_timestamp_seconds(self) -> float:
        if self.fps <= 0:
            return 0.0
        return round(self.current_frame_index / self.fps, 2)

    def get_metadata(self) -> Dict[str, Any]:
        base = super().get_metadata()
        base.update({
            "file_name": os.path.basename(self.file_path),
            "file_path": self.file_path,
            "total_frames": self.total_frames,
            "fps": self.fps,
            "duration_seconds": self.duration_seconds,
            "current_frame_index": self.current_frame_index,
            "progress_percentage": self.progress_percentage,
            "current_timestamp_seconds": self.current_timestamp_seconds,
            "resolution": (
                int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            ) if self._cap and self._cap.isOpened() else (0, 0)
        })
        return base

    async def disconnect(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self.status = "OFFLINE"
        logger.info(f"Recorded video source '{self.source_id}' closed.")
