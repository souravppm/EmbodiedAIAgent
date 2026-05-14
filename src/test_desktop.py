# src/test_desktop.py
import pyautogui
import time

def test_desktop_control():
    print("🚀 Booting up Desktop Agent Hands...")
    print("⚠️ WARNING: Keep your hands off the mouse!")
    print("Taking a screenshot in 3 seconds. Minimize your windows and go to your desktop!")
    
    # Give the user 3 seconds to minimize VS Code and look at the desktop
    time.sleep(3)

    # 1. The Eyes: Take a screenshot of the whole monitor
    screenshot = pyautogui.screenshot()
    screenshot.save("desktop_state.png")
    print("\n📸 Screenshot captured and saved as 'desktop_state.png'")

    # 2. The Environment: Find out the monitor resolution
    width, height = pyautogui.size()
    print(f"🖥️ Monitor Resolution detected: {width} x {height}")

    # 3. The Hands: Take physical control of the mouse
    print("🖱️ Moving mouse to the exact center of your screen in 2 seconds...")
    time.sleep(2)
    
    # Move the mouse to the middle (duration=1.5 makes it move smoothly like a human)
    pyautogui.moveTo(width / 2, height / 2, duration=1.5)
    
    print("✅ Desktop Control Test Complete!")

if __name__ == "__main__":
    test_desktop_control()
