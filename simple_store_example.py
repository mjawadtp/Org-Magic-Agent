from simple_store import SimpleStore

# Create a store instance
store = SimpleStore()

# Example 1: Save org details
store.set("org_details", {
    "instance_url": "https://mycompany.salesforce.com",
    "username": "mjawadtp@example.com",
    "access_token": "00D1234567890ABC",
    "api_version": "60.0"
})

print("Saved org details\n")

# Example 2: Retrieve org details later (e.g., in a deploy function)
org_details = store.get("org_details")
if org_details:
    print(f"Retrieved org details: {org_details['instance_url']}\n")
    # Use org_details["instance_url"] and org_details["access_token"] for deployment

# Example 3: Save any data
store.set("last_deployment", "RemoteSiteSetting")
store.set("environment", "production")

# Example 4: Get all stored data
all_data = store.get_all()
print(f"All stored data: {all_data}\n")