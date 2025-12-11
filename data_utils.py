import requests
import csv
import os
import json
import time
import io
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


@tool
def fetch_object_fields_map(sobject: str) -> dict:
    """Fetch field information for a Salesforce SObject to help generate sample records.
    
    This tool retrieves detailed field information about a Salesforce object by calling
    the Salesforce describe API. It returns a mapping of field labels to their data types,
    which is essential for generating sample records in CSV format. Use this tool when
    a user requests to generate sample records for a specific Salesforce entity (e.g., 
    Account, Contact, CustomObject__c, etc.).
    
    The function returns field information filtered to include only required system fields
    (non-nullable, non-updateable, non-createable, and not defaulted on create). This
    information helps understand the object structure and field types when generating
    sample CSV data.
    
    Args:
        sobject: The API name of the Salesforce SObject (e.g., "Account", "Contact", 
                "CustomObject__c", "Opportunity", etc.). Use the exact API name as it
                appears in Salesforce, including the __c suffix for custom objects.
    
    Returns:
        A dictionary mapping field labels to their data types. For example:
        {
            "Account Name": "string",
            "Phone": "phone",
            "Annual Revenue": "currency",
            ...
        }
        This mapping provides field label and type information that can be used to
        generate CSV records with appropriate column headers and data types matching
        the Salesforce object structure.
    
    Example:
        When a user asks "Generate 10 sample Account records", first call this tool
        with sobject="Account" to get the field information, then use that information
        to generate CSV records with appropriate column headers and data types.
    """
    query_url = (
        f"{ORG_INSTANCE_URL}/services/data/v{ORG_API_VERSION}/sobjects/{sobject}/describe/"
    )

    headers = {
        "Authorization": f"Bearer {ORG_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.get(query_url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    return {
        field["label"]: field.get("type")
        for field in data.get("fields", [])
        if (
            not field.get("nillable", True)
            and field.get("updateable", False)
            and field.get("createable", False)
            and not field.get("defaultedOnCreate", False)
        )
    }


