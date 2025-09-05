#!/bin/bash
# Force load ExternalControl.urp on both UR robots

echo "========================================"
echo "FORCE LOADING ExternalControl.urp"
echo "========================================"
echo ""
echo "This will attempt to load ExternalControl.urp on both robots."
echo "Make sure:"
echo "1. Both robots are powered on"
echo "2. Remote Control is enabled"
echo "3. No protective stops are active"
echo ""

# Test LEFT UR
echo "Testing LEFT UR (192.168.1.211)..."
python3 - << 'EOF'
import socket
import time

host = "192.168.1.211"
try:
    s = socket.create_connection((host, 29999), timeout=2)
    s.recv(4096)  # Welcome
    
    print(f"Connected to {host}")
    
    # Stop and clear
    for cmd in ["stop", "close safety popup", "unlock protective stop"]:
        s.send((cmd + "\n").encode())
        s.recv(4096)
        time.sleep(0.2)
    
    # Try multiple load formats
    for prog in ["/programs/ExternalControl.urp", 
                 "programs/ExternalControl.urp",
                 "ExternalControl.urp",
                 "ExternalControl"]:
        print(f"  Trying: load {prog}")
        s.send(f"load {prog}\n".encode())
        resp = s.recv(4096).decode()
        if "File not found" not in resp and "error" not in resp.lower():
            print(f"  Load command accepted")
            break
    
    # Play
    s.send("play\n".encode())
    s.recv(4096)
    time.sleep(0.5)
    
    # Check state
    s.send("programState\n".encode())
    state = s.recv(4096).decode().strip()
    print(f"  State: {state}")
    
    if "PLAYING" in state:
        print("  ✓ SUCCESS - ExternalControl is PLAYING")
    else:
        print("  ✗ Not playing - manual load required on pendant")
    
    s.close()
except Exception as e:
    print(f"  Error: {e}")
EOF

echo ""
echo "Testing RIGHT UR (192.168.1.210)..."
python3 - << 'EOF'
import socket
import time

host = "192.168.1.210"
try:
    s = socket.create_connection((host, 29999), timeout=2)
    s.recv(4096)  # Welcome
    
    print(f"Connected to {host}")
    
    # Stop and clear
    for cmd in ["stop", "close safety popup", "unlock protective stop"]:
        s.send((cmd + "\n").encode())
        s.recv(4096)
        time.sleep(0.2)
    
    # Try multiple load formats
    for prog in ["/programs/ExternalControl.urp", 
                 "programs/ExternalControl.urp",
                 "ExternalControl.urp",
                 "ExternalControl"]:
        print(f"  Trying: load {prog}")
        s.send(f"load {prog}\n".encode())
        resp = s.recv(4096).decode()
        if "File not found" not in resp and "error" not in resp.lower():
            print(f"  Load command accepted")
            break
    
    # Play
    s.send("play\n".encode())
    s.recv(4096)
    time.sleep(0.5)
    
    # Check state
    s.send("programState\n".encode())
    state = s.recv(4096).decode().strip()
    print(f"  State: {state}")
    
    if "PLAYING" in state:
        print("  ✓ SUCCESS - ExternalControl is PLAYING")
    else:
        print("  ✗ Not playing - manual load required on pendant")
    
    s.close()
except Exception as e:
    print(f"  Error: {e}")
EOF

echo ""
echo "========================================"
echo "If programs are not PLAYING:"
echo "1. On each pendant: Menu → Run Program"
echo "2. Select ExternalControl.urp"
echo "3. Press Play button (▶)"
echo "4. Verify Remote Control is ON"
echo "========================================"

