import os
import re
import logging
import requests
import socket
import time
import http.client
from typing import Dict, Callable, Optional, List, Tuple
from pathlib import Path
import unicodedata

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
SERVICE_URLS = {
    "Google": "www.google.com",
    "YouTube": "www.youtube.com",
    "Instagram": "www.instagram.com",
    "Twitter": "twitter.com"
}

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe for all operating systems.
    
    Args:
        filename: The original filename
        
    Returns:
        A sanitized filename
    """
    # Remove invalid characters
    valid_chars = re.compile(r'[^\w\s.\-]')
    filename = valid_chars.sub('_', filename)
    
    # Normalize unicode characters
    filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode('ASCII')
    
    # Limit length
    max_length = 255 - 10  # Leave room for extension and potential suffix
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    return filename.strip()

def check_site_connection(service: str) -> Tuple[bool, str]:
    """
    Check connectivity to a specific service.
    
    Args:
        service: The service name (must be in SERVICE_URLS)
        
    Returns:
        Tuple[bool, str]: (is_connected, error_message)
    """
    if service not in SERVICE_URLS:
        return False, f"Unknown service: {service}"
    
    url = SERVICE_URLS[service]
    
    # Try HTTP connection first
    try:
        conn = http.client.HTTPSConnection(url, timeout=DEFAULT_TIMEOUT)
        conn.request("HEAD", "/")
        response = conn.getresponse()
        conn.close()
        
        if 200 <= response.status < 400:
            return True, ""
        elif response.status == 403:
            return False, f"Access to {service} is forbidden (HTTP 403)"
        else:
            return False, f"HTTP error connecting to {service}: {response.status}"
    except Exception as e:
        # Fall back to simple DNS lookup
        try:
            socket.gethostbyname(url)
            return False, f"DNS resolves but HTTP connection to {service} failed: {str(e)}"
        except socket.gaierror:
            return False, f"Cannot resolve DNS for {service}"
        except Exception as e2:
            return False, f"Complete connection failure to {service}: {str(e2)}"

def check_internet_connection() -> Tuple[bool, str]:
    """
    Check if the device has a working internet connection.
    
    Returns:
        Tuple[bool, str]: (is_connected, error_message)
    """
    # First check if we can open a socket to Google's DNS (basic connectivity)
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=DEFAULT_TIMEOUT)
    except OSError as e:
        return False, f"Cannot connect to network: {str(e)}"
    
    # Next, check HTTP connectivity to a major service
    for service in ["Google", "YouTube"]:
        try:
            connected, _ = check_site_connection(service)
            if connected:
                return True, ""
        except Exception:
            pass
    
    return False, "Internet connection appears to be limited or restricted"

def check_all_services() -> Dict[str, Tuple[bool, str]]:
    """
    Check connectivity to all services defined in SERVICE_URLS.
    
    Returns:
        Dict[str, Tuple[bool, str]]: Dictionary of services with (is_connected, error_message)
    """
    results = {}
    for service in SERVICE_URLS:
        try:
            connected, error = check_site_connection(service)
            results[service] = (connected, error)
        except Exception as e:
            results[service] = (False, str(e))
    
    return results

def get_problem_services() -> list:
    """
    Get a list of services with connectivity issues.
    
    Returns:
        list: List of service names with connection problems
    """
    results = check_all_services()
    return [service for service, (connected, _) in results.items() if not connected]

def is_service_connected(service: str) -> bool:
    """
    Check if a specific service is connected.
    
    Args:
        service: The service name (must be in SERVICE_URLS)
        
    Returns:
        bool: True if connected, False otherwise
    """
    if service not in SERVICE_URLS:
        return False
    
    connected, _ = check_site_connection(service)
    return connected

def download_file(
    url: str,
    save_path: str,
    progress_callback: Optional[Callable[[float, float], None]] = None,
    chunk_size: int = 8192
) -> bool:
    """
    Download a file with progress monitoring.
    
    Args:
        url: URL to download from
        save_path: Path to save the file to
        progress_callback: Callback for progress updates
        chunk_size: Size of chunks to download
        
    Returns:
        True if download was successful, False otherwise
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    
    # Extract the domain from the URL to check connectivity
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    site_name = None
    
    for name, service_url in SERVICE_URLS.items():
        if domain in service_url:
            site_name = name
            break
    
    if site_name:
        connected, error_msg = check_site_connection(site_name)
        if not connected:
            logger.error(f"Download failed: {error_msg}")
            return False
    
    # Setup session with retries
    session = requests.Session()
    temp_file = f"{save_path}.part"
    
    try:
        # Make a streaming request with simple custom headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = session.get(url, stream=True, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        # Get file size if available
        file_size = int(response.headers.get('content-length', 0))
        
        # Progress tracking
        downloaded = 0
        start_time = time.time()
        
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive chunks
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Calculate progress and speed
                    progress = (downloaded / file_size * 100) if file_size > 0 else -1
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    
                    if progress_callback:
                        # If file size unknown, report indeterminate progress
                        progress_to_report = progress if progress >= 0 else min(99, downloaded / (1024 * 1024))
                        progress_callback(progress_to_report, speed)
        
        # Rename temp file to final filename
        os.replace(temp_file, save_path)
        
        if progress_callback:
            progress_callback(100, 0)  # Final progress update
            
        logger.info(f"Download completed: {save_path} ({downloaded/1024/1024:.2f} MB)")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Download error for {url}: {str(e)}")
        # Clean up failed download
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {str(e)}")
        # Clean up failed download
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False