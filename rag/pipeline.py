import os
import logging
import chromadb
from chromadb.utils.embedding_functions import  GoogleGenerativeAiEmbeddingFunction
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "vector_db")
EMBED_MODEL  = "sentence-transformers/all-MiniLM-L6-v2"

_chroma_client = None
_embed_fn      = None
_query_embed_fn = None


def _get_client():
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
    return _chroma_client


def _get_embed_fn():
    global _embed_fn
    if _embed_fn is None:
        _embed_fn = GoogleGenerativeAiEmbeddingFunction(
            model_name="gemini-embedding-001",
            task_type="RETRIEVAL_DOCUMENT",
            api_key=os.getenv("GEMINI_API_KEY"),
        )
    return _embed_fn


def _get_query_embed_fn():
    global _query_embed_fn
    if _query_embed_fn is None:
        _query_embed_fn = GoogleGenerativeAiEmbeddingFunction(
            model_name="gemini-embedding-001",
            task_type="RETRIEVAL_DOCUMENT",
            api_key=os.getenv("GEMINI_API_KEY"),
        )
    return _query_embed_fn


def _sanitize(name: str) -> str:
    """Convert display name to a valid ChromaDB collection name."""
    import re
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", name.strip())
    return f"course_{clean}" if len(clean) < 3 else clean


def list_collections() -> list[dict]:
    """
    Return all indexed courses as list of dicts with display_name and collection_name.
    e.g. [{"display_name": "Andrew Ng ML", "collection_name": "Andrew_Ng_ML"}]
    """
    try:
        collections = _get_client().list_collections()
        result = []
        for col in collections:
            display = col.metadata.get("display_name", col.name) if col.metadata else col.name
            result.append({"display_name": display, "collection_name": col.name})
        return result
    except Exception:
        return []


def course_exists(display_name: str) -> bool:
    """Check if a course with this display name is already indexed."""
    existing = list_collections()
    return any(
        c["display_name"].lower().strip() == display_name.lower().strip()
        for c in existing
    )


def _get_collection(collection_name: str, display_name: str = None, for_query: bool = False):
    embed_fn = _get_query_embed_fn() if for_query else _get_embed_fn()
    metadata = {"hnsw:space": "cosine"}
    if display_name:
        metadata["display_name"] = display_name
    return _get_client().get_or_create_collection(
        name=collection_name,
        embedding_function=embed_fn,
        metadata=metadata,
    )


LOADERS = {
    ".pdf":  PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".xlsx": UnstructuredExcelLoader,
}


def _load_file(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    loader_cls = LOADERS.get(ext)
    if loader_cls is None:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {', '.join(LOADERS.keys())}")
    return loader_cls(file_path).load()


def _clean_chunks(chunks: list) -> list[dict]:
    clean = []
    for i, doc in enumerate(chunks):
        text = doc.page_content
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        text = text.strip().replace("\x00", " ")
        if len(text) < 10:
            continue
        clean.append({
            "id":       f"chunk_{i}",
            "text":     text,
            "metadata": {k: str(v) for k, v in (doc.metadata or {}).items()},
        })
    return clean


def process_file(file_path: str, display_name: str) -> str:
    """
    Index a course file. display_name is what the user typed — stored in
    collection metadata so dropdowns show human-readable names.
    Returns a message string. Raises ValueError if already exists or no text found.
    """
    # Check duplicate by display name
    if course_exists(display_name):
        raise ValueError(
            f"'{display_name}' is already indexed. "
            f"Go to Summary or Notes tab to use it directly."
        )

    docs = _load_file(file_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    raw_chunks = splitter.split_documents(docs)
    clean = _clean_chunks(raw_chunks)

    if not clean:
        raise ValueError(
            "No readable text found in this file.\n"
            "If it's a scanned PDF, pages are images — use a text-based PDF "
            "where you can select and copy text."
        )

    collection_name = _sanitize(display_name)
    collection = _get_collection(collection_name, display_name=display_name)

    batch_size = 50
    for start in range(0, len(clean), batch_size):
        batch = clean[start: start + batch_size]
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
        )

    return f"✅ Indexed {len(clean)} chunks for '{display_name}'."


def retrieve_notes_content(query: str, collection_name: str, k: int = 7) -> str:
    try:
        collection = _get_collection(collection_name, for_query=True)
        count = collection.count()
    except Exception as e:
        logger.warning(f"Collection access failed for '{collection_name}': {e}")
        return f"No content found. Please upload the course file first."

    if count == 0:
        return "No content found. Please upload the course file first."

    results = collection.query(query_texts=[query], n_results=min(k, count))
    docs = results.get("documents", [[]])[0]
    if not docs:
        return "No relevant content found for this query."
    return "\n\n".join(docs)
