"""
File: "src/auditora/decorators/sentinel.py"
Context: A context wrapper decorator for Auditora framework.
"""
import time
import inspect

from typing import Any, Callable
from functools import wraps

from ..core.bifrost import bifrost_sync, bifrost_async
from ..adats.session import DefaultSession
from ..adats.monitor import DefaultMonitor
from ..adats.report import DefaultReport


def sentinel(
        session: Any | None = None,
        monitor: Any | None = None,
        report: Any | None = None,
        session_id: str | None = None,
) -> Callable:
    """
    Decorator that provides context-local access to session, monitor and report tools.

    Functions decorated with this can use the global 'session', 'monitor',
    and 'report' adats/variables directly without parameters.

    Args:
        session: Custom session object. Defaults to DefaultSession() if None.
        monitor: Custom monitor object. Defaults to DefaultMonitor() if None.
        report: Custom report object. Defaults to DefaultReport() if None.
        session_id: Optional session ID for tracking. Auto-generated if not provided.
    """
    session_obj = session if session is not None else DefaultSession(session_id=session_id)
    monitor_obj = monitor if session is not None else DefaultMonitor()
    report_obj = report if session is not None else DefaultReport()

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                report_obj.debug(
                    f"Starting {func.__name__!r}",
                    function_name=func.__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys()),
                )
                async with bifrost_async(session=session_obj, monitor=monitor_obj, report=report_obj):
                    try:
                        start_time = time.perf_counter()
                        result = await func(*args, **kwargs)
                        duration = time.perf_counter() - start_time

                        report_obj.debug(
                            f"Completed {func.__name__!r}",
                            function_name=func.__name__,
                            duration=duration,
                            success=True,
                        )

                        return result

                    except Exception as e:
                        report_obj.error(
                            f"Exception in {func.__name__!r}: {str(e)}",
                            function_name=func.__name__,
                            exception_type=type(e).__name__,
                            success=False,
                        )
                        raise

            async_wrapper._session = session_obj
            async_wrapper._monitor = monitor_obj
            async_wrapper._report = report_obj

            return async_wrapper

        else:
            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                report_obj.debug(
                    f"Starting {func.__name__!r}",
                    function_name=func.__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys()),
                )
                with bifrost_sync(session=session_obj, monitor=monitor_obj, report=report_obj):
                    try:
                        start_time = time.perf_counter()
                        result = func(*args, **kwargs)
                        duration = time.perf_counter() - start_time

                        report_obj.debug(
                            f"Completed {func.__name__!r}",
                            function_name=func.__name__,
                            duration=duration,
                            success=True,
                        )
                        return result
                    except Exception as e:
                        report_obj.error(
                            f"Exception in {func.__name__!r}: {str(e)}",
                            function_name=func.__name__,
                            exception_type=type(e).__name__,
                            success=False,
                        )
                        raise

            sync_wrapper._session = session_obj
            sync_wrapper._monitor = monitor_obj
            sync_wrapper._report = report_obj
            return sync_wrapper

    return decorator