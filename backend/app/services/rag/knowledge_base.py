import os
from typing import List, Dict, Any, Optional
import structlog
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.services.rag.document_processor import DocumentProcessor, get_initial_knowledge_base

logger = structlog.get_logger()


class KnowledgeBase:
    """RAG Knowledge Base using ChromaDB for vector storage."""

    def __init__(self, collection_name: str = "cyberx_knowledge"):
        self.collection_name = collection_name
        self.document_processor = DocumentProcessor()

        # Initialize ChromaDB client
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=settings.VECTOR_DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            f"Knowledge base initialized",
            collection=collection_name,
            documents=self.collection.count(),
        )

    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """Add documents to the knowledge base."""
        if not documents:
            return 0

        ids = []
        contents = []
        metadatas = []

        for doc in documents:
            chunk_id = doc.get("metadata", {}).get("chunk_id", str(hash(doc["content"])))
            ids.append(chunk_id)
            contents.append(doc["content"])
            metadatas.append(doc.get("metadata", {}))

        self.collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas,
        )

        logger.info(f"Added {len(documents)} documents to knowledge base")
        return len(documents)

    def add_text(
        self,
        text: str,
        source: str = "direct_input",
        title: Optional[str] = None,
        category: Optional[str] = None,
    ) -> int:
        """Add raw text to the knowledge base."""
        chunks = self.document_processor.process_text(text, source, title, category)
        return self.add_documents(chunks)

    def add_file(self, file_path: str) -> int:
        """Add a file to the knowledge base."""
        chunks = self.document_processor.process_document(file_path)
        return self.add_documents(chunks)

    def add_directory(self, directory_path: str) -> int:
        """Add all files from a directory to the knowledge base."""
        chunks = self.document_processor.process_directory(directory_path)
        return self.add_documents(chunks)

    def search(
        self,
        query: str,
        n_results: int = None,
        category: Optional[str] = None,
        min_relevance: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant documents."""
        n_results = n_results or settings.TOP_K_RESULTS

        where_filter = None
        if category:
            where_filter = {"category": category}

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        # Format results
        formatted_results = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                relevance = 1 - distance  # Convert distance to similarity

                if relevance >= min_relevance:
                    formatted_results.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "relevance": relevance,
                        "id": results["ids"][0][i] if results["ids"] else None,
                    })

        return formatted_results

    def get_context_for_query(
        self,
        query: str,
        n_results: int = None,
        max_tokens: int = 2000,
    ) -> str:
        """Get formatted context for a query to inject into AI prompt."""
        results = self.search(query, n_results=n_results)

        if not results:
            return ""

        context_parts = []
        total_chars = 0

        for result in results:
            content = result["content"]
            source = result["metadata"].get("source", "Unknown")
            title = result["metadata"].get("title", "")

            # Approximate token count (1 token ≈ 4 chars)
            if total_chars + len(content) > max_tokens * 4:
                break

            header = f"### Source: {title or source}"
            context_parts.append(f"{header}\n{content}")
            total_chars += len(content)

        return "\n\n---\n\n".join(context_parts)

    def get_sources_for_query(
        self,
        query: str,
        n_results: int = None,
    ) -> List[Dict[str, Any]]:
        """Get source information for citation."""
        results = self.search(query, n_results=n_results)

        return [
            {
                "title": r["metadata"].get("title", r["metadata"].get("source", "Unknown")),
                "source": r["metadata"].get("source", ""),
                "category": r["metadata"].get("category", ""),
                "relevance": r["relevance"],
                "preview": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
            }
            for r in results
        ]

    def delete_by_source(self, source: str) -> int:
        """Delete all documents from a specific source."""
        # Get IDs matching the source
        results = self.collection.get(
            where={"source": source},
        )

        if results and results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} documents from source: {source}")
            return len(results["ids"])

        return 0

    def clear(self) -> None:
        """Clear all documents from the knowledge base."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Knowledge base cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        count = self.collection.count()

        # Get unique sources
        all_metadata = self.collection.get()
        sources = set()
        categories = set()

        if all_metadata and all_metadata["metadatas"]:
            for meta in all_metadata["metadatas"]:
                if meta.get("source"):
                    sources.add(meta["source"])
                if meta.get("category"):
                    categories.add(meta["category"])

        return {
            "total_documents": count,
            "unique_sources": len(sources),
            "sources": list(sources),
            "categories": list(categories),
        }

    def initialize_with_defaults(self) -> int:
        """Initialize knowledge base with default cybersecurity content."""
        if self.collection.count() > 0:
            logger.info("Knowledge base already has content, skipping initialization")
            return 0

        initial_docs = get_initial_knowledge_base()
        return self.add_documents(initial_docs)


# Singleton instance
knowledge_base = KnowledgeBase()
