# PaperPulse - RBAC Document Management System

A secure document management system with Role-Based Access Control (RBAC) for organizational documents, featuring semantic search and a RAG pipeline for answering questions about your documents.

## Features

- **Role-Based Access Control (RBAC)**
  - Executive: Full access to all documents, user management, and audit logs
  - Manager: Access to Manager and Employee documents, upload capabilities
  - Employee: Access to Employee-level documents, search only

- **Document Management**
  - Upload and process PDF documents
  - Assign role-based access metadata to documents
  - Store document embeddings in ChromaDB for semantic search

- **Search and RAG Pipeline**
  - Authenticate users securely
  - Filter search results based on user roles and permissions
  - Generate contextual answers using LangChain and Groq

- **User Interface**
  - Streamlit app with role-specific UI components
  - Login page for authentication
  - Document search, chat, and management interfaces

- **Audit Logging**
  - Log all user actions with role and timestamp
  - View audit logs (Executive role only)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/paperpulse.git
cd paperpulse
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   - Rename `.env.example` to `.env`
   - Add your Groq API key and update the secret key

## Usage

1. Run the Streamlit application:
```bash
streamlit run app.py
```

2. Access the application in your web browser at `http://localhost:8501`

3. Login with default credentials:
   - Executive: username `admin`, password `admin123`
   - Manager: username `manager`, password `manager123`
   - Employee: username `employee`, password `employee123`

## Project Structure

- `app.py` - Streamlit application for the user interface
- `auth.py` - Authentication and authorization module
- `models.py` - Data models for users, documents, and audit logs
- `rag.py` - Document processing, retrieval, and RAG pipeline
- `.env` - Environment variables (API keys, security settings)

## Security Notes

- For production use, change the default passwords and secret key
- Consider using a proper database instead of file-based storage
- Enable HTTPS for secure communication

## Requirements

- Python 3.8+
- Streamlit
- LangChain
- ChromaDB
- PyPDF
- Groq API access
