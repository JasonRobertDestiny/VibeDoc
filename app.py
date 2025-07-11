import os
import subprocess

print("--- VibeDoc Launcher: Starting Next.js server ---")

# Command to run the standalone Next.js server
cmd = ["node", "server.js"]

process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Stream the output
for line in iter(process.stdout.readline, ''):
    print(line.strip(), flush=True)

process.stdout.close()
exit_code = process.wait()

print(f"--- VibeDoc Launcher: Server has exited with code {exit_code} ---")