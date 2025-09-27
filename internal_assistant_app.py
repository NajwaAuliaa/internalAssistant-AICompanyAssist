from depedencies import *
from azure.storage.blob import ContentSettings


from internal_assistant_core import (
    get_or_create_agent, settings, 
    blob_container
)

from rag_modul import (
    rag_answer, process_and_index_docs
)

# Project management imports dengan alias untuk menghindari konflik
from projectProgress_modul import (
    process_project_query, list_all_projects,
    analyze_project_data, generate_project_response,
    get_plans, get_plan_tasks, intelligent_project_query
)

# Todo management imports dengan alias untuk menghindari konflik
from to_do_modul_test import (
    # build_auth_url as todo_build_auth_url,
    # exchange_code_for_token as todo_exchange_code_for_token,
    # get_login_status as todo_get_login_status,
    process_todo_query_advanced,
    # is_user_logged_in as todo_is_user_logged_in,
)

from unified_auth import(
    build_unified_auth_url,
    exchange_unified_code_for_token,
    is_unified_authenticated,
    get_unified_login_status,
    unified_token_manager as token_manager,
    clear_unified_token as clear_user_token
)

def set_user_token(token_data: dict, user_id: str = "current_user"):
    """Set user token using unified token manager"""
    token_manager.set_token(user_id, token_data)    

from documentManagement import (
    upload_file_to_blob,
    batch_upload_files,
    process_and_index_documents,
    upload_and_index_complete,
    list_documents_in_blob,
    delete_document_complete,
    batch_delete_documents,
    inspect_search_index_sample,
    get_search_index_schema,
    rebuild_search_index
)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import os

