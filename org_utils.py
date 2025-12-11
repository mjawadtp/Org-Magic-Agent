import os
import zipfile
import io
import time
import json
import uuid
import requests
import xml.etree.ElementTree as ET
import yaml
import re
from langchain_core.tools import tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --------------------------------------------------------
# ORG CONFIGURATION
# --------------------------------------------------------
# Org information loaded from .env file
ORG_INSTANCE_URL = os.getenv("ORG_INSTANCE_URL")
ORG_ACCESS_TOKEN = os.getenv("ORG_ACCESS_TOKEN")
ORG_API_VERSION = os.getenv("ORG_API_VERSION", "61.0")  # Default to 61.0 if not set


def deploy_metadata_xml(instance_url: str, access_token: str, metadata_xml: str, api_version: str = "61.0"):
    """
    Deploy a single metadata XML to Salesforce using REST Metadata API.
    
    Args:
        instance_url: Salesforce instance URL (e.g., 'https://mycompany.salesforce.com')
        access_token: OAuth access token
        metadata_xml: The metadata XML string to deploy
        api_version: API version to use (default: "61.0")
    
    Returns:
        Dictionary with deployment result, or None if deployment request failed
    
    Example:
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <RemoteSiteSetting xmlns="http://soap.sforce.com/2006/04/metadata">
            <fullName>MySite</fullName>
            <isActive>true</isActive>
            <url>https://example.com</url>
        </RemoteSiteSetting>'''
        
        result = deploy_metadata_xml(instance_url, access_token, xml)
    """
    
    print("\n=== Starting Metadata Deploy ===")

    # ---------------------------
    # 1. Parse XML to extract metadata type and name
    # ---------------------------
    root = ET.fromstring(metadata_xml)
    
    # Extract namespace
    if "}" in root.tag:
        namespace = "{" + root.tag.split("}")[0].replace("{", "") + "}"
    else:
        namespace = ""
    
    # Extract metadata type (e.g., "RemoteSiteSetting", "CustomObject")
    metadata_type = root.tag.replace(namespace, "")
    
    # Extract fullName
    fullName_elem = root.find(f"{namespace}fullName")
    if fullName_elem is None:
        raise ValueError("Metadata XML must contain a <fullName> element.")
    fullName = fullName_elem.text

    print(f"Detected metadata type: {metadata_type}")
    print(f"Detected name: {fullName}")

    # ---------------------------
    # 2. Determine folder name and file extension from metadata_map.yml
    # ---------------------------
    metadata_map_path = os.path.join(os.path.dirname(__file__), "metadata_map.yml")
    
    if not os.path.exists(metadata_map_path):
        raise FileNotFoundError(f"metadata_map.yml file not found at {metadata_map_path}")
    
    with open(metadata_map_path, "r", encoding="utf-8") as f_metadata_map:
        metadata_map = yaml.safe_load(f_metadata_map)
        
        # Find entity configuration (like reference code)
        entity_configurations = [
            entry
            for entry in metadata_map
            if any(
                [
                    subentry["type"] == metadata_type
                    for subentry in metadata_map[entry]
                ]
            )
        ]
        
        if not entity_configurations:
            raise ValueError(f"Unable to locate configuration for entity {metadata_type} in metadata_map.yml")
        
        # Get configuration
        entity_config = entity_configurations[0]
        configuration = metadata_map[entity_config][0]
        extension = configuration["extension"]
        folder_name = entity_config
    
    # ---------------------------
    # 3. Get the correct filename (handling special cases)
    # ---------------------------
    if metadata_type == 'CustomObject':
        label_elem = root.find(f"{namespace}label")
        if label_elem is not None and label_elem.text:
            metadata_filename = label_elem.text.replace(' ', '')
            metadata_filename += f'__c.{extension}'
        else:
            metadata_filename = f"{fullName}.{extension}"
    elif metadata_type == 'RemoteSiteSetting':
        metadata_filename = fullName.replace(' ', '')
        metadata_filename += f'.{extension}'
    elif metadata_type == 'SurveySettings':
        metadata_filename = 'Survey'
        metadata_filename += f'.{extension}'
    else:
        metadata_filename = f"{fullName}.{extension}"
    
    # Filename must include -meta.xml suffix
    if not metadata_filename.endswith("-meta.xml"):
        metadata_filename += "-meta.xml"

    # ---------------------------
    # 4. Determine package.xml name and member
    # ---------------------------
    # For Settings metadata types, use "Settings" as the name in package.xml
    # Check if it's in the settings folder
    if folder_name == "settings":
        package_xml_name = "Settings"
        # For Settings, the member is typically the fullName (e.g., "Survey" for SurveySettings)
        package_xml_member = fullName
    else:
        # For other metadata types, use the metadata_type as the name
        package_xml_name = metadata_type
        package_xml_member = fullName
    
    print(f"Package.xml name: {package_xml_name}")
    print(f"Package.xml member: {package_xml_member}")
    
    # ---------------------------
    # 5. Build package.xml
    # ---------------------------
    package_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>{package_xml_member}</members>
        <name>{package_xml_name}</name>
    </types>
    <version>{api_version}</version>
