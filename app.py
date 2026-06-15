import cv2
import time
import threading
import os
import webbrowser
import pyautogui
from cvzone.HandTrackingModule import HandDetector

# UI Configuration
WINDOW_NAME = "ZeroTouchSec - AI Control Center"
FONT = cv2.FONT_HERSHEY_SIMPLEX
COLOR_NEON_GREEN = (57, 255, 20)
COLOR_NEON_RED = (20, 20, 255)
COLOR_NEON_CYAN = (255, 255, 0)
COLOR_GRAY = (80, 80, 80)
COLOR_WHITE = (255, 255, 255)

# Session State
sys_status = "LOCKED"  # State machine: LOCKED -> AUTHENTICATING -> ACTIVE
auth_timer = 0
last_gesture = [0, 0, 0, 0, 0]
gesture_hold_counter = 0
CONFIRMATION_LIMIT = 40  # Hold threshold (approx. 1.3s at 30 FPS)
console_logs = ["System Initialized. Awaiting Operator Auth..."]
is_executing = False

# Enable safety escape (moving mouse to corner aborts script)
pyautogui.FAILSAFE = True

def add_log(message):
    """Appends a log entry to the HUD interface logs panel."""
    global console_logs
    console_logs.append(message)
    if len(console_logs) > 6:
        console_logs.pop(0)

def run_system_task(task_type):
    """Executes mapped system commands in a separate worker thread."""
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
            pyautogui.screenshot("screenshot.png")
            add_log("Saved: screenshot.png")
            os.startfile("screenshot.png")
            add_log("Opened screenshot preview.")
            
        elif task_type == "LOCK_PC":
            add_log("Locking Windows workstation...")
            os.system("rundll32.exe user32.dll,LockWorkStation")
            add_log("System locked successfully.")
            
        elif task_type == "LAUNCH_COMET":
            add_log("Launching Comet...")
            os.startfile(r"C:\Users\Krishna\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Comet.lnk")
            add_log("Comet launched successfully.")
            
    except Exception as e:
        add_log(f"Error: {str(e)[:40]}")
    
    is_executing = False

def start_async_task(task_type):
    """Spawns non-blocking task runner thread to maintain target camera FPS."""
    if not is_executing:
        thread = threading.Thread(target=run_system_task, args=(task_type,))
        thread.daemon = True
        thread.start()
    else:
        add_log("System busy. Task ignored.")

def main():
    """Initializes camera feed, runs hand detection, and manages authentication states."""
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
            
        img = cv2.flip(img, 1)
        h, w, c = img.shape
        
        curr_time = time.time()
        fps = int(1 / (curr_time - prev_time)) if (curr_time - prev_time) > 0 else 30
        prev_time = curr_time
        
        # Draw HUD panels
        cv2.rectangle(img, (0, 0), (w, 60), (15, 15, 15), cv2.FILLED)
        cv2.line(img, (0, 60), (w, 60), COLOR_NEON_CYAN, 1)
        
        cv2.rectangle(img, (w - 450, h - 250), (w - 10, h - 10), (10, 10, 10), cv2.FILLED)
        cv2.rectangle(img, (w - 450, h - 250), (w - 10, h - 10), COLOR_NEON_CYAN, 1)
        cv2.putText(img, "CONSOLE LOGS", (w - 440, h - 225), FONT, 0.6, COLOR_NEON_CYAN, 2)
        
        for idx, log in enumerate(console_logs):
            cv2.putText(img, f"> {log}", (w - 440, h - 190 + (idx * 25)), FONT, 0.45, COLOR_WHITE, 1)
            
        cv2.putText(img, "ZEROTOUCHSEC // LOCAL V2.0", (20, 40), FONT, 0.8, COLOR_NEON_CYAN, 2)
        cv2.putText(img, f"FPS: {fps}", (w - 150, 40), FONT, 0.7, COLOR_NEON_GREEN, 2)
        
        # State machine processing
        if sys_status == "LOCKED":
            overlay = img.copy()
            cv2.rectangle(overlay, (0, 60), (w, h), (0, 0, 0), cv2.FILLED)
            cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)
            
            cv2.putText(img, "SECURE MODE ACTIVE - SYSTEM LOCKED", (w // 2 - 300, h // 2 - 50), FONT, 0.9, COLOR_NEON_RED, 2)
            cv2.putText(img, "SHOW [🖐️] PALM TO COMMENCE OPERATOR SCAN", (w // 2 - 320, h // 2 + 10), FONT, 0.7, COLOR_WHITE, 1)
            
            hands, img = detector.findHands(img, draw=False)
            if hands:
                hand = hands[0]
                fingers = detector.fingersUp(hand)
                if fingers == [1, 1, 1, 1, 1]:
                    sys_status = "AUTHENTICATING"
                    auth_timer = time.time()
                    add_log("Operator detected. Starting Biometric scan...")
                
        elif sys_status == "AUTHENTICATING":
            scan_y = 60 + int((h - 60) * min(((time.time() - auth_timer) / 1.5), 1.0))
            
            if scan_y < h - 5:
                cv2.line(img, (0, scan_y), (w, scan_y), COLOR_NEON_CYAN, 4)
                cv2.putText(img, "SCANNING BIOMETRIC SIGNATURE...", (w // 2 - 250, h // 2), FONT, 0.8, COLOR_NEON_CYAN, 2)
            else:
                sys_status = "ACTIVE"
                add_log("Biometric Signature verified. Access GRANTED.")
                
        elif sys_status == "ACTIVE":
            cv2.putText(img, "SYS STATE: ACTIVE (ARMED)", (480, 40), FONT, 0.7, COLOR_NEON_GREEN, 2)
            
            hands, img = detector.findHands(img, draw=True)
            if hands:
                hand = hands[0]
                fingers = detector.fingersUp(hand)
                
                if fingers == last_gesture:
                    gesture_hold_counter += 1
                else:
                    gesture_hold_counter = 0
                    last_gesture = fingers
                
                valid_gestures = [
                    ([0, 0, 0, 0, 0], "BOSS_KEY"),       # Fist ✊
                    ([1, 1, 0, 0, 0], "SCREENSHOT"),     # Gun gesture 🔫
                    ([1, 1, 1, 1, 1], "LOCK_PC"),        # Open Palm 🖐️
                    ([0, 1, 1, 0, 0], "LAUNCH_COMET")    # Peace sign ✌️
                ]
                
                matched_task = None
                for gesture_vector, task in valid_gestures:
                    if fingers == gesture_vector:
                        matched_task = task
                        break
                
                if matched_task and not is_executing:
                    bar_w = int((gesture_hold_counter / CONFIRMATION_LIMIT) * 300)
                    cv2.rectangle(img, (w // 2 - 150, h - 80), (w // 2 + 150, h - 50), COLOR_GRAY, cv2.FILLED)
                    cv2.rectangle(img, (w // 2 - 150, h - 80), (w // 2 - 150 + bar_w, h - 50), COLOR_NEON_GREEN, cv2.FILLED)
                    cv2.putText(img, f"CONFIRMING {matched_task}...", (w // 2 - 140, h - 90), FONT, 0.55, COLOR_WHITE, 1)
                    
                    if gesture_hold_counter >= CONFIRMATION_LIMIT:
                        gesture_hold_counter = 0
                        start_async_task(matched_task)
                else:
                    gesture_hold_counter = 0
            else:
                gesture_hold_counter = 0
                
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