app = FastAPI(title="Internal Assistant – LangChain + Azure + UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8001", "http://127.0.0.1:3000", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    answer: str
    tool_calls: Optional[List[Dict[str, Any]]] = None

class IndexRequest(BaseModel):
    prefix: str = "sop/"

class DocumentDeleteRequest(BaseModel):
    blob_names: List[str]

# Enhanced System Prompt untuk lebih smart project handling
ENHANCED_SYSTEM_PROMPT = """
You are the company's Internal Assistant with advanced project management capabilities. You can:

1) **RAG Q&A Internal (qna_internal)** – Jawab pertanyaan policy/SOP, handbook dari dokumen internal, disini intinya adalah semua document yang hubungannya dengan internal company, dan anda harus menjawabnya sesuai dengan pertanyaan dari user. Jika konteks berasal dari beberapa potongan, gabungkan untuk menyusun jawaban lengkap”.
2) **Smart Project Progress (project_progress)** – Analisis mendalam project dari Microsoft Planner (REQUIRES LOGIN)
3) **Project List & Comparison** – List semua project atau bandingkan multiple projects  
4) **Client Status Check** – Cek status client
5) **Template Documents** – Ambil template dokumen
6) **Notifications** – Kirim notifikasi/pengingat
7) **Document Management** - Upload, list, delete, and manage documents in Azure Blob Storage

**ENHANCED PROJECT CAPABILITIES:**
- Deteksi otomatis project name dari natural language
- Analisis progress dengan insight dan recommendations
- Perbandingan multiple projects
- Identifikasi masalah (overdue tasks, bottlenecks)
- Smart suggestions untuk project management

**DOCUMENT MANAGEMENT CAPABILITIES:**
- Upload and automatically index documents
- List and manage existing documents
- Delete documents from both storage and search index
- Rebuild search indexes when needed

**AUTHENTICATION NOTE:**
- Project features require Microsoft login via delegated permissions with PKCE for SPA
- If user asks about projects but not authenticated, inform them to login first

**IMPORTANT DISTINCTION:**
- **PLANNER TASKS** = Project management tasks from Microsoft Planner (use project_progress tools)
- **TO-DO TASKS** = Personal tasks from Microsoft To-Do (use separate To-Do interface)

**USAGE GUIDELINES:**
- Untuk pertanyaan tentang PROJECT/PLANNER tasks, gunakan project_progress tool
- Untuk pertanyaan tentang personal TO-DO tasks, arahkan ke tab "Smart To-Do"
- Jika user tanya "list project" atau "semua project", gunakan project_list tool
- Untuk comparison, deteksi bila user menyebut 2+ project names
- Selalu berikan insight yang actionable dan highlight masalah penting
- Gunakan emoji untuk membuat response lebih engaging dan mudah dibaca

**KEYWORD DETECTION:**
- "project", "planner", "project management" → Use project tools
- "todo", "to-do", "personal task", "my tasks" → Direct to To-Do tab

**RESPONSE STYLE:**
- Professional namun friendly
- Gunakan format yang clear dengan bullet points atau sections
- Highlight urgent items dengan emoji peringatan  
- Berikan next steps recommendations
- Jawab dalam bahasa Indonesia kecuali diminta otherwise

Gunakan tools secara selektif dan berikan jawaban yang komprehensif namun tidak berlebihan.
"""

@app.get("/health")
def health():
    return {"ok": True, "service": "Internal Assistant – LangChain + Azure + UI (Fixed Version)"}

# ========== UPLOAD & INDEX ENDPOINT ==========
def _detect_mime(path: str) -> str:
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
# ========== DOCUMENT MANAGEMENT ENDPOINTS ==========

@app.get("/documents")
def list_documents(prefix: str = "sop/"):
    """List all documents in blob storage with metadata"""
    try:
        documents = list_documents_in_blob(prefix)
        return {
            "success": True,
            "prefix": prefix,
            "documents": documents,
            "total_documents": len(documents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...), prefix: str = Form("sop/")):
    """Upload multiple documents to blob storage and index them"""
    try:
        if not prefix.endswith("/"):
            prefix += "/"
        
        files_data = []
        for file in files:
            content = await file.read()
            files_data.append({
                "filename": file.filename,
                "data": content,
                "content_type": _detect_mime(file.filename)
            })
        
        result = upload_and_index_complete(files_data, prefix)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading documents: {str(e)}")

@app.delete("/documents")
def delete_documents(request: DocumentDeleteRequest):
    """Delete multiple documents from both blob storage and search index"""
    try:
        result = batch_delete_documents(request.blob_names)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting documents: {str(e)}")

@app.delete("/documents/{blob_name:path}")
def delete_single_document(blob_name: str):
    """Delete single document from both blob storage and search index"""
    try:
        result = delete_document_complete(blob_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@app.get("/documents/inspect")
def inspect_documents(blob_name: Optional[str] = None):
    """Inspect search index structure and find documents (debugging tool)"""
    try:
        result = inspect_search_index_sample(blob_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inspecting index: {str(e)}")

@app.get("/documents/schema")
def get_index_schema():
    """Get search index schema information"""
    try:
        schema_info = get_search_index_schema()
        return schema_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting schema: {str(e)}")

@app.post("/documents/reindex")
def reindex_documents(prefix: str = "sop/"):
    """Re-index all documents from blob storage"""
    try:
        result = process_and_index_documents(prefix)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reindexing documents: {str(e)}")

@app.post("/upload-and-index")
async def upload_and_index(
    files: List[UploadFile] = File(...),
    prefix: str = Form("sop/")
):
    uploaded = []
    errors = []
    if not prefix.endswith("/"):
        prefix += "/"
    for f in files:
        try:
            fname = f.filename
            blob_name = f"{prefix}{fname}"
            data = await f.read()
            content_type = _detect_mime(fname)
            blob_client = blob_container.get_blob_client(blob_name)
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
            uploaded.append(blob_name)
        except Exception as e:
            errors.append(f"{fname}: {e}")
    index_report = process_and_index_docs(prefix=prefix)
    return {
        "uploaded": uploaded,
        "upload_errors": errors,
        "index_report": index_report
    }

# ========== RAG CHAT ENDPOINT ==========
@app.post("/rag-chat")
def rag_chat(req: dict):
    message = req.get("message", "")
    try:
        answer = rag_answer(message)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_name}")
def get_project_detail(project_name: str):
    """Enhanced API endpoint untuk detail project tertentu dengan SPA support"""
    try:
        if not is_unified_authenticated("current_user"):
            return {
                "error": "Authentication required", 
                "message": "Please login first via /project/login",
                "login_url": "/auth/microsoft",
                "authenticated": False,
                "client_type": "Single-Page Application (SPA)"
            }
        
        result = process_project_query(f"detail progress {project_name}", "current_user")
        return {
            "status": "success",
            "project_detail": result,
            "project_name": project_name,
            "authenticated": True,
            "client_type": "SPA",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": f"Error fetching project detail: {str(e)}",
            "project_name": project_name,
            "authenticated": is_unified_authenticated("current_user"),
            "client_type": "SPA",
            "login_url": "/auth/microsoft" if not is_unified_authenticated("current_user") else None
        }


@app.get("/auth/microsoft")
def unified_microsoft_login():
    """Unified login endpoint untuk Todo dan Project Management"""
    try:
        auth_url = build_unified_auth_url()
        return RedirectResponse(auth_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Auth configuration error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication service unavailable")

@app.get("/auth/callback")
def unified_callback(code: str, state: str = None, error: str = None, error_description: str = None):
    """Unified callback untuk Todo dan Project Management"""
    import html
    
    print(f"DEBUG: Callback received - code: {code[:20] if code else 'None'}..., state: {state}")
    
    if error:
        print(f"DEBUG: OAuth error - {error}: {error_description}")
        safe_error = html.escape(error or "Unknown error")
        safe_description = html.escape(error_description or "No description")
        return HTMLResponse(f"""
            <html><body>
                <h1>❌ Login Error</h1>
                <p>Error: {safe_error}</p>
                <p>Description: {safe_description}</p>
                <script>setTimeout(() => window.location.href='http://localhost:3000', 3000);</script>
            </body></html>
        """)
    
    if not code:
        print("DEBUG: No code received")
        return HTMLResponse("""
            <html><body>
                <h1>❌ Missing authorization code</h1>
                <script>setTimeout(() => window.location.href='http://localhost:3000', 3000);</script>
            </body></html>
        """)
    
    try:
        print("DEBUG: Attempting token exchange...")
        token = exchange_unified_code_for_token(code, state)
        print(f"DEBUG: Token exchange result: {token is not None}")
        
        if not token:
            raise ValueError("Token exchange failed")
        
        print("DEBUG: Token stored successfully")
        return HTMLResponse("""
            <html>
                <head>
                    <title>Login Successful</title>
                    <script>
                        setTimeout(() => window.location.href='http://localhost:3000', 2000);
                    </script>
                </head>
                <body>
                    <h1>✅ Login Successful!</h1>
                    <p>Microsoft To-Do dan Smart Project Management sudah tersedia!</p>
                    <p><small>Redirecting to app...</small></p>
                </body>
            </html>
        """)
    except ValueError as e:
        print(f"DEBUG: ValueError in token exchange: {str(e)}")
        safe_error = html.escape(str(e))
        return HTMLResponse(f"""
            <html>
                <body>
                    <h1>❌ Login Error</h1>
                    <p>Error: {safe_error}</p>
                    <script>setTimeout(() => window.location.href='http://localhost:3000', 3000);</script>
                </body>
            </html>
        """)
    except Exception as e:
        print(f"DEBUG: Exception in token exchange: {str(e)}")
        return HTMLResponse("""
            <html>
                <body>
                    <h1>❌ Login Error</h1>
                    <p>Authentication failed. Please try again.</p>
                    <script>setTimeout(() => window.location.href='http://localhost:3000', 3000);</script>
                </body>
            </html>
        """)

@app.get("/project/status")
def project_status():
    try:
        if is_unified_authenticated("current_user"):
            return {
                "authenticated": True,
                "status": "✅ Sudah login Smart Project Management",
                "features_available": [
                    "Project Progress Analysis",
                    "Multi-Project Comparison", 
                    "Portfolio Overview",
                    "Task Management Insights"
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "authenticated": False,
                "status": "❌ Belum login",
                "login_url": "/auth/microsoft"
            }
    except Exception as e:
        return {"authenticated": False, "status": f"Error: {str(e)}"}

@app.get("/todo/login-status")
def todo_login_status():
    try:
        if is_unified_authenticated("current_user"):
            return {
                "authenticated": True,
                "status": "✅ Sudah login Microsoft To-Do"
            }
        else:
            return {
                "authenticated": False,
                "status": "❌ Belum login"
            }
    except Exception as e:
        return {
            "authenticated": False,
            "status": f"Error: {str(e)}"
        }

@app.post("/project-chat")
def project_chat(req: dict):
    message = req.get("message", "")
    print(f"🔍 DEBUG project_chat: Received message: {message}")
    
    try:
        if not is_unified_authenticated("current_user"):
            print(f"❌ DEBUG project_chat: User not authenticated")
            return {"answer": "🔒 Authentication Required. Please login first"}
        
        print(f"✅ DEBUG project_chat: User authenticated, processing query")
        result = intelligent_project_query(message, "current_user")
        print(f"📤 DEBUG project_chat: Result length: {len(result)} chars")
        
        return {"answer": result}
    except Exception as e:
        print(f"❌ DEBUG project_chat: Exception: {str(e)}")
        return {"answer": f"❌ Error: {str(e)}"}

@app.post("/todo-chat")
def todo_chat(req: dict):
    message = req.get("message", "")
    try:
        if not is_unified_authenticated("current_user"):
            return {"answer": "❌ Belum login. Silakan login terlebih dahulu."}
        
        answer = process_todo_query_advanced(message, None)  # token sudah dihandle di module
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"❌ Error: {str(e)}"}
    
@app.get("/projects")
def get_all_projects():
    if not is_unified_authenticated("current_user"):
        return {
            "error": "Authentication required",
            "message": "Please login first",
            "login_url": "/auth/microsoft",
            "authenticated": False
        }

    try:
        result = list_all_projects("current_user")
        return {
            "status": "success", 
            "projects": result,
            "authenticated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "error": f"Error fetching projects: {str(e)}",
            "authenticated": True,
            "error_details": str(e)
        }

@app.get("/todo/examples")
def todo_examples():
    """Get contoh-contoh query todo"""
    examples = [
        "Tampilkan semua task saya",
        "Task apa saja yang deadline hari ini?",
        "Buatkan task baru: Review laporan keuangan deadline besok",
        "Tandai task 'Meeting pagi' sebagai selesai",
        "Task mana saja yang belum selesai?",
        "Berapa banyak task yang overdue?",
        "Buat reminder untuk call client deadline 5 September",
        "Ubah deadline task presentation jadi minggu depan",
        "Tunjukkan task yang sudah selesai bulan ini",
        "Ada task apa saja yang urgent?"
    ]
    return {"examples": examples}

@app.get("/todo/suggestions")
def todo_suggestions():
    """Get suggestions untuk todo management"""
    suggestions = """💡 Smart Suggestions:
- Analisis produktivitas saya minggu ini
- Task apa yang paling urgent?
- Buatkan planning task untuk project baru
- Reminder untuk follow up client besok

Tips:
- Gunakan bahasa natural, AI akan memahami maksud Anda
- Sebutkan deadline dengan jelas: "hari ini", "besok", "5 September"
- Deskripsi task bisa lebih detail untuk tracking yang better
- AI bisa membantu prioritisasi berdasarkan deadline dan urgency
"""
    return {"suggestions": suggestions}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Unified chat endpoint yang bisa handle semua jenis query
    """
    try:
        agent = get_or_create_agent(req.user_id)

        # Update system prompt with enhanced version
        from langchain.schema import SystemMessage
        agent.agent.llm_chain.prompt.messages[0] = SystemMessage(content=ENHANCED_SYSTEM_PROMPT)
        
        # Process query
        result = agent.invoke({"input": req.message})
        answer = result.get("output", "")
        steps = result.get("intermediate_steps", [])
        
        # Serialize tool calls for debugging
        serialized_steps = []
        for s in steps:
            try:
                action, observation = s
                serialized_steps.append({
                    "tool": getattr(action, "tool", None),
                    "tool_input": getattr(action, "tool_input", None),
                    "log": getattr(action, "log", None),
                    "observation": observation,
                })
            except Exception:
                pass
                
        return ChatResponse(answer=answer, tool_calls=serialized_steps)
        
    except Exception as e:
        if settings.debug:
            raise
        raise HTTPException(status_code=500, detail=str(e))

# Tambah endpoint debug
@app.get("/auth/debug")
def auth_debug():
    from unified_auth import unified_token_manager
    token_data = unified_token_manager.get_token("current_user")
    return {
        "has_token": token_data is not None,
        "token_keys": list(token_data.keys()) if token_data else None,
        "is_authenticated": is_unified_authenticated("current_user")
    }

@app.get("/auth/status") 
def auth_status():
    return {
        "authenticated": is_unified_authenticated("current_user"),
        "status": get_unified_login_status("current_user") if is_unified_authenticated("current_user") else "Not logged in"
    }

@app.post("/auth/logout")
def logout():
    """Logout endpoint that clears unified token"""
    try:
        from unified_auth import clear_unified_token
        clear_unified_token("current_user")
        return {
            "status": "success",
            "message": "Successfully logged out",
            "authenticated": False
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Logout error: {str(e)}",
            "authenticated": False
        }

@app.get("/debug/ideation")
def debug_ideation():
    """Debug endpoint khusus untuk project ideation"""
    from projectProgress_modul import analyze_project_data, get_plans, get_plan_tasks
    
    debug_result = {
        "timestamp": datetime.now().isoformat(),
        "authenticated": is_unified_authenticated("current_user"),
        "steps": []
    }
    
    try:
        # Step 1: Check authentication
        debug_result["steps"].append({
            "step": 1,
            "action": "Check authentication",
            "result": debug_result["authenticated"]
        })
        
        if not debug_result["authenticated"]:
            debug_result["error"] = "User not authenticated"
            return debug_result
        
        # Step 2: Get all plans
        plans = get_plans(user_id="current_user")
        debug_result["steps"].append({
            "step": 2,
            "action": "Get all plans",
            "result": f"Found {len(plans)} plans",
            "plan_titles": [p.get('title', 'No title') for p in plans]
        })
        
        # Step 3: Find ideation project
        ideation_plan = None
        for p in plans:
            if "ideation" in p.get("title", "").lower():
                ideation_plan = p
                break
        
        debug_result["steps"].append({
            "step": 3,
            "action": "Find ideation project",
            "result": "Found" if ideation_plan else "Not found",
            "plan_info": ideation_plan if ideation_plan else None
        })
        
        if not ideation_plan:
            debug_result["error"] = "Ideation project not found"
            return debug_result
        
        # Step 4: Get tasks from ideation project
        plan_id = ideation_plan["id"]
        tasks = get_plan_tasks(plan_id, "current_user")
        
        debug_result["steps"].append({
            "step": 4,
            "action": "Get tasks from ideation project",
            "result": f"Found {len(tasks)} tasks",
            "task_titles": [t.get('title', 'No title') for t in tasks[:5]]  # First 5 tasks
        })
        
        # Step 5: Full analysis
        analysis_result = analyze_project_data("ideation", "current_user")
        
        debug_result["steps"].append({
            "step": 5,
            "action": "Full project analysis",
            "result": "Success" if "error" not in analysis_result else "Failed",
            "error": analysis_result.get("error") if "error" in analysis_result else None,
            "task_count": analysis_result.get("analysis", {}).get("total_tasks") if "error" not in analysis_result else None
        })
        
        debug_result["final_result"] = analysis_result
        
    except Exception as e:
        debug_result["exception"] = str(e)
        import traceback
        debug_result["traceback"] = traceback.format_exc()
    
    return debug_result

@app.get("/debug/analyze-project/{project_name}")
def debug_analyze_project(project_name: str):
    """Debug endpoint untuk analyze_project_data function"""
    from projectProgress_modul import analyze_project_data
    
    try:
        if not is_unified_authenticated("current_user"):
            return {
                "error": "User not authenticated",
                "authenticated": False
            }
        
        result = analyze_project_data(project_name, "current_user")
        return {
            "project_name": project_name,
            "authenticated": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "project_name": project_name,
            "error": str(e),
            "authenticated": is_unified_authenticated("current_user"),
            "timestamp": datetime.now().isoformat()
        }

# ========== DEV RUN ==========
if __name__ == "__main__":
    import nest_asyncio
    import uvicorn
    nest_asyncio.apply()
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)