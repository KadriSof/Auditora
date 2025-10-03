"""
File: "src/auditora/__init__.py"
Context: Auditora - Non-invasive monitoring, tracking, and reporting framework
for data processing pipelines and LLM-powered systems.
"""
from .decorators.sentinel import sentinel

from .core.proxies import session, monitor, report

from .adats.session import DefaultSession
from .adats.monitor import DefaultMonitor
from .adats.report import DefaultReport

__version__ = '0.1.0'
__all__ = [
    'sentinel',
    'session', 'monitor', 'report',
    'DefaultSession', 'DefaultMonitor', 'DefaultReport',
]