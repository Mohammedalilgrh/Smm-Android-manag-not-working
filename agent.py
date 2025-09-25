import os
import sys
import subprocess
import time
import json
import re
import threading
import pyautogui
from datetime import datetime

# Auto-install dependencies if missing
def install_packages():
    try:
        import selenium, google.generativeai, webdriver_manager, pyautogui
    except ImportError:
        print("[!] Installing required packages... (This may take 1-2 minutes)")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("[✓] All packages installed successfully!\n")
        # Reload modules
        globals()['selenium'] = __import__('selenium')
        globals()['google'] = __import__('google')
        globals()['webdriver_manager'] = __import__('webdriver_manager')
        globals()['pyautogui'] = __import__('pyautogui')

install_packages()

# Now safe to import
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import google.generativeai as genai
from PIL import ImageGrab

# === CONFIGURATION ===
GEMINI_KEY = "AIzaSyDnsQ_EaKER5TghXoh8mpkoy_tXZoaYZ58"
DATA_DIR = "agent_data"
os.makedirs(DATA_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
LOG_FILE = os.path.join(DATA_DIR, "agent.log")

# Configure Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Setup logging
def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    print(msg)

# Load conversation history
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

# Save conversation history
def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# Initialize browser (with manual driver path fallback)
def init_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    
    # Use ONLY custom driver — no fallback!
custom_driver = r"C:\deepseek\New folder\chromedriver.exe"
if os.path.exists(custom_driver):
    service = Service(executable_path=custom_driver)
    driver = webdriver.Chrome(service=service, options=options)
    log("[✓] Using custom 64-bit ChromeDriver")
    return driver
else:
    log("[ERROR] Custom ChromeDriver NOT FOUND at C:\\deepseek\\New folder\\chromedriver.exe")
    log("Please download chromedriver-win64.zip and place chromedriver.exe there!")
    return None
    
    # Fallback to auto-managed driver
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        log("[✓] Browser started with auto-managed ChromeDriver")
        return driver
    except Exception as e:
        log(f"[ERROR] Failed to start browser: {e}")
        return None

# Global state
driver = None
history = load_history()
running = True

# === CORE FUNCTIONS ===

def execute_cmd(command):
    log(f"[CMD] Executing: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout or result.stderr
        log(f"[CMD OUTPUT]\n{output}")
        return output[:1000]  # Truncate long outputs
    except Exception as e:
        err = f"[CMD ERROR] {str(e)}"
        log(err)
        return err

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        log(f"[READ] {path} ({len(content)} chars)")
        return content[:2000]
    except Exception as e:
        err = f"[READ ERROR] {str(e)}"
        log(err)
        return err

def write_file(path, content):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        log(f"[WRITE] {path} ({len(content)} chars)")
        return f"[✓] Written to {path}"
    except Exception as e:
        err = f"[WRITE ERROR] {str(e)}"
        log(err)
        return err

def take_screenshot():
    path = os.path.join(DATA_DIR, f"screenshot_{int(time.time())}.png")
    screenshot = ImageGrab.grab()
    screenshot.save(path)
    log(f"[SCREENSHOT] Saved: {path}")
    return path

def move_mouse(x, y, action="move"):
    log(f"[MOUSE] {action} to ({x}, {y})")
    pyautogui.moveTo(x, y, duration=0.3)
    if action == "click":
        pyautogui.click()
    elif action == "double_click":
        pyautogui.doubleClick()

def type_text(text):
    log(f"[TYPE] {text[:50]}...")
    pyautogui.write(text, interval=0.05)

def search_google(query):
    global driver
    if not driver:
        driver = init_browser()
        if not driver:
            return "[ERROR] Browser failed to start"
    
    log(f"[BROWSER] Searching Google for: {query}")
    try:
        driver.get("https://www.google.com")
        wait = WebDriverWait(driver, 10)
        search_box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(2)
        return "[✓] Google search completed"
    except Exception as e:
        err = f"[BROWSER ERROR] {str(e)}"
        log(err)
        return err

def browse_url(url):
    global driver
    if not driver:
        driver = init_browser()
        if not driver:
            return "[ERROR] Browser failed to start"
    log(f"[BROWSER] Opening: {url}")
    try:
        driver.get(url)
        time.sleep(2)
        return "[✓] Page loaded"
    except Exception as e:
        err = f"[BROWSER ERROR] {str(e)}"
        log(err)
        return err

def check_for_login_or_captcha():
    """Check if current page has login/CAPTCHA and pause for user"""
    global driver
    if not driver:
        return False
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if any(kw in page_text for kw in ["sign in", "login", "captcha", "verify", "robot", "consent"]):
            log("\n[⚠️  ACTION REQUIRED] Detected login, CAPTCHA, or consent page!")
            log("Please handle this manually in the browser window.")
            input("Press ENTER in this CMD window when you're done...")
            return True
    except:
        pass
    return False

# === AI PROMPT ===
def get_ai_response(user_input):
    global history
    
    # Build context
    context = (
        "You are an advanced Windows automation agent. The user gives you tasks in natural language. "
        "You must respond with a JSON list of actions to perform. Each action is a dict with 'tool' and 'params'.\n\n"
        "Available tools:\n"
        "- cmd: execute Windows command\n"
        "- read: read file content\n"
        "- write: write to file\n"
        "- mouse: move/click mouse (params: x, y, action='move'|'click'|'double_click')\n"
        "- type: type text\n"
        "- screenshot: take screenshot\n"
        "- search: search Google\n"
        "- browse: open URL\n"
        "- chat: respond directly to user\n\n"
        "Rules:\n"
        "1. Break complex tasks into small steps\n"
        "2. Always use absolute paths\n"
        "3. If a step requires user interaction (login, CAPTCHA), output a 'chat' message asking user to handle it\n"
        "4. After user handles it, continue automation\n"
        "5. Show live progress in CMD\n"
        "6. NEVER assume paths; ask if unclear\n\n"
        "Respond ONLY with valid JSON array. No explanations."
    )
    
    messages = [{"role": "user", "parts": [context]}]
    for h in history[-5:]:  # Last 5 exchanges
        messages.append({"role": "user", "parts": [h["user"]]})
        messages.append({"role": "model", "parts": [h["ai"]]})
    messages.append({"role": "user", "parts": [user_input]})
    
    try:
        response = model.generate_content(messages)
        return response.text.strip()
    except Exception as e:
        return '[{"tool": "chat", "params": {"text": "[AI ERROR] ' + str(e) + '"}}]'

# === MAIN LOOP ===
def main():
    global history, running, driver
    
    log("\n" + "="*60)
    log("🤖 ADVANCED AI AUTOMATION AGENT STARTED")
    log("✅ Type your request in natural language (e.g., 'search me latest AI news')")
    log("✅ I will show every action live in this CMD window")
    log("✅ If I hit login/CAPTCHA, I'll pause and wait for you")
    log("✅ Type 'exit' to quit")
    log("="*60 + "\n")
    
    while running:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "exit":
                running = False
                break
            
            # Save to history
            history.append({"user": user_input, "ai": ""})
            
            # Get AI plan
            ai_response = get_ai_response(user_input)
            log(f"\n[🧠 AI PLAN] {ai_response}")
            
            # Parse and execute actions
            try:
                actions = json.loads(ai_response)
                if not isinstance(actions, list):
                    actions = [actions]
            except:
                actions = [{"tool": "chat", "params": {"text": f"[PARSE ERROR] Invalid AI response: {ai_response}"}}]
            
            results = []
            for action in actions:
                if not running:
                    break
                tool = action.get("tool")
                params = action.get("params", {})
                result = ""
                
                if tool == "cmd":
                    result = execute_cmd(params.get("command", ""))
                elif tool == "read":
                    result = read_file(params.get("file_path", ""))
                elif tool == "write":
                    result = write_file(params.get("file_path", ""), params.get("content", ""))
                elif tool == "mouse":
                    move_mouse(params.get("x", 0), params.get("y", 0), params.get("action", "move"))
                    result = f"[MOUSE] {params.get('action')} at ({params.get('x')}, {params.get('y')})"
                elif tool == "type":
                    type_text(params.get("text", ""))
                    result = f"[TYPED] {params.get('text', '')[:30]}..."
                elif tool == "screenshot":
                    result = take_screenshot()
                elif tool == "search":
                    result = search_google(params.get("query", ""))
                    # Check for login/CAPTCHA after search
                    if driver:
                        check_for_login_or_captcha()
                elif tool == "browse":
                    result = browse_url(params.get("url", ""))
                    if driver:
                        check_for_login_or_captcha()
                elif tool == "chat":
                    result = params.get("text", "")
                    log(f"AI: {result}")
                else:
                    result = f"[UNKNOWN TOOL] {tool}"
                
                results.append(result)
                time.sleep(0.5)  # Prevent overwhelming
            
            # Save AI response
            final_response = " | ".join(str(r) for r in results if r)
            history[-1]["ai"] = final_response
            if not any(a.get("tool") == "chat" for a in actions):
                log(f"AI: {final_response}")
            
            save_history(history)
            
        except KeyboardInterrupt:
            log("\n[!] Interrupted by user")
            break
        except Exception as e:
            log(f"[CRITICAL ERROR] {str(e)}")
    
    # Cleanup
    if driver:
        driver.quit()
    log("\n[✓] Agent stopped. Goodbye!")

if __name__ == "__main__":
    main()
