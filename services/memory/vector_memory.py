import chromadb
from database import CHROMA_PATH
import uuid

# Initialize persistent client
chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

def init_project_collection(project_name: str) -> None:
    """Initialize a ChromaDB collection for a project."""
    # User requested: "project_{project_name}"
    name = f"project_{project_name}"
    # get_or_create_collection is safe to call multiple times
    chroma_client.get_or_create_collection(name=name)

def save_vector_memory(project_name: str, content: str, metadata: dict = None) -> None:
    """Save an action/error/fix as a searchable embedding in the project collection."""
    name = f"project_{project_name}"
    collection = chroma_client.get_or_create_collection(name=name)
    
    doc_id = str(uuid.uuid4())
    collection.add(
        documents=[content],
        metadatas=[metadata or {}],
        ids=[doc_id]
    )

def search_vector_memory(project_name: str, query: str, limit: int = 5) -> list[dict]:
    """Search project memory for similar past actions."""
    name = f"project_{project_name}"
    try:
        collection = chroma_client.get_collection(name=name)
    except Exception:
        # Collection might not exist if no memories saved yet
        return []
        
    results = collection.query(
        query_texts=[query],
        n_results=limit
    )
    
    formatted_results = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        # Check if distances exists
        distances = results.get("distances", [[]])[0] if results.get("distances") else [0.5] * len(docs)
        metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(docs)
        
        for i, (doc, meta) in enumerate(zip(docs, metas)):
            # Convert distance to relevance (rough estimate)
            relevance = 1.0 - (distances[i] if i < len(distances) else 0.5)
            formatted_results.append({
                "content": doc,
                "metadata": meta,
                "relevance": round(relevance, 2)
            })
            
    return formatted_results