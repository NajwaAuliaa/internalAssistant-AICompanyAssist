from depedencies import *
from internal_assistant_core import settings, llm
import msal
import requests
from datetime import datetime, timedelta,timezone
from typing import Dict, List, Optional, Any
import json
from pydantic import BaseModel, Field

from unified_auth import (
    unified_token_manager as token_manager,
    build_unified_auth_url as build_auth_url,
    is_unified_authenticated as is_user_authenticated,
    get_unified_token as get_unified_token,
    get_unified_login_status as get_unified_login_status,
    exchange_unified_code_for_token
)

# Auth functions now handled by unified_auth.py

def get_user_token(user_id: str = "current_user") -> str:
    """Get access token for current user (delegated)"""
    from unified_auth import get_unified_token 
    return get_unified_token(user_id)

def refresh_user_token(user_id: str = "current_user") -> str:
    """Refresh user token if available"""
    token_data = token_manager.get_token(user_id)
    if not token_data or "refresh_token" not in token_data:
        raise Exception("No refresh token available. Please re-authenticate.")
    
    try:
        token_endpoint = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token"
        
        refresh_data = {
            'client_id': settings.MS_CLIENT_ID,
            'grant_type': 'refresh_token',
            'refresh_token': token_data["refresh_token"],
            'scope': ' '.join([
                "https://graph.microsoft.com/User.Read",
                "https://graph.microsoft.com/Tasks.Read",
                "https://graph.microsoft.com/Group.Read.All"
            ])
            # Note: No client_secret for SPA
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'http://localhost:8001'  # Add origin for SPA
        }
        response = requests.post(token_endpoint, data=refresh_data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            token_manager.set_token(user_id, result)
            return result["access_token"]
        else:
            error_response = response.json() if response.content else {}
            raise Exception(f"Failed to refresh token: {error_response}")
            
    except Exception as e:
        raise Exception(f"Token refresh failed: {str(e)}. Please re-authenticate.")

def is_user_authenticated(user_id: str = "current_user") -> bool:
    """Check if user is authenticated"""
    from unified_auth import is_unified_authenticated  
    return is_unified_authenticated(user_id)

def make_authenticated_request(url: str, user_id: str = "current_user", method: str = "GET", data: dict = None):
    """Helper function to make authenticated requests with error handling for SPA"""
    if not is_user_authenticated(user_id):  
        raise Exception("User not authenticated. Please login first.")
    
    token = get_user_token(user_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "http://localhost:8001"  # Add origin for SPA requests
    }
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            response = requests.request(method, url, headers=headers, json=data)
        
        # Handle 401 (unauthorized) - try to refresh token
        if response.status_code == 401:
            try:
                # Try to refresh token if available
                token = refresh_user_token(user_id)
                headers["Authorization"] = f"Bearer {token}"
                
                # Retry the request
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, json=data)
                else:
                    response = requests.request(method, url, headers=headers, json=data)
                    
            except Exception as refresh_error:
                raise Exception(f"Authentication expired and refresh failed: {str(refresh_error)}. Please re-login.")
        
        # Check for other HTTP errors
        if response.status_code == 403:
            raise Exception("Access denied. Please check if your account has the required permissions for Microsoft Planner.")
        elif response.status_code == 404:
            raise Exception("Resource not found. The requested item may not exist or you may not have access to it.")
        elif response.status_code >= 400:
            error_detail = "Unknown error"
            try:
                error_json = response.json()
                error_detail = error_json.get('error', {}).get('message', str(error_json))
            except:
                error_detail = response.text
            raise Exception(f"HTTP {response.status_code}: {error_detail}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {str(e)}")

# === Get user's groups (delegated) ===
def get_user_groups(user_id: str = "current_user"):
    """Get groups that user is member of"""
    url = "https://graph.microsoft.com/v1.0/me/memberOf"
    response_data = make_authenticated_request(url, user_id)
    
    groups = response_data.get("value", [])
    # Filter only groups (not other directory objects)
    return [g for g in groups if g.get("@odata.type") == "#microsoft.graph.group"]

# === Ambil daftar plan dari sebuah group (delegated) ===
def get_plans(group_id: str = None, user_id: str = "current_user"):
    """Get plans from a group using delegated permissions"""
    if not group_id:
        group_id = settings.MS_GROUP_ID
    
    # If no group_id specified, get from user's groups
    if not group_id:
        groups = get_user_groups(user_id)
        if not groups:
            raise Exception("No groups found for user. Please make sure you are a member of at least one group with Planner plans.")
        group_id = groups[0]["id"]  # Use first group as default
        print(f"Using default group: {groups[0].get('displayName', 'Unknown')} ({group_id})")
    
    url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/planner/plans"
    response_data = make_authenticated_request(url, user_id)
    
    return response_data.get("value", [])

# === Ambil semua task dari sebuah plan (delegated) ===
def get_plan_tasks(plan_id: str, user_id: str = "current_user"):
    """Get tasks from a plan using delegated permissions"""
    url = f"https://graph.microsoft.com/v1.0/planner/plans/{plan_id}/tasks"
    response_data = make_authenticated_request(url, user_id)
    
    return response_data.get("value", [])

