import shutil
import os

base = r"C:\Users\Acer\.gemini\antigravity\scratch\habitflow"

# Create css and js dirs in root if not exist
os.makedirs(os.path.join(base, "css"), exist_ok=True)
os.makedirs(os.path.join(base, "js"), exist_ok=True)

# Copy files
shutil.copyfile(os.path.join(base, "frontend", "index.html"), os.path.join(base, "index.html"))
shutil.copyfile(os.path.join(base, "frontend", "css", "styles.css"), os.path.join(base, "css", "styles.css"))
shutil.copyfile(os.path.join(base, "frontend", "js", "api.js"), os.path.join(base, "js", "api.js"))
shutil.copyfile(os.path.join(base, "frontend", "js", "app.js"), os.path.join(base, "js", "app.js"))

print("Frontend files synchronized to root for Vercel Zero Config!")
