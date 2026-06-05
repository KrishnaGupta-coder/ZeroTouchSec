import cv2
import time
import threading
import os
import webbrowser
import pyautogui
from cvzone.HandTrackingModule import HandDetector

# --- Configuration & Styling Constants ---
WINDOW_NAME = "ZeroTouchSec - AI Control Center"
FONT = cv2.FONT_HERSHEY_SIMPLEX
COLOR_NEON_GREEN = (57, 255, 20)
COLOR_NEON_RED = (20, 20, 255)
COLOR_NEON_CYAN = (255, 255, 0)
COLOR_GRAY = (80, 80, 80)
COLOR_WHITE = (255, 255, 255)

# --- Global State Variables ---
sys_status = "LOCKED"  # LOCKED -> AUTHENTICATING -> ACTIVE
auth_timer = 0
last_gesture = [0, 0, 0, 0, 0]
gesture_hold_counter = 0
CONFIRMATION_LIMIT = 40 # Frames to hold gesture (~1.3s at 30 FPS)
console_logs = ["System Initialized. Awaiting Operator Auth..."]
is_executing = False

# Ensure pyautogui safety fail-safe is enabled (moving mouse to corner aborts scripts)
pyautogui.FAILSAFE = True

def add_log(message):
    global console_logs
    console_logs.append(message)
    if len(console_logs) > 6:
        console_logs.pop(0)

# --- Background Task Runner (Non-blocking Threads for Smooth FPS) ---
def run_system_task(task_type):
    global is_executing
    is_executing = True
    add_log(f"Dispatching: {task_type}...")
    try:
        if task_type == "BOSS_KEY":
            add_log("Toggling Desktop (Win + D)...")
            pyautogui.hotkey('win', 'd')
            add_log("Desktop toggled successfully.")
            
        elif task_type == "SCREENSHOT":
            add_log("Taking screenshot in 0.5s...")
            time.sleep(0.5)
            # Save screenshot in the current directory
            pyautogui.screenshot("screenshot.png")
            add_log("Saved: screenshot.png")
            # Open screenshot using Windows default image viewer
            os.startfile("screenshot.png")
            add_log("Opened screenshot preview.")
            
        elif task_type == "LOCK_PC":
            add_log("Locking Windows workstation...")
            os.system("rundll32.exe user32.dll,LockWorkStation")
            add_log("System locked successfully.")
            
        elif task_type == "LAUNCH_BROWSER":
            add_log("Launching YouTube...")
            webbrowser.open("https://youtube.com")
            add_log("Browser page opened.")
            
    except Exception as e:
        add_log(f"Error: {str(e)[:40]}")
    
    is_executing = False

def start_async_task(task_type):
    if not is_executing:
        thread = threading.Thread(target=run_system_task, args=(task_type,))
        thread.daemon = True
        thread.start()
    else:
        add_log("System busy. Task ignored.")