# === Ambil detail bucket untuk organizasi task (delegated) ===
def get_plan_buckets(plan_id: str, user_id: str = "current_user"):
    """Get buckets from a plan using delegated permissions"""
    url = f"https://graph.microsoft.com/v1.0/planner/plans/{plan_id}/buckets"
    response_data = make_authenticated_request(url, user_id)
    
    return response_data.get("value", [])

# === Authentication status functions ===
def get_login_status(user_id: str = "current_user") -> str:
    """Get current login status"""
    return get_unified_login_status(user_id)

# === Rest of the functions remain the same (analyze_project_data, etc.) ===
def analyze_project_data(project_name: str, user_id: str = "current_user") -> Dict[str, Any]:
    """
    Mengumpulkan dan menganalisis semua data project dari Microsoft Planner (delegated)
    """
    if not is_user_authenticated(user_id):
        return {"error": "User not authenticated. Please login first.", "auth_required": True}
    
    try:
        plans = get_plans(user_id=user_id)
        selected_plan = None
        
        # Cari plan yang sesuai (fuzzy search)
        for p in plans:
            if project_name.lower() in p.get("title", "").lower():
                selected_plan = p
                break
        
        if not selected_plan:
            # Coba cari dengan similarity yang lebih loose
            for p in plans:
                plan_title = p.get("title", "").lower()
                if any(word in plan_title for word in project_name.lower().split()):
                    selected_plan = p
                    break
        
        if not selected_plan:
            available_plans_list = [p.get("title") for p in plans]
            return {
                "error": f"Tidak ditemukan plan dengan nama '{project_name}'", 
                "available_plans": available_plans_list,
                "suggestion": f"Available projects: {', '.join(available_plans_list[:5])}" + ("..." if len(available_plans_list) > 5 else "")
            }

        plan_id = selected_plan["id"]
        tasks = get_plan_tasks(plan_id, user_id)
        buckets = get_plan_buckets(plan_id, user_id)

        if not tasks:
            return {
                "error": f"Plan '{selected_plan.get('title')}' tidak memiliki task", 
                "plan_info": selected_plan,
                "suggestion": "This project exists but has no tasks yet."
            }

        # Analisis tasks
        task_analysis = {
            "total_tasks": len(tasks),
            "completed_tasks": 0,
            "in_progress_tasks": 0,
            "not_started_tasks": 0,
            "overdue_tasks": 0,
            "upcoming_due_tasks": 0,
            "tasks_by_bucket": {},
            "tasks_by_priority": {"urgent": 0, "important": 0, "medium": 0, "low": 0},
            "recent_activity": [],
            "completion_percentage": 0
        }

        # Buat mapping bucket
        bucket_map = {bucket["id"]: bucket["name"] for bucket in buckets}
        
        current_date = datetime.now(timezone.utc)
        
        for task in tasks:
            # Status completion
            percent = task.get("percentComplete", 0)
            if percent == 100:
                task_analysis["completed_tasks"] += 1
            elif percent > 0:
                task_analysis["in_progress_tasks"] += 1
            else:
                task_analysis["not_started_tasks"] += 1
            
            # Analisis due date
            due_date_str = task.get("dueDateTime")
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    if due_date < current_date and percent < 100:
                        task_analysis["overdue_tasks"] += 1
                    elif due_date <= current_date + timedelta(days=3) and percent < 100:
                        task_analysis["upcoming_due_tasks"] += 1
                except ValueError:
                    # Handle different date formats
                    pass
            
            # Group by bucket
            bucket_id = task.get("bucketId")
            bucket_name = bucket_map.get(bucket_id, "No Bucket")
            if bucket_name not in task_analysis["tasks_by_bucket"]:
                task_analysis["tasks_by_bucket"][bucket_name] = {"total": 0, "completed": 0, "progress": 0}
            
            task_analysis["tasks_by_bucket"][bucket_name]["total"] += 1
            if percent == 100:
                task_analysis["tasks_by_bucket"][bucket_name]["completed"] += 1
            task_analysis["tasks_by_bucket"][bucket_name]["progress"] += percent
            
            # Priority analysis
            priority = task.get("priority", 5)  # Default medium
            if priority <= 1:
                task_analysis["tasks_by_priority"]["urgent"] += 1
            elif priority <= 3:
                task_analysis["tasks_by_priority"]["important"] += 1
            elif priority <= 7:
                task_analysis["tasks_by_priority"]["medium"] += 1
            else:
                task_analysis["tasks_by_priority"]["low"] += 1

        # Hitung completion percentage
        if task_analysis["total_tasks"] > 0:
            task_analysis["completion_percentage"] = (task_analysis["completed_tasks"] / task_analysis["total_tasks"]) * 100
            
            # Update bucket progress
            for bucket in task_analysis["tasks_by_bucket"]:
                bucket_data = task_analysis["tasks_by_bucket"][bucket]
                if bucket_data["total"] > 0:
                    bucket_data["progress"] = bucket_data["progress"] / bucket_data["total"]

        return {
            "plan_info": selected_plan,
            "analysis": task_analysis,
            "raw_tasks": tasks,
            "buckets": buckets,
            "timestamp": current_date.isoformat()
        }
    
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "login" in error_msg.lower():
            return {"error": f"Authentication issue: {error_msg}", "auth_required": True}
        return {"error": f"Error analyzing project: {error_msg}"}

