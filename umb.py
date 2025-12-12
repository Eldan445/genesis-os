import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction 
import uuid
import datetime
import streamlit as st

# CACHING: Prevents "Database Locked" errors on Streamlit Cloud
@st.cache_resource(show_spinner="Initializing Neural Memory...")
def get_memory_bus():
    return UniversalMemoryBus()

class UniversalMemoryBus:
    def __init__(self):
        # 1. SETUP
        # We use a persistent path so memory survives restarts
        self.client = chromadb.PersistentClient(path="./genesis_memory")
        
        # 2. EMBEDDING MODEL (Local & Free)
        self.embedding_function = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2" 
        )
        
        # 3. COLLECTION
        self.collection = self.client.get_or_create_collection(
            name="genesis_knowledge",
            embedding_function=self.embedding_function
        )
        
        # 4. BOOTSTRAP DEFAULTS
        if self.collection.count() == 0:
            self._populate_default_memory()

    def _populate_default_memory(self):
        """Injects core operational rules."""
        defaults = [
            ("User prefers concise, terminal-style answers.", "personality"),
            ("Default meeting duration is 30 minutes.", "scheduler_rule"),
            ("Always ask for confirmation before sending external emails.", "security_protocol"),
            ("Genesis is an Agentic OS, not a chatbot.", "identity")
        ]
        for text, category in defaults:
            self.save_memory(text, {"type": "core_directive", "category": category})

    def save_memory(self, memory_text: str, metadata: dict = None):
        if metadata is None: metadata = {}
        metadata["timestamp"] = datetime.datetime.now().isoformat()
        
        self.collection.add(
            documents=[memory_text],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )

    def retrieve_context(self, query: str, n_results=2):
        if self.collection.count() == 0: return ""
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        context_string = ""
        if results and results['documents']:
            for doc in results['documents'][0]:
                context_string += f"- {doc}\n"
        
        return context_string