# --- MAIN CONTROLLER LOOP ---
def main():
    global sys_status, auth_timer, last_gesture, gesture_hold_counter, is_executing
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    detector = HandDetector(detectionCon=0.8, maxHands=1)
    prev_time = time.time()
    
    add_log("Webcam stream initialized.")
    add_log("Press 'L' to lock manually. Press 'Q' to quit.")
    
    while True:
        success, img = cap.read()
        if not success:
            break
            
        # Flip image for a mirror-like experience
        img = cv2.flip(img, 1)
        h, w, c = img.shape
        
        # Calculate FPS
        curr_time = time.time()
        fps = int(1 / (curr_time - prev_time)) if (curr_time - prev_time) > 0 else 30
        prev_time = curr_time
        
        # Draw HUD Background Panels
        # Top Panel
        cv2.rectangle(img, (0, 0), (w, 60), (15, 15, 15), cv2.FILLED)
        cv2.line(img, (0, 60), (w, 60), COLOR_NEON_CYAN, 1)
        
        # Console Log Panel (Bottom Right)
        cv2.rectangle(img, (w - 450, h - 250), (w - 10, h - 10), (10, 10, 10), cv2.FILLED)
        cv2.rectangle(img, (w - 450, h - 250), (w - 10, h - 10), COLOR_NEON_CYAN, 1)
        cv2.putText(img, "CONSOLE LOGS", (w - 440, h - 225), FONT, 0.6, COLOR_NEON_CYAN, 2)
        
        # Draw Current Logs
        for idx, log in enumerate(console_logs):
            cv2.putText(img, f"> {log}", (w - 440, h - 190 + (idx * 25)), FONT, 0.45, COLOR_WHITE, 1)
            
        # Draw System Info (Top Bar)
        cv2.putText(img, "ZEROTOUCHSEC // LOCAL V2.0", (20, 40), FONT, 0.8, COLOR_NEON_CYAN, 2)
        cv2.putText(img, f"FPS: {fps}", (w - 150, 40), FONT, 0.7, COLOR_NEON_GREEN, 2)
        
        # --- Authentication State Machine ---
        if sys_status == "LOCKED":
            # Draw locked overlay
            overlay = img.copy()
            cv2.rectangle(overlay, (0, 60), (w, h), (0, 0, 0), cv2.FILLED)
            cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)
            
            cv2.putText(img, "SECURE MODE ACTIVE - SYSTEM LOCKED", (w // 2 - 300, h // 2 - 50), FONT, 0.9, COLOR_NEON_RED, 2)
            cv2.putText(img, "SHOW [🖐️] PALM TO COMMENCE OPERATOR SCAN", (w // 2 - 320, h // 2 + 10), FONT, 0.7, COLOR_WHITE, 1)
            
            # Look for hand to trigger scanning authentication
            hands, img = detector.findHands(img, draw=False)
            if hands:
                hand = hands[0]
                fingers = detector.fingersUp(hand)
                if fingers == [1, 1, 1, 1, 1]:  # Must be open palm
                    sys_status = "AUTHENTICATING"
                    auth_timer = time.time()
                    add_log("Operator detected. Starting Biometric scan...")
                
        elif sys_status == "AUTHENTICATING":
            # Simulate a futuristic scanner bar moving down
            scan_y = 60 + int((h - 60) * min(((time.time() - auth_timer) / 1.5), 1.0))
            
            if scan_y < h - 5:
                cv2.line(img, (0, scan_y), (w, scan_y), COLOR_NEON_CYAN, 4)
                cv2.putText(img, "SCANNING BIOMETRIC SIGNATURE...", (w // 2 - 250, h // 2), FONT, 0.8, COLOR_NEON_CYAN, 2)
            else:
                sys_status = "ACTIVE"
                add_log("Biometric Signature verified. Access GRANTED.")
                
        elif sys_status == "ACTIVE":
            # Active state
            cv2.putText(img, "SYS STATE: ACTIVE (ARMED)", (480, 40), FONT, 0.7, COLOR_NEON_GREEN, 2)
            
            # Detect Hands
            hands, img = detector.findHands(img, draw=True)
            
            if hands:
                hand = hands[0]
                fingers = detector.fingersUp(hand)
                
                # Check gesture stability
                if fingers == last_gesture:
                    gesture_hold_counter += 1
                else:
                    gesture_hold_counter = 0
                    last_gesture = fingers
                
                # Valid command gestures list
                valid_gestures = [
                    ([0, 0, 0, 0, 0], "BOSS_KEY"),       # Fist ✊
                    ([1, 1, 0, 0, 0], "SCREENSHOT"),     # Gun gesture 🔫
                    ([1, 1, 1, 1, 1], "LOCK_PC"),        # Open Palm 🖐️
                    ([0, 1, 1, 0, 0], "LAUNCH_BROWSER")   # Peace sign ✌️
                ]
                
                matched_task = None
                for gesture_vector, task in valid_gestures:
                    if fingers == gesture_vector:
                        matched_task = task
                        break
                
                # Draw Progress Indicator if a valid gesture is held and not currently busy
                if matched_task and not is_executing:
                    bar_w = int((gesture_hold_counter / CONFIRMATION_LIMIT) * 300)
                    # Draw a nice dark background and neon bar
                    cv2.rectangle(img, (w // 2 - 150, h - 80), (w // 2 + 150, h - 50), COLOR_GRAY, cv2.FILLED)
                    cv2.rectangle(img, (w // 2 - 150, h - 80), (w // 2 - 150 + bar_w, h - 50), COLOR_NEON_GREEN, cv2.FILLED)
                    cv2.putText(img, f"CONFIRMING {matched_task}...", (w // 2 - 140, h - 90), FONT, 0.55, COLOR_WHITE, 1)
                    
                    if gesture_hold_counter >= CONFIRMATION_LIMIT:
                        gesture_hold_counter = 0  # Reset
                        start_async_task(matched_task)
                else:
                    gesture_hold_counter = 0
            else:
                gesture_hold_counter = 0
                
        # Key listeners
        cv2.imshow(WINDOW_NAME, img)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('l'):
            sys_status = "LOCKED"
            add_log("Operator manually locked system.")
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
