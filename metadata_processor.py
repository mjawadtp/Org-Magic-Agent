from bs4 import BeautifulSoup
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
from langchain_core.tools import tool


def metadata_information_for_metadata_type(type):
    file_path = f'resources/{type}.html'

    # Check if the file exists
    if not os.path.exists(file_path):
        return []  # Return an empty list if the file does not exist
    
    print(f'\n ******** Metadata information file found. Processing {file_path} ...   ******* \n')
    # Read the HTML file
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the table with the class 'featureTable'
    table = soup.find('table', class_='featureTable')


    if table:
        # Extract table header
        headers = [header.find(string=True) for header in table.find('thead').find_all('th')]
        # Extract table rows
        rows = table.find('tbody').find_all('tr')

        fields = []
        
        for row in rows:
            columns = row.find_all('td')
            data = []
            fieldDict = {}
            for index, column in enumerate(columns):
                # Extract all text, including nested tags
                texts = column.find_all(string=True, recursive=True)
                data.append(' '.join(texts).strip())
                fieldDict[headers[index]] = ' '.join(texts).strip()
            fields.append(fieldDict)
            # print("Row data: \n", data)
            # print("\n")
            
        # for field in fields:
        #     print(field)
        
        print(f"Metadata information for {type}: \n", fields)
        return fields
    #print(fields)
    else:
        print("Table with class 'featureTable' not found.")
        return []


def _get_available_metadata_types():
    """Helper function to get all available metadata types from resources folder."""
    resources_dir = 'resources'
    if not os.path.exists(resources_dir):
        return []
    
    metadata_types = []
    for filename in os.listdir(resources_dir):
        if filename.endswith('.html'):
            # Remove .html extension to get the metadata type name
            metadata_type = filename[:-5]  # Remove '.html'
            metadata_types.append(metadata_type)
    
    return metadata_types


@tool
def get_metadata_information(metadata_type: str) -> list:
    """Get metadata field information for a specific Salesforce metadata type.
    
    This tool searches the resources folder for HTML documentation files matching
    the provided metadata type, parses the documentation to extract field information,
    and returns structured data about the metadata fields. This information can be
    used to generate XML files for deploying metadata to a Salesforce org.
    
    Args:
        metadata_type: The name of the Salesforce metadata type (e.g., 'RemoteSiteSetting', 
                      'FlexiPage', 'CustomObject', etc.). The tool will search for a 
                      matching HTML file in the resources folder.
    
    Returns:
        A list of dictionaries, where each dictionary contains field information with
        keys like 'Field', 'Field Type', 'Description', etc. Returns an empty list
        if the metadata type is not found or if no field information can be extracted.
    
    Example:
        get_metadata_information("RemoteSiteSetting") returns field information
        for RemoteSiteSetting metadata type.
    """
    # Normalize the metadata type (strip whitespace, handle case)
    metadata_type = metadata_type.strip()
    
    # Get available metadata types for better error messages
    available_types = _get_available_metadata_types()
    
    # Check if the file exists (case-insensitive search)
    file_path = f'resources/{metadata_type}.html'
    actual_metadata_type = metadata_type
    
    if not os.path.exists(file_path):
        # Try case-insensitive matching
        found_file = None
        for available_type in available_types:
            if available_type.lower() == metadata_type.lower():
                file_path = f'resources/{available_type}.html'
                actual_metadata_type = available_type  # Use the actual filename case
                found_file = available_type
                break
        
        if not found_file:
            error_msg = f"Metadata type '{metadata_type}' not found in resources folder."
            if available_types:
                error_msg += f" Available types: {', '.join(available_types)}"
            print(error_msg)
            return []
    
    # Call the metadata information extraction function with the actual metadata type
    result = metadata_information_for_metadata_type(actual_metadata_type)
    
    # Ensure we return a list (the function might return empty string)
    if result == "" or result is None:
        return []
    
    return result