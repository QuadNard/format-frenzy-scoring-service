import json
import logging
from pathlib import Path
from datetime import datetime, timezone
import queue
from threading import Thread, Lock
from typing import Dict, Any, Optional
import time

# Configure standard logging for errors in the logger itself
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("error_logger")

# Configuration
class LogConfig:
    BASE_DIR = Path("logs")
    ERROR_LOG_NAME = "error_snippets_{date}.jsonl"
    MAX_LOG_SIZE_MB = 10
    MAX_LOG_FILES = 30
    BUFFER_SIZE = 100
    FLUSH_INTERVAL_SEC = 5

class ErrorLogger:
    def __init__(self, config: LogConfig = LogConfig()):
        self.config = config
        self.buffer = queue.Queue(maxsize=config.BUFFER_SIZE)
        self.lock = Lock()
        self.stop_requested = False
        # Create the directory structure
        self.config.BASE_DIR.mkdir(exist_ok=True, parents=True)
        # Start background processing thread
        self.worker_thread = Thread(target=self._process_buffer, daemon=True)
        self.worker_thread.start()
    def log_error(self, question_id: str, user_code: str, error_msg: str,
                  additional_context: Optional[Dict[str, Any]] = None) -> None:
        """
        Append a JSON-L entry whenever user_code fails parsing or runtime checks.
        
        Args:
            question_id: Identifier for the question/task
            user_code: The code submitted by the user
            error_msg: The error message generated
            additional_context: Optional dict with additional contextual information
        """
        try:
            # Create the log entry
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),# Z indicates UTC
                "question_id": question_id,
                "user_code": user_code,
                "error": error_msg
            }
            # Add additional context if provided
            if additional_context:
                entry["context"] = additional_context
            # Try to add to buffer, don't block if buffer is full
            try:
                self.buffer.put_nowait(entry)
            except queue.Full:
                # If buffer is full, write directly to disk as fallback
                logger.warning("Error log buffer full, writing directly to disk")
                self._write_entry_to_disk(entry)
        except ImportError as e:
            # Using lazy % formatting for logging
            logger.error("Failed to log error: %s", str(e))
    def _process_buffer(self) -> None:
        """Background thread that processes the buffer and writes to disk."""
        entries_to_write = []
        while not self.stop_requested:
            try:
                # Collect entries from the buffer
                while len(entries_to_write) < self.config.BUFFER_SIZE:
                    try:
                        entry = self.buffer.get(block=True, timeout=0.1)
                        entries_to_write.append(entry)
                        self.buffer.task_done()
                    except queue.Empty:
                        break
                # Write collected entries if we have any
                if entries_to_write:
                    with self.lock:
                        for entry in entries_to_write:
                            self._write_entry_to_disk(entry)
                    entries_to_write = []
                # Sleep a bit before next processing cycle
                time.sleep(self.config.FLUSH_INTERVAL_SEC)
            except ImportError as e:
                logger.error("Error in log processing thread: %s", str(e))
                time.sleep(1)  # Avoid tight loop in case of persistent errors
    def _write_entry_to_disk(self, entry: Dict[str, Any]) -> None:
        """Write a single entry to the appropriate log file with rotation."""
        try:
            # Get current log file path with date
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = self.config.BASE_DIR / self.config.ERROR_LOG_NAME.format(date=date_str)
            # Check if we need to rotate based on size
            if log_file.exists() and (log_file.stat().st_size > self.config.MAX_LOG_SIZE_MB
                                       * 1024 * 1024):
                # Add a timestamp to create a new rotated file
                timestamp = datetime.now().strftime("%H%M%S")
                log_file = self.config.BASE_DIR / f"error_snippets_{date_str}_{timestamp}.jsonl"
            # Write the entry
            with log_file.open("a") as f:
                f.write(json.dumps(entry) + "\n")
            # Clean up old log files if we exceed the maximum
            self._cleanup_old_logs()
        except ImportError as e:
            logger.error("Failed to write to error log: %s", str(e))
    def _cleanup_old_logs(self) -> None:
        """Delete oldest log files if we exceed the maximum number."""
        try:
            log_files = sorted(
                [f for f in self.config.BASE_DIR.glob("error_snippets_*.jsonl")],
                key=lambda x: x.stat().st_mtime
            )
            # Remove oldest files if we have too many
            while len(log_files) > self.config.MAX_LOG_FILES:
                oldest_file = log_files.pop(0)
                oldest_file.unlink()
                logger.info("Removed old log file: %s", oldest_file)
        except ImportError as e:
            logger.error("Failed to clean up old logs: %s", str(e))
    def shutdown(self) -> None:
        """Cleanly shut down the logger, ensuring all entries are written."""
        self.stop_requested = True
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)
        # Process any remaining entries
        entries_to_write = []
        while not self.buffer.empty():
            try:
                entries_to_write.append(self.buffer.get_nowait())
                self.buffer.task_done()
            except queue.Empty:
                break
        # Write remaining entries
        for entry in entries_to_write:
            self._write_entry_to_disk(entry)

# Global instance for easy importing
error_logger = ErrorLogger()

# Function wrapper for backward compatibility
def log_error(question_id: str, user_code: str, error_msg: str,
              additional_context: Optional[Dict[str, Any]] = None) -> None:
    """Compatibility wrapper for the original function."""
    error_logger.log_error(question_id, user_code, error_msg, additional_context)