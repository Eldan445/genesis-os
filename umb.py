# umb.py (Wedge 2 - Using local SentenceTransformer)

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction 
import os 
import uuid

class UniversalMemoryBus:
    def __init__(self):
        # 1. ChromaDB Client Setup
        # Note: If you encounter issues, ensure your genesis_memory folder is clean or deleted on first run
        self.client = chromadb.PersistentClient(path="./genesis_memory")
        
        # 2. Embedding Function Setup (SentenceTransformer for local, free embeddings)
        # This will download the model 'all-MiniLM-L6-v2' on first run.
        self.embedding_function = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2" 
        )
        self.collection = self.client.get_or_create_collection(
            name="genesis_knowledge",
            embedding_function=self.embedding_function
        )
        
        # Initial check to populate with default memory if empty
        if self.collection.count() == 0:
            self._populate_default_memory()


    def _populate_default_memory(self):
        """Populates the UMB with essential, foundational knowledge."""
        print("💾 [UMB] Initializing foundational knowledge...")
        self.save_memory("The default format for market reports should be a summary of 3 bullet points.", {"type": "system_config"})
        self.save_memory("All scheduled meetings should be set for the next available Friday afternoon.", {"type": "system_config"})


    def save_memory(self, memory_text, metadata=None):
        """Stores a piece of knowledge into the UMB."""
        if metadata is None:
            metadata = {}
            
        print(f"💾 [UMB] Storing memory: {memory_text[:40]}...")
        self.collection.add(
            documents=[memory_text],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )
        # We don't print "Success" here to keep the terminal clean during execution

    def retrieve_context(self, query):
        """Retrieves relevant context based on a query (RAG)."""
        print(f"🔍 [UMB] Retrieving context for: {query[:40]}...")
        
        if self.collection.count() == 0:
            return "No prior memory available. System is fresh."

        results = self.collection.query(
            query_texts=[query],
            n_results=1
        )
        
        # Format the result for the LLM
        if results and results['documents'] and results['documents'][0]:
            return f"Found prior knowledge: {results['documents'][0][0]}"
        return "No relevant prior memory found."

# Test Function (Useful for pre-populating data)
if __name__ == "__main__":
    try:
        # Note: If you run this, it will re-initialize the UMB
        umb = UniversalMemoryBus()
        print("\n--- UMB Test Retrieval ---")
        print(umb.retrieve_context("How should I format the report?"))
    except Exception as e:
        print(f"Error during UMB test: {e}")




