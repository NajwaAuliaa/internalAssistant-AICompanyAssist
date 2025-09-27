import requests
import json

def debug_ideation_via_api():
    """
    Debug project ideation via API endpoints
    """
    base_url = "http://localhost:8001"
    
    print("=" * 60)
    print("🔍 DEBUG: Testing ideation project via API")
    print("=" * 60)
    
    try:
        # Test 1: Check auth status
        print("\n1. Checking auth status:")
        auth_response = requests.get(f"{base_url}/auth/status")
        auth_data = auth_response.json()
        print(f"Auth status: {auth_data}")
        
        if not auth_data.get("authenticated", False):
            print("❌ User not authenticated. Please login first.")
            return
        
        # Test 2: Debug ideation endpoint
        print("\n2. Testing debug ideation endpoint:")
        debug_response = requests.get(f"{base_url}/debug/ideation")
        debug_data = debug_response.json()
        
        print(f"Debug response status: {debug_response.status_code}")
        print(f"Authenticated: {debug_data.get('authenticated')}")
        
        for step in debug_data.get('steps', []):
            print(f"Step {step['step']}: {step['action']} - {step['result']}")
            if 'error' in step:
                print(f"  Error: {step['error']}")
        
        if 'error' in debug_data:
            print(f"❌ Final error: {debug_data['error']}")
        
        if 'final_result' in debug_data:
            final = debug_data['final_result']
            if 'error' in final:
                print(f"❌ Analysis error: {final['error']}")
            else:
                print(f"✅ Analysis success: {final['analysis']['total_tasks']} tasks")
        
        # Test 3: Project chat with ideation
        print("\n3. Testing project chat with ideation:")
        chat_response = requests.post(f"{base_url}/project-chat", 
                                    json={"message": "progress project ideation"})
        chat_data = chat_response.json()
        
        print(f"Chat response status: {chat_response.status_code}")
        answer = chat_data.get('answer', '')
        print(f"Answer length: {len(answer)} chars")
        print(f"First 300 chars: {answer[:300]}...")
        
        # Test 4: Get all projects
        print("\n4. Testing get all projects:")
        projects_response = requests.get(f"{base_url}/projects")
        projects_data = projects_response.json()
        
        print(f"Projects response status: {projects_response.status_code}")
        if 'error' in projects_data:
            print(f"❌ Projects error: {projects_data['error']}")
        else:
            projects_text = projects_data.get('projects', '')
            print(f"Projects text length: {len(projects_text)} chars")
            print(f"First 200 chars: {projects_text[:200]}...")
        
    except Exception as e:
        print(f"❌ Exception in API debug: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🔍 DEBUG: Completed API testing")
    print("=" * 60)

if __name__ == "__main__":
    debug_ideation_via_api()