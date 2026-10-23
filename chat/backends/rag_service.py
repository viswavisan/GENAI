"""
Retrieval-Augmented Generation (RAG) Service for GenAI Studio.
Provides document ingestion, text chunking, vector embeddings, similarity search,
augmented prompt construction, and grounded generation with full pipeline transparency.
"""
import os
import re
import math
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = "gemini-embedding-001"

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


# Default Initial Knowledge Documents (Clean & Empty by default)
DEFAULT_DOCUMENTS = []


class RAGKnowledgeBase:
    """In-memory Knowledge Base with chunking, embeddings, and cosine similarity retrieval."""

    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.chunks: List[Dict[str, Any]] = []
        self._load_defaults()

    def _load_defaults(self):
        """Scans the project documents directory (GENAI/documents/) and auto-ingests all files."""
        self.documents.clear()
        self.chunks.clear()

        # Target directory in project root: 'documents/' (or 'chat/data/' as fallback)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidate_folders = [
            os.path.join(project_root, "documents"),
            os.path.join(os.getcwd(), "documents"),
            os.path.join(project_root, "chat", "data"),
            os.path.join(os.getcwd(), "chat", "data"),
        ]

        target_folder = None
        for folder in candidate_folders:
            if os.path.isdir(folder) and os.listdir(folder):
                target_folder = folder
                break

        if not target_folder:
            return

        supported_exts = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".json", ".log"}
        file_count = 0

        for filename in sorted(os.listdir(target_folder)):
            filepath = os.path.join(target_folder, filename)
            if not os.path.isfile(filepath):
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext not in supported_exts:
                continue

            base_name = os.path.splitext(filename)[0]
            clean_title = base_name.replace("-", " ").replace("_", " ").title()
            if "resume" in base_name.lower():
                clean_title = "Resume - Viswanathan L"
                category = "Resume"
            else:
                category = "General"

            content = ""
            try:
                if ext == ".pdf":
                    import pypdf
                    reader = pypdf.PdfReader(filepath)
                    pages_text = []
                    for page_num, page in enumerate(reader.pages, 1):
                        p_text = page.extract_text() or ""
                        if p_text.strip():
                            pages_text.append(f"[Page {page_num}]\n{p_text.strip()}")
                    content = "\n\n".join(pages_text).strip()

                elif ext == ".docx":
                    import docx
                    doc_obj = docx.Document(filepath)
                    paras = [p.text.strip() for p in doc_obj.paragraphs if p.text.strip()]
                    content = "\n\n".join(paras).strip()

                elif ext in {".txt", ".md", ".csv", ".json", ".log"}:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().strip()

                if content:
                    doc_id = f"doc_{re.sub(r'[^a-zA-Z0-9_]', '_', base_name.lower())}_{file_count}"
                    self.add_document(doc_id, clean_title, content, category)
                    file_count += 1
            except Exception:
                pass

    def add_document(self, doc_id: str, title: str, content: str, category: str = "General") -> Dict[str, Any]:
        """Ingests a document and breaks it into semantic chunks."""
        clean_content = content.strip()
        doc = {
            "id": doc_id,
            "title": title.strip(),
            "content": clean_content,
            "category": category,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.documents[doc_id] = doc

        # Chunk document (900 characters with 150 overlap to preserve full paragraphs and skill blocks)
        new_chunks = self._chunk_text(doc_id, title, clean_content, chunk_size=900, overlap=150)
        self.chunks.extend(new_chunks)
        return {"document": doc, "chunks_created": len(new_chunks)}

    def remove_document(self, doc_id: str) -> bool:
        """Removes a document and all its chunks from the knowledge base."""
        if doc_id in self.documents:
            del self.documents[doc_id]
            self.chunks = [c for c in self.chunks if c["doc_id"] != doc_id]
            return True
        return False

    def clear(self):
        """Clears all documents and chunks from the knowledge base."""
        self.documents.clear()
        self.chunks.clear()

    def reset_defaults(self):
        """Resets the knowledge base to default state (resume.pdf)."""
        self._load_defaults()

    def get_documents_summary(self) -> List[Dict[str, Any]]:
        """Returns metadata for all indexed documents."""
        summary = []
        for doc_id, doc in self.documents.items():
            doc_chunks = [c for c in self.chunks if c["doc_id"] == doc_id]
            summary.append({
                "id": doc["id"],
                "title": doc["title"],
                "category": doc["category"],
                "chunks_count": len(doc_chunks),
                "created_at": doc.get("created_at", "")
            })
        return summary

    def _chunk_text(self, doc_id: str, title: str, text: str, chunk_size: int = 900, overlap: int = 150) -> List[Dict[str, Any]]:
        """Splits text into overlapping chunks along sentence or whitespace boundaries."""
        chunks = []
        words = text.split()
        if not words:
            return chunks

        step = max(1, chunk_size - overlap)
        cur_pos = 0
        chunk_idx = 1

        # Use character windowing with word boundary protection
        while cur_pos < len(text):
            end_pos = min(len(text), cur_pos + chunk_size)
            # Adjust to word boundary if not at end
            if end_pos < len(text) and not text[end_pos].isspace():
                next_space = text.find(" ", end_pos)
                if next_space != -1 and next_space - end_pos < 50:
                    end_pos = next_space

            chunk_str = text[cur_pos:end_pos].strip()
            if chunk_str:
                chunk_id = f"{doc_id}_c{chunk_idx}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "doc_title": title,
                    "text": chunk_str,
                    "index": chunk_idx,
                    "vector": None  # Computed on-demand or precomputed
                })
                chunk_idx += 1

            if end_pos >= len(text):
                break
            cur_pos += step

        return chunks


