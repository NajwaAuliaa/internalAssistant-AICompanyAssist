from depedencies import *

# Import enhanced tools dan update agent creation
from internal_assistant_core import (
    get_or_create_agent, settings, 
    blob_container  # Keep existing core functionality
)

# Modul RAG (answering & indexing) - UNCHANGED
from rag_modul import (
    rag_answer, process_and_index_docs
)

# Enhanced project tools - NOW WITH SPA SUPPORT
from projectProgress_modul import (
    project_tool, project_detail_tool, project_list_tool, portfolio_analysis_tool,
    process_project_query, list_all_projects, intelligent_project_query,
    # Import authentication functions with SPA support
    build_auth_url as project_build_auth_url,
    exchange_code_for_token as project_exchange_code_for_token,
    is_user_authenticated as project_is_user_authenticated,
    get_login_status as project_get_login_status,
    set_user_token, clear_user_token,
    # Import the centralized token manager
    token_manager
)

# Modul To Do - UNCHANGED
from to_do_modul_test import (
    build_auth_url,
    exchange_code_for_token,
    get_todo_lists,
    get_todo_tasks,
    get_current_token,
    is_user_logged_in,
    get_login_status,
    process_todo_query_advanced,
    create_todo_task,
    complete_todo_task,
    update_todo_task
)

from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import webbrowser
import threading

# FastAPI App & Schemas
app = FastAPI(title="Internal Assistant – LangChain + Azure + UI")

