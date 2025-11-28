"""Interface for parsing and validating media content."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IParser(ABC):
    """Base interface for parsing and validating media content.
    
    This interface defines the contract for any parser implementation.
    Platform-specific parsers (e.g., YouTube, Vimeo) should implement this interface.
    """
    
    @abstractmethod
    def validate(self, url: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Validate if a URL is valid and processable.
        
        Args:
            url: URL to validate
            context: Optional context dictionary with additional validation parameters
            
        Returns:
            True if URL is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def parse(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Parse data into a formatted list.
        
        Args:
            data: Raw data dictionary to parse
            context: Optional context dictionary with additional parsing parameters
            
        Returns:
            List of parsed and validated items. Format depends on implementation.
        """
        pass

