"""Test enum values."""

def test_download_status_enum():
    """Test DownloadStatus enum values."""
    from core.enums.download_status import DownloadStatus
    
    assert DownloadStatus.PENDING == "Pending"
    assert DownloadStatus.DOWNLOADING == "Downloading"
    assert DownloadStatus.COMPLETED == "Completed"
    assert DownloadStatus.FAILED == "Failed"
    assert DownloadStatus.PAUSED == "Paused"
    assert DownloadStatus.CANCELLED == "Cancelled"


def test_service_type_enum():
    """Test ServiceType enum values."""
    from core.enums.service_type import ServiceType
    
    assert ServiceType.YOUTUBE == "youtube"
    assert ServiceType.TWITTER == "twitter"
    assert ServiceType.INSTAGRAM == "instagram"
    assert ServiceType.PINTEREST == "pinterest"


def test_instagram_auth_status_enum():
    """Test InstagramAuthStatus enum values."""
    from core.enums.instagram_auth_status import InstagramAuthStatus
    
    assert InstagramAuthStatus.FAILED == "failed"
    assert InstagramAuthStatus.LOGGING_IN == "logging_in"
    assert InstagramAuthStatus.AUTHENTICATED == "authenticated"


def test_message_level_enum():
    """Test MessageLevel enum values."""
    from core.enums.message_level import MessageLevel
    
    assert MessageLevel.INFO == "info"
    assert MessageLevel.WARNING == "warning"
    assert MessageLevel.ERROR == "error"
    assert MessageLevel.SUCCESS == "success"


def test_network_status_enum():
    """Test NetworkStatus enum values."""
    from core.enums.network_status import NetworkStatus
    
    assert NetworkStatus.UNKNOWN == "unknown"
    assert NetworkStatus.CHECKING == "checking"
    assert NetworkStatus.CONNECTED == "connected"
    assert NetworkStatus.ERROR == "error"