# Enable CORS untuk SPA compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],  # Specific origins for SPA
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
    return {"ok": True, "service": "Internal Assistant – LangChain + Azure + UI (SPA Compatible)"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
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

class IndexRequest(BaseModel):
    prefix: str = "sop/"

@app.post("/admin/index")
def admin_index(req: IndexRequest):
    return process_and_index_docs(prefix=req.prefix)

# =====================================================
# PROJECT AUTHENTICATION ENDPOINTS - FIXED FOR SPA
# =====================================================

@app.get("/project/login")
def project_login():
    """Redirect user ke Microsoft login page untuk project access (SPA dengan PKCE)."""
    try:
        # Generate auth URL with PKCE parameters for SPA
        auth_url = project_build_auth_url()
        return RedirectResponse(auth_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building auth URL: {str(e)}")

@app.get("/project/auth/callback")
def project_auth_callback(
    code: Optional[str] = None, 
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """
    Enhanced callback untuk SPA dengan robust error handling dan PKCE support.
    Menangani berbagai error scenarios termasuk SPA-specific issues.
    """
    
    # Handle OAuth errors dari Microsoft
    if error:
        error_details = f"Microsoft OAuth Error: {error}"
        if error_description:
            error_details += f" - {error_description}"
        
        # Specific handling untuk SPA dan PKCE errors
        if "Single-Page Application" in str(error_description):
            error_details += "\n\nSPA Authentication Issue: This error occurs when there's a mismatch in client configuration or request origin. The application is configured correctly for SPA with PKCE."
        elif "PKCE" in str(error_description):
            error_details += "\n\nPKCE (Proof Key for Code Exchange) Issue: Please try the following:\n1. Clear your browser cache\n2. Try logging in again\n3. If the issue persists, check the application configuration."
        
        return HTMLResponse(f"""
            <html>
                <head>
                    <title>SPA Authentication Failed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .error {{ color: #d32f2f; margin-bottom: 20px; background: #fff5f5; padding: 15px; border-radius: 4px; }}
                        .retry-btn {{ background: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 15px; }}
                        .spa-info {{ background: #e3f2fd; padding: 15px; border-radius: 4px; margin: 15px 0; border-left: 4px solid #1976d2; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🔒 SPA Authentication Failed</h1>
                        <div class="error">{error_details}</div>
                        <div class="spa-info">
                            <strong>SPA Configuration:</strong> This application is configured as a Single-Page Application (SPA) with PKCE security. 
                            Make sure you're accessing from the correct origin (http://localhost:8001).
                        </div>
                        <p>You can try logging in again or close this window and return to the main application.</p>
                        <a href="/project/login" class="retry-btn">Try Login Again</a>
                    </div>
                </body>
            </html>
        """, status_code=400)

    # Handle missing authorization code
    if not code:
        return HTMLResponse("""
            <html>
                <head>
                    <title>SPA Authentication Cancelled</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>❌ SPA Authentication Cancelled</h1>
                        <p>Authorization code not found. The login process may have been cancelled or interrupted.</p>
                        <p>Please close this window and try logging in again from the main application.</p>
                        <a href="/project/login" style="background: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Try Again</a>
                    </div>
                </body>
            </html>
        """, status_code=400)

    # Process successful authorization code for SPA
    try:
        # Exchange code for token with PKCE for SPA - pass the state for validation
        token = project_exchange_code_for_token(code, state)
        
        if not token:
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code for access token in SPA flow")
        
        # Store token menggunakan centralized token manager
        set_user_token(token, "current_user")
        
        # Return success page dengan auto-close functionality for SPA
        return HTMLResponse("""
            <html>
                <head>
                    <title>SPA Login Successful</title>
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
                        .success { color: #2e7d32; font-size: 18px; margin-bottom: 20px; }
                        .close-btn { 
                            background: #4caf50; 
                            color: white; 
                            padding: 12px 24px; 
                            border: none; 
                            border-radius: 4px; 
                            cursor: pointer; 
                            font-size: 16px;
                            margin-top: 15px;
                        }
                        .spa-badge {
                            background: #1976d2;
                            color: white;
                            padding: 5px 10px;
                            border-radius: 12px;
                            font-size: 12px;
                            display: inline-block;
                            margin: 10px 0;
                        }
                    </style>
                    <script>
                        // Auto close window setelah 3 detik
                        setTimeout(function() {
                            window.close();
                        }, 3000);
                        
                        function closeWindow() {
                            window.close();
                        }
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h1>✅ SPA Login Successful!</h1>
                        <div class="spa-badge">Single-Page Application</div>
                        <div class="success">
                            You have successfully logged in to Microsoft Project Management using SPA with PKCE security.
                        </div>
                        <p>You can now access project data and features securely.</p>
                        <p><small>This window will close automatically in 3 seconds...</small></p>
                        <button class="close-btn" onclick="closeWindow()">Close Window</button>
                    </div>
                </body>
            </html>
        """)
        
    except Exception as e:
        error_message = str(e)
        
        # Enhanced error handling untuk SPA-specific issues
        if "Single-Page Application" in error_message:
            error_details = f"SPA Token Exchange Error: {error_message}\n\nThis occurs when the token request doesn't match SPA configuration. Please ensure:\n1. The application is registered as SPA in Azure\n2. PKCE parameters are correctly generated\n3. Origin header matches the registered redirect URI"
        elif "PKCE" in error_message or "code_verifier" in error_message:
            error_details = f"PKCE Verification Failed: {error_message}\n\nThis is likely due to a session mismatch in SPA flow. Please try:\n1. Starting a fresh login process\n2. Clearing browser cache if the issue persists\n3. Ensure cookies are enabled"
        elif "invalid_grant" in error_message:
            error_details = f"Authorization Grant Invalid: The authorization code may have expired or already been used. Please try logging in again."
        elif "invalid_client" in error_message:
            error_details = f"Client Configuration Error: There may be an issue with the SPA application configuration. Please contact support."
        else:
            error_details = f"SPA Authentication Error: {error_message}"
        
        return HTMLResponse(f"""
            <html>
                <head>
                    <title>SPA Authentication Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #ffeaa7; }}
                        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .error {{ color: #d63031; background: #fff5f5; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                        .spa-note {{ background: #dbeafe; padding: 15px; border-radius: 4px; margin: 15px 0; border-left: 4px solid #3b82f6; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>⚠️ SPA Authentication Error</h1>
                        <div class="error">{error_details}</div>
                        <div class="spa-note">
                            <strong>Note:</strong> This application uses Single-Page Application (SPA) authentication with PKCE for enhanced security.
                        </div>
                        <p>Please try logging in again. If the problem persists, please contact support.</p>
                        <a href="/project/login" style="background: #0984e3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Retry Login</a>
                    </div>
                </body>
            </html>
        """, status_code=500)

@app.get("/project/status")
def project_auth_status():
    """Check current project authentication status dengan enhanced info untuk SPA"""
    try:
        is_authenticated = project_is_user_authenticated("current_user")
        status_message = project_get_login_status("current_user")
        
        return {
            "authenticated": is_authenticated,
            "status": status_message,
            "login_url": "/project/login" if not is_authenticated else None,
            "client_type": "Single-Page Application (SPA)",
            "security": "PKCE Enhanced",
            "features_available": [
                "Project Progress Analysis",
                "Multi-Project Comparison", 
                "Portfolio Overview",
                "Task Management Insights"
            ] if is_authenticated else [],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "authenticated": False,
            "status": f"Error checking authentication status: {str(e)}",
            "login_url": "/project/login",
            "client_type": "Single-Page Application (SPA)",
            "error": str(e)
        }

@app.get("/project/logout")
def project_logout():
    """Logout and clear project authentication for SPA"""
    try:
        clear_user_token("current_user")
        return {
            "status": "success",
            "message": "Successfully logged out from SPA project management",
            "client_type": "Single-Page Application",
            "login_url": "/project/login"
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error during SPA logout: {str(e)}"
        }

# Enhanced project endpoints untuk direct API access dengan SPA support
@app.get("/projects")
def get_all_projects():
    """Enhanced API endpoint untuk mendapatkan list semua projects dengan SPA status check"""
    try:
        if not project_is_user_authenticated("current_user"):
            return {
                "error": "Authentication required",
                "message": "Please login first via /project/login",
                "login_url": "/project/login",
                "authenticated": False,
                "client_type": "Single-Page Application (SPA)"
            }
        
        result = list_all_projects("current_user")
        return {
            "status": "success",
            "projects": result,
            "authenticated": True,
            "client_type": "SPA",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": f"Error fetching projects: {str(e)}",
            "authenticated": project_is_user_authenticated("current_user"),
            "client_type": "SPA",
            "login_url": "/project/login" if not project_is_user_authenticated("current_user") else None
        }

@app.get("/projects/{project_name}")
def get_project_detail(project_name: str):
    """Enhanced API endpoint untuk detail project tertentu dengan SPA support"""
    try:
        if not project_is_user_authenticated("current_user"):
            return {
                "error": "Authentication required", 
                "message": "Please login first via /project/login",
                "login_url": "/project/login",
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
            "authenticated": project_is_user_authenticated("current_user"),
            "client_type": "SPA",
            "login_url": "/project/login" if not project_is_user_authenticated("current_user") else None
        }

# =====================================================
# EXISTING TO-DO ENDPOINTS - UNCHANGED but keep separate tokens
# =====================================================

# Keep separate token storage for todo (if needed)
user_todo_tokens: Dict[str, dict] = {}

@app.get("/login")
def login():
    """Redirect user ke Microsoft login page (delegated) - FOR TODO."""
    auth_url = build_auth_url()
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
def auth_callback(code: str, state: Optional[str] = None):
    """Callback setelah user login, tukarkan code dengan token - FOR TODO."""
    try:
        token = exchange_code_for_token(code)
        if not token:
            raise HTTPException(status_code=400, detail="Gagal tukar code jadi token")
        # Simpan ke memory (demo) - separate from project tokens
        user_todo_tokens["current_user"] = token
        return {
            "status": "success", 
            "message": "Login berhasil! Anda bisa menutup tab ini dan kembali ke aplikasi.",
            "token": "tersimpan di server memory"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error saat login: {str(e)}")

# ====================
# Gradio UI Functions - UPDATED WITH SPA SUPPORT
# ====================

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

def ui_upload_and_index(files: List, prefix: str):
    if not prefix:
        prefix = "sop/"
    if not prefix.endswith("/"):
        prefix += "/"

    uploaded = []
    errors = []

    for f in files or []:
        try:
            local_path = getattr(f, "name", None) or str(f)
            fname = os.path.basename(local_path)
            blob_name = f"{prefix}{fname}"
            with open(local_path, "rb") as fp:
                data = fp.read()
            content_type = _detect_mime(local_path)
            blob_client = blob_container.get_blob_client(blob_name)
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
            uploaded.append(blob_name)
        except Exception as e:
            errors.append(f"{getattr(f,'name',str(f))}: {e}")

    index_report = process_and_index_docs(prefix=prefix)
    return json.dumps(
        {"uploaded": uploaded, "upload_errors": errors, "index_report": index_report},
        indent=2,
        ensure_ascii=False
    )

def ui_rag_chat(message: str, history: List[Dict[str, str]]):
    try:
        answer = rag_answer(message)
        return answer
    except Exception as e:
        return f"Terjadi error saat RAG: {e}"

def ui_project_progress(project_name: str):
    try:
        return intelligent_project_query(project_name, "current_user")
    except Exception as e:
        return f"Terjadi error saat ambil progress project: {e}"

def ui_project_smart_chat(message: str, history: List[List[str]]):
    """Enhanced project chat dengan natural language processing + SPA auth check"""
    try:
        if not message.strip():
            return """🚀 **Selamat datang di Smart Project Assistant!**

Saya bisa membantu Anda dengan:

**📊 Cek Progress Project:**
• "Sudah sampai mana progress project A?"
• "Bagaimana status project website baru?"
• "Project mana yang paling tertinggal?"

**📋 List & Overview:**
• "Tampilkan semua project"
• "Project apa saja yang sedang berjalan?"
• "Berikan overview semua project"

**⚖️ Perbandingan Project:**
• "Bandingkan project A dengan project B"
• "Mana yang lebih maju antara project X dan Y?"

**🔍 Analisis Mendalam:**
• "Analisis bottleneck di project A"
• "Task apa yang overdue di project B?"
• "Berikan insight untuk project C"

⚠️ **PERLU LOGIN:** Fitur project memerlukan autentikasi Microsoft SPA.
Klik tombol '🔑 Login untuk Project Management' di bawah jika belum login.

Coba tanyakan sesuatu tentang project Anda! 🤖"""
        
        # Check authentication using SPA-compatible centralized system
        if not project_is_user_authenticated("current_user"):
            return """🔒 **SPA Authentication Required untuk Project Management**

Untuk mengakses data Microsoft Planner, Anda perlu login terlebih dahulu.

**Cara Login (SPA Mode):**
1. Klik tombol '🔑 Login untuk Project Management' di bawah
2. Login dengan akun Microsoft Anda
3. Berikan izin akses untuk membaca data Planner
4. Kembali ke sini dan coba query Anda lagi

**Permissions yang dibutuhkan:**
- User.Read (info user dasar)
- Tasks.Read (data task dari Planner)  
- Group.Read.All (akses group dan plan)

**Enhanced Security:**
Aplikasi ini menggunakan Single-Page Application (SPA) authentication dengan PKCE (Proof Key for Code Exchange) untuk keamanan maksimal.

Silakan login terlebih dahulu untuk melanjutkan."""
        
        # Process menggunakan enhanced project query with SPA-compatible auth
        response = intelligent_project_query(message, "current_user")
        return response
        
    except Exception as e:
        error_msg = str(e)
        if "Single-Page Application" in error_msg:
            return f"❌ **SPA Authentication Error:** {error_msg}\n\nSilakan coba login ulang. Pastikan Anda mengakses dari origin yang benar (http://localhost:8001)."
        elif "PKCE" in error_msg or "code_verifier" in error_msg:
            return f"❌ **PKCE Authentication Error:** {error_msg}\n\nSilakan coba login ulang. Jika masalah berlanjut, clear browser cache dan coba lagi."
        return f"❌ **Error:** {error_msg}\n\nSilakan coba lagi atau refresh halaman."

def ui_project_login():
    """Login ke Microsoft untuk project access dengan SPA + PKCE support"""
    try:
        # URL ini harus sesuai dengan yang di-handle oleh FastAPI backend
        login_url = "http://127.0.0.1:8001/project/login"
        
        # Buka browser dalam thread terpisah
        def open_browser():
            webbrowser.open(login_url)
        
        threading.Thread(target=open_browser, daemon=True).start()
        return "🔗 Browser akan terbuka untuk login Microsoft Project dengan SPA + PKCE security. Setelah login, kembali ke sini dan klik 'Refresh Status'."
    except Exception as e:
        return f"❌ Error membuka login: {str(e)}"

def ui_project_check_status():
    """Check authentication status untuk project dengan SPA enhanced info"""
    try:
        status = project_get_login_status("current_user")
        if project_is_user_authenticated("current_user"):
            return f"{status}\n\n✅ **SPA Authentication:** Secure connection established\n🔐 **PKCE Security:** Active and validated\n🌐 **Client Type:** Single-Page Application"
        else:
            return f"{status}\n\n💡 **Tip:** Setelah login, pastikan untuk memberikan consent untuk semua permissions yang diminta.\n🔒 **Security:** SPA dengan PKCE protection"
    except Exception as e:
        return f"❌ Error check status: {str(e)}"

def ui_get_project_suggestions():
    """Generate smart suggestions untuk project management dengan SPA context"""
    try:
        if not project_is_user_authenticated("current_user"):
            return """🔒 **SPA Login Required**

Silakan login terlebih dahulu untuk mendapatkan project suggestions.

**Enhanced Security:** Aplikasi menggunakan Single-Page Application dengan PKCE untuk keamanan maksimal."""
        
        suggestions = """💡 **Smart Project Management Suggestions:**

**🎯 Quick Actions:**
• "Status semua project yang overdue"
• "Project mana yang butuh perhatian urgent?"
• "Ranking project berdasarkan completion rate"
• "Task bottleneck di semua project"

**📈 Analytics & Insights:**
• "Tren completion rate bulan ini"
• "Project dengan risk tertinggi"
• "Rekomendasi prioritas untuk minggu depan"
• "Analisis productive team performance"

**🔄 Management Actions:**
• "Update status project berdasarkan progress real"
• "Identifikasi dependencies yang blocking"
• "Saran resource allocation untuk project tertinggal"

**🔐 Secure:** All data accessed via SPA + PKCE secured Microsoft Graph API
"""
        return suggestions
        
    except Exception as e:
        return f"Error generating suggestions: {str(e)}"

# =======================================
# ====  TO DO UI Functions - UNCHANGED  =====
# =======================================

def ui_login_to_microsoft():
    """Buka browser ke login Microsoft dan return status"""
    try:
        auth_url = build_auth_url()
        # Buka browser dalam thread terpisah
        def open_browser():
            webbrowser.open(auth_url)
        
        threading.Thread(target=open_browser, daemon=True).start()
        return "🔗 Browser akan terbuka untuk login Microsoft. Setelah login, kembali ke sini dan klik 'Refresh Status'."
    except Exception as e:
        return f"❌ Error membuka login: {str(e)}"

def ui_check_login_status():
    """Check apakah user sudah login"""
    try:
        return get_login_status()
    except Exception as e:
        return f"❌ Error check status: {str(e)}"

def ui_todo_chat(message: str, history: List[List[str]]):
    """Main function untuk chat dengan To-Do menggunakan LLM (Enhanced Version)"""
    try:
        # Check login status first
        if not is_user_logged_in():
            return "❌ **Belum login ke Microsoft To-Do.** \n\nSilakan login terlebih dahulu dengan klik tombol '🔑 Login ke Microsoft' di atas."
        
        if not message.strip():
            return """📝 **Selamat datang di Smart To-Do Assistant!** Saya menggunakan AI untuk memahami perintah Anda dalam bahasa natural. Anda bisa mengatakan hal seperti:

**Melihat Tasks:**
• "Tampilkan semua task saya"
• "Apa saja task yang deadline hari ini?"
• "Task mana yang sudah selesai minggu ini?"
• "Tunjukkan task yang overdue"

**Membuat Tasks:**
• "Buatkan task baru: Review laporan keuangan"
• "Tambahkan task meeting dengan client besok"
• "Buat reminder untuk call vendor deadline 5 September"

**Menyelesaikan Tasks:**
• "Tandai task 'Meeting pagi' sebagai selesai"
• "Task review document sudah selesai"
• "Complete task presentation"

**Update Tasks:**
• "Ubah deadline task meeting jadi besok"
• "Update deskripsi task review: tambahkan notes dari client"

Coba katakan sesuatu dan saya akan membantu mengelola To-Do Anda! 🤖"""
        
        # Process query dengan advanced LLM processing
        response = process_todo_query_advanced(message, user_todo_tokens.get("current_user"))
        return response
        
    except Exception as e:
        return f"❌ **Error:** {str(e)}\n\nSilakan coba lagi atau refresh status login Anda."

def ui_todo_examples():
    """Return contoh-contoh query yang bisa digunakan (Updated for LLM)"""
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
    return "\n".join([f"• {ex}" for ex in examples])

def ui_get_smart_suggestions():
    """Generate smart suggestions berdasarkan current state (LLM-powered)"""
    try:
        if not is_user_logged_in():
            return "Silakan login terlebih dahulu untuk mendapatkan suggestions."
        
        # This could be enhanced to use LLM for generating contextual suggestions
        return """💡 **Smart Suggestions berdasarkan AI:**

**Perintah Populer:**
• "Analisis produktivitas saya minggu ini"
• "Task apa yang paling urgent?"
• "Buatkan planning task untuk project baru"
• "Reminder untuk follow up client besok"

**Tips Manajemen Task:**
• Gunakan bahasa natural - AI akan memahami maksud Anda
• Sebutkan deadline dengan jelas: "hari ini", "besok", "5 September"  
• Deskripsi task bisa lebih detail untuk tracking yang better
• AI bisa membantu prioritisasi berdasarkan deadline dan urgency"""
        
    except Exception as e:
        return f"Error generating suggestions: {str(e)}"

# ====================
# Gradio UI (WITH SPA PROJECT AUTH SUPPORT AND PKCE)
# ====================

with gr.Blocks(title="Internal Assistant – RAG + SPA Project Management", theme=gr.themes.Soft()) as ui:
    gr.Markdown("# Internal Assistant – Knowledge + Smart Project Management (SPA) + AI To-Do")

    with gr.Tab("Upload & Index"):
        gr.Markdown("Upload dokumen kamu ke Azure Blob, lalu index ke Cognitive Search.")
        prefix = gr.Textbox(value="sop/", label="Folder/Prefix di Blob (akan dibuat jika belum ada)")
        files = gr.File(label="Upload Files", file_count="multiple")
        run_btn = gr.Button("Upload & Index")
        output = gr.Code(label="Hasil Upload + Index (JSON)")

        run_btn.click(
            fn=ui_upload_and_index,
            inputs=[files, prefix],
            outputs=[output],
        )

    with gr.Tab("Chat (RAG)"):
        gr.Markdown("Tanya dokumen yang sudah di-index.")
        chat = gr.ChatInterface(
            fn=ui_rag_chat,
            title="RAG Chat",
            textbox=gr.Textbox(placeholder="Tanyakan SOP/kebijakan…"),
        )

    with gr.Tab("🚀 Smart Project Management (SPA)"):
        gr.Markdown("# 🚀 Smart Project Management Assistant (SPA)")
        gr.Markdown("**Powered by Azure OpenAI + SPA + PKCE Security** - Chat dengan AI untuk mengelola project dari Microsoft Planner!")

        # Authentication Status Section - UPDATED WITH SPA INFO
        with gr.Row():
            with gr.Column(scale=2):
                project_login_status = gr.Textbox(
                    label="🔐 Status Login Project (SPA + PKCE Secured)", 
                    value="Checking...", 
                    interactive=False,
                    lines=3
                )
            with gr.Column(scale=1):
                project_login_btn = gr.Button("🔑 Login untuk Project Management (SPA)", variant="primary", size="sm")
                project_refresh_btn = gr.Button("🔄 Refresh Status", size="sm")
                project_logout_btn = gr.Button("🚪 Logout", size="sm", variant="secondary")

        # SPA + PKCE Security Info
        gr.Markdown("""
        ### 🔒 **Enhanced Security Features (SPA Mode):**
        - **Single-Page Application (SPA)** - Modern web application architecture
        - **PKCE (Proof Key for Code Exchange)** - Industry standard security untuk OAuth flows
        - **Delegated Permissions** - Access data sesuai dengan permissions user
        - **Secure Token Management** - Tokens disimpan dengan enkripsi di server
        - **Session Validation** - Regular validation untuk memastikan token masih valid
        - **Origin Validation** - Additional security layer untuk SPA
        """)

        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("### 💬 Chat dengan Project Assistant")
                
                # Main project chat interface dengan SPA enhanced capabilities
                project_chat = gr.ChatInterface(
                    fn=ui_project_smart_chat,
                    title="🤖 Smart Project Assistant (SPA + PKCE Secured)",
                    textbox=gr.Textbox(
                        placeholder="Contoh: 'Progress project website sudah sampai mana?' atau 'Analisis semua project yang overdue'",
                        lines=2
                    )
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### ⚡ Quick Actions")
                
                quick_project_btn1 = gr.Button("📋 List Semua Project", size="sm", variant="secondary")
                quick_project_btn2 = gr.Button("📊 Overview Progress", size="sm", variant="secondary")
                quick_project_btn3 = gr.Button("⚠️ Project dengan Masalah", size="sm", variant="secondary")
                quick_project_btn4 = gr.Button("🎯 Top Priority Projects", size="sm", variant="secondary")
                quick_project_btn5 = gr.Button("📈 Weekly Project Summary", size="sm", variant="secondary")

        # Enhanced Examples and Analysis Features
        with gr.Accordion("💡 Advanced Features & Examples", open=False):
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### 🎯 **Natural Language Examples:**")
                    project_examples = gr.Textbox(
                        label="Contoh Query untuk Project",
                        value="""• "Sudah sampai mana progress project A berjalan?"
• "Project mana yang paling tertinggal?"
• "Bandingkan progress project website dengan mobile app"
• "Task apa saja yang overdue di project B?"
• "Berikan insight untuk project yang stuck"
• "Analisis bottleneck di semua project"
• "Ranking project berdasarkan completion rate"
• "Project mana yang butuh resource tambahan?"
• "Status milestone project Q4"
• "Estimasi completion time project C"
• "Task critical path di project development"
• "Risk assessment untuk project tertinggal" """,
                        interactive=False,
                        lines=12
                    )
                
                with gr.Column():
                    gr.Markdown("#### 🧠 **AI Capabilities:**")
                    ai_features = gr.Textbox(
                        label="Fitur AI Project Management",
                        value=ui_get_project_suggestions(),
                        interactive=False,
                        lines=12
                    )

        # Project Authentication Event Handlers untuk SPA
        def handle_project_tab_select():
            """Dipanggil ketika tab project dibuka"""
            return ui_project_check_status()

        ui.load(
            fn=handle_project_tab_select,
            inputs=None,
            outputs=[project_login_status]
        )

        project_login_btn.click(
            fn=ui_project_login,
            inputs=None,
            outputs=[project_login_status]
        )

        project_refresh_btn.click(
            fn=ui_project_check_status,
            inputs=None,
            outputs=[project_login_status]
        )

        # Enhanced logout functionality for SPA
        def handle_logout():
            try:
                clear_user_token("current_user")
                return "🚪 Successfully logged out from SPA. Click 'Login untuk Project Management' to login again."
            except Exception as e:
                return f"❌ Error during SPA logout: {str(e)}"

        project_logout_btn.click(
            fn=handle_logout,
            inputs=None,
            outputs=[project_login_status]
        )

        # Quick Action Event Handlers untuk Project (SPA compatible)
        quick_project_btn1.click(
            fn=lambda: "Tampilkan semua project dengan status dan progress lengkap",
            inputs=None,
            outputs=project_chat.textbox
        )
        
        quick_project_btn2.click(
            fn=lambda: "Berikan overview progress semua project dengan insight dan recommendations",
            inputs=None,
            outputs=project_chat.textbox
        )
        
        quick_project_btn3.click(
            fn=lambda: "Identifikasi project yang bermasalah atau tertinggal dengan analisis root cause",
            inputs=None,
            outputs=project_chat.textbox
        )
        
        quick_project_btn4.click(
            fn=lambda: "Ranking project berdasarkan prioritas dan urgency dengan actionable recommendations",
            inputs=None,
            outputs=project_chat.textbox
        )
        
        quick_project_btn5.click(
            fn=lambda: "Buatkan weekly summary semua project dengan achievement dan next steps",
            inputs=None,
            outputs=project_chat.textbox
        )

    # Legacy Project Tab (simplified) - KEPT FOR COMPATIBILITY
    with gr.Tab("Progress Project (Simple)"):
        gr.Markdown("Cek progress project sederhana dari Microsoft Planner.")
        project_name = gr.Textbox(label="Nama Project")
        run_btn2 = gr.Button("Cek Progress")
        output2 = gr.Textbox(label="Hasil Progress", lines=15)

        run_btn2.click(
            fn=ui_project_progress,
            inputs=[project_name],
            outputs=[output2],
        )
    
    with gr.Tab("🤖 Smart To-Do (AI-Powered)"):
        gr.Markdown("# 🤖 Smart Microsoft To-Do Assistant")
        gr.Markdown("**Powered by Azure OpenAI** - Chat dengan AI untuk mengelola To-Do Anda menggunakan bahasa natural!")

        # Login Status Section
        with gr.Row():
            with gr.Column(scale=2):
                login_status = gr.Textbox(
                    label="🔐 Status Login", 
                    value="Checking...", 
                    interactive=False,
                    lines=1
                )
            with gr.Column(scale=1):
                login_btn = gr.Button("🔑 Login ke Microsoft", variant="primary", size="sm")
                refresh_btn = gr.Button("🔄 Refresh Status", size="sm")

        # AI Info Banner
        gr.Markdown("""
        ### 🧠 **AI-Enhanced Features:**
        - **Natural Language Understanding** - Gunakan bahasa sehari-hari
        - **Smart Task Matching** - AI akan mencari task yang Anda maksud
        - **Intelligent Insights** - Analisis produktivitas dan suggestions
        - **Context-Aware Responses** - Memahami konteks dan intent Anda
        """)

        # Main Chat Interface  
        gr.Markdown("### 💬 Chat dengan Smart To-Do Assistant")
        
        # Enhanced chat interface untuk To-Do dengan LLM
        todo_chat = gr.ChatInterface(
            fn=ui_todo_chat,
            title="🤖 AI To-Do Assistant",
            textbox=gr.Textbox(
                placeholder="Contoh: 'Analisis produktivitas saya' atau 'Buatkan task review laporan deadline besok'",
                lines=2
            )
        )

        # Enhanced Examples and Quick Actions
        with gr.Accordion("💡 Contoh & Quick Actions", open=False):
            
            # Smart suggestions powered by LLM context
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### 📝 **Contoh Natural Language:**")
                    examples_text = gr.Textbox(
                        label="Contoh Query AI-Powered",
                        value=ui_todo_examples(),
                        interactive=False,
                        lines=12
                    )
                
                with gr.Column():
                    gr.Markdown("#### 🎯 **Smart Suggestions:**")
                    suggestions_text = gr.Textbox(
                        label="AI Suggestions",
                        value=ui_get_smart_suggestions(),
                        interactive=False,
                        lines=12
                    )

        # Login event handlers untuk To-Do
        def handle_todo_tab_select():
            """Dipanggil ketika tab To Do dibuka"""
            return ui_check_login_status()

        # Set initial values saat tab dibuka
        ui.load(
            fn=handle_todo_tab_select,
            inputs=None,
            outputs=[login_status]
        )

        login_btn.click(
            fn=ui_login_to_microsoft,
            inputs=None,
            outputs=[login_status]
        )

        refresh_btn.click(
            fn=ui_check_login_status,
            inputs=None,
            outputs=[login_status]
        )

# Mount Gradio di /ui
if mount_gradio_app is not None:
    mount_gradio_app(app, ui, path="/ui")
else:
    app = gr.mount_gradio_app(app, ui, path="/ui")  # type: ignore

# Dev run (python internal_assistant_app.py)
if __name__ == "__main__":
    import nest_asyncio
    import uvicorn
    nest_asyncio.apply()
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)