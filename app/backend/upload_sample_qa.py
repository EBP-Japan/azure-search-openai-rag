import asyncio
import os
import aiohttp
import json
from azure.identity.aio import AzureDeveloperCliCredential
from load_azd_env import load_azd_env

async def upload_sample_qa():
    # Load environment variables
    load_azd_env()
    
    # Get Azure Search service details
    backend_uri = os.environ.get("BACKEND_URI", "http://localhost:50505")
    qa_index_name = os.environ.get("AZURE_SEARCH_QA_INDEX", "gptkbindex_qa")
    
    # Set up Azure credentials for token
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    if tenant_id:
        credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    else:
        credential = AzureDeveloperCliCredential(process_timeout=60)
    
    # Get token for authentication
    token = await credential.get_token("https://management.azure.com/.default")
    
    # Prepare the file for upload
    file_path = os.path.join(os.path.dirname(__file__), "sample_qa.csv")
    # file_path = os.path.join(os.path.dirname(__file__), "nra_1_attachment.csv")
    
    if not os.path.exists(file_path):
        print(f"Sample file not found at {file_path}")
        return
    
    # Upload the file directly to the index
    print(f"Uploading sample Q&A data to index '{qa_index_name}'...")
    
    # Read the CSV file
    with open(file_path,'r', encoding='UTF-8-SIG') as file:
        lines = file.readlines()
    
    # Skip header
    qa_pairs = []
    for i, line in enumerate(lines[1:]):
        parts = line.strip().split(',', 1)
        if len(parts) == 2:
            question, answer = parts
            qa_pairs.append({
                "id": f"qa-{i+1}",
                "content": f"Question: {question}\nAnswer: {answer}",
                "category": "QA",
                "sourcepage": f"sample_qa.csv",
                "sourcefile": "sample_qa.csv"
            })
    
    # Use the Azure Search REST API to upload documents directly
    search_service = os.environ["AZURE_SEARCH_SERVICE"]
    search_endpoint = f"https://{search_service}.search.windows.net"
    api_version = "2023-10-01-Preview"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": await get_admin_key(credential),
    }
    
    url = f"{search_endpoint}/indexes/{qa_index_name}/docs/index?api-version={api_version}"
    
    payload = {
        "value": qa_pairs
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200 or response.status == 201:
                result = await response.json()
                print(f"Successfully uploaded {len(qa_pairs)} Q&A pairs to index '{qa_index_name}'")
                print(f"Result: {json.dumps(result, indent=2)}")
            else:
                error_text = await response.text()
                print(f"Error uploading documents: {response.status}")
                print(error_text)

async def get_admin_key(credential):
    # This is a simplified approach - in production, you should use a more secure method
    # to get the admin key, such as Azure Key Vault
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_SEARCH_SERVICE_RESOURCE_GROUP"]
    search_service = os.environ["AZURE_SEARCH_SERVICE"]
    
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Search/searchServices/{search_service}/listAdminKeys?api-version=2020-08-01"
    
    token = await credential.get_token("https://management.azure.com/.default")
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                return result["primaryKey"]
            else:
                error_text = await response.text()
                print(f"Error getting admin key: {response.status}")
                print(error_text)
                return None

if __name__ == "__main__":
    asyncio.run(upload_sample_qa())