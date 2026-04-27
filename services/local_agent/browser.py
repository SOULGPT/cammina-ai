import subprocess
import time

def take_screenshot() -> dict:
    """Take a screenshot using screencapture"""
    try:
        import tempfile, base64, os
        tmp = tempfile.mktemp(suffix='.png')
        result = subprocess.run(
            ['screencapture', '-x', tmp],
            capture_output=True, timeout=10
        )
        if result.returncode == 0:
            with open(tmp, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode()
            os.unlink(tmp)
            return {"success": True, "image_base64": img_data}
        return {"success": False, "error": result.stderr.decode()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def focus_and_type_in_cursor(text: str) -> dict:
    """Focus Cursor app and type text into its chat using AppleScript"""
    try:
        # Step 1: Focus Cursor app
        focus_script = '''
        tell application "Cursor"
            activate
        end tell
        '''
        subprocess.run(
            ['osascript', '-e', focus_script],
            capture_output=True, timeout=5
        )
        time.sleep(1.5)
        
        # Step 2: Escape special characters for AppleScript
        safe_text = text.replace('\\', '\\\\').replace('"', '\\"')
        
        # Step 3: Type the text and press Enter
        type_script = f'''
        tell application "System Events"
            tell process "Cursor"
                keystroke "{safe_text}"
                delay 0.5
                key code 36
            end tell
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', type_script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return {"success": True, "message": "Text typed in Cursor and Enter pressed"}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def focus_and_type_in_antigravity(text: str) -> dict:
    """Focus Antigravity app and type text into its chat"""
    try:
        focus_script = '''
        tell application "Antigravity"
            activate
        end tell
        '''
        subprocess.run(
            ['osascript', '-e', focus_script],
            capture_output=True, timeout=5
        )
        time.sleep(1.5)
        
        safe_text = text.replace('\\', '\\\\').replace('"', '\\"')
        
        type_script = f'''
        tell application "System Events"
            tell process "Antigravity"
                keystroke "{safe_text}"
                delay 0.5
                key code 36
            end tell
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', type_script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return {"success": True, "message": "Text typed in Antigravity and Enter pressed"}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_active_window() -> dict:
    """Get the currently active application name"""
    try:
        script = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            return frontApp
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {"success": True, "app": result.stdout.strip()}
        return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def focus_app(app_name: str) -> dict:
    """Focus any app by name"""
    try:
        script = f'''
        tell application "{app_name}"
            activate
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {"success": True, "message": f"{app_name} focused"}
        return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def take_screenshot_base64() -> str:
    """Take screenshot and return base64 string"""
    import tempfile, base64, os
    tmp = tempfile.mktemp(suffix='.png')
    subprocess.run(['screencapture', '-x', tmp], timeout=10)
    with open(tmp, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    os.unlink(tmp)
    return data

def read_cursor_chat() -> dict:
    """Read the current Cursor chat content by scraping the UI or clipboard"""
    try:
        import time
        
        # 1. Focus Cursor first
        focus_script = """
        tell application "Cursor"
            activate
        end tell
        """
        subprocess.run(['osascript', '-e', focus_script], timeout=5)
        time.sleep(2)
        
        # 2. Use AppleScript to get text from Cursor's window
        # Try to find the last AI response in chat
        script = """
        tell application "System Events"
            tell process "Cursor"
                set allText to ""
                try
                    set allText to value of text area 1 of scroll area 1 of group 1 of group 1 of window 1
                end try
                return allText
            end tell
        end tell
        """
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return {"success": True, "text": result.stdout.strip()}
        
        # Fallback: read clipboard
        clip_script = "return the clipboard"
        clip_result = subprocess.run(
            ['osascript', '-e', clip_script],
            capture_output=True, text=True, timeout=5
        )
        return {"success": True, "text": clip_result.stdout.strip()}
        
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}