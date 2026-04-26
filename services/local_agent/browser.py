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