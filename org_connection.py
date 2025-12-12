"""
Tools for connecting to Salesforce orgs and managing credentials.
"""
from langchain_core.tools import tool
from simple_store import SimpleStore
from getToken import generate_token

# Initialize store for persisting org credentials
store = SimpleStore("org_data.json")


@tool
def connect_to_salesforce_org(instance_url: str, username: str, password: str) -> str:
    """Connect to a Salesforce org and store credentials for later use.
    
    This tool authenticates with a Salesforce org using username and password,
    generates an access token, and stores the credentials (instance_url and access_token)
    for use in subsequent metadata and data deployment operations.
    
    IMPORTANT: This tool must be called before any metadata or data deployment operations.
    The agent should ask the user for these credentials if they haven't been provided yet.
    
    Args:
        instance_url: The Salesforce instance URL (e.g., "https://mycompany.salesforce.com" 
                     or "https://mycompany--sandbox.salesforce.com" for sandboxes)
        username: Salesforce username (email address)
        password: Salesforce password (may include security token if required)
    
    Returns:
        A string indicating success or failure of the connection attempt.
        On success, credentials are stored and can be used for deployments.
    
    Example:
        When a user provides credentials, call this tool:
        connect_to_salesforce_org(
            instance_url="https://mycompany.salesforce.com",
            username="user@example.com",
            password="mypassword123"
        )
    """
    try:
        print(f"\n=== Connecting to Salesforce Org ===")
        print(f"Instance URL: {instance_url}")
        print(f"Username: {username}")
        
        # Generate access token using SOAP API
        # Returns both access_token and the actual server URL (may differ from login URL)
        access_token, server_url = generate_token(instance_url, username, password)
        
        if not access_token:
            return "❌ Failed to generate access token. Please check your credentials."
        
        # Store credentials in SimpleStore
        # Use server_url from SOAP response (this is the actual instance URL to use for API calls)
        org_details = {
            "instance_url": server_url,  # Use server URL from SOAP response
            "username": username,
            "access_token": access_token,
            "api_version": "61.0"  # Default API version
        }
        
        store.set("org_details", org_details)
        
        print(f"✅ Successfully connected to Salesforce org")
        print(f"✅ Credentials stored for future use")
        
        return f"✅ Successfully connected to Salesforce org at {instance_url}. Credentials have been stored and are ready for use in metadata and data deployments."
        
    except Exception as e:
        error_msg = f"❌ Failed to connect to Salesforce org: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return error_msg


def get_stored_org_credentials():
    """Get stored org credentials from SimpleStore.
    
    Returns:
        Dictionary with instance_url, access_token, and api_version, or None if not set
    """
    org_details = store.get("org_details")
    if org_details and org_details.get("instance_url") and org_details.get("access_token"):
        return org_details
    return None


def has_org_credentials() -> bool:
    """Check if org credentials are stored.
    
    Returns:
        True if credentials are available, False otherwise
    """
    return get_stored_org_credentials() is not None

