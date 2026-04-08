import re
import os

os.chdir(r'e:\Crime-Proj-backup\backend\app\routers')

files = ['dispatch_routes.py', 'case_intelligence_routes.py', 'suspect_routes.py']

for filename in files:
    with open(filename, 'r') as f:
        content = f.read()
    
    # Replace pattern: ] = Depends(), with ],
    fixed = re.sub(r'\] = Depends\(\),', '],', content)
    
    with open(filename, 'w') as f:
        f.write(fixed)
    
    print(f"✓ Fixed {filename}")

print("\n✅ All route files fixed!")
