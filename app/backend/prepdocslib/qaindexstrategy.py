import logging
from typing import Optional

from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .fileprocessor import FileProcessor
from .listfilestrategy import File
from .searchmanager import SearchManager, Section
from .strategy import SearchInfo
from .filestrategy import parse_file

logger = logging.getLogger("scripts")


class QAIndexStrategy:
    """
    Strategy for ingesting Q&A CSV files into a separate search index
    """

    def __init__(
        self,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        embeddings: Optional[OpenAIEmbeddings] = None,
        search_field_name_embedding: Optional[str] = None,
    ):
        self.file_processors = file_processors
        self.embeddings = embeddings
        self.search_info = search_info
        self.search_field_name_embedding = search_field_name_embedding

    async def create_qa_index(self, index_name: str) -> SearchManager:
        """Create a new search index for Q&A data"""
        # Create a new SearchInfo with the custom index name
        qa_search_info = SearchInfo(
            endpoint=self.search_info.endpoint,
            credential=self.search_info.credential,
            index_name=index_name,
            semantic_config_name=self.search_info.semantic_config_name,
            use_agentic_retrieval=self.search_info.use_agentic_retrieval,
            agent_name=f"{index_name}-agent" if self.search_info.agent_name else None,
            azure_openai_endpoint=self.search_info.azure_openai_endpoint,
            azure_openai_searchagent_deployment=self.search_info.azure_openai_searchagent_deployment,
            azure_openai_searchagent_model=self.search_info.azure_openai_searchagent_model,
            agent_max_output_tokens=self.search_info.agent_max_output_tokens,
        )
        
        # Create a search manager for the new index
        search_manager = SearchManager(
            search_info=qa_search_info,
            search_analyzer_name=None,
            use_acls=True,
            use_int_vectorization=False,
            embeddings=self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=False,
        )
        
        # Create the index
        await search_manager.create_index()
        return search_manager

    async def add_qa_file(self, file: File, index_name: str):
        """Process a Q&A CSV file and add it to the specified index"""
        # Create the index if it doesn't exist
        search_manager = await self.create_qa_index(index_name)
        
        # Parse and process the file
        sections = await parse_file(file, self.file_processors)
        if sections:
            await search_manager.update_content(sections, url=file.url)
            logger.info(f"Added Q&A content to index '{index_name}'")
            return True
        return False