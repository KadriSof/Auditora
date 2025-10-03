"""
File: "src/auditora/adats/report.py"
Context: Report Adat - Enhanced reporting utility with structured logging for events.
"""
import sys
import json

from typing import Any
from datetime import datetime


class DefaultReport:
    """Enhanced reporting utility with structured logging for events."""
    def __init__(self, output_stream: Any = None, log_level: str = "INFO") -> None:
        self._stream = output_stream or sys.stdout
        self._log_level = log_level
        self._levels = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

    def _should_log(self, level: str) -> bool:
        return self._levels.get(level, 20) >= self._levels.get(self._log_level, 20)

    @staticmethod
    def _format_message(message: str, level: str, **kwargs: Any) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")[:-3]
        base_msg = f"[{timestamp}] {level}: {message}"

        if kwargs:
            metadata_str = json.dumps(kwargs, default=str, separators=(",", ":"))
            base_msg += f" | {metadata_str}"

        return base_msg

    def log(self, message: str, level: str = "INFO", **kwargs: Any) -> None:
        """Log a message with optional structured metadata."""
        if self._should_log(level):
            formatted_message = self._format_message(message, level, **kwargs)
            self._stream.write(formatted_message + "\n")
            self._stream.flush()

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debugging message with optional structured metadata."""
        self.log(message=message, level="DEBUG", **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message with optional structured metadata."""
        self.log(message=message, level="INFO", **kwargs)

    def warn(self, message: str, **kwargs: Any) -> None:
        """Log a warning message with optional structured metadata."""
        self.log(message=message, level="WARNING", **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message with optional structured metadata."""
        self.log(message=message, level="ERROR", **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message with optional structured metadata."""
        self.log(message=message, level="CRITICAL", **kwargs)

    def log_llm_call(
            self,
            model: str,
            prompt_tokens: int,
            completion_tokens: int,
            response_time: float,
            success: bool = True,
            **kwargs: Any
    ) -> None:
        """Specialized logging for LLM API calls."""
        self.info(
            message="LLM call completed",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            response_time=response_time,
            success=success,
            **kwargs,
        )

    def log_evaluation_results(
            self,
            metric_name: str,
            value: float,
            threshold: float | None = None,
            **kwargs: Any
    ) -> None:
        """Specialized logging for evaluation results."""
        status = "PASS" if threshold is None or value >= threshold else "FAIL"
        self.info(
            message=f"Evaluation result: {metric_name} = {value:.4f}",
            metric_name=metric_name,
            value=value,
            threshold=threshold,
            status=status,
            **kwargs,
        )

    def __str__(self) -> str:
        return f"<DefaultReport(level={self._log_level}), stream={self._stream}>"

    def __repr__(self) -> str:
        return self.__str__()