# === Generate intelligent response menggunakan LLM ===
# === Generate intelligent response menggunakan LLM ===
def generate_project_response(user_query: str, project_data: Dict[str, Any]) -> str:
    """
    Menggunakan LLM untuk menghasilkan jawaban yang sesuai dengan pertanyaan user
    berdasarkan data project yang sudah dianalisis
    """
    if "error" in project_data:
        if project_data.get("auth_required"):
            return "🔒 Anda belum login ke Microsoft atau sesi telah expired. Silakan login terlebih dahulu untuk mengakses data project."
        
        error_msg = project_data["error"]
        if "available_plans" in project_data:
            suggestion = project_data.get("suggestion", "")
            return f"❌ {error_msg}\n\n💡 {suggestion}"
        
        return f"❌ {error_msg}"
    
    # Siapkan konteks untuk LLM
    context = f"""
Data Project Analysis:
======================
Project Name: {project_data['plan_info']['title']}
Created: {project_data['plan_info'].get('createdDateTime', 'N/A')}
Total Tasks: {project_data['analysis']['total_tasks']}
Completed: {project_data['analysis']['completed_tasks']}
In Progress: {project_data['analysis']['in_progress_tasks']}
Not Started: {project_data['analysis']['not_started_tasks']}
Overall Progress: {project_data['analysis']['completion_percentage']:.1f}%

Overdue Tasks: {project_data['analysis']['overdue_tasks']}
Upcoming Due (3 days): {project_data['analysis']['upcoming_due_tasks']}

Tasks by Bucket:
"""
    
    for bucket_name, bucket_data in project_data['analysis']['tasks_by_bucket'].items():
        context += f"- {bucket_name}: {bucket_data['completed']}/{bucket_data['total']} completed ({bucket_data['progress']:.1f}% avg progress)\n"
    
    context += f"""
Priority Distribution:
- Urgent: {project_data['analysis']['tasks_by_priority']['urgent']}
- Important: {project_data['analysis']['tasks_by_priority']['important']}
- Medium: {project_data['analysis']['tasks_by_priority']['medium']}
- Low: {project_data['analysis']['tasks_by_priority']['low']}

Recent Tasks Details:
"""
    
    # Tambahkan detail task yang relevan
    for task in project_data['raw_tasks'][:10]:  # Limit to 10 most relevant
        due_info = ""
        if task.get('dueDateTime'):
            try:
                due_date = task.get('dueDateTime')[:10]  # Get date part only
                due_info = f" (Due: {due_date})"
            except:
                due_info = f" (Due: {task.get('dueDateTime')})"
        context += f"- {task.get('title')}: {task.get('percentComplete', 0)}%{due_info}\n"

    # PROMPT BARU DENGAN FORMAT TABLE
    prompt = f"""
Anda adalah assistant yang ahli dalam project management. User bertanya: "{user_query}"

Berdasarkan data project di atas, berikan jawaban yang:
1. Menjawab pertanyaan user secara spesifik
2. Memberikan insight yang berguna
3. Highlight masalah atau perhatian khusus (overdue, bottleneck, dll)
4. Berikan saran actionable jika diperlukan
5. WAJIB gunakan format tabel Markdown untuk menampilkan daftar tasks
6. Berikan breakdown detail per task jika user menanyakan progress

Data Project:
{context}

IMPORTANT: Jawab dalam bahasa Indonesia dengan tone profesional namun friendly. 
WAJIB gunakan format berikut:

## 📊 Progress Project: [Nama Project]

**Overall Progress: [X]%**

## 📋 Daftar Tasks & Status

| No | Task Name | Status | Progress | Due Date |
|----|-----------|---------|----------|----------|
| 1  | [Task 1]  | [Status] | [X]%     | [Date]   |
| 2  | [Task 2]  | [Status] | [X]%     | [Date]   |

## 📈 Summary & Insights
[Berikan analisis dan recommendations]

Pastikan tabel menggunakan format Markdown yang valid dan mudah dibaca.
"""

    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        # Fallback ke format tabel juga
        print(f"LLM failed, using table fallback: {str(e)}")
        return _generate_fallback_table_response(project_data)

