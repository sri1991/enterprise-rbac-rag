# RBAC Based RAG Pipeline - Architecture Overview

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RBAC Based RAG Pipeline                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   EXECUTIVE     │    │    MANAGER      │    │   EMPLOYEE      │
│   (Full Access) │    │ (Dept Access)   │    │ (Limited Access)│
│                 │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │                         │
                    │   STREAMLIT FRONTEND    │
                    │   (User Interface)      │
                    │                         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │                         │
                    │   AUTHENTICATION &      │
                    │   AUTHORIZATION         │
                    │   (auth.py)             │
                    │                         │
                    │ • JWT Token Management  │
                    │ • Password Hashing      │
                    │ • Role Validation       │
                    │ • Session Management    │
                    │                         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │                         │
                    │   MAIN APPLICATION      │
                    │   (app.py)              │
                    │                         │
                    │ • Route Management      │
                    │ • UI Components         │
                    │ • Session State         │
                    │ • User Interactions     │
                    │                         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │                         │
                    │   RAG PIPELINE          │
                    │   (rag.py)              │
                    │                         │
                    │ • Document Processing   │
                    │ • Text Chunking         │
                    │ • Embedding Generation  │
                    │ • Retrieval & Search    │
                    │ • Answer Generation     │
                    │                         │
                    └────────────┬────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│             │        │             │        │             │
│  CHROMADB   │        │   GROQ LLM  │        │   FILE      │
│  (Vector    │        │   (Answer   │        │   STORAGE   │
│   Store)    │        │ Generation) │        │             │
│             │        │             │        │             │
│ • Embeddings│        │ • Llama3    │        │ • PDF Files │
│ • Metadata  │        │ • Context   │        │ • JSON      │
│ • Search    │        │ • Responses │        │ • Logs      │
│             │        │             │        │             │
└─────────────┘        └─────────────┘        └─────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                          │
└─────────────────────────────────────────────────────────────────────────────────┘

1. User Authentication → JWT Token Generation
2. Document Upload → PDF Processing → Text Chunking → Embedding → ChromaDB Storage
3. User Query → Role-based Document Filtering → Vector Search → Context Retrieval
4. Context + Query → LLM Processing → Answer Generation → Response to User
5. All Actions → Audit Logging → JSON File Storage
```

## Component Details

### 1. **Frontend Layer (Streamlit)**
- **Purpose**: User interface and interaction management
- **Features**:
  - Login/logout functionality
  - Role-based UI components
  - Document upload interface
  - Search and chat interfaces
  - User management (Executive only)
  - Audit log viewing (Executive only)

### 2. **Authentication & Authorization (auth.py)**
- **Purpose**: Security and access control
- **Features**:
  - JWT token-based authentication
  - Password hashing with bcrypt
  - Role-based access validation
  - User session management
  - Audit logging for all actions

### 3. **Main Application Controller (app.py)**
- **Purpose**: Application orchestration and routing
- **Features**:
  - Session state management
  - Route handling for different user roles
  - UI component rendering
  - Integration between frontend and backend services

### 4. **RAG Pipeline (rag.py)**
- **Purpose**: Document processing and intelligent retrieval
- **Features**:
  - PDF text extraction and chunking
  - Embedding generation and storage
  - Role-based document filtering
  - Semantic search capabilities
  - Context-aware answer generation

### 5. **Data Storage**
- **ChromaDB**: Vector embeddings and document chunks
- **File System**: PDF documents, user data, metadata
- **JSON Files**: User profiles, audit logs, document metadata

## Security Architecture

### Role-Based Access Control (RBAC)
```
EXECUTIVE
├── Full system access
├── User management
├── All document access
├── Audit log viewing
└── Document deletion

MANAGER
├── Department-level access
├── Document upload
├── Manager/Employee document access
└── Limited deletion rights

EMPLOYEE
├── Employee-level documents only
├── Search and chat functionality
└── No upload or management rights
```

### Data Flow Security
1. **Authentication**: JWT tokens with expiration
2. **Authorization**: Role validation at each access point
3. **Document Filtering**: Automatic role-based content filtering
4. **Audit Trail**: Complete action logging for compliance

## Technology Stack

- **Frontend**: Streamlit (Python web framework)
- **Authentication**: JWT + bcrypt password hashing
- **Vector Database**: ChromaDB for embeddings
- **LLM**: Groq (Llama3-70B) for answer generation
- **Text Processing**: LangChain for document chunking
- **PDF Processing**: PyPDF for text extraction
- **Storage**: JSON files + file system

## Scalability Considerations

### Current Architecture (Development)
- File-based user storage
- Local ChromaDB instance
- Single-instance deployment

### Production Recommendations
- Database migration (PostgreSQL/MongoDB)
- Distributed vector storage
- Load balancing and clustering
- Enhanced security measures
- Monitoring and logging infrastructure
