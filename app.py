import os
import streamlit as st
import tempfile
from datetime import datetime
import json
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models import User, Role
from auth import authenticate_user, create_access_token, decode_token, log_action, create_user
from rag import process_pdf, search_documents, generate_answer, delete_document, get_audit_logs

# Page configuration
st.set_page_config(
    page_title="PaperPulse - RBAC Document Management",
    page_icon="📚",
    layout="wide"
)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "token" not in st.session_state:
    st.session_state.token = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def login():
    """Handle user login"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.token = None
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            user = authenticate_user(username, password)
            if user:
                # Create access token
                token = create_access_token({"sub": username, "role": user.role.value})
                
                # Update session state
                st.session_state.authenticated = True
                st.session_state.user = user
                st.session_state.token = token
                
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")


def logout():
    """Handle user logout"""
    if st.session_state.authenticated and st.session_state.user:
        log_action(
            st.session_state.user.username,
            st.session_state.user.role,
            "logout"
        )
    
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.token = None
    st.session_state.chat_history = []
    st.rerun()


def user_management():
    """User management interface for executives"""
    st.subheader("User Management")
    
    # Create new user form
    with st.form("create_user_form"):
        st.write("Create New User")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        new_role = st.selectbox(
            "Role",
            options=[role.value for role in Role],
            format_func=lambda x: x
        )
        new_department = st.text_input("Department")
        
        submit_user = st.form_submit_button("Create User")
        
        if submit_user:
            try:
                create_user(
                    username=new_username,
                    password=new_password,
                    role=Role(new_role),
                    department=new_department
                )
                st.success(f"User {new_username} created successfully!")
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Error creating user: {str(e)}")


def document_upload():
    """Document upload interface"""
    st.subheader("Upload Document")
    
    with st.form("upload_form"):
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        title = st.text_input("Document Title")
        
        # Access control options based on user role
        available_roles = []
        if st.session_state.user.role == Role.EXECUTIVE:
            available_roles = [Role.EXECUTIVE, Role.MANAGER, Role.EMPLOYEE]
        elif st.session_state.user.role == Role.MANAGER:
            available_roles = [Role.MANAGER, Role.EMPLOYEE]
        else:
            available_roles = [Role.EMPLOYEE]
        
        selected_roles = st.multiselect(
            "Who can access this document?",
            options=[role.value for role in available_roles],
            default=[st.session_state.user.role.value]
        )
        
        submit = st.form_submit_button("Upload")
        
        if submit and uploaded_file is not None:
            if not title:
                title = uploaded_file.name
            
            # Convert selected roles from strings to Role enum
            access_roles = [Role(role) for role in selected_roles]
            
            # Save uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Process the document
                document = process_pdf(
                    file_path=tmp_path,
                    user=st.session_state.user,
                    title=title,
                    access_roles=access_roles
                )
                
                st.success(f"Document '{title}' uploaded successfully!")
                st.write(f"Document ID: {document.id}")
                
                # Clean up the temporary file
                os.unlink(tmp_path)
            except Exception as e:
                st.error(f"Error processing document: {str(e)}")
                # Clean up the temporary file
                os.unlink(tmp_path)


def document_search():
    """Document search interface"""
    st.subheader("Search Documents")
    
    query = st.text_input("Enter your search query")
    
    if query:
        results = search_documents(query, st.session_state.user)
        
        if results:
            st.write(f"Found {len(results)} documents:")
            
            for i, result in enumerate(results):
                with st.expander(f"{i+1}. {result['title']}"):
                    st.write(f"Document ID: {result['document_id']}")
                    st.write(f"Relevance: {1 - result['relevance_score']:.2f}")
                    st.write("Preview:")
                    st.write(result['chunk'][:300] + "...")
                    
                    # Delete button (only for Executives and Managers)
                    if st.session_state.user.role in [Role.EXECUTIVE, Role.MANAGER]:
                        if st.button(f"Delete Document {result['document_id']}", key=f"delete_{result['document_id']}"):
                            success = delete_document(result['document_id'], st.session_state.user)
                            if success:
                                st.success(f"Document {result['document_id']} deleted successfully!")
                                st.rerun()
                            else:
                                st.error("You don't have permission to delete this document.")
        else:
            st.info("No documents found matching your query and access permissions.")


def document_chat():
    """Chat interface for document Q&A"""
    st.subheader("Chat with Your Documents")
    
    # Display chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
                if "sources" in message and message["sources"]:
                    st.write("Sources:")
                    for source in message["sources"]:
                        st.write(f"- {source['title']} (ID: {source['document_id']})")
    
    # Chat input
    user_query = st.chat_input("Ask a question about your documents")
    
    if user_query:
        # Add user message to chat history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_query
        })
        
        # Display user message
        st.chat_message("user").write(user_query)
        
        # Generate response
        with st.spinner("Generating answer..."):
            response = generate_answer(user_query, st.session_state.user)
        
        # Add assistant message to chat history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response["answer"],
            "sources": response["sources"]
        })
        
        # Display assistant message
        with st.chat_message("assistant"):
            st.write(response["answer"])
            if response["sources"]:
                st.write("Sources:")
                for source in response["sources"]:
                    st.write(f"- {source['title']} (ID: {source['document_id']})")
        
        # Force a rerun to update the UI
        st.rerun()


def audit_logs():
    """Audit logs interface for executives"""
    st.subheader("Audit Logs")
    
    logs = get_audit_logs(st.session_state.user)
    
    if logs:
        st.write(f"Showing {len(logs)} recent audit logs:")
        
        # Create a dataframe for better display
        import pandas as pd
        
        logs_data = []
        for log in logs:
            logs_data.append({
                "Timestamp": log["timestamp"],
                "User": log["user_id"],
                "Role": log["user_role"],
                "Action": log["action"],
                "Details": json.dumps(log["details"]) if log["details"] else ""
            })
        
        logs_df = pd.DataFrame(logs_data)
        st.dataframe(logs_df)
    else:
        st.info("No audit logs available or you don't have permission to view them.")


def main():
    """Main application"""
    # Display header
    st.title("PaperPulse - RBAC Document Management")
    
    # Sidebar for navigation and user info
    with st.sidebar:
        if st.session_state.authenticated:
            st.write(f"Logged in as: **{st.session_state.user.username}**")
            st.write(f"Role: **{st.session_state.user.role.value}**")
            st.write(f"Department: **{st.session_state.user.department}**")
            
            st.button("Logout", on_click=logout)
            
            st.divider()
            
            # Navigation
            st.subheader("Navigation")
            page = st.radio(
                "Go to",
                options=["Search", "Chat", "Upload"] + 
                        (["User Management", "Audit Logs"] if st.session_state.user.role == Role.EXECUTIVE else [])
            )
        else:
            page = "Login"
    
    # Display the selected page
    if not st.session_state.authenticated:
        login()
    else:
        if page == "Search":
            document_search()
        elif page == "Chat":
            document_chat()
        elif page == "Upload":
            # Only Executives and Managers can upload documents
            if st.session_state.user.role in [Role.EXECUTIVE, Role.MANAGER]:
                document_upload()
            else:
                st.warning("You don't have permission to upload documents.")
        elif page == "User Management" and st.session_state.user.role == Role.EXECUTIVE:
            user_management()
        elif page == "Audit Logs" and st.session_state.user.role == Role.EXECUTIVE:
            audit_logs()


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("documents", exist_ok=True)
    os.makedirs("chroma_db", exist_ok=True)
    
    main()