def _generate_fallback_table_response(project_data: Dict[str, Any]) -> str:
    """Fallback response dengan format tabel jika LLM tidak tersedia"""
    analysis = project_data['analysis']
    plan_info = project_data['plan_info']
    raw_tasks = project_data.get('raw_tasks', [])
    
    response = f"""## 📊 Progress Project: {plan_info['title']}

**Overall Progress: {analysis['completion_percentage']:.1f}%**

### 📈 Status Overview:
- ✅ Completed: {analysis['completed_tasks']}
- 🔄 In Progress: {analysis['in_progress_tasks']}  
- ⏳ Not Started: {analysis['not_started_tasks']}
- 📋 Total: {analysis['total_tasks']}

"""
    
    if analysis['overdue_tasks'] > 0:
        response += f"⚠️ **Perhatian:** {analysis['overdue_tasks']} task overdue\n\n"
    
    if analysis['upcoming_due_tasks'] > 0:
        response += f"⏰ **Upcoming:** {analysis['upcoming_due_tasks']} task deadline dalam 3 hari ke depan\n\n"
    
    # Add table format
    if raw_tasks:
        response += """## 📋 Daftar Tasks & Status

| No | Task Name | Status | Progress | Due Date |
|----|-----------|---------|----------|----------|
"""
        
        for i, task in enumerate(raw_tasks[:15], 1):  # Show first 15 tasks
            title = task.get('title', 'Untitled')[:40] + ("..." if len(task.get('title', '')) > 40 else "")
            percent = task.get('percentComplete', 0)
            
            # Determine status
            if percent == 100:
                status = "✅ Selesai"
            elif percent > 0:
                status = "🔄 Sedang Berjalan"
            else:
                status = "⏳ Belum Dimulai"
            
            # Format due date
            due_date = "-"
            if task.get('dueDateTime'):
                try:
                    due_date = task.get('dueDateTime')[:10]
                    # Check if overdue
                    from datetime import datetime
                    if datetime.now() > datetime.fromisoformat(due_date):
                        due_date = f"🔴 {due_date}"
                except:
                    due_date = str(task.get('dueDateTime', '-'))[:10]
            
            response += f"| {i} | {title} | {status} | {percent}% | {due_date} |\n"
        
        if len(raw_tasks) > 15:
            response += f"\n*... dan {len(raw_tasks) - 15} task lainnya*\n"
    
    response += "\n## 💡 Recommendations\n"
    response += "- Fokus pada task yang overdue untuk mengejar deadline\n"
    response += "- Review task yang tidak ada progress untuk identify bottlenecks\n"
    response += "- Prioritaskan task dengan due date terdekat\n"
    
    return response
# === Enhanced project progress function ===
def get_project_progress(project_name: str, user_id: str = "current_user") -> str:
    """
    Fungsi utama untuk mendapatkan progress project dengan analisis mendalam
    """
    try:
        # Analisis data project
        project_data = analyze_project_data(project_name, user_id)
        
        # Generate response menggunakan LLM
        response = generate_project_response(f"analisis progress project {project_name}", project_data)
        
        return response
        
    except Exception as e:
        return f"❌ Error mengambil data project: {str(e)}"

# === List all projects dengan authentication check ===
def list_all_projects(user_id: str = "current_user") -> str:
    """
    Menampilkan semua available projects (delegated)
    """
    if not is_user_authenticated(user_id):
        return "🔒 Anda belum login ke Microsoft. Silakan login terlebih dahulu untuk mengakses data project."
    
    try:
        plans = get_plans(user_id=user_id)
        if not plans:
            return "Tidak ada project yang ditemukan. Pastikan Anda adalah anggota dari grup yang memiliki Microsoft Planner plans."
        
        context = f"Available Projects ({len(plans)} total):\n"
        for i, plan in enumerate(plans, 1):
            created_date = ""
            if plan.get('createdDateTime'):
                try:
                    created_date = f" (Created: {plan['createdDateTime'][:10]})"
                except:
                    pass
            context += f"{i}. {plan.get('title', 'Untitled')}{created_date}\n"
        
        prompt = f"""
Berdasarkan daftar project berikut, berikan summary yang informatif:

{context}

Berikan response yang include:
1. Total jumlah project
2. Format yang rapi dan mudah dibaca
3. Ajakan untuk user menanyakan detail project tertentu

Response dalam bahasa Indonesia, format friendly dengan emoji yang sesuai.
"""
        
        try:
            response = llm.invoke(prompt)
            return response.content
        except:
            return context + "\nTanyakan detail project tertentu untuk melihat progress lengkap."
            
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "login" in error_msg.lower():
            return "🔒 Authentication error. Silakan login kembali melalui tombol 'Login untuk Project Management'."
        return f"❌ Error listing projects: {error_msg}"

# === Helper functions untuk UI integration ===
def set_user_token(token_data: dict, user_id: str = "current_user"):
    """Set user token untuk authentication (dipanggil dari app.py setelah login)"""
    token_manager.set_token(user_id, token_data)

def clear_user_token(user_id: str = "current_user"):
    """Clear user token (untuk logout)"""
    token_manager.clear_token(user_id)

# === Create aliases for backward compatibility with existing code ===
project_build_auth_url = build_auth_url
project_exchange_code_for_token = exchange_unified_code_for_token
project_get_login_status = get_login_status

# (Continue with remaining functions - intelligent_project_query, compare_projects, etc.)
# These remain largely the same, just ensure they use the corrected authentication functions

