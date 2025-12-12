import requests
import xml.etree.ElementTree as ET
import argparse

API_VERSION = "58.0"

def build_soap_url(base_url: str) -> str:
    # Remove trailing slashes
    base = base_url.strip()
    if base.endswith("/"):
        base = base[:-1]
    # If user didn’t supply scheme, add https://
    if not base.startswith("http://") and not base.startswith("https://"):
        base = "https://" + base
    # Append SOAP path
    return f"{base}/services/Soap/u/{API_VERSION}"

def generate_token(login_base: str, username: str, password: str) -> tuple:
    """Generate access token and get server URL from Salesforce SOAP API.
    
    Args:
        login_base: Salesforce login URL or instance URL
        username: Salesforce username
        password: Salesforce password (may include security token)
    
    Returns:
        Tuple of (access_token, server_url) where server_url is the actual instance URL to use
    """
    soap_url = build_soap_url(login_base)
    xml_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<env:Envelope xmlns:xsd="http://www.w3.org/2001/XMLSchema"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <n1:login xmlns:n1="urn:partner.soap.sforce.com">
      <n1:username>{username}</n1:username>
      <n1:password>{password}</n1:password>
    </n1:login>
  </env:Body>
</env:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=UTF-8",
        "SOAPAction": "login",
        "Accept": "text/xml"
    }

    resp = requests.post(soap_url, headers=headers, data=xml_payload)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    
    # Extract session ID (access token)
    session = root.find('.//{urn:partner.soap.sforce.com}sessionId')
    if session is None:
        raise Exception("sessionId not found. Full response:\n" + resp.text)
    access_token = session.text
    
    # Extract server URL (actual instance URL to use)
    server_url_elem = root.find('.//{urn:partner.soap.sforce.com}serverUrl')
    if server_url_elem is not None:
        # Extract base URL from serverUrl (remove /services/Soap/u/...)
        server_url = server_url_elem.text
        # Remove the SOAP endpoint path to get base instance URL
        if '/services/Soap/u/' in server_url:
            server_url = server_url.split('/services/Soap/u/')[0]
    else:
        # Fallback to login_base if serverUrl not found
        server_url = login_base
    
    return access_token, server_url

def main():
    instance_url = "https://orgfarm-a3ede0530b-dev-ed.develop.my.salesforce.com"
    username = "sidosho2208310@agentforce.com"
    password = "abcd@1234IzZC0VoI6Gv3u4z7NpazniYT"

    try:
        token, server_url = generate_token(instance_url, username, password)
        print("Session token:", token)
        print("Server URL:", server_url)
    except Exception as e:
        print("Error obtaining token:", e)

if __name__ == "__main__":
    main()
