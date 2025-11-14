"""Configuration validation and management for launch readiness."""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LaunchValidator:
    """Validates system configuration and readiness for launch."""

    def __init__(self):
        self.validation_results: Dict[str, Tuple[bool, str]] = {}

    def validate_all(self) -> bool:
        """Run all validation checks."""
        logger.info("Starting launch validation...")

        checks = [
            ("Python Dependencies", self._check_dependencies),
            ("yt-dlp Installation", self._check_ytdlp),
            ("Download Directory", self._check_download_directory),
            ("Temp Directory Access", self._check_temp_directory),
            ("Network Connectivity", self._check_network_connectivity),
            ("Security Settings", self._check_security),
            ("UI Components", self._check_ui_requirements),
            ("Cookie Detection", self._check_cookie_detection),
        ]

        all_passed = True
        for check_name, check_func in checks:
            try:
                result = check_func()
                self.validation_results[check_name] = result
                if not result[0]:
                    all_passed = False
                    logger.error(f"Validation failed: {check_name} - {result[1]}")
                else:
                    logger.info(f"Validation passed: {check_name}")
            except Exception as e:
                logger.error(f"Validation error for {check_name}: {e}")
                self.validation_results[check_name] = (False, str(e))
                all_passed = False

        self._generate_validation_report()
        return all_passed

    def _check_dependencies(self) -> Tuple[bool, str]:
        """Check required Python packages."""
        required_packages = [
            'customtkinter',
            'yt_dlp',
            'requests',
            'pathlib',
            'tkinter'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                if package == 'tkinter':
                    import tkinter  # noqa: F401
                elif package == 'customtkinter':
                    import customtkinter  # noqa: F401
                elif package == 'yt_dlp':
                    import yt_dlp  # noqa: F401
                elif package == 'requests':
                    import requests  # noqa: F401
                else:
                    import importlib
                    importlib.import_module(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            return False, f"Missing packages: {', '.join(missing_packages)}"
        return True, "All dependencies available"

    def _check_ytdlp(self) -> Tuple[bool, str]:
        """Check yt-dlp installation and functionality."""
        try:
            import yt_dlp
            import subprocess

            # Check version (handle different versions)
            try:
                version = getattr(yt_dlp, '__version__', 'unknown')
                logger.info(f"yt-dlp version: {version}")
            except AttributeError:
                logger.info("yt-dlp version not available in module")

            # Test basic functionality using virtual environment
            venv_ytdlp = '.venv/bin/yt-dlp'
            if os.path.exists(venv_ytdlp):
                cmd = [venv_ytdlp, '--version']
            else:
                cmd = ['yt-dlp', '--version']

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                version_output = result.stdout.strip()
                return True, f"yt-dlp {version_output} working correctly"
            else:
                return False, f"yt-dlp command failed: {result.stderr}"

        except Exception as e:
            return False, f"yt-dlp check failed: {str(e)}"

    def _check_download_directory(self) -> Tuple[bool, str]:
        """Check default download directory."""
        try:
            download_dir = Path.home() / "Downloads"

            # Check if directory exists or can be created
            if not download_dir.exists():
                download_dir.mkdir(parents=True, exist_ok=True)

            # Test write permissions
            test_file = download_dir / ".media_downloader_test"
            test_file.write_text("test")
            test_file.unlink()

            return True, f"Download directory accessible: {download_dir}"

        except Exception as e:
            return False, f"Download directory issue: {str(e)}"

    def _check_temp_directory(self) -> Tuple[bool, str]:
        """Check temporary directory access."""
        try:
            temp_dir = Path(tempfile.gettempdir())

            # Test write permissions
            test_file = temp_dir / "media_downloader_test"
            test_file.write_text("test")
            test_file.unlink()

            return True, f"Temp directory accessible: {temp_dir}"

        except Exception as e:
            return False, f"Temp directory issue: {str(e)}"

    def _check_network_connectivity(self) -> Tuple[bool, str]:
        """Check basic network connectivity."""
        try:
            import requests

            # Test basic connectivity
            response = requests.get('https://www.google.com', timeout=5)
            if response.status_code == 200:
                return True, "Network connectivity OK"
            else:
                return False, f"Network error: HTTP {response.status_code}"

        except Exception as e:
            return False, f"Network connectivity failed: {str(e)}"

    def _check_security(self) -> Tuple[bool, str]:
        """Check security-related settings."""
        issues = []

        # Check for unsafe file permissions
        try:
            config_dir = Path.home() / ".config" / "media_downloader"
            if config_dir.exists():
                stat_info = config_dir.stat()
                # Check if others have write permissions (security risk on Unix)
                if hasattr(stat_info, 'st_mode') and (stat_info.st_mode & 0o002):
                    issues.append("Config directory has world-write permissions")
        except Exception:
            pass

        # Check for hardcoded sensitive data (more sophisticated)
        try:
            app_dir = Path(__file__).parent.parent
            for py_file in app_dir.rglob("*.py"):
                if py_file.name != "launch_validator.py":
                    content = py_file.read_text()
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        # Skip comments and imports
                        if line_stripped.startswith('#') or line_stripped.startswith('import') or line_stripped.startswith('from'):
                            continue

                        # Look for actual hardcoded credentials, not just references
                        # Pattern: variable = "sensitive_value" where variable contains sensitive terms
                        if ('=' in line_stripped and
                            ('"' in line_stripped or "'" in line_stripped) and
                            not line_stripped.startswith('#') and
                            not 'print(' in line_stripped and
                            not 'log.' in line_stripped):

                            # Check for common credential patterns
                            credential_patterns = [
                                r'password\s*=\s*["\'][^"\']+["\']',
                                r'token\s*=\s*["\'][^"\']+["\']',
                                r'secret\s*=\s*["\'][^"\']+["\']',
                                r'api_key\s*=\s*["\'][^"\']+["\']',
                                r'private_key\s*=\s*["\'][^"\']+["\']',
                            ]

                            import re
                            for pattern in credential_patterns:
                                if re.search(pattern, line_stripped, re.IGNORECASE):
                                    # Additional check: make sure it's not a placeholder or example
                                    if not any(placeholder in line_stripped.lower()
                                              for placeholder in ['example', 'placeholder', 'xxx', 'your_', 'enter_']):
                                        issues.append(f"Potential hardcoded credential in {py_file.name}:{i+1}")
                                        break
        except Exception as e:
            issues.append(f"Security check incomplete: {str(e)}")

        if issues:
            return False, f"Security issues: {'; '.join(issues[:3])}"  # Limit output
        return True, "Security checks passed"

    def _check_ui_requirements(self) -> Tuple[bool, str]:
        """Check UI framework requirements."""
        try:
            import customtkinter as ctk
            import tkinter as tk

            # Test basic window creation (don't show it)
            root = tk.Tk()
            root.withdraw()  # Hide the window
            root.destroy()

            # Check CustomTkinter theme
            ctk.set_appearance_mode("dark")

            return True, "UI framework working correctly"

        except Exception as e:
            return False, f"UI framework issue: {str(e)}"

    def _check_cookie_detection(self) -> Tuple[bool, str]:
        """Check cookie detection capabilities."""
        try:
            # Simple check - just verify the cookie detection files exist and have basic structure
            from pathlib import Path

            cookie_detector_path = Path(__file__).parent.parent / "services" / "youtube" / "cookie_detector.py"
            cookie_handler_path = Path(__file__).parent.parent / "handlers" / "cookie_handler.py"

            if not cookie_detector_path.exists():
                return False, "Cookie detector module not found"

            if not cookie_handler_path.exists():
                return False, "Cookie handler module not found"

            # Check if the modules have the required classes/functions by looking at file content
            detector_content = cookie_detector_path.read_text()
            if 'class CookieManager' not in detector_content:
                return False, "CookieManager class not found in detector module"

            handler_content = cookie_handler_path.read_text()
            if 'class CookieHandler' not in handler_content:
                return False, "CookieHandler class not found in handler module"

            return True, "Cookie detection modules available"

        except Exception as e:
            return False, f"Cookie detection check failed: {str(e)}"

    def _generate_validation_report(self) -> None:
        """Generate a validation report."""
        logger.info("=" * 50)
        logger.info("LAUNCH VALIDATION REPORT")
        logger.info("=" * 50)

        passed = sum(1 for result in self.validation_results.values() if result[0])
        total = len(self.validation_results)

        for check_name, (passed_check, message) in self.validation_results.items():
            status = "✓ PASS" if passed_check else "✗ FAIL"
            logger.info(f"{status:8} {check_name:25} - {message}")

        logger.info("=" * 50)
        logger.info(f"Overall: {passed}/{total} checks passed")

        if passed == total:
            logger.info("🚀 Application is ready for launch!")
        else:
            logger.warning(f"⚠️  {total - passed} issues need to be resolved before launch")
        logger.info("=" * 50)


def run_launch_validation() -> bool:
    """Run complete launch validation."""
    validator = LaunchValidator()
    return validator.validate_all()


if __name__ == "__main__":
    # Run validation when executed directly
    success = run_launch_validation()
    exit(0 if success else 1)