# Singleton Knowledge Base instance
kb = RAGKnowledgeBase()


# Common stopwords to exclude from keyword search so they don't skew ranking
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for", "with",
    "by", "from", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "can", "could", "should", "would", "what", "which",
    "who", "whom", "this", "that", "these", "those", "my", "your", "his", "her",
    "show", "tell", "give", "me", "find", "search", "all", "get", "list", "please"
}


def _get_embedding(text: str) -> Optional[List[float]]:
    """Generates vector embedding using Gemini embedding API if available."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not (api_key and HAS_GENAI):
        return None

    try:
        client = genai.Client(api_key=api_key)
        res = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text
        )
        if hasattr(res, "embeddings") and res.embeddings:
            return list(res.embeddings[0].values)
    except Exception:
        pass
    return None


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two numeric vectors."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _lexical_similarity(query: str, text: str) -> float:
    """Calculates keyword overlap similarity after filtering common stopwords."""
    all_q_tokens = re.findall(r'\w+', query.lower())
    meaningful_q = [t for t in all_q_tokens if t not in STOPWORDS]
    if not meaningful_q:
        meaningful_q = all_q_tokens
    q_tokens = set(meaningful_q)
    t_tokens = re.findall(r'\w+', text.lower())
    if not q_tokens or not t_tokens:
        return 0.0

    match_count = sum(1 for t in t_tokens if t in q_tokens)
    ratio = match_count / math.sqrt(len(q_tokens) * len(t_tokens))
    return min(1.0, ratio * 1.5)


def retrieve_top_k(query: str, k: int = 4) -> List[Dict[str, Any]]:
    """
    Performs Hybrid Search:
    1. Semantic Vector Cosine Similarity (Embeddings)
    2. BM25 / Keyword Overlap (filtered stopwords)
    3. Exact Substring & Identifier Boost (for numbers, names, phone, email)
    """
    if not kb.chunks:
        return []

    raw_query_lower = query.lower().strip()
    q_tokens = [t for t in re.findall(r'\w+', raw_query_lower) if t not in STOPWORDS]
    if not q_tokens:
        q_tokens = re.findall(r'\w+', raw_query_lower)

    query_vec = _get_embedding(query)
    scored_chunks = []

    for chunk in kb.chunks:
        chunk_text_lower = chunk["text"].lower()
        vector_score = 0.0
        method = "lexical"

        if query_vec:
            if chunk.get("vector") is None:
                chunk["vector"] = _get_embedding(chunk["text"])

            if chunk.get("vector"):
                vector_score = _cosine_similarity(query_vec, chunk["vector"])
                method = "semantic_vector"

        lexical_score = _lexical_similarity(query, chunk["text"])

        # Exact substring / keyword match boost for names, phone numbers, exact terms
        exact_boost = 0.0
        for token in q_tokens:
            if len(token) >= 2 and token in chunk_text_lower:
                exact_boost += 0.35 if token.isdigit() else 0.20

        # Entire raw query verbatim match
        if len(raw_query_lower) >= 4 and raw_query_lower in chunk_text_lower:
            exact_boost += 0.50

        # Calculate Combined Hybrid Score
        if vector_score > 0.0:
            final_score = (vector_score * 0.65) + (lexical_score * 0.25) + exact_boost
            if exact_boost > 0:
                method = "hybrid_vector_exact"
        else:
            final_score = lexical_score + exact_boost
            method = "hybrid_bm25_exact" if exact_boost > 0 else "lexical_bm25"

        scored_chunks.append({
            "chunk_id": chunk["chunk_id"],
            "doc_id": chunk["doc_id"],
            "doc_title": chunk["doc_title"],
            "text": chunk["text"],
            "similarity_score": round(final_score, 4),
            "match_percentage": round(min(1.0, max(0.0, final_score)) * 100, 1),
            "method": method
        })

    # Sort descending by similarity score
    scored_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored_chunks[:k]


def execute_rag_pipeline(user_query: str, top_k: int = 4) -> Dict[str, Any]:
    """
    Full end-to-end RAG pipeline:
    1. Retrieve Top-K relevant knowledge chunks using Hybrid Search.
    2. Build Augmented Context Prompt.
    3. Generate Grounded LLM Response with chunk citations.
    4. Return full pipeline trace for UI inspection.
    """
    start_time = time.time()
    retrieved = retrieve_top_k(user_query, k=top_k)

    # Format Context Injection Block
    context_blocks = []
    for i, c in enumerate(retrieved, 1):
        context_blocks.append(f"[{i}] (Source: '{c['doc_title']}' | Match: {c['match_percentage']}%)\n{c['text']}")

    context_str = "\n\n".join(context_blocks) if context_blocks else "No relevant knowledge found."

    augmented_prompt = (
        f"You are a factual, precision AI assistant. Answer the user's question directly, clearly, and concisely using ONLY the retrieved context below.\n"
        f"Cite the exact sources using bracketed citations like [1] or [2] whenever stating facts from the context.\n"
        f"If the answer is explicitly found in the context (like a name, phone number, skill, or project), state it clearly.\n"
        f"If the answer cannot be found in the provided context, state clearly: "
        f"'I cannot find this information in the provided knowledge base.'\n\n"
        f"=== RETRIEVED KNOWLEDGE CONTEXT ===\n"
        f"{context_str}\n\n"
        f"=== USER QUESTION ===\n"
        f"{user_query}\n\n"
        f"=== GROUNDED ANSWER ==="
    )

    api_key = os.getenv("GEMINI_API_KEY")
    reply_text = ""
    engine_used = "Offline Fallback (Heuristic RAG)"

    if api_key and HAS_GENAI:
        # Multi-model quota fallback chain
        candidate_models = [
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash-lite",
            os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "gemini-flash-lite-latest",
            "gemini-flash-latest"
        ]
        candidate_models = list(dict.fromkeys(candidate_models))
        client = genai.Client(api_key=api_key)
        for model_cand in candidate_models:
            try:
                resp = client.models.generate_content(
                    model=model_cand,
                    contents=augmented_prompt
                )
                if resp.text:
                    reply_text = resp.text.strip()
                    engine_used = f"Google Gemini ({model_cand})"
                    break
            except Exception:
                continue

    if not reply_text:
        # Offline heuristic fallback
        if retrieved and retrieved[0]["similarity_score"] > 0.05:
            top = retrieved[0]
            reply_text = (
                f"Based on **{top['doc_title']}** [1]:\n\n"
                f"{top['text']}\n\n"
                f"*(Note: LLM quota limit reached. Above is the most relevant raw passage retrieved with {top['match_percentage']}% match.)*"
            )
        else:
            reply_text = "I cannot find this information in the provided knowledge base."

    duration_ms = round((time.time() - start_time) * 1000, 1)

    return {
        "query": user_query,
        "reply": reply_text,
        "retrieved_chunks": retrieved,
        "augmented_prompt": augmented_prompt,
        "engine": engine_used,
        "latency_ms": duration_ms,
        "total_chunks_scanned": len(kb.chunks),
        "total_docs_indexed": len(kb.documents)
    }