def deploy_csv_data(csv_file_path: str, sobject: str) -> dict:
    """
    Deploy data from a CSV file to a Salesforce org.
    
    This function reads a CSV file, parses the records, and inserts them into
    the specified Salesforce object using the Salesforce REST API. It uses the
    composite API for efficient batch inserts (up to 200 records per request).
    
    Args:
        csv_file_path: Path to the CSV file containing the data to deploy
        sobject: The API name of the Salesforce SObject (e.g., "Account", "Contact", 
                "CustomObject__c", etc.)
    
    Returns:
        Dictionary containing deployment results:
        {
            "success": bool,
            "total_records": int,
            "successful": int,
            "failed": int,
            "errors": list,
            "created_ids": list
        }
    
    Example:
        result = deploy_csv_data("sample_accounts.csv", "Account")
        print(f"Deployed {result['successful']} out of {result['total_records']} records")
    """
    print(f"\n=== Starting CSV Data Deploy ===")
    print(f"CSV File: {csv_file_path}")
    print(f"SObject: {sobject}")
    
    # Validate CSV file exists
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
    
    # Read and parse CSV file
    records = []
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Remove empty values and convert to proper format
            record = {k: v for k, v in row.items() if v and v.strip()}
            if record:  # Only add non-empty records
                records.append(record)
    
    if not records:
        return {
            "success": False,
            "total_records": 0,
            "successful": 0,
            "failed": 0,
            "errors": ["No records found in CSV file"],
            "created_ids": []
        }
    
    print(f"Found {len(records)} records to deploy")
    
    # Prepare headers for JSON requests
    json_headers = {
        "Authorization": f"Bearer {ORG_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Prepare headers for CSV upload
    csv_headers = {
        "Authorization": f"Bearer {ORG_ACCESS_TOKEN}",
        "Content-Type": "text/csv",
    }
    
    # Initialize results
    all_results = {
        "success": True,
        "total_records": len(records),
        "successful": 0,
        "failed": 0,
        "errors": [],
        "created_ids": []
    }
    
    # ---------------------------
    # Step 1: Create Bulk API 2.0 Job
    # ---------------------------
    print("\nStep 1: Creating Bulk API 2.0 job...")
    bulk_api_base = f"{ORG_INSTANCE_URL}/services/data/v{ORG_API_VERSION}/jobs/ingest"
    
    job_payload = {
        "operation": "insert",
        "object": sobject,
        "contentType": "CSV",
        "lineEnding": "LF"
    }
    
    try:
        response = requests.post(bulk_api_base, headers=json_headers, json=job_payload, timeout=30)
        response.raise_for_status()
        job_info = response.json()
        job_id = job_info.get("id")
        print(f"Job created successfully. Job ID: {job_id}")
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to create bulk job: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" - Response: {e.response.text}"
        print(f"Error: {error_msg}")
        all_results["success"] = False
        all_results["errors"].append({"step": "create_job", "error": error_msg})
        return all_results
    
    # ---------------------------
    # Step 2: Upload CSV Data
    # ---------------------------
    print("\nStep 2: Uploading CSV data...")
    upload_url = f"{bulk_api_base}/{job_id}/batches"
    
    # Convert records back to CSV format
    if not records:
        return all_results
    
    # Get field names from first record
    fieldnames = list(records[0].keys())
    
    # Create CSV content in memory with LF line endings
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    writer.writerows(records)
    csv_content = csv_buffer.getvalue()
    csv_buffer.close()
    
    # Normalize line endings to LF (remove any CRLF and ensure only LF)
    csv_content = csv_content.replace('\r\n', '\n').replace('\r', '\n')
    
    try:
        response = requests.put(upload_url, headers=csv_headers, data=csv_content.encode('utf-8'), timeout=60)
        response.raise_for_status()
        print("CSV data uploaded successfully")
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to upload CSV data: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" - Response: {e.response.text}"
        print(f"Error: {error_msg}")
        all_results["success"] = False
        all_results["errors"].append({"step": "upload_data", "error": error_msg})
        return all_results
    
    # ---------------------------
    # Step 3: Close the Job (set to UploadComplete)
    # ---------------------------
    print("\nStep 3: Closing job (setting to UploadComplete)...")
    close_url = f"{bulk_api_base}/{job_id}"
    close_payload = {"state": "UploadComplete"}
    
    try:
        response = requests.patch(close_url, headers=json_headers, json=close_payload, timeout=30)
        response.raise_for_status()
        print("Job closed successfully. Processing started...")
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to close job: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" - Response: {e.response.text}"
        print(f"Error: {error_msg}")
        all_results["success"] = False
        all_results["errors"].append({"step": "close_job", "error": error_msg})
        return all_results
    
    # ---------------------------
    # Step 4: Poll Job Status
    # ---------------------------
    print("\nStep 4: Polling job status...")
    status_url = f"{bulk_api_base}/{job_id}"
    
    max_wait_time = 300  # 5 minutes max wait
    poll_interval = 3  # Poll every 3 seconds
    elapsed_time = 0
    
    while elapsed_time < max_wait_time:
        try:
            response = requests.get(status_url, headers=json_headers, timeout=30)
            response.raise_for_status()
            job_status = response.json()
            
            state = job_status.get("state")
            print(f"Job state: {state} (elapsed: {elapsed_time}s)")
            
            if state == "JobComplete":
                print("Job completed successfully!")
                break
            elif state == "Failed" or state == "Aborted":
                error_msg = f"Job {state.lower()}: {job_status.get('errorMessage', 'Unknown error')}"
                print(f"Error: {error_msg}")
                all_results["success"] = False
                all_results["errors"].append({"step": "job_processing", "error": error_msg})
                return all_results
            elif state in ["InProgress", "Open"]:
                time.sleep(poll_interval)
                elapsed_time += poll_interval
            else:
                print(f"Unknown state: {state}, continuing to poll...")
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error polling job status: {str(e)}"
            print(f"Error: {error_msg}")
            all_results["success"] = False
            all_results["errors"].append({"step": "poll_status", "error": error_msg})
            return all_results
    
    if elapsed_time >= max_wait_time:
        error_msg = "Job did not complete within the maximum wait time"
        print(f"Error: {error_msg}")
        all_results["success"] = False
        all_results["errors"].append({"step": "poll_status", "error": error_msg})
        return all_results
    
    # ---------------------------
    # Step 5: Get Results
    # ---------------------------
    print("\nStep 5: Retrieving results...")
    
    # Get successful results
    success_url = f"{bulk_api_base}/{job_id}/successfulResults"
    try:
        response = requests.get(success_url, headers=json_headers, timeout=30)
        response.raise_for_status()
        success_content = response.text
        if success_content:
            # Parse CSV results
            success_reader = csv.DictReader(io.StringIO(success_content))
            for row in success_reader:
                all_results["successful"] += 1
                if "sf__Id" in row:
                    all_results["created_ids"].append(row["sf__Id"])
            print(f"Successfully processed: {all_results['successful']} records")
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not retrieve successful results: {str(e)}")
    
    # Get failed results
    failed_url = f"{bulk_api_base}/{job_id}/failedResults"
    try:
        response = requests.get(failed_url, headers=json_headers, timeout=30)
        response.raise_for_status()
        failed_content = response.text
        if failed_content:
            # Parse CSV results
            failed_reader = csv.DictReader(io.StringIO(failed_content))
            for row in failed_reader:
                all_results["failed"] += 1
                error_msg = row.get("sf__Error", "Unknown error")
                all_results["errors"].append({
                    "record": row.get("sf__Id", "Unknown"),
                    "error": error_msg
                })
            print(f"Failed: {all_results['failed']} records")
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not retrieve failed results: {str(e)}")
    
    # Print summary
    print(f"\n=== Deployment Summary ===")
    print(f"Total records: {all_results['total_records']}")
    print(f"Successful: {all_results['successful']}")
    print(f"Failed: {all_results['failed']}")
    if all_results['errors']:
        print(f"\nErrors:")
        for error in all_results['errors'][:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(all_results['errors']) > 10:
            print(f"  ... and {len(all_results['errors']) - 10} more errors")
    
    all_results["success"] = all_results["failed"] == 0
    return all_results


# --------------------------------------------------------
# TEST CSV DATA DEPLOYMENT
# --------------------------------------------------------
if __name__ == "__main__":
    # Test deploying sample Account records from CSV
    csv_file = "sample_accounts.csv"
    sobject_type = "Account"
    
    print("=" * 60)
    print("Testing CSV Data Deployment")
    print("=" * 60)
    
    try:
        result = deploy_csv_data(csv_file, sobject_type)
        
        print("\n" + "=" * 60)
        print("FINAL RESULT")
        print("=" * 60)
        print(f"Success: {result['success']}")
        print(f"Total Records: {result['total_records']}")
        print(f"Successful: {result['successful']}")
        print(f"Failed: {result['failed']}")
        
        if result['created_ids']:
            print(f"\nCreated Record IDs (first 10):")
            for record_id in result['created_ids'][:10]:
                print(f"  - {record_id}")
        
        if result['errors']:
            print(f"\nErrors encountered:")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Make sure {csv_file} exists in the current directory.")
    except Exception as e:
        print(f"Error during deployment: {e}")
        import traceback
        traceback.print_exc()