def intelligent_project_query(user_query: str, user_id: str = "current_user") -> str:
    """
    Advanced query processing yang menggunakan LLM untuk understanding user intent
    """
    if not is_user_authenticated(user_id):
        return "🔒 Anda belum login ke Microsoft. Silakan login terlebih dahulu untuk mengakses data project. Gunakan tombol 'Login untuk Project Management' di aplikasi."
    
    try:
        # Ambil list semua projects untuk context
        plans = get_plans(user_id=user_id)
        available_projects = [p.get('title', '') for p in plans]
        
        # Enhanced LLM prompt untuk understanding intent dan extract project info
        intent_prompt = f"""
User Query: "{user_query}"

Available Projects: {', '.join(available_projects)}

Analyze the user query and determine:
1. Intent (list_all, single_project, compare_projects, general_analysis, or specific_task)
2. Which project(s) they are asking about (exact name from available projects)
3. What specific information they want (progress, status, issues, specific task name, etc.)
4. If asking about specific task, extract the task name/keyword

Respond in JSON format:
{{
    "intent": "list_all|single_project|compare_projects|general_analysis|specific_task",
    "projects": ["exact project names from available list"],
    "specific_request": "brief description of what they want to know",
    "task_name": "specific task name if asking about a task, null otherwise"
}}

Examples:
- "progress project X" -> intent: "single_project"
- "jelaskan task dave di project Y" -> intent: "specific_task", task_name: "dave"
- "bagaimana status task ABC" -> intent: "specific_task", task_name: "ABC"
- "list semua project" -> intent: "list_all"

Only return the JSON, no additional text.
"""
        
        try:
            llm_response = llm.invoke(intent_prompt)
            intent_data = json.loads(llm_response.content.strip())
            
            intent = intent_data.get("intent", "single_project")
            projects = intent_data.get("projects", [])
            specific_request = intent_data.get("specific_request", "")
            task_name = intent_data.get("task_name", "")
            
            # Route based on intent
            if intent == "list_all":
                return list_all_projects(user_id)
            elif intent == "compare_projects" and len(projects) >= 2:
                return compare_projects(projects[:3], user_id)
            elif intent == "general_analysis":
                return analyze_all_projects_overview(user_id)
            elif intent == "specific_task" and task_name and projects:
                # Handle specific task query - INI YANG PENTING!
                return get_task_specific_analysis(projects[0], task_name, specific_request, user_id)
            else:
                # Single project - use first matched project or try fuzzy search
                if projects:
                    return get_enhanced_project_progress(projects[0], specific_request, user_id)
                else:
                    return find_projects_by_query(user_query, user_id)
                    
        except (json.JSONDecodeError, Exception) as e:
            # Fallback ke method lama jika LLM parsing gagal
            print(f"LLM parsing failed: {str(e)}, falling back to simple processing")
            return process_project_query_with_task_detection(user_query, user_id)  # Ganti dari process_project_query
            
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "login" in error_msg.lower():
            return "🔒 Authentication error. Silakan login kembali melalui tombol 'Login untuk Project Management'."
        return f"❌ Error processing query: {error_msg}"
    
def compare_projects(project_names: List[str], user_id: str = "current_user") -> str:
    """
    Membandingkan multiple projects (delegated auth version)
    """
    if not is_user_authenticated(user_id):
        return "🔒 Anda belum login ke Microsoft. Silakan login terlebih dahulu."
    
    try:
        comparisons = []
        for project_name in project_names:
            data = analyze_project_data(project_name, user_id)
            if "error" not in data:
                comparisons.append(data)
        
        if not comparisons:
            return "Tidak ada project yang valid untuk dibandingkan."
        
        # Generate comparison using LLM
        comparison_context = ""
        for data in comparisons:
            comparison_context += f"""
Project: {data['plan_info']['title']}
Progress: {data['analysis']['completion_percentage']:.1f}%
Total Tasks: {data['analysis']['total_tasks']}
Completed: {data['analysis']['completed_tasks']}
Overdue: {data['analysis']['overdue_tasks']}
---
"""
        
        prompt = f"""
Berdasarkan data berikut, buatkan perbandingan project yang informatif:

{comparison_context}

User ingin membandingkan project-project ini. Berikan:
1. Ranking berdasarkan progress
2. Insight tentang mana yang perlu perhatian lebih
3. Analisis comparative yang membantu decision making

Response dalam bahasa Indonesia, format yang clear dan actionable.
"""
        
        try:
            response = llm.invoke(prompt)
            return response.content
        except:
            return comparison_context + "\nPerbandingan basic tersedia di atas."
            
    except Exception as e:
        return f"❌ Error comparing projects: {str(e)}"

def find_projects_by_query(user_query: str, user_id: str = "current_user") -> str:
    """
    Mencari project berdasarkan query user yang lebih fleksibel (delegated version)
    """
    if not is_user_authenticated(user_id):
        return "🔒 Anda belum login ke Microsoft. Silakan login terlebih dahulu."
    
    try:
        plans = get_plans(user_id=user_id)
        
        # Analisis query dengan LLM untuk mencari project yang relevan
        plans_list = "\n".join([f"- {p.get('title', '')}" for p in plans])
        
        prompt = f"""
User query: "{user_query}"

Available projects:
{plans_list}

Tentukan project mana yang paling relevan dengan query user. Jika tidak ada yang cocok, return "NONE".
Jika ada yang cocok, return nama project yang PERSIS seperti di list.
Hanya return nama project, tidak ada text tambahan.
"""
        
        try:
            response = llm.invoke(prompt)
            matched_project = response.content.strip()
            
            if matched_project == "NONE" or matched_project not in [p.get('title', '') for p in plans]:
                available_list = [p.get('title', '') for p in plans]
                return f"Tidak ditemukan project yang sesuai dengan '{user_query}'. Available projects: {', '.join(available_list)}"
            
            return get_project_progress(matched_project, user_id)
            
        except Exception as llm_error:
            print(f"LLM matching failed: {str(llm_error)}")
            # Fallback ke simple matching
            for p in plans:
                if any(word.lower() in p.get("title", "").lower() for word in user_query.split()):
                    return get_project_progress(p.get("title", ""), user_id)
            
            return f"Tidak ditemukan project yang sesuai dengan '{user_query}'"
            
    except Exception as e:
        return f"❌ Error searching projects: {str(e)}"

