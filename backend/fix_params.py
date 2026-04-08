import re
import os

os.chdir(r'e:\Crime-Proj-backup\backend\app\routers')

files = ['dispatch_routes.py', 'case_intelligence_routes.py', 'suspect_routes.py']

for filename in files:
    with open(filename, 'r') as f:
        content = f.read()
    
    # Replace pattern: Annotated[...Depends...] (without =) with Annotated[...Depends...] = None
    # This allows them to come after Query params
    fixed = re.sub(
        r'(db: Annotated\[Session, Depends\(get_db\)\]),',
        r'\1 = None,',
        content
    )
    fixed = re.sub(
        r'(user: Annotated\[dict, Depends\(get_current_user\)\]),',
        r'\1 = None,',
        fixed
    )
    # Handle case where the parameter is last (no comma after)
    fixed = re.sub(
        r'(db: Annotated\[Session, Depends\(get_db\)\])(\n\):)',
        r'\1 = None\2',
        fixed
    )
    fixed = re.sub(
        r'(user: Annotated\[dict, Depends\(get_current_user\)\])(\n\):)',
        r'\1 = None\2',
        fixed
    )
    
    with open(filename, 'w') as f:
        f.write(fixed)
    
    print(f"✓ Fixed {filename}")

print("\n✅ All route files fixed!")
