# documentManagement.py - Document Management Module for Project A
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os
from typing import List, Dict, Any, Optional
import json
from internal_assistant_core import blob_container, settings

def _detect_mime(path: str) -> str:
    """Detect MIME type from file extension"""
    ext = (os.path.splitext(path)[1] or "").lower()
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }.get(ext, "application/octet-stream")

# ==============================================
# UPLOAD & INDEXING FUNCTIONS
# ==============================================

def upload_file_to_blob(file_data: bytes, blob_name: str, content_type: str = None) -> Dict[str, Any]:
    """Upload single file to Azure Blob Storage"""
    try:
        if content_type is None:
            content_type = _detect_mime(blob_name)
        
        blob_client = blob_container.get_blob_client(blob_name)
        
        blob_client.upload_blob(
            file_data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        
        return {
            "success": True,
            "blob_name": blob_name,
            "size": len(file_data),
            "content_type": content_type,
            "message": f"Successfully uploaded {blob_name}"
        }
    except Exception as e:
        return {
            "success": False,
            "blob_name": blob_name,
            "error": str(e),
            "message": f"Failed to upload {blob_name}: {str(e)}"
        }

def batch_upload_files(files_data: List[Dict[str, Any]], prefix: str) -> Dict[str, Any]:
    """
    Upload multiple files to blob storage
    files_data: List of dicts with keys: 'filename', 'data', 'content_type' (optional)
    """
    if not prefix.endswith("/"):
        prefix += "/"
    
    results = {
        "successful_uploads": 0,
        "failed_uploads": 0,
        "total_files": len(files_data) if files_data else 0,
        "uploaded_files": [],
        "failed_files": [],
        "details": []
    }
    
    if not files_data:
        results["message"] = "No files provided for upload"
        return results
    
    for file_info in files_data:
        try:
            filename = file_info["filename"]
            file_data = file_info["data"]
            content_type = file_info.get("content_type")
            
            blob_name = f"{prefix}{filename}"
            
            upload_result = upload_file_to_blob(file_data, blob_name, content_type)
            results["details"].append(upload_result)
            
            if upload_result["success"]:
                results["successful_uploads"] += 1
                results["uploaded_files"].append(blob_name)
            else:
                results["failed_uploads"] += 1
                results["failed_files"].append({
                    "file": filename,
                    "error": upload_result["error"]
                })
                
        except Exception as e:
            results["failed_uploads"] += 1
            results["failed_files"].append({
                "file": file_info.get("filename", "unknown"),
                "error": str(e)
            })
    
    results["message"] = f"Upload completed: {results['successful_uploads']} successful, {results['failed_uploads']} failed"
    return results

def process_and_index_documents(prefix: str = "sop/") -> Dict[str, Any]:
    """Process and index documents from blob storage to Azure AI Search"""
    try:
        # Import RAG module for indexing
        from rag_modul import process_and_index_docs
        
        index_report = process_and_index_docs(prefix=prefix)
        
        return {
            "success": True,
            "prefix": prefix,
            "index_report": index_report,
            "message": f"Successfully processed and indexed documents from {prefix}"
        }
    except Exception as e:
        return {
            "success": False,
            "prefix": prefix,
            "error": str(e),
            "message": f"Failed to index documents from {prefix}: {str(e)}"
        }

def upload_and_index_complete(files_data: List[Dict[str, Any]], prefix: str) -> Dict[str, Any]:
    """Complete upload and index workflow"""
    results = {
        "upload_results": None,
        "index_results": None,
        "overall_success": False,
        "message": ""
    }
    
    try:
        # Step 1: Upload files
        upload_results = batch_upload_files(files_data, prefix)
        results["upload_results"] = upload_results
        
        # Step 2: Index documents (only if some files were uploaded successfully)
        if upload_results["successful_uploads"] > 0:
            index_results = process_and_index_documents(prefix)
            results["index_results"] = index_results
            
            # Overall success if either partial upload success or full success
            results["overall_success"] = upload_results["successful_uploads"] > 0
            results["message"] = f"Upload: {upload_results['message']}. Index: {index_results.get('message', 'Completed')}"
        else:
            results["overall_success"] = False
            results["message"] = f"Upload failed: {upload_results['message']}. Indexing skipped."
            
    except Exception as e:
        results["overall_success"] = False
        results["message"] = f"Complete workflow failed: {str(e)}"
    
    return results

# ==============================================
# DOCUMENT LISTING FUNCTIONS  
# ==============================================

def list_documents_in_blob(prefix: str = "sop/") -> List[Dict[str, Any]]:
    """List all documents in Azure Blob Storage with their metadata"""
    try:
        if not prefix.endswith("/"):
            prefix += "/"
        
        documents = []
        blob_list = blob_container.list_blobs(name_starts_with=prefix)
        
        for blob in blob_list:
            blob_client = blob_container.get_blob_client(blob.name)
            properties = blob_client.get_blob_properties()
            
            documents.append({
                "name": blob.name,
                "display_name": blob.name.replace(prefix, ""),
                "size": blob.size,
                "content_type": properties.content_settings.content_type if properties.content_settings else "unknown",
                "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                "creation_time": properties.creation_time.isoformat() if properties.creation_time else None,
                "blob_url": blob_client.url
            })
        
        return sorted(documents, key=lambda x: x["last_modified"] or "", reverse=True)
        
    except Exception as e:
        print(f"Error listing documents: {str(e)}")
        return []

# ==============================================
# DOCUMENT DELETION FUNCTIONS
# ==============================================

def delete_document_from_blob(blob_name: str) -> bool:
    """Delete document from Azure Blob Storage"""
    try:
        blob_client = blob_container.get_blob_client(blob_name)
        
        if not blob_client.exists():
            print(f"Blob {blob_name} does not exist")
            return False
        
        blob_client.delete_blob()
        print(f"Successfully deleted blob: {blob_name}")
        return True
        
    except Exception as e:
        print(f"Error deleting blob {blob_name}: {str(e)}")
        return False

def search_documents_in_index(blob_name: str) -> List[str]:
    """Find all document IDs in search index that belong to a specific blob"""
    try:
        search_client = SearchClient(
            endpoint=settings.search_endpoint,
            index_name=settings.search_index,
            credential=AzureKeyCredential(settings.search_key)
        )
        
        # Try multiple possible field names for source/filename
        possible_filters = [
            f"source eq '{blob_name}'",
            f"filename eq '{blob_name}'",
            f"sourcefile eq '{blob_name}'",
            f"document_name eq '{blob_name}'",
            f"blob_name eq '{blob_name}'"
        ]
        
        document_ids = []
        
        # Try each possible filter
        for filter_expr in possible_filters:
            try:
                results = search_client.search(
                    search_text="*",
                    filter=filter_expr,
                    select=["id"],
                    top=1000
                )
                
                batch_ids = [result["id"] for result in results]
                document_ids.extend(batch_ids)
                
                if batch_ids:
                    print(f"Found {len(batch_ids)} documents using filter: {filter_expr}")
                    break  # Stop if we found documents
                    
            except Exception as filter_error:
                print(f"Filter {filter_expr} failed: {str(filter_error)}")
                continue
        
        # If no specific field worked, try searching in content
        if not document_ids:
            try:
                # Search for the blob name in the content/text fields
                results = search_client.search(
                    search_text=f'"{blob_name}"',
                    select=["id"],
                    top=1000
                )
                
                content_ids = [result["id"] for result in results]
                document_ids.extend(content_ids)
                
                if content_ids:
                    print(f"Found {len(content_ids)} documents by searching content for: {blob_name}")
                    
            except Exception as search_error:
                print(f"Content search failed: {str(search_error)}")
        
        # Remove duplicates
        document_ids = list(set(document_ids))
        print(f"Total found {len(document_ids)} indexed chunks for blob: {blob_name}")
        return document_ids
        
    except Exception as e:
        print(f"Error searching for documents in index for blob {blob_name}: {str(e)}")
        return []

def delete_document_from_search_index(document_id: str) -> bool:
    """Delete document from Azure AI Search index"""
    try:
        search_client = SearchClient(
            endpoint=settings.search_endpoint,
            index_name=settings.search_index,
            credential=AzureKeyCredential(settings.search_key)
        )
        
        result = search_client.delete_documents(documents=[{"id": document_id}])
        
        if result and len(result) > 0:
            success = result[0].succeeded
            if success:
                print(f"Successfully deleted document from search index: {document_id}")
                return True
            else:
                error_msg = getattr(result[0], 'error_message', 'Unknown error')
                print(f"Failed to delete from search index: {error_msg}")
                return False
        else:
            print(f"No result returned for deletion of document: {document_id}")
            return False
            
    except Exception as e:
        print(f"Error deleting from search index {document_id}: {str(e)}")
        return False

def get_search_index_schema() -> Dict[str, Any]:
    """Get search index schema to understand field names"""
    try:
        from azure.search.documents.indexes import SearchIndexClient
        
        index_client = SearchIndexClient(
            endpoint=settings.search_endpoint,
            credential=AzureKeyCredential(settings.search_key)
        )
        
        index = index_client.get_index(settings.search_index)
        
        fields_info = []
        for field in index.fields:
            fields_info.append({
                "name": field.name,
                "type": str(field.type),
                "searchable": field.searchable,
                "filterable": field.filterable,
                "key": field.key
            })
        
        return {
            "index_name": settings.search_index,
            "fields": fields_info
        }
        
    except Exception as e:
        return {"error": f"Failed to get index schema: {str(e)}"}

def delete_document_complete(blob_name: str) -> Dict[str, Any]:
    """Complete document deletion from both Blob Storage and Search Index"""
    result = {
        "blob_name": blob_name,
        "blob_deleted": False,
        "search_documents_deleted": 0,
        "search_deletion_errors": [],
        "success": False,
        "message": "",
        "debug_info": {}
    }
    
    try:
        # Debug: Get index schema first
        schema_info = get_search_index_schema()
        result["debug_info"]["schema"] = schema_info
        
        # Step 1: Find all related documents in search index
        document_ids = search_documents_in_index(blob_name)
        result["debug_info"]["found_document_ids"] = document_ids
        
        # Step 2: Delete from search index first
        deleted_count = 0
        for doc_id in document_ids:
            if delete_document_from_search_index(doc_id):
                deleted_count += 1
            else:
                result["search_deletion_errors"].append(doc_id)
        
        result["search_documents_deleted"] = deleted_count
        
        # Step 3: Delete from blob storage
        blob_deleted = delete_document_from_blob(blob_name)
        result["blob_deleted"] = blob_deleted
        
        # Step 4: Determine overall success
        if blob_deleted and (deleted_count == len(document_ids) or len(document_ids) == 0):
            result["success"] = True
            result["message"] = f"Document successfully deleted. Removed {deleted_count} indexed chunks and 1 blob file."
        elif blob_deleted and deleted_count > 0:
            result["success"] = True
            result["message"] = f"Document partially deleted. Removed {deleted_count}/{len(document_ids)} indexed chunks and 1 blob file."
        elif blob_deleted:
            result["success"] = True
            result["message"] = "Blob file deleted, but no indexed content found (file may not have been indexed yet)."
        else:
            result["success"] = False
            result["message"] = "Failed to delete document from blob storage."
            
        # Add debug info about what was attempted
        result["debug_info"]["deletion_summary"] = {
            "blob_existed": blob_deleted,
            "search_chunks_found": len(document_ids),
            "search_chunks_deleted": deleted_count,
            "search_errors": len(result["search_deletion_errors"])
        }
        
    except Exception as e:
        result["success"] = False
        result["message"] = f"Error during document deletion: {str(e)}"
        result["debug_info"]["error"] = str(e)
    
    return result

def batch_delete_documents(blob_names: List[str]) -> Dict[str, Any]:
    """Delete multiple documents in batch"""
    results = {
        "total_requested": len(blob_names),
        "successful_deletions": 0,
        "failed_deletions": 0,
        "details": []
    }
    
    for blob_name in blob_names:
        delete_result = delete_document_complete(blob_name)
        results["details"].append(delete_result)
        
        if delete_result["success"]:
            results["successful_deletions"] += 1
        else:
            results["failed_deletions"] += 1
    
    return results

# ==============================================
# SEARCH INDEX MANAGEMENT FUNCTIONS
# ==============================================

def inspect_search_index_sample(blob_name: Optional[str] = None) -> Dict[str, Any]:
    """Inspect search index to understand structure and find documents"""
    try:
        search_client = SearchClient(
            endpoint=settings.search_endpoint,
            index_name=settings.search_index,
            credential=AzureKeyCredential(settings.search_key)
        )
        
        # Get sample documents
        if blob_name:
            # Search for specific blob name
            results = search_client.search(
                search_text=f'"{blob_name}"',
                top=5,
                include_total_count=True
            )
        else:
            # Get general sample
            results = search_client.search(
                search_text="*",
                top=5,
                include_total_count=True
            )
        
        sample_docs = []
        for result in results:
            # Convert result to dict, handling all possible fields
            doc_dict = dict(result)
            sample_docs.append(doc_dict)
        
        return {
            "total_documents": getattr(results, 'get_count', lambda: 'Unknown')(),
            "sample_documents": sample_docs,
            "search_query": f'"{blob_name}"' if blob_name else "*",
            "index_name": settings.search_index
        }
        
    except Exception as e:
        return {"error": f"Failed to inspect index: {str(e)}"}

def rebuild_search_index(prefix: str = "sop/") -> Dict[str, Any]:
    """Rebuild search index from blob storage - USE WITH CAUTION"""
    try:
        # This would typically involve:
        # 1. Clear existing index
        # 2. Re-process all documents from blob storage
        # 3. Re-index everything
        
        # For now, just return guidance
        return {
            "message": "Index rebuild not implemented. Use process_and_index_documents for incremental updates.",
            "recommendation": "Contact administrator for full index rebuild if needed."
        }
        
    except Exception as e:
        return {"error": f"Failed to rebuild index: {str(e)}"}