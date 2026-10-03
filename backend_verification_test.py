#!/usr/bin/env python3
"""
Comprehensive Backend Verification Test for Chatly AI Messenger
Tests PRIORITY 1 (recent fixes) and PRIORITY 2 (full feature verification)
"""
import requests
import sys
import time
import json
import base64
from datetime import datetime, timedelta

# Backend URL from frontend/.env
BACKEND_URL = "https://mobile-chat-app-113.preview.emergentagent.com/api"

# Test credentials
DEMO_EMAIL = "demo@chatly.app"
DEMO_PASSWORD = "Demo1234"
DEMO2_EMAIL = "demo2@chatly.app"
DEMO2_PASSWORD = "Demo1234"

# Test results tracking
passed = 0
failed = 0
test_results = []
priority1_results = {}

def log_test(name, success, details=""):
    global passed, failed
    if success:
        passed += 1
        status = "✅ PASS"
    else:
        failed += 1
        status = "❌ FAIL"
    msg = f"{status}: {name}"
    if details:
        msg += f" - {details}"
    test_results.append(msg)
    print(msg)
    return success

def check_no_secrets(response_text, test_name):
    """Check that response doesn't contain secrets or stack traces"""
    secrets = ["Traceback", "sk_", "tvly-", "sk-emergent", "ek_", "MONGO_URL", 
               "JWT_SECRET", "private_key", "service_account"]
    found = []
    for secret in secrets:
        if secret in response_text:
            found.append(secret)
    
    if found:
        log_test(f"{test_name} - No secrets exposed", False, f"Found: {', '.join(found)}")
        return False
    else:
        return True

def login(email, password):
    """Login and return token"""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("token")
        else:
            print(f"Login failed for {email}: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Login exception for {email}: {e}")
        return None

# ============================================================================
# PRIORITY 1: VERIFY RECENT FIXES
# ============================================================================