# Tambahkan fungsi-fungsi ini ke projectProgress_modul.py di Project A

def get_task_specific_analysis(project_name: str, task_name: str, specific_request: str = "", user_id: str = "current_user") -> str:
    """
    Analisis spesifik untuk satu task dalam project
    """
    if not is_user_authenticated(user_id):
        return "🔒 Anda belum login ke Microsoft. Silakan login terlebih dahulu."
    
    try:
        project_data = analyze_project_data(project_name, user_id)
        
        if "error" in project_data:
            if project_data.get("auth_required"):
                return "🔒 Authentication error. Silakan login kembali melalui tombol 'Login untuk Project Management'."
            return project_data["error"]
        
        # Cari task yang sesuai
        raw_tasks = project_data.get('raw_tasks', [])
        matched_task = None
        
        for task in raw_tasks:
            task_title = task.get('title', '').lower()
            if task_name.lower() in task_title or any(word.lower() in task_title for word in task_name.split()):
                matched_task = task
                break
        
        if not matched_task:
            available_tasks = [t.get('title', 'Untitled') for t in raw_tasks]
            return f"❌ Task '{task_name}' tidak ditemukan dalam project '{project_name}'.\n\nTask yang tersedia: {', '.join(available_tasks)}"
        
        # Generate task-specific analysis
        return generate_task_specific_response(project_name, matched_task, project_data, specific_request)
        
    except Exception as e:
        return f"❌ Error analyzing task {task_name} in project {project_name}: {str(e)}"

def generate_task_specific_response(project_name: str, task: dict, project_data: dict, specific_request: str = "") -> str:
    """
    Generate detailed response for specific task
    """
    task_title = task.get('title', 'Untitled')
    task_percent = task.get('percentComplete', 0)
    due_date = task.get('dueDateTime', '')
    priority = task.get('priority', 5)
    bucket_id = task.get('bucketId', '')
    
    # Get bucket name
    bucket_name = "No Bucket"
    for bucket in project_data.get('buckets', []):
        if bucket['id'] == bucket_id:
            bucket_name = bucket['name']
            break
    
    # Format due date
    due_info = ""
    status_icon = ""
    if due_date:
        try:
            due_date_formatted = due_date[:10]  # Get date part
            due_info = f"Due date: {due_date_formatted}"
            # Check if overdue
            from datetime import datetime, timezone
            current_date = datetime.now(timezone.utc)
            task_due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            if task_due < current_date and task_percent < 100:
                due_info += " ⏰ (Overdue)"
                status_icon = "⚠️"
        except:
            due_info = f"Due date: {due_date}"
    
    # Determine status
    if task_percent == 100:
        status = "Selesai"
        status_icon = "✅"
    elif task_percent > 0:
        status = "Sedang berjalan"
        status_icon = "🔄"
    else:
        status = "Belum dimulai"
        status_icon = "⏳"
    
    # Priority mapping
    priority_map = {1: "Urgent", 2: "Urgent", 3: "Important", 4: "Important", 
                   5: "Medium", 6: "Medium", 7: "Medium", 8: "Low", 9: "Low", 10: "Low"}
    priority_text = priority_map.get(priority, "Medium")
    
    # Generate analysis context for LLM
    analysis = project_data['analysis']
    context = f"""
Project: {project_name}
Task Analysis for: {task_title}

Task Details:
=============
Status: {status} ({task_percent}%)
Priority: {priority_text}
Bucket: {bucket_name}
{due_info}

Project Context:
================
Total Tasks in Project: {analysis['total_tasks']}
Completed Tasks: {analysis['completed_tasks']}
Overall Project Progress: {analysis['completion_percentage']:.1f}%
Tasks Overdue: {analysis['overdue_tasks']}

Task Performance Context:
This task is part of a project with {analysis['completion_percentage']:.1f}% overall completion.
"""

    prompt = f"""
User bertanya tentang task spesifik: "{task_title}" dalam project "{project_name}".

Berdasarkan data berikut, berikan analisis yang fokus pada task ini:

{context}

Berikan response yang mencakup:
1. Penjelasan spesifik tentang tugas {task_title}
2. Status dan progress detail
3. Insight berguna tentang posisi task ini dalam project
4. Highlight masalah atau perhatian khusus
5. Saran actionable
6. Format ringkas & mudah dibaca

Berikan analisis yang fokus pada task ini, bukan overview project secara keseluruhan.
Gunakan format yang professional dan mudah dipahami.
"""

    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        # Fallback response
        return f"""
{status_icon} **Analisis Task: {task_title}**

**Status:** {status} ({task_percent}%)
**Priority:** {priority_text}
**Bucket:** {bucket_name}
{due_info if due_info else "No due date set"}

**Context dalam Project:**
- Task ini adalah bagian dari project "{project_name}"
- Project memiliki {analysis['total_tasks']} total tasks
- Progress keseluruhan project: {analysis['completion_percentage']:.1f}%

**Insight:**
{'✅ Task ini sudah selesai dengan baik.' if task_percent == 100 else '🔄 Task ini sedang dalam progress.' if task_percent > 0 else '⏳ Task ini belum dimulai.'}

**Recommendations:**
{'Manfaatkan hasil dari task ini untuk mendukung task lain yang masih berjalan.' if task_percent == 100 else 'Fokuskan resource untuk menyelesaikan task ini sesuai timeline.' if task_percent > 0 else 'Segera mulai task ini agar tidak menghambat progress project.'}
"""

