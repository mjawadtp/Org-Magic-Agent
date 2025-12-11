"""
Simple key-value store for persisting data.
Uses a JSON file for storage - perfect for POC/hackathon use.
"""
import json
from pathlib import Path
from typing import Any, Dict


class SimpleStore:
    """Simple key-value store using JSON file.
    
    This class provides a simple way to persist and retrieve data
    using a JSON file. Perfect for POC/hackathon projects.
    
    Example:
        # Create a store instance
        store = SimpleStore()
        
        # Store data
        store.set("org_details", {
            "instance_url": "https://mycompany.salesforce.com",
            "username": "user@example.com",
            "access_token": "00D..."
        })
        
        # Retrieve data
        org_details = store.get("org_details")
        print(org_details)  # {'instance_url': '...', 'username': '...', ...}
        
        # Get all data
        all_data = store.get_all()
        
        # Delete a key
        store.delete("org_details")
        
        # Clear everything
        store.clear()
    """
    
    def __init__(self, store_file: str = "org_data.json"):
        """Initialize the store.
        
        Args:
            store_file: Name of the JSON file to use for storage (default: "org_data.json")
        """
        self.store_file = Path(store_file)
        if not self.store_file.exists():
            self._save({})
    
    def _load(self) -> Dict[str, Any]:
        """Load data from file."""
        if not self.store_file.exists():
            return {}
        
        try:
            with open(self.store_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save(self, data: Dict[str, Any]):
        """Save data to file."""
        with open(self.store_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def set(self, key: str, value: Any):
        """Set a key-value pair.
        
        Args:
            key: The key to store the value under
            value: The value to store (can be any JSON-serializable type)
        
        Example:
            store.set("org_name", "production")
            store.set("org_details", {"url": "https://...", "token": "..."})
        """
        data = self._load()
        data[key] = value
        self._save(data)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key.
        
        Args:
            key: The key to retrieve
            default: Default value to return if key doesn't exist (default: None)
        
        Returns:
            The stored value, or default if key doesn't exist
        
        Example:
            org_name = store.get("org_name")  # Returns value or None
            org_name = store.get("org_name", "default")  # Returns value or "default"
        """
        data = self._load()
        return data.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all stored data.
        
        Returns:
            Dictionary containing all key-value pairs
        
        Example:
            all_data = store.get_all()
            print(all_data)  # {'org_name': 'production', 'org_details': {...}}
        """
        return self._load()
    
    def delete(self, key: str) -> bool:
        """Delete a key.
        
        Args:
            key: The key to delete
        
        Returns:
            True if key was deleted, False if key didn't exist
        
        Example:
            deleted = store.delete("org_name")  # Returns True if deleted
        """
        data = self._load()
        if key in data:
            del data[key]
            self._save(data)
            return True
        return False
    
    def clear(self):
        """Clear all data from the store.
        
        Example:
            store.clear()  # Removes all stored data
        """
        self._save({})


# Example usage
if __name__ == "__main__":
    # Create a store instance
    store = SimpleStore()
    
    # Example 1: Store simple values
    print("=== Example 1: Storing simple values ===")
    store.set("org_name", "production")
    store.set("api_version", "60.0")
    print(f"Stored org_name: {store.get('org_name')}")
    print(f"Stored api_version: {store.get('api_version')}")
    print()
    
    # Example 2: Store complex data (dictionaries, lists, etc.)
    print("=== Example 2: Storing complex data ===")
    org_details = {
        "instance_url": "https://mycompany.salesforce.com",
        "username": "user@example.com",
        "access_token": "00D1234567890ABC",
        "org_id": "00D000000000001",
        "api_version": "60.0"
    }
    store.set("org_details", org_details)
    retrieved = store.get("org_details")
    print(f"Stored org_details: {retrieved}")
    print()
    
    # Example 3: Get all data
    print("=== Example 3: Getting all data ===")
    all_data = store.get_all()
    print(f"All stored data: {all_data}")
    print()
    
    # Example 4: Update existing data
    print("=== Example 4: Updating existing data ===")
    store.set("org_name", "sandbox-dev")  # Updates existing key
    print(f"Updated org_name: {store.get('org_name')}")
    print()
    
    # Example 5: Delete a key
    print("=== Example 5: Deleting a key ===")
    deleted = store.delete("api_version")
    print(f"Deleted 'api_version': {deleted}")
    print(f"After deletion, all data: {store.get_all()}")
    print()
    
    # Example 6: Get non-existent key with default
    print("=== Example 6: Getting non-existent key ===")
    value = store.get("non_existent_key", "default_value")
    print(f"Value for non-existent key: {value}")
    print()
    
    # Uncomment to clear all data
    # store.clear()
    # print("All data cleared!")