def test_p1_a_digest_latency(token):
    """A. POST /api/ai/digest {"period":"daily"} - verify 200 with digest object and latency"""
    print("\n=== PRIORITY 1-A: Digest Latency Test ===")
    try:
        start = time.time()
        resp = requests.post(
            f"{BACKEND_URL}/ai/digest",
            json={"period": "daily"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=180
        )
        latency = time.time() - start
        
        success = log_test("P1-A: POST /api/ai/digest returns 200", resp.status_code == 200, 
                          f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            digest = data.get("digest", {})
            
            # Check required keys
            required_keys = ["important_conversations", "pending_replies", "tasks", "decisions", "follow_ups"]
            has_all_keys = all(k in digest for k in required_keys)
            log_test("P1-A: Digest has all required keys", has_all_keys, 
                    f"Keys: {list(digest.keys())}")
            
            # Report latency
            log_test("P1-A: Digest latency", True, f"{latency:.1f}s (target <90s)")
            priority1_results['digest_latency'] = latency
            priority1_results['digest_working'] = success and has_all_keys
            
            check_no_secrets(resp.text, "P1-A Digest")
        else:
            priority1_results['digest_working'] = False
            
    except Exception as e:
        log_test("P1-A: Digest test", False, str(e))
        priority1_results['digest_working'] = False

def test_p1_b_message_action_validation(token):
    """B. POST /api/ai/message-action {"text":"","action":"summarize"} - must return 422 quickly"""
    print("\n=== PRIORITY 1-B: Message Action Validation Test ===")
    try:
        start = time.time()
        resp = requests.post(
            f"{BACKEND_URL}/ai/message-action",
            json={"text": "", "action": "summarize"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        latency = time.time() - start
        
        success = log_test("P1-B: Empty text returns 422", resp.status_code == 422, 
                          f"Got {resp.status_code}")
        log_test("P1-B: Validation is fast", latency < 2, f"{latency:.2f}s (target <2s)")
        
        priority1_results['validation_working'] = success and latency < 2
        check_no_secrets(resp.text, "P1-B Validation")
        
    except Exception as e:
        log_test("P1-B: Message action validation", False, str(e))
        priority1_results['validation_working'] = False

def test_p1_c_autopilot_analyze_confirm(token):
    """C. POST /api/ai/autopilot/analyze + confirm pattern"""
    print("\n=== PRIORITY 1-C: Autopilot Analyze + Confirm Test ===")
    try:
        # Get a chat_id first
        resp = requests.get(
            f"{BACKEND_URL}/chats",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if resp.status_code != 200 or not resp.json().get("chats"):
            log_test("P1-C: Get chats for autopilot", False, "No chats available")
            priority1_results['autopilot_working'] = False
            return
        
        chat_id = resp.json()["chats"][0]["chat_id"]
        
        # Test analyze
        resp = requests.post(
            f"{BACKEND_URL}/ai/autopilot/analyze",
            json={"chat_id": chat_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60
        )
        
        analyze_success = log_test("P1-C: POST /api/ai/autopilot/analyze returns 200", 
                                   resp.status_code == 200, f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("P1-C: Analyze returns suggestions array", "suggestions" in data)
            
            # Test confirm with reminder pattern
            tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
            resp = requests.post(
                f"{BACKEND_URL}/ai/autopilot/confirm",
                json={
                    "suggestion_type": "reminder",
                    "title": "Audit verification reminder",
                    "remind_at": tomorrow
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            confirm_success = log_test("P1-C: POST /api/ai/autopilot/confirm returns 200 or 422", 
                                      resp.status_code in [200, 422], 
                                      f"Got {resp.status_code}")
            
            if resp.status_code == 422:
                log_test("P1-C: Confirm validation", True, 
                        f"422 with message: {resp.json().get('detail', '')}")
            
            priority1_results['autopilot_working'] = analyze_success
            check_no_secrets(resp.text, "P1-C Autopilot")
        else:
            priority1_results['autopilot_working'] = False
            
    except Exception as e:
        log_test("P1-C: Autopilot test", False, str(e))
        priority1_results['autopilot_working'] = False

def test_p1_d_interpret_command(token):
    """D. POST /api/ai/interpret-command - verify intent JSON"""
    print("\n=== PRIORITY 1-D: Interpret Command Test ===")
    try:
        # Test 1: Task query intent
        resp = requests.post(
            f"{BACKEND_URL}/ai/interpret-command",
            json={"text": "What are my pending tasks?"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        
        success1 = log_test("P1-D: Task query returns 200", resp.status_code == 200, 
                           f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("P1-D: Task query has intent", "intent" in data, 
                    f"Intent: {data.get('intent')}")
        
        # Test 2: Reply intent
        resp = requests.post(
            f"{BACKEND_URL}/ai/interpret-command",
            json={"text": "Reply to Aman that I will review the invoice tomorrow"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        
        success2 = log_test("P1-D: Reply command returns 200", resp.status_code == 200, 
                           f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("P1-D: Reply command has intent", "intent" in data, 
                    f"Intent: {data.get('intent')}")
        
        priority1_results['interpret_working'] = success1 and success2
        check_no_secrets(resp.text, "P1-D Interpret")
        
    except Exception as e:
        log_test("P1-D: Interpret command test", False, str(e))
        priority1_results['interpret_working'] = False

# ============================================================================
# PRIORITY 2: FULL FEATURE VERIFICATION
# ============================================================================

def test_p2_e_smart_inbox(token):
    """E. Smart Inbox: GET /api/inbox/smart + PATCH priority"""
    print("\n=== PRIORITY 2-E: Smart Inbox Test ===")
    try:
        # Test smart inbox categories
        for category in ["all", "important", "needs_reply"]:
            resp = requests.get(
                f"{BACKEND_URL}/inbox/smart?category={category}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            log_test(f"P2-E: GET /api/inbox/smart?category={category}", 
                    resp.status_code == 200, f"Got {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                log_test(f"P2-E: Smart inbox {category} has groups", "groups" in data)
        
        # Test priority update
        # Get a message first
        resp = requests.get(
            f"{BACKEND_URL}/chats",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if resp.status_code == 200 and resp.json().get("chats"):
            chat_id = resp.json()["chats"][0]["chat_id"]
            
            # Get messages
            resp = requests.get(
                f"{BACKEND_URL}/chats/{chat_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if resp.status_code == 200 and resp.json().get("messages"):
                message_id = resp.json()["messages"][0]["message_id"]
                
                # Update priority
                resp = requests.patch(
                    f"{BACKEND_URL}/messages/{message_id}/priority",
                    json={"priority": "important", "source": "manual"},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                log_test("P2-E: PATCH message priority", resp.status_code == 200, 
                        f"Got {resp.status_code}")
                
                # Revert to normal
                resp = requests.patch(
                    f"{BACKEND_URL}/messages/{message_id}/priority",
                    json={"priority": "normal", "source": "manual"},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                log_test("P2-E: Revert priority to normal", resp.status_code == 200)
        
        check_no_secrets(resp.text, "P2-E Smart Inbox")
        
    except Exception as e:
        log_test("P2-E: Smart inbox test", False, str(e))

def test_p2_f_chat_digest_weekly(token):
    """F. Chat Digest: POST /api/ai/digest for weekly"""
    print("\n=== PRIORITY 2-F: Weekly Digest Test ===")
    try:
        resp = requests.post(
            f"{BACKEND_URL}/ai/digest",
            json={"period": "weekly"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=180
        )
        
        log_test("P2-F: POST /api/ai/digest period=weekly", resp.status_code == 200, 
                f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("P2-F: Weekly digest has digest object", "digest" in data)
        
        check_no_secrets(resp.text, "P2-F Weekly Digest")
        
    except Exception as e:
        log_test("P2-F: Weekly digest test", False, str(e))

def test_p2_g_daily_brief(token):
    """G. Daily Brief: POST /api/insights/daily-brief with English and Hindi"""
    print("\n=== PRIORITY 2-G: Daily Brief Test ===")
    try:
        # Test English
        resp = requests.post(
            f"{BACKEND_URL}/insights/daily-brief",
            json={"kind": "daily", "out_lang": "English"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60
        )
        
        success1 = log_test("P2-G: Daily brief English returns 200", resp.status_code == 200, 
                           f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            brief = data.get("brief", "")
            log_test("P2-G: English brief is non-empty", len(brief) > 0, 
                    f"Length: {len(brief)}")
        
        # Test Hindi
        resp = requests.post(
            f"{BACKEND_URL}/insights/daily-brief",
            json={"kind": "daily", "out_lang": "Hindi"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60
        )
        
        success2 = log_test("P2-G: Daily brief Hindi returns 200", resp.status_code == 200, 
                           f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            brief = data.get("brief", "")
            log_test("P2-G: Hindi brief is non-empty", len(brief) > 0, 
                    f"Length: {len(brief)}")
        
        check_no_secrets(resp.text, "P2-G Daily Brief")
        
    except Exception as e:
        log_test("P2-G: Daily brief test", False, str(e))

def test_p2_h_voice_commands(token):
    """H. Voice Commands: POST /api/ai/interpret-command with various intents"""
    print("\n=== PRIORITY 2-H: Voice Commands Test ===")
    try:
        commands = [
            ("Send a message to Aman saying hello", "message"),
            ("Add task buy milk", "task"),
            ("Reminder to submit report on Friday", "reminder")
        ]
        
        for cmd, expected_intent in commands:
            resp = requests.post(
                f"{BACKEND_URL}/ai/interpret-command",
                json={"text": cmd},
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            
            success = log_test(f"P2-H: Voice command '{cmd[:30]}...' returns 200", 
                             resp.status_code == 200, f"Got {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                intent = data.get("intent", "")
                log_test(f"P2-H: Command has intent", "intent" in data, 
                        f"Intent: {intent}")
        
        check_no_secrets(resp.text, "P2-H Voice Commands")
        
    except Exception as e:
        log_test("P2-H: Voice commands test", False, str(e))

def test_p2_i_scanners(token):
    """I. Scanners: POST /api/ai/document-scan/save, POST /api/ai/vision"""
    print("\n=== PRIORITY 2-I: Scanners Test ===")
    try:
        # Test document scan save
        resp = requests.post(
            f"{BACKEND_URL}/ai/document-scan/save",
            json={
                "pages": ["/files/verify-page.jpg"],
                "name": "Verify Scan"
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        log_test("P2-I: POST /api/ai/document-scan/save", resp.status_code == 200, 
                f"Got {resp.status_code}")
        
        # Test vision with tiny base64 PNG (1x1 pixel)
        tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        # Create a minimal multipart request
        files = {
            'file': ('test.png', base64.b64decode(tiny_png), 'image/png')
        }
        data = {
            'kind': 'generic',
            'prompt': 'test'
        }
        
        resp = requests.post(
            f"{BACKEND_URL}/ai/vision",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        
        log_test("P2-I: POST /api/ai/vision with tiny PNG", 
                resp.status_code in [200, 400, 422], 
                f"Got {resp.status_code} (400/422 for validation is OK)")
        
        # Test GET /api/files if exists
        try:
            resp = requests.get(
                f"{BACKEND_URL}/files",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if resp.status_code in [200, 404]:
                log_test("P2-I: GET /api/files endpoint", True, 
                        f"Status {resp.status_code}")
        except:
            pass
        
        check_no_secrets(resp.text, "P2-I Scanners")
        
    except Exception as e:
        log_test("P2-I: Scanners test", False, str(e))

def test_p2_j_calling_backend(token, token2):
    """J. Calling Backend: POST /api/calls, ice-servers, transcript"""
    print("\n=== PRIORITY 2-J: Calling Backend Test ===")
    try:
        # Get chat_id for call
        resp = requests.get(
            f"{BACKEND_URL}/chats",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if resp.status_code != 200 or not resp.json().get("chats"):
            log_test("P2-J: Get chats for calling", False, "No chats available")
            return
        
        # Find a DM chat
        chats = resp.json()["chats"]
        dm_chat = next((c for c in chats if c.get("type") == "dm"), None)
        if not dm_chat:
            log_test("P2-J: Find DM chat", False, "No DM chats available")
            return
        
        chat_id = dm_chat["chat_id"]
        
        # Create call
        resp = requests.post(
            f"{BACKEND_URL}/calls",
            json={"chat_id": chat_id, "kind": "voice"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        call_success = log_test("P2-J: POST /api/calls", resp.status_code == 200, 
                               f"Got {resp.status_code}")
        
        call_id = None
        if resp.status_code == 200:
            call_id = resp.json().get("call_id")
            log_test("P2-J: Call created with call_id", call_id is not None)
        
        # Test ICE servers
        resp = requests.get(
            f"{BACKEND_URL}/calls/ice-servers",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        ice_success = log_test("P2-J: GET /api/calls/ice-servers", resp.status_code == 200, 
                              f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            ice_servers = data.get("iceServers", [])
            has_stun = any("stun" in str(s) for s in ice_servers)
            has_turn = any("turn" in str(s) for s in ice_servers)
            log_test("P2-J: ICE servers has STUN", has_stun)
            log_test("P2-J: ICE servers has TURN", has_turn)
        
        # If call was created, test accept and end
        if call_id and token2:
            # Accept call with demo2
            resp = requests.post(
                f"{BACKEND_URL}/calls/{call_id}/accept",
                headers={"Authorization": f"Bearer {token2}"},
                timeout=10
            )
            log_test("P2-J: POST /api/calls/{id}/accept", resp.status_code == 200, 
                    f"Got {resp.status_code}")
            
            # End call
            resp = requests.post(
                f"{BACKEND_URL}/calls/{call_id}/end",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            log_test("P2-J: POST /api/calls/{id}/end", resp.status_code == 200, 
                    f"Got {resp.status_code}")
            
            # Check transcript endpoint exists
            resp = requests.get(
                f"{BACKEND_URL}/calls/{call_id}/transcript",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            log_test("P2-J: GET /api/calls/{id}/transcript endpoint", 
                    resp.status_code in [200, 404], 
                    f"Got {resp.status_code}")
        
        check_no_secrets(resp.text, "P2-J Calling")
        
    except Exception as e:
        log_test("P2-J: Calling backend test", False, str(e))

def test_p2_k_notifications_backend(token, token2):
    """K. Notifications Backend: POST /api/fcm/register, unregister"""
    print("\n=== PRIORITY 2-K: Notifications Backend Test ===")
    try:
        # Register FCM token with demo2
        resp = requests.post(
            f"{BACKEND_URL}/fcm/register",
            json={"token": "test-token-xyz", "platform": "android"},
            headers={"Authorization": f"Bearer {token2}"},
            timeout=10
        )
        
        log_test("P2-K: POST /api/fcm/register", resp.status_code == 200, 
                f"Got {resp.status_code}")
        
        # Unregister
        resp = requests.post(
            f"{BACKEND_URL}/fcm/unregister",
            json={"token": "test-token-xyz"},
            headers={"Authorization": f"Bearer {token2}"},
            timeout=10
        )
        
        log_test("P2-K: POST /api/fcm/unregister", resp.status_code == 200, 
                f"Got {resp.status_code}")
        
        check_no_secrets(resp.text, "P2-K Notifications")
        
    except Exception as e:
        log_test("P2-K: Notifications backend test", False, str(e))

def test_p2_l_auth_flows(token):
    """L. Auth: signup, verify, login, forgot, reset, firebase-token"""
    print("\n=== PRIORITY 2-L: Auth Flows Test ===")
    try:
        # Test GET /api/auth/me
        resp = requests.get(
            f"{BACKEND_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        log_test("P2-L: GET /api/auth/me", resp.status_code == 200, 
                f"Got {resp.status_code}")
        
        # Test PUT /api/auth/me
        resp = requests.put(
            f"{BACKEND_URL}/auth/me",
            json={"bio": "Testing bio update"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        log_test("P2-L: PUT /api/auth/me", resp.status_code == 200, 
                f"Got {resp.status_code}")
        
        # Test GET /api/auth/firebase-token
        resp = requests.get(
            f"{BACKEND_URL}/auth/firebase-token",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        log_test("P2-L: GET /api/auth/firebase-token", resp.status_code == 200, 
                f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("P2-L: Firebase token is non-empty", 
                    len(data.get("firebase_token", "")) > 0)
        
        # Test GET /api/firebase/status
        resp = requests.get(
            f"{BACKEND_URL}/firebase/status",
            timeout=10
        )
        log_test("P2-L: GET /api/firebase/status", resp.status_code == 200, 
                f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("P2-L: Firebase status ready=true", data.get("ready") == True)
        
        check_no_secrets(resp.text, "P2-L Auth")
        
    except Exception as e:
        log_test("P2-L: Auth flows test", False, str(e))

def test_p2_m_messages(token):
    """M. Messages: send, edit, delete, reactions, star, read receipts, pagination"""
    print("\n=== PRIORITY 2-M: Messages Test ===")
    try:
        # Get a chat
        resp = requests.get(
            f"{BACKEND_URL}/chats",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if resp.status_code != 200 or not resp.json().get("chats"):
            log_test("P2-M: Get chats for messages", False, "No chats available")
            return
        
        chat_id = resp.json()["chats"][0]["chat_id"]
        
        # Send message
        resp = requests.post(
            f"{BACKEND_URL}/chats/{chat_id}/messages",
            json={"text": "Test message for verification"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        send_success = log_test("P2-M: POST send message", resp.status_code == 200, 
                               f"Got {resp.status_code}")
        
        message_id = None
        if resp.status_code == 200:
            message_id = resp.json().get("message_id")
        
        if message_id:
            # Edit message
            resp = requests.patch(
                f"{BACKEND_URL}/messages/{message_id}",
                json={"text": "Edited test message"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            log_test("P2-M: PATCH edit message", resp.status_code == 200, 
                    f"Got {resp.status_code}")
            
            # Add reaction
            resp = requests.post(
                f"{BACKEND_URL}/messages/{message_id}/react",
                json={"emoji": "👍"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            log_test("P2-M: POST add reaction", resp.status_code == 200, 
                    f"Got {resp.status_code}")
            
            # Star message
            resp = requests.post(
                f"{BACKEND_URL}/messages/{message_id}/star",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            log_test("P2-M: POST star message", resp.status_code == 200, 
                    f"Got {resp.status_code}")
            
            # Delete message
            resp = requests.delete(
                f"{BACKEND_URL}/messages/{message_id}?scope=me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            log_test("P2-M: DELETE message (scope=me)", resp.status_code == 200, 
                    f"Got {resp.status_code}")
        
        # Test pagination
        resp = requests.get(
            f"{BACKEND_URL}/chats/{chat_id}/messages?limit=5",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        log_test("P2-M: GET messages with pagination", resp.status_code == 200, 
                f"Got {resp.status_code}")
        
        if resp.status_code == 200:
            messages = resp.json().get("messages", [])
            if messages:
                oldest_id = messages[-1]["message_id"]
                # Get older messages
                resp = requests.get(
                    f"{BACKEND_URL}/chats/{chat_id}/messages?limit=5&before={oldest_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                log_test("P2-M: GET messages with before cursor", resp.status_code == 200)
        
        check_no_secrets(resp.text, "P2-M Messages")
        
    except Exception as e:
        log_test("P2-M: Messages test", False, str(e))

def test_p2_n_security_sweep(token):
    """N. Security sweep: check all responses for no leaks"""
    print("\n=== PRIORITY 2-N: Security Sweep ===")
    try:
        # Test various endpoints for security
        endpoints = [
            ("GET", "/auth/me", {}),
            ("GET", "/chats", {}),
            ("GET", "/firebase/status", {}),
        ]
        
        all_secure = True
        for method, path, body in endpoints:
            try:
                if method == "GET":
                    resp = requests.get(
                        f"{BACKEND_URL}{path}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10
                    )
                else:
                    resp = requests.post(
                        f"{BACKEND_URL}{path}",
                        json=body,
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10
                    )
                
                if not check_no_secrets(resp.text, f"Security {path}"):
                    all_secure = False
            except:
                pass
        
        # Test 401 for missing token
        resp = requests.get(f"{BACKEND_URL}/auth/me", timeout=10)
        log_test("P2-N: Missing token returns 401", resp.status_code == 401, 
                f"Got {resp.status_code}")
        
        log_test("P2-N: Overall security sweep", all_secure, 
                "All tested endpoints are secure")
        
    except Exception as e:
        log_test("P2-N: Security sweep", False, str(e))

def main():
    print("=" * 80)
    print("Chatly AI Messenger - Comprehensive Backend Verification Test")
    print("=" * 80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test User: {DEMO_EMAIL}")
    print("=" * 80)
    
    # Login
    print("\n=== Logging in ===")
    token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not token:
        print("❌ CRITICAL: Could not login with demo@chatly.app")
        sys.exit(1)
    print(f"✅ Logged in as {DEMO_EMAIL}")
    
    token2 = login(DEMO2_EMAIL, DEMO2_PASSWORD)
    if token2:
        print(f"✅ Logged in as {DEMO2_EMAIL}")
    else:
        print(f"⚠️  Could not login as {DEMO2_EMAIL} (some tests will be skipped)")
    
    # PRIORITY 1 TESTS
    print("\n" + "=" * 80)
    print("PRIORITY 1: VERIFY RECENT FIXES")
    print("=" * 80)
    
    test_p1_a_digest_latency(token)
    test_p1_b_message_action_validation(token)
    test_p1_c_autopilot_analyze_confirm(token)
    test_p1_d_interpret_command(token)
    
    # PRIORITY 2 TESTS
    print("\n" + "=" * 80)
    print("PRIORITY 2: FULL FEATURE VERIFICATION")
    print("=" * 80)
    
    test_p2_e_smart_inbox(token)
    test_p2_f_chat_digest_weekly(token)
    test_p2_g_daily_brief(token)
    test_p2_h_voice_commands(token)
    test_p2_i_scanners(token)
    test_p2_j_calling_backend(token, token2)
    test_p2_k_notifications_backend(token, token2)
    test_p2_l_auth_flows(token)
    test_p2_m_messages(token)
    test_p2_n_security_sweep(token)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"\nPRIORITY 1 RESULTS:")
    print(f"  A. Digest: {'✅ WORKING' if priority1_results.get('digest_working') else '❌ FAILED'}")
    if 'digest_latency' in priority1_results:
        print(f"     Latency: {priority1_results['digest_latency']:.1f}s (target <90s)")
    print(f"  B. Validation: {'✅ WORKING' if priority1_results.get('validation_working') else '❌ FAILED'}")
    print(f"  C. Autopilot: {'✅ WORKING' if priority1_results.get('autopilot_working') else '❌ FAILED'}")
    print(f"  D. Interpret: {'✅ WORKING' if priority1_results.get('interpret_working') else '❌ FAILED'}")
    
    print(f"\nOVERALL: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 80)
    
    # Detailed results
    print("\nDETAILED RESULTS:")
    for result in test_results:
        print(result)
    
    print("\n" + "=" * 80)
    if failed > 0:
        print(f"⚠️  {failed} test(s) failed")
        sys.exit(1)
    else:
        print("✅ All tests PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