def process_project_query_with_task_detection(user_query: str, user_id: str = "current_user") -> str:
    """
    Enhanced fallback processing dengan task detection
    """
    if not is_user_authenticated(user_id):
        return "🔒 Anda belum login ke Microsoft. Silakan login terlebih dahulu untuk mengakses data project."
    
    query_lower = user_query.lower()
    
    # Deteksi task-specific keywords
    task_keywords = ["task", "tugas", "jelaskan task", "status task", "bagaimana task", "progress task"]
    
    if any(keyword in query_lower for keyword in task_keywords):
        # Try to extract project and task name
        plans = get_plans(user_id=user_id)
        for plan in plans:
            plan_name = plan.get("title", "").lower()
            if plan_name in query_lower:
                # Found project, now extract task name
                # Simple extraction: look for words after "task"
                words = user_query.split()
                task_name = ""
                for i, word in enumerate(words):
                    if "task" in word.lower() and i + 1 < len(words):
                        task_name = words[i + 1]
                        break
                
                if task_name:
                    return get_task_specific_analysis(plan.get("title", ""), task_name, "", user_id)
    
    # Fallback to original logic
    if any(word in query_lower for word in ["semua", "list", "daftar", "projects", "project apa"]):
        return list_all_projects(user_id)
    elif any(word in query_lower for word in ["bandingkan", "compare", "vs", "versus"]):
        plans = get_plans(user_id=user_id)
        mentioned_projects = []
        for plan in plans:
            if plan.get("title", "").lower() in query_lower:
                mentioned_projects.append(plan.get("title", ""))
        
        if len(mentioned_projects) >= 2:
            return compare_projects(mentioned_projects[:3], user_id)
        else:
            return "Untuk perbandingan, sebutkan minimal 2 nama project. Contoh: 'bandingkan project A dengan project B'"
    else:
        return find_projects_by_query(user_query, user_id)

def get_enhanced_project_progress(project_name: str, specific_request: str = "", user_id: str = "current_user") -> str:
    """
    Enhanced version yang include specific request context (delegated version)
    """
    if not is_user_authenticated(user_id):
        return "🔒 Anda belum login ke Microsoft. Silakan login terlebih dahulu."
    
    try:
        project_data = analyze_project_data(project_name, user_id)
        
        if "error" in project_data:
            if project_data.get("auth_required"):
                return "🔒 Authentication error. Silakan login kembali melalui tombol 'Login untuk Project Management'."
            return project_data["error"]
        
        # Enhanced prompt dengan specific request
        full_query = f"analisis project {project_name}"
        if specific_request:
            full_query += f" dengan fokus pada {specific_request}"
            
        response = generate_project_response(full_query, project_data)
        return response
        
    except Exception as e:
        return f"❌ Error analyzing project {project_name}: {str(e)}"

def analyze_all_projects_overview(user_id: str = "current_user") -> str:
    """
    Memberikan overview analysis untuk semua projects (delegated version)
    """
    if not is_user_authenticated(user_id):
        return "🔒 Anda belum login ke Microsoft. Silakan login terlebih dahulu."
    
    try:
        plans = get_plans(user_id=user_id)
        if not plans:
            return "Tidak ada project yang ditemukan."
        
        overview_data = []
        total_completion = 0
        total_projects = len(plans)
        projects_with_issues = []
        successful_analysis = 0
        
        for plan in plans:
            try:
                project_data = analyze_project_data(plan.get('title', ''), user_id)
                if "error" not in project_data:
                    analysis = project_data['analysis']
                    overview_data.append({
                        'name': plan.get('title', ''),
                        'progress': analysis['completion_percentage'],
                        'total_tasks': analysis['total_tasks'],
                        'overdue': analysis['overdue_tasks'],
                        'status': 'On Track' if analysis['overdue_tasks'] == 0 and analysis['completion_percentage'] > 70 else 'Needs Attention'
                    })
                    total_completion += analysis['completion_percentage']
                    successful_analysis += 1
                    
                    if analysis['overdue_tasks'] > 0 or analysis['completion_percentage'] < 50:
                        projects_with_issues.append(plan.get('title', ''))
            except Exception as project_error:
                print(f"Error analyzing project {plan.get('title', '')}: {str(project_error)}")
                continue
        
        if successful_analysis == 0:
            return "❌ Tidak bisa menganalisis project. Pastikan Anda memiliki akses ke Microsoft Planner."
        
        avg_completion = total_completion / successful_analysis if successful_analysis > 0 else 0
        
        # Generate overview menggunakan LLM
        overview_context = f"""
Portfolio Overview:
===================
Total Projects: {total_projects}
Successfully Analyzed: {successful_analysis}
Average Completion: {avg_completion:.1f}%
Projects with Issues: {len(projects_with_issues)}

Project Details:
"""
        
        for project in overview_data:
            overview_context += f"""
- {project['name']}: {project['progress']:.1f}% ({project['status']})
  Tasks: {project['total_tasks']}, Overdue: {project['overdue']}
"""
        
        if projects_with_issues:
            overview_context += f"\nProjects Needing Attention: {', '.join(projects_with_issues)}"
        
        prompt = f"""
Berdasarkan portfolio overview berikut, berikan executive summary yang mencakup:
1. Overall portfolio health
2. Key achievements dan concerns
3. Projects yang perlu immediate attention
4. Strategic recommendations untuk portfolio management
5. Next steps yang actionable

Data:
{overview_context}

Berikan response dalam format executive summary yang professional dan actionable.
Use emojis untuk highlight poin penting.
"""
        
        try:
            response = llm.invoke(prompt)
            return response.content
        except:
            return overview_context + "\n\nPortfolio overview tersedia di atas."
            
    except Exception as e:
        return f"❌ Error analyzing portfolio: {str(e)}"

