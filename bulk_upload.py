import requests

# TODO: Replace with your org's instance URL and a fresh access token
BASE_URL = "https://dtc000004zfvn2ay.sfdctest.test1.my.pc-rnd.salesforce.com"
API_VERSION = "v66.0"
ACCESS_TOKEN = "Bearer 00DTC000004zfVN2AY!AQEAQJBaxP7ue.PYULwnrV7KFUECTR1yG0FOCqLxmTXhN7VzVZtmfDpbq_Dn_FJIkYBwuBJINOzPdXaO4d7znjpd54KOUI0g"

def _auth_headers(content_type: str):
    return {
        "Authorization": ACCESS_TOKEN,
        "Content-Type": content_type,
    }


def _create_ingest_job(object_name: str = "Account"):
    url = f"{BASE_URL}/services/data/{API_VERSION}/jobs/ingest"
    print("url", url)
    payload = {
        "object": object_name,
        "operation": "insert",
        "lineEnding": "LF",
        "columnDelimiter": "COMMA",
    }
    response = requests.post(
        url,
        headers=_auth_headers("application/json"),
        json=payload,
        timeout=30,
    )
    print("response", response.json())
    response.raise_for_status()
    return response.json()["id"]


def _upload_csv_batch(job_id: str, csv_body: str):
    url = f"{BASE_URL}/services/data/{API_VERSION}/jobs/ingest/{job_id}/batches"
    print("url", url)
    response = requests.put(
        url,
        headers=_auth_headers("text/csv"),
        data=csv_body,
        timeout=30,
    )
    response.raise_for_status()


def _close_ingest_job(job_id: str):
    url = f"{BASE_URL}/services/data/{API_VERSION}/jobs/ingest/{job_id}"
    response = requests.patch(
        url,
        headers=_auth_headers("application/json"),
        json={"state": "UploadComplete"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_job_status(job_id: str) -> str:
    """
    Fetch ingest job status via Bulk API v2 and return the state.
    Endpoint: GET /services/data/{version}/jobs/ingest/{jobId}
    """
    url = f"{BASE_URL}/services/data/{API_VERSION}/jobs/ingest/{job_id}"
    response = requests.get(url, headers=_auth_headers("application/json"), timeout=30)
    response.raise_for_status()
    return response.json().get("state")


def bulk_upload_accounts(records):
    """
    Bulk upload Account records (Name, MobilePhone) via Bulk API v2 ingest.

    Args:
        records: Iterable of dicts with keys 'Name' and 'MobilePhone'

    Returns:
        Dict with jobId and final state.
    """
    rows = list(records)
    if not rows:
        return {"jobId": None, "state": "NoRecords"}

    csv_lines = ["Name"]
    for row in rows:
        name = row.get("Name", "")
        csv_lines.append(f"{name}")

    csv_body = "\n".join(csv_lines)
    job_id = _create_ingest_job("Account")
    _upload_csv_batch(job_id, csv_body)
    job_info = _close_ingest_job(job_id)
    return {"jobId": job_id, "state": job_info.get("state")}


if __name__ == "__main__":
    sample_records = [
        {"Name": "Acme One"},
        {"Name": "Beta Two"},
    ]
    result = bulk_upload_accounts(sample_records)
    job_id = result.get("jobId")
    print(result)
    if job_id:
        state = get_job_status(job_id)
        print(f"Job {job_id} state: {state}")


