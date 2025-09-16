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
    build_auth_url as project_build_auth_url,
    exchange_code_for_token as project_exchange_code_for_token,
    is_user_authenticated as project_is_user_authenticated,
    get_login_status as project_get_login_status,
    set_user_token, clear_user_token,
    token_manager
)

# Todo management imports dengan alias untuk menghindari konflik
from to_do_modul_test import (
    build_auth_url as todo_build_auth_url,
    exchange_code_for_token as todo_exchange_code_for_token,
    get_login_status as todo_get_login_status,
    process_todo_query_advanced,
    is_user_logged_in as todo_is_user_logged_in,
)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
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

# Enhanced System Prompt untuk lebih smart project handling
ENHANCED_SYSTEM_PROMPT = """
You are the company's Internal Assistant with advanced project management capabilities. You can:

1) **RAG Q&A Internal (qna_internal)** – Jawab pertanyaan policy/SOP dari dokumen internal
2) **Smart Project Progress (project_progress)** – Analisis mendalam project dari Microsoft Planner (REQUIRES LOGIN)
3) **Project List & Comparison** – List semua project atau bandingkan multiple projects  
4) **Client Status Check** – Cek status client
5) **Template Documents** – Ambil template dokumen
6) **Notifications** – Kirim notifikasi/pengingat

**ENHANCED PROJECT CAPABILITIES:**
- Deteksi otomatis project name dari natural language
- Analisis progress dengan insight dan recommendations
- Perbandingan multiple projects
- Identifikasi masalah (overdue tasks, bottlenecks)
- Smart suggestions untuk project management

**AUTHENTICATION NOTE:**
- Project features require Microsoft login via delegated permissions with PKCE for SPA
- If user asks about projects but not authenticated, inform them to login first

**USAGE GUIDELINES:**
- Untuk pertanyaan project, gunakan project_progress tool dengan query lengkap user
- Jika user tanya "list project" atau "semua project", gunakan project_list tool
- Untuk comparison, deteksi bila user menyebut 2+ project names
- Selalu berikan insight yang actionable dan highlight masalah penting
- Gunakan emoji untuk membuat response lebih engaging dan mudah dibaca

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

# =====================================================
# PROJECT MANAGEMENT - TOKEN STORAGE & ENDPOINTS
# =====================================================
user_project_tokens: Dict[str, dict] = {}

def set_project_user_token(user_id: str, token: dict):
    """Set token untuk project management"""
    user_project_tokens[user_id] = token

def get_project_user_token(user_id: str) -> Optional[dict]:
    """Get token untuk project management"""
    return user_project_tokens.get(user_id)

def clear_project_user_token(user_id: str):
    """Clear token untuk project management"""
    if user_id in user_project_tokens:
        del user_project_tokens[user_id]

def is_project_user_authenticated(user_id: str) -> bool:
    """Check apakah user sudah login untuk project management"""
    return user_id in user_project_tokens and user_project_tokens[user_id] is not None

# ===== PROJECT AUTH FLOW =====
@app.get("/project/login")
def project_login():
    """
    Endpoint login untuk project management
    """
    try:
        auth_url = project_build_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        return {"error": f"Gagal membuat login URL: {str(e)}"}

@app.get("/project/auth/callback")
def project_auth_callback(code: str, state: str = None):
    """
    Callback dari Microsoft untuk project management
    """
    try:
        token = project_exchange_code_for_token(code)
        if not token:
            raise HTTPException(status_code=400, detail="Gagal tukar code jadi token")

        set_project_user_token("current_user", token)

        return HTMLResponse("""
            <html>
                <head>
                    <title>Project Login Successful</title>
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            margin: 40px; 
                            background-color: #e8f5e8; 
                            text-align: center;
                        }
                        .container { 
                            background: white; 
                            padding: 30px; 
                            border-radius: 8px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                            max-width: 500px;
                            margin: 0 auto;
                        }
                    </style>
                    <script>
                        setTimeout(function() {
                            window.close();
                        }, 3000);
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h1>✅ Project Login Successful!</h1>
                        <p>You can now access Microsoft Project Management features.</p>
                        <p><small>This window will close automatically in 3 seconds...</small></p>
                    </div>
                </body>
            </html>
        """)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error saat login: {str(e)}")

@app.get("/project/status")
def project_status():
    """
    Cek status login project management
    """
    try:
        if is_project_user_authenticated("current_user"):
            return {
                "authenticated": True,
                "status": "✅ Sudah login Smart Project Management",
                "features_available": [
                    "Project Progress Analysis",
                    "Multi-Project Comparison",
                    "Portfolio Overview",
                    "Task Management Insights"
                ],
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "authenticated": False,
                "status": "❌ Belum login",
                "login_url": "/project/login"
            }
    except Exception as e:
        return {"authenticated": False, "status": f"Error: {str(e)}"}

@app.get("/project/logout")
def project_logout():
    """
    Logout dari project management
    """
    try:
        clear_project_user_token("current_user")
        return {
            "status": "success",
            "message": "✅ Successfully logged out from Project Management",
            "login_url": "/project/login"
        }
    except Exception as e:
        return {"status": "error", "message": f"Error during logout: {str(e)}"}

@app.get("/projects")
def get_all_projects():
    """Get semua projects"""
    if not is_project_user_authenticated("current_user"):
        return {
            "error": "Authentication required",
            "message": "Please login first via /project/login",
            "login_url": "/project/login",
            "authenticated": False
        }

    try:
        # Pass token directly to ensure module uses the same token
        token = get_project_user_token("current_user")
        if token:
            # Import and use the module function that accepts token directly
            from projectProgress_modul import set_user_token
            set_user_token(token, "current_user")  # Sync token to module
        
        result = list_all_projects("current_user")
        return {
            "status": "success",
            "projects": result,
            "authenticated": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": f"Error fetching projects: {str(e)}",
            "authenticated": True,
            "error_details": str(e)
        }

@app.get("/projects/{project_name}")
def get_project_detail(project_name: str):
    """Get detail project tertentu"""
    if not is_project_user_authenticated("current_user"):
        return {
            "error": "Authentication required",
            "message": "Please login first via /project/login",
            "login_url": "/project/login",
            "authenticated": False
        }

    try:
        result = process_project_query(f"detail progress {project_name}", "current_user")
        return {
            "status": "success",
            "project_detail": result,
            "project_name": project_name,
            "authenticated": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": f"Error fetching project detail: {str(e)}",
            "project_name": project_name,
            "authenticated": True
        }

@app.post("/project-chat")
def project_chat(req: dict):
    """Chat endpoint untuk project management"""
    message = req.get("message", "")
    try:
        if not is_project_user_authenticated("current_user"):
            return {"answer": "🔒 Authentication Required. Please login first via /project/login"}
        
        result = process_project_query(message, "current_user")
        return {"answer": result}
    except Exception as e:
        return {"answer": f"❌ Error: {str(e)}"}

# =====================================================
# TO-DO MANAGEMENT - TOKEN STORAGE & ENDPOINTS
# =====================================================
user_todo_tokens: Dict[str, dict] = {}

def set_todo_user_token(user_id: str, token: dict):
    """Set token untuk todo management"""
    user_todo_tokens[user_id] = token

def get_todo_user_token(user_id: str) -> Optional[dict]:
    """Get token untuk todo management"""
    return user_todo_tokens.get(user_id)

def clear_todo_user_token(user_id: str):
    """Clear token untuk todo management"""
    if user_id in user_todo_tokens:
        del user_todo_tokens[user_id]

def is_todo_user_authenticated(user_id: str) -> bool:
    """Check apakah user sudah login untuk todo management"""
    return user_id in user_todo_tokens and user_todo_tokens[user_id] is not None

# ===== TO-DO AUTH FLOW =====
@app.get("/login")  # Keep original path untuk compatibility dengan Azure AD registration
def todo_login():
    """
    Endpoint login untuk todo management - redirect ke Microsoft
    """
    try:
        auth_url = todo_build_auth_url()
        return RedirectResponse(auth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat login URL: {str(e)}")

@app.get("/todo/login")
def todo_login_api():
    """
    API endpoint untuk get login URL (for frontend)
    """
    try:
        auth_url = todo_build_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        return {"error": f"Gagal membuat login URL: {str(e)}"}

@app.get("/auth/callback")  # KEEP ORIGINAL PATH - ini yang diexpect Microsoft
def todo_auth_callback(code: str, state: str = None):
    """
    Callback dari Microsoft untuk todo management
    """
    try:
        token = todo_exchange_code_for_token(code)
        if not token:
            raise HTTPException(status_code=400, detail="Gagal tukar code jadi token")

        set_todo_user_token("current_user", token)

        return HTMLResponse("""
            <html>
                <head>
                    <title>Todo Login Successful</title>
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            margin: 40px; 
                            background-color: #e8f5e8; 
                            text-align: center;
                        }
                        .container { 
                            background: white; 
                            padding: 30px; 
                            border-radius: 8px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                            max-width: 500px;
                            margin: 0 auto;
                        }
                    </style>
                    <script>
                        setTimeout(function() {
                            window.close();
                        }, 3000);
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h1>✅ Todo Login Successful!</h1>
                        <p>You can now access Microsoft To-Do features.</p>
                        <p><small>This window will close automatically in 3 seconds...</small></p>
                    </div>
                </body>
            </html>
        """)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error saat login: {str(e)}")

@app.get("/todo/login-status")
def todo_login_status():
    """Check status login todo"""
    try:
        if is_todo_user_authenticated("current_user"):
            return {
                "authenticated": True,
                "status": "✅ Sudah login Microsoft To-Do"
            }
        else:
            # Cek juga menggunakan function dari module (fallback)
            try:
                module_status = todo_get_login_status()
                is_logged_in = todo_is_user_logged_in()
                return {
                    "authenticated": is_logged_in,
                    "status": module_status
                }
            except Exception as module_error:
                return {
                    "authenticated": False,
                    "status": f"❌ Belum login. Module error: {str(module_error)}"
                }
    except Exception as e:
        return {
            "authenticated": False,
            "status": f"Error: {str(e)}"
        }

@app.get("/todo/login-url")
def todo_login_url():
    """Get URL untuk login todo"""
    try:
        auth_url = todo_build_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        return {"auth_url": None, "error": str(e)}

@app.get("/todo/logout")
def todo_logout():
    """Logout dari todo management"""
    try:
        clear_todo_user_token("current_user")
        return {
            "status": "success",
            "message": "✅ Successfully logged out from To-Do",
            "login_url": "/todo/login"
        }
    except Exception as e:
        return {"status": "error", "message": f"Error during logout: {str(e)}"}

@app.post("/todo-chat")
def todo_chat(req: dict):
    """Chat endpoint untuk todo management"""
    message = req.get("message", "")
    try:
        # Check authentication menggunakan multiple methods
        local_auth = is_todo_user_authenticated("current_user")
        module_auth = False
        
        try:
            module_auth = todo_is_user_logged_in()
        except Exception:
            pass
        
        if not local_auth and not module_auth:
            return {"answer": "❌ Belum login ke Microsoft To-Do. Silakan login terlebih dahulu."}
        
        # Get token - prioritize local storage, fallback to module
        token = get_todo_user_token("current_user")
        
        answer = process_todo_query_advanced(message, token)
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"❌ Error: {str(e)}"}

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

# ========== DEV RUN ==========
if __name__ == "__main__":
    import nest_asyncio
    import uvicorn
    nest_asyncio.apply()
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)