def process_project_query(user_query: str, user_id: str = "current_user") -> str:
    """
    Process user query dengan intelligence untuk menentukan action yang tepat (delegated version)
    """
    if not is_user_authenticated(user_id):
        return "🔒 Anda belum login ke Microsoft. Silakan login terlebih dahulu untuk mengakses data project."
    
    query_lower = user_query.lower()
    
    # Deteksi intent menggunakan keyword matching + LLM backup
    if any(word in query_lower for word in ["semua", "list", "daftar", "projects", "project apa"]):
        return list_all_projects(user_id)
    
    elif any(word in query_lower for word in ["bandingkan", "compare", "vs", "versus"]):
        # Extract project names untuk comparison (simplified)
        plans = get_plans(user_id=user_id)
        mentioned_projects = []
        for plan in plans:
            if plan.get("title", "").lower() in query_lower:
                mentioned_projects.append(plan.get("title", ""))
        
        if len(mentioned_projects) >= 2:
            return compare_projects(mentioned_projects[:3], user_id)  # Max 3 projects
        else:
            return "Untuk perbandingan, sebutkan minimal 2 nama project. Contoh: 'bandingkan project A dengan project B'"
    
    else:
        # Single project query - Enhanced dengan LLM untuk extract project name
        return find_projects_by_query(user_query, user_id)

def get_available_groups(user_id: str = "current_user") -> List[Dict[str, Any]]:
    """Get list of groups yang bisa diakses user (untuk UI selection)"""
    if not is_user_authenticated(user_id):
        return []
    
    try:
        return get_user_groups(user_id)
    except:
        return []

# === LangChain Tools dengan Enhanced Intelligence dan Auth Check ===

# Definisikan skema input agar LLM lebih mudah menggunakan tool
class ProjectQueryInput(BaseModel):
    query: str = Field(description="The user's full natural language query about a project or projects, such as asking for progress, a list, or a comparison.")

class ProjectDetailInput(BaseModel):
    project_name: str = Field(description="The exact name of the project to get a detailed analysis for.")

class NoArgsInput(BaseModel):
    """An empty model for tools that don't require any arguments."""
    pass

# Update project_tool di bagian bawah file projectProgress_modul.py Project A:

project_tool = StructuredTool.from_function(
    name="project_progress",
    description="MAIN PROJECT TOOL: Gunakan untuk semua pertanyaan terkait project dari Microsoft Planner. Tool ini intelligent dan bisa handle: single project progress, comparison multiple projects, list all projects, portfolio analysis, SPECIFIC TASK ANALYSIS. REQUIRES USER LOGIN FIRST. Berikan full user query sebagai input untuk processing yang optimal. Contoh: 'jelaskan task dave yang ada pada project ideation planner'",
    func=lambda query: intelligent_project_query(query, "current_user"),
    args_schema=ProjectQueryInput,
)

project_detail_tool = StructuredTool.from_function(
    name="project_detail_analysis", 
    description="Analisis mendalam untuk satu project tertentu dengan insight, recommendations, dan detailed breakdown. REQUIRES USER LOGIN.",
    func=lambda project_name: get_enhanced_project_progress(project_name, "analisis mendalam dengan insight dan recommendations", "current_user"),
    args_schema=ProjectDetailInput,
)

project_list_tool = StructuredTool.from_function(
    name="list_projects",
    description="Menampilkan semua available projects dalam Microsoft Planner dengan summary status. REQUIRES USER LOGIN.",
    func=lambda: list_all_projects("current_user"),
    args_schema=NoArgsInput,
)

portfolio_analysis_tool = StructuredTool.from_function(
    name="portfolio_analysis",
    description="Executive overview dan analysis untuk seluruh portfolio projects dengan strategic insights. REQUIRES USER LOGIN.",
    func=lambda: analyze_all_projects_overview("current_user"),
    args_schema=NoArgsInput,
)