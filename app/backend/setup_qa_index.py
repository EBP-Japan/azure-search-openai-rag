import asyncio
import os
from azure.identity.aio import AzureDeveloperCliCredential
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    SemanticSearch,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    HnswParameters,
)

from load_azd_env import load_azd_env

async def setup_qa_index():
    # Load environment variables
    load_azd_env()
    
    # Get Azure Search service details
    search_service = os.environ["AZURE_SEARCH_SERVICE"]
    search_endpoint = f"https://{search_service}.search.windows.net"
    # qa_index_name = os.environ.get("AZURE_SEARCH_QA_INDEX", "gptkbindex_qa")
    qa_index_name = os.environ["AZURE_SEARCH_QA_INDEX"]
    
    # Set up Azure credentials
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    if tenant_id:
        credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    else:
        credential = AzureDeveloperCliCredential(process_timeout=60)
    
    # Create a search index client
    async with SearchIndexClient(endpoint=search_endpoint, credential=credential) as client:
        # Check if index already exists
        index_names = [name async for name in client.list_index_names()]
        if qa_index_name in index_names:
            print(f"Index '{qa_index_name}' already exists.")
        else:
            # Define vector search components
            vector_search_algorithm = HnswAlgorithmConfiguration(
                name="hnsw_config",
                parameters=HnswParameters(metric="cosine")
            )
            
            vector_search_profile = VectorSearchProfile(
                name="embedding-profile",
                algorithm_configuration_name=vector_search_algorithm.name
            )
            
            # Define fields for the Q&A index
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
                SimpleField(name="sourcepage", type=SearchFieldDataType.String, filterable=True, facetable=True),
                SimpleField(name="sourcefile", type=SearchFieldDataType.String, filterable=True, facetable=True),
                SimpleField(name="oids", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name="embedding-profile"
                )
            ]
            
            # Create the index
            index = SearchIndex(
                name=qa_index_name,
                fields=fields,
                semantic_search=SemanticSearch(
                    default_configuration_name="default",
                    configurations=[
                        SemanticConfiguration(
                            name="default",
                            prioritized_fields=SemanticPrioritizedFields(
                                title_field=SemanticField(field_name="sourcepage"),
                                content_fields=[SemanticField(field_name="content")]
                            )
                        )
                    ]
                ),
                vector_search=VectorSearch(
                    profiles=[vector_search_profile],
                    algorithms=[vector_search_algorithm]
                )
            )
            
            print(f"Creating index '{qa_index_name}'...")
            await client.create_index(index)
            print(f"Index '{qa_index_name}' created successfully!")
    
    # Upload sample data
    # file_path = os.path.join(os.path.dirname(__file__), "sample_qa.csv")
    file_name = "nra_1_attachment.csv"
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    
    if not os.path.exists(file_path):
        print(f"Sample file not found at {file_path}")
        return
    
    # Read the CSV file
    with open(file_path, 'r', encoding='UTF-8-SIG') as file:
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
                "sourcepage": f"{file_name}",
                "sourcefile": file_name
            })
    
    # Upload documents to the index
    async with SearchClient(
        endpoint=search_endpoint,
        index_name=qa_index_name,
        credential=credential
    ) as search_client:
        print(f"Uploading {len(qa_pairs)} Q&A pairs to index '{qa_index_name}'...")
        result = await search_client.upload_documents(documents=qa_pairs)
        print(f"Upload completed with status: {result[0].succeeded}")

if __name__ == "__main__":
    asyncio.run(setup_qa_index())