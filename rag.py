import os
import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import chromadb
from chromadb.utils import embedding_functions
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document as LangchainDocument, BaseRetriever
from pypdf import PdfReader
from models import Document, Role, User
from auth import has_access_to_document, log_action

# Initialize ChromaDB
client = chromadb.PersistentClient("./chroma_db")
embedding_function = embedding_functions.DefaultEmbeddingFunction()

# Create collections for different document types
document_collection = client.get_or_create_collection(
    name="documents",
    embedding_function=embedding_function,
    metadata={"hnsw:space": "cosine"}
)

# Initialize Groq LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not found in environment variables. Chat functionality will be limited.")
    llm = None
else:
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model_name="llama3-70b-8192",
        temperature=0.5,
        max_tokens=1024
    )


def process_pdf(file_path: str, user: User, title: str = None, access_roles: List[Role] = None) -> Document:
    """
    Process a PDF file, extract text, split into chunks, and store in ChromaDB with role-based access control
    """
    if not title:
        title = os.path.basename(file_path)
    
    # Default access roles if not specified
    if not access_roles:
        if user.role == Role.EXECUTIVE:
            access_roles = [Role.EXECUTIVE, Role.MANAGER, Role.EMPLOYEE]
        elif user.role == Role.MANAGER:
            access_roles = [Role.MANAGER, Role.EMPLOYEE]
        else:
            access_roles = [Role.EMPLOYEE]
    
    # Check if user has permission to assign these roles
    if user.role == Role.EMPLOYEE and any(role != Role.EMPLOYEE for role in access_roles):
        raise ValueError("Employees can only assign Employee-level access")
    
    if user.role == Role.MANAGER and Role.EXECUTIVE in access_roles:
        raise ValueError("Managers cannot assign Executive-level access")
    
    # Extract text from PDF
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    
    # Generate a unique document ID
    doc_id = str(uuid.uuid4())
    
    # Store document metadata
    document = Document(
        id=doc_id,
        title=title,
        content=text[:1000] + "...",  # Store a preview of the content
        metadata={
            "source": file_path,
            "pages": len(reader.pages),
            "department": user.department
        },
        access_roles=[role.value for role in access_roles],
        uploaded_by=user.username
    )
    
    # Save document metadata to a JSON file
    save_document_metadata(document)
    
    # Add chunks to ChromaDB with document metadata
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [{
        "document_id": doc_id,
        "title": title,
        "chunk": i,
        "access_roles": json.dumps([role.value for role in access_roles]),
        "department": user.department,
        "uploaded_by": user.username,
        "uploaded_at": str(datetime.now())
    } for i in range(len(chunks))]
    
    document_collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas
    )
    
    # Log the document upload
    log_action(
        user.username, 
        user.role, 
        "upload_document", 
        {"document_id": doc_id, "title": title, "access_roles": [role.value for role in access_roles]}
    )
    
    return document


def save_document_metadata(document: Document):
    """Save document metadata to a JSON file"""
    os.makedirs("documents", exist_ok=True)
    with open(f"documents/{document.id}.json", "w") as f:
        json.dump(document.dict(), f, default=str)


def get_document_metadata(doc_id: str) -> Optional[Document]:
    """Get document metadata from JSON file"""
    try:
        with open(f"documents/{doc_id}.json", "r") as f:
            data = json.load(f)
            return Document(**data)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def search_documents(query: str, user: User, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for documents based on query and filter by user's role and department
    """
    # Log the search action
    log_action(user.username, user.role, "search", {"query": query})
    
    # Perform the search
    results = document_collection.query(
        query_texts=[query],
        n_results=top_k * 3  # Retrieve more results than needed to account for filtering
    )
    
    filtered_results = []
    seen_doc_ids = set()
    
    for i, (doc_id, document, metadata) in enumerate(zip(results["ids"][0], results["documents"][0], results["metadatas"][0])):
        # Extract document ID from chunk ID
        original_doc_id = doc_id.split("_")[0]
        
        # Skip if we've already included this document
        if original_doc_id in seen_doc_ids:
            continue
        
        # Parse access roles from metadata
        access_roles = [Role(role) for role in json.loads(metadata["access_roles"])]
        
        # Check if user has access to this document
        if has_access_to_document(user.role, access_roles):
            # If user is not an executive, also check department match
            if user.role != Role.EXECUTIVE and metadata["department"] != user.department:
                continue
                
            # Add to filtered results
            filtered_results.append({
                "document_id": original_doc_id,
                "title": metadata["title"],
                "chunk": document,
                "metadata": metadata,
                "relevance_score": results["distances"][0][i] if "distances" in results else 1.0
            })
            seen_doc_ids.add(original_doc_id)
            
            # Stop once we have enough results
            if len(filtered_results) >= top_k:
                break
    
    return filtered_results


def generate_answer(query: str, user: User) -> Dict[str, Any]:
    """
    Generate an answer to a query using RAG with role-based access control
    """
    # Check if LLM is available
    if llm is None:
        return {
            "answer": "Sorry, the chat functionality is not available. Please check that the GROQ_API_KEY is properly set in your environment variables.",
            "sources": []
        }
    
    # Log the query action
    log_action(user.username, user.role, "query", {"query": query})
    
    # Search for relevant documents
    search_results = search_documents(query, user)
    
    if not search_results:
        return {
            "answer": "I couldn't find any documents that you have access to that answer this question.",
            "sources": []
        }
    
    # Create context from documents
    context = "\n\n".join([
        f"Document: {result['metadata']['title']}\nContent: {result['chunk']}"
        for result in search_results
    ])
    
    # Create a simple prompt
    prompt = f"""Based on the following documents, please answer the question: {query}

Documents:
{context}

Please provide a comprehensive answer based on the information in the documents above. If the documents don't contain enough information to answer the question, please say so.

Answer:"""
    
    try:
        # Generate answer using the LLM directly
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        sources = []
        for result in search_results:
            sources.append({
                "title": result["metadata"]["title"],
                "document_id": result["document_id"]
            })
        
        return {
            "answer": answer,
            "sources": sources
        }
    except Exception as e:
        sources = []
        for result in search_results:
            sources.append({
                "title": result["metadata"]["title"],
                "document_id": result["document_id"]
            })
        
        return {
            "answer": f"Sorry, I encountered an error while generating the answer: {str(e)}",
            "sources": sources
        }


def delete_document(doc_id: str, user: User) -> bool:
    """
    Delete a document if the user has appropriate permissions
    """
    # Get document metadata
    document = get_document_metadata(doc_id)
    if not document:
        return False
    
    # Check if user has permission to delete
    if user.role == Role.EMPLOYEE:
        return False
    
    if user.role == Role.MANAGER and Role.EXECUTIVE in [Role(role) for role in document.access_roles]:
        return False
    
    # Delete from ChromaDB
    results = document_collection.get(
        where={"document_id": doc_id}
    )
    
    if results and "ids" in results and results["ids"]:
        document_collection.delete(
            ids=results["ids"]
        )
    
    # Delete metadata file
    try:
        os.remove(f"documents/{doc_id}.json")
    except FileNotFoundError:
        pass
    
    # Log the deletion
    log_action(
        user.username, 
        user.role, 
        "delete_document", 
        {"document_id": doc_id, "title": document.title}
    )
    
    return True


def get_audit_logs(user: User, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get audit logs if user has appropriate permissions
    """
    if user.role != Role.EXECUTIVE:
        return []
    
    logs = []
    try:
        with open("audit_log.json", "r") as f:
            for line in f:
                logs.append(json.loads(line))
                if len(logs) >= limit:
                    break
    except FileNotFoundError:
        pass
    
    return logs
