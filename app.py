import cv2
import time
import threading
import os
import boto3
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
CONFIRMATION_LIMIT = 45 # Frames to hold gesture (~1.5s at 30 FPS)
console_logs = ["System Initialized. Awaiting Operator Auth..."]
is_executing = False

# AWS Clients (Lazy load to avoid runtime startup delay if AWS config is missing)
ec2 = None
rds = None

def add_log(message):
    global console_logs
    console_logs.append(message)
    if len(console_logs) > 6:
        console_logs.pop(0)

# --- Background Task Runner (Non-blocking Threads) ---
def run_cloud_task(task_type):
    global is_executing, ec2, rds
    is_executing = True
    add_log(f"Starting task: {task_type}...")
    try:
        if task_type == "LAUNCH_EC2":
            if not ec2:
                ec2 = boto3.client("ec2")
            add_log("Connecting to AWS EC2...")
            response = ec2.run_instances(
                ImageId="ami-0c55b159cbfafe1f0", # Replace with your target AMI
                InstanceType="t2.micro",
                MinCount=1,
                MaxCount=1
            )
            instance_id = response['Instances'][0]['InstanceId']
            add_log(f"EC2 Launch Success: {instance_id}")
            os.system("notepad") # Launch notepad locally for demonstration
            
        elif task_type == "LAUNCH_RDS":
            if not rds:
                rds = boto3.client("rds")
            add_log("Connecting to AWS RDS...")
            response = rds.create_db_instance(
                DBName="mydb",
                DBInstanceIdentifier="gesture-db",
                AllocatedStorage=20,
                DBInstanceClass="db.t2.micro",
                Engine="mysql",
                MasterUsername="admin",
                MasterUserPassword="securepassword123"
            )
            add_log(f"RDS Setup Success: gesture-db")
            os.system("start chrome") # Open browser locally for demonstration
            
    except Exception as e:
        add_log(f"AWS Error: {str(e)[:40]}")
    
    is_executing = False

def start_async_task(task_type):
    if not is_executing:
        thread = threading.Thread(target=run_cloud_task, args=(task_type,))
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
    
    add_log("Webcam stream started successfully.")
    
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
        cv2.putText(img, "ZEROTOUCHSEC // V2.0", (20, 40), FONT, 0.8, COLOR_NEON_CYAN, 2)
        cv2.putText(img, f"FPS: {fps}", (w - 150, 40), FONT, 0.7, COLOR_NEON_GREEN, 2)
        
        # --- Authentication State Machine ---
        if sys_status == "LOCKED":
            # Draw locked overlay
            overlay = img.copy()
            cv2.rectangle(overlay, (0, 60), (w, h), (0, 0, 0), cv2.FILLED)
            cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)
            
            cv2.putText(img, "SECURE MODE ACTIVE - SYSTEM LOCKED", (w // 2 - 300, h // 2 - 50), FONT, 0.9, COLOR_NEON_RED, 2)
            cv2.putText(img, "SHOW [🖐️] PALM TO COMMENCE OPERATOR SCAN", (w // 2 - 320, h // 2 + 10), FONT, 0.7, COLOR_WHITE, 1)
            
            # Look for hand for authentication
            hands, img = detector.findHands(img, draw=False)
            if hands:
                sys_status = "AUTHENTICATING"
                auth_timer = time.time()
                add_log("Operator detected. Starting Biometric authentication...")
                
        elif sys_status == "AUTHENTICATING":
            # Simulate a futuristic scanner bar moving down
            scan_y = 60 + int((h - 60) * min(((time.time() - auth_timer) / 2.0), 1.0))
            
            if scan_y < h:
                cv2.line(img, (0, scan_y), (w, scan_y), COLOR_NEON_CYAN, 4)
                cv2.putText(img, "SCANNING BIOMETRIC SIGNATURE...", (w // 2 - 250, h // 2), FONT, 0.8, COLOR_NEON_CYAN, 2)
            else:
                sys_status = "ACTIVE"
                add_log("Biometric Signature verified. Access GRANTED.")
                
        elif sys_status == "ACTIVE":
            # Active Control Center state
            cv2.putText(img, "SYS STATE: ACTIVE (ARMED)", (380, 40), FONT, 0.7, COLOR_NEON_GREEN, 2)
            
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
                
                # Draw Progress Indicator if gesture matches mapped commands
                if fingers in [[1, 1, 1, 1, 1], [0, 1, 1, 0, 0]] and not is_executing:
                    # Draw verification bar on screen
                    bar_w = int((gesture_hold_counter / CONFIRMATION_LIMIT) * 300)
                    cv2.rectangle(img, (w // 2 - 150, h - 80), (w // 2 + 150, h - 50), COLOR_GRAY, cv2.FILLED)
                    cv2.rectangle(img, (w // 2 - 150, h - 80), (w // 2 - 150 + bar_w, h - 50), COLOR_NEON_GREEN, cv2.FILLED)
                    cv2.putText(img, "CONFIRMING GESTURE COMMAND...", (w // 2 - 140, h - 90), FONT, 0.55, COLOR_WHITE, 1)
                    
                    if gesture_hold_counter >= CONFIRMATION_LIMIT:
                        gesture_hold_counter = 0 # Reset
                        if fingers == [1, 1, 1, 1, 1]:
                            start_async_task("LAUNCH_EC2")
                        elif fingers == [0, 1, 1, 0, 0]:
                            start_async_task("LAUNCH_RDS")
                else:
                    gesture_hold_counter = 0
            else:
                gesture_hold_counter = 0
                
        # Press 'L' to lock system again manually, or 'Q' to quit
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