</Package>
"""

    # Print package.xml for debugging
    print("\n=== PACKAGE.XML CONTENT ===")
    print(package_xml)
    print("=" * 40)

    # ---------------------------
    # 6. Create ZIP in memory
    # ---------------------------
    print("Building ZIP package in memory...")

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add metadata file to the correct folder
        zip_path = f"{folder_name}/{metadata_filename}"
        zip_file.writestr(zip_path, metadata_xml)
        print(f"Added to ZIP: {zip_path}")

        # Add package.xml
        zip_file.writestr("package.xml", package_xml)
        print(f"Added to ZIP: package.xml")
        
        # Debug: List all files in zip
        print(f"\nZIP contents:")
        for name in zip_file.namelist():
            print(f"  - {name}")

    zip_buffer.seek(0)

    # ---------------------------
    # 7. Send deploy request
    # ---------------------------
    print("Sending deploy request...")

    deploy_url = f"{instance_url}/services/data/v{api_version}/metadata/deployRequest"
    
    # Create multipart boundary
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    
    # Deploy options JSON
    deploy_options = {
        "deployOptions": {
            "allowMissingFiles": False,
            "autoUpdatePackage": False,
            "checkOnly": False,
            "ignoreWarnings": False,
            "performRetrieve": False,
            "purgeOnDelete": False,
            "rollbackOnError": True,
            "runTests": [],
            "singlePackage": True,
            "testLevel": "NoTestRun"
        }
    }
    
    # Build multipart form data manually
    zip_bytes = zip_buffer.getvalue()
    
    body_parts = [
        f"--{boundary}\r\n".encode('utf-8'),
        b'Content-Disposition: form-data; name="json"\r\n',
        b'Content-Type: application/json\r\n\r\n',
        json.dumps(deploy_options).encode('utf-8'),
        f"\r\n--{boundary}\r\n".encode('utf-8'),
        b'Content-Disposition: form-data; name="file"; filename="metadata.zip"\r\n',
        b'Content-Type: application/zip\r\n\r\n',
        zip_bytes,
        f"\r\n--{boundary}--\r\n".encode('utf-8')
    ]
    
    body = b''.join(body_parts)
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }

    response = requests.post(deploy_url, headers=headers, data=body)

    if response.status_code >= 300:
        print("Deployment request failed:")
        print(response.text)
        return

    deploy_id = response.json().get("id")
    print(f"Deploy request created. ID = {deploy_id}")

    # ---------------------------
    # 8. Poll deployment status
    # ---------------------------
    print("\nPolling deployment status...")

    status_url = f"{instance_url}/services/data/v{api_version}/metadata/deployRequest/{deploy_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    while True:
        r = requests.get(status_url, headers=headers)
        result = r.json()

        status = result["deployResult"]["status"]
        print(f"Status: {status}")

        if result["deployResult"]["done"]:
            print("\n=== FINAL DEPLOY RESULT ===")
            deploy_result = result["deployResult"]
            
            # Print full JSON for debugging
            print("\nFull deploy result JSON:")
            print(json.dumps(result, indent=2))
            
            if deploy_result.get("success"):
                print(f"\n✅ Deployment successful!")
                print(f"Components deployed: {deploy_result.get('numberComponentsDeployed', 0)}")
            else:
                print(f"\n❌ Deployment failed!")
                print(f"Errors: {deploy_result.get('numberComponentErrors', 0)}")
                print(f"Status: {deploy_result.get('status', 'Unknown')}")
                
                # Print component failures if any
                if "details" in deploy_result:
                    if "componentFailures" in deploy_result["details"]:
                        failures = deploy_result["details"]["componentFailures"]
                        if failures:
                            print("\nComponent Failures:")
                            for failure in failures:
                                print(f"  - Full Name: {failure.get('fullName', 'Unknown')}")
                                print(f"    Problem: {failure.get('problem', 'Unknown error')}")
                                print(f"    File: {failure.get('fileName', 'Unknown')}")
                                print(f"    Problem Type: {failure.get('problemType', 'Unknown')}")
                                print()
                    
                    # Also print all component messages for more details
                    if "allComponentMessages" in deploy_result["details"]:
                        messages = deploy_result["details"]["allComponentMessages"]
                        if messages:
                            print("All Component Messages:")
                            for msg in messages:
                                if not msg.get("success", False):
                                    print(f"  - {msg.get('fullName', 'Unknown')}: {msg.get('problem', 'Unknown error')}")
            
            return result

        time.sleep(3)


# --------------------------------------------------------
# LANGCHAIN TOOL FOR DEPLOYING METADATA
# --------------------------------------------------------
@tool
def deploy_metadata(metadata_xml: str) -> str:
    """Deploy metadata XML to a Salesforce org.
    
    This tool deploys metadata XML files to a Salesforce org using the org configuration
    set at the top of org_utils.py file.
    
    Args:
        metadata_xml: The metadata XML string to deploy (required)
    
    Returns:
        A string describing the deployment result (success or failure with details)
    
    Example:
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <RemoteSiteSetting xmlns="http://soap.sforce.com/2006/04/metadata">
            <fullName>MySite</fullName>
            <isActive>true</isActive>
            <url>https://example.com</url>
        </RemoteSiteSetting>'''
        
        result = deploy_metadata(xml)
    """
    # Validate we have required org info
    if not ORG_INSTANCE_URL:
        return "Error: ORG_INSTANCE_URL is not set at the top of org_utils.py file."
    
    if not ORG_ACCESS_TOKEN:
        return "Error: ORG_ACCESS_TOKEN is not set at the top of org_utils.py file."
    
    # Validate XML
    if not metadata_xml or not metadata_xml.strip():
        return "Error: metadata_xml is required and cannot be empty."
    
    try:
        # Deploy the metadata using hardcoded org info
        result = deploy_metadata_xml(
            instance_url=ORG_INSTANCE_URL,
            access_token=ORG_ACCESS_TOKEN,
            metadata_xml=metadata_xml,
            api_version=ORG_API_VERSION
        )
        
        if not result:
            return "Error: Deployment request failed. Check the console output for details."
        
        deploy_result = result.get("deployResult", {})
        
        if deploy_result.get("success"):
            components_deployed = deploy_result.get("numberComponentsDeployed", 0)
            return f"✅ Deployment successful! Deployed {components_deployed} component(s) to {ORG_INSTANCE_URL}"
        else:
            # Build error message
            error_count = deploy_result.get("numberComponentErrors", 0)
            error_msg = f"❌ Deployment failed! {error_count} error(s) occurred.\n"
            
            # Add component failure details
            if "details" in deploy_result and "componentFailures" in deploy_result["details"]:
                failures = deploy_result["details"]["componentFailures"]
                if failures:
                    error_msg += "\nComponent Failures:\n"
                    for failure in failures:
                        error_msg += f"  - {failure.get('fullName', 'Unknown')}: {failure.get('problem', 'Unknown error')}\n"
            
            return error_msg.strip()
            
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error deploying metadata: {str(e)}"


# --------------------------------------------------------
# TEST HARDCODED REMOTE SITE
# --------------------------------------------------------
if __name__ == "__main__":

    INSTANCE_URL = os.getenv("ORG_INSTANCE_URL")
    ACCESS_TOKEN = os.getenv("ORG_ACCESS_TOKEN")

    # A full RemoteSiteSetting XML for testing
    TEST_REMOTE_SITE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<RemoteSiteSetting xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>MyTestSite</fullName>
    <description>Test Remote Site</description>
    <disableProtocolSecurity>false</disableProtocolSecurity>
    <isActive>true</isActive>
    <url>https://example.com</url>
</RemoteSiteSetting>
"""

    deploy_metadata_xml(INSTANCE_URL, ACCESS_TOKEN, TEST_REMOTE_SITE_XML)
