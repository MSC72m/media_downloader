"""Core application modules organized by feature."""

# Downloads
from .downloads.models import Download, DownloadOptions, ServiceType, DownloadStatus, UIState, ButtonState
from .downloads.repository import DownloadRepository, OptionsRepository

# Events
from .events.coordinator import EventCoordinator
from .events.queue import MessageQueue

# Application
from .application.orchestrator import ApplicationOrchestrator
from .application.container import ServiceContainer

# Detection
from .detection.link_detector import LinkDetector, LinkDetectionRegistry, DetectionResult

# Services
from .services.accessor import ServiceAccessor
from .services.controller import ServiceController

# Network
from .network.checker import HTTPNetworkChecker, NetworkService, ConnectionResult

# Base
from .base import BaseDownloader

__all__ = [
    # Downloads
    'Download',
    'DownloadOptions',
    'ServiceType',
    'DownloadStatus',
    'UIState',
    'ButtonState',
    'DownloadRepository',
    'OptionsRepository',
    # Events
    'EventCoordinator',
    'MessageQueue',
    # Application
    'ApplicationOrchestrator',
    'ServiceContainer',
    # Detection
    'LinkDetector',
    'LinkDetectionRegistry',
    'DetectionResult',
    # Services
    'ServiceAccessor',
    'ServiceController',
    # Network
    'HTTPNetworkChecker',
    'NetworkService',
    'ConnectionResult',
    # Base
    'BaseDownloader'
]