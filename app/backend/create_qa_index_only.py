import asyncio
import os
from azure.identity.aio import AzureDeveloperCliCredential
from azure.search.documents.indexes.aio import SearchIndexClient
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

async def create_qa_index():
    # Load environment variables
    load_azd_env()
    
    # Get Azure Search service details
    search_service = os.environ["AZURE_SEARCH_SERVICE"]
    search_endpoint = f"https://{search_service}.search.windows.net"
    qa_index_name = os.environ["AZURE_SEARCH_QA_INDEX"]
    
    print(f"Creating index '{qa_index_name}' in search service '{search_service}'...")
    
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
            return
        
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

if __name__ == "__main__":
    asyncio.run(create_qa_index())