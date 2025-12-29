#!/usr/bin/env python3
"""
AI Outfit App - File Organization Script
Organizes downloaded files into proper project structure
"""
import os
import shutil
from pathlib import Path


# File mapping: {current_name: (destination_folder, final_name)}
FILE_MAPPING = {
    # Root level files
    'README.md': ('', 'README.md'),
    'QUICKSTART.md': ('', 'QUICKSTART.md'),
    'START_HERE.md': ('', 'START_HERE.md'),
    'FILE_PLACEMENT_GUIDE.md': ('', 'FILE_PLACEMENT_GUIDE.md'),
    
    # Backend files
    'requirements': ('backend', 'requirements.txt'),
    'requirements.txt': ('backend', 'requirements.txt'),
    '.env.example': ('backend', '.env.example'),
    
    # Backend app files
    'backend_app_init': ('backend/app', '__init__.py'),
    'backend_app_init.py': ('backend/app', '__init__.py'),
    'main': ('backend/app', 'main.py'),
    'main.py': ('backend/app', 'main.py'),
    'config': ('backend/app', 'config.py'),
    'config.py': ('backend/app', 'config.py'),
    'models': ('backend/app', 'models.py'),
    'models.py': ('backend/app', 'models.py'),
    'database': ('backend/app', 'database.py'),
    'database.py': ('backend/app', 'database.py'),
    
    # Backend services files
    'backend_services_init': ('backend/app/services', '__init__.py'),
    'backend_services_init.py': ('backend/app/services', '__init__.py'),
    'llama_service': ('backend/app/services', 'llama_service.py'),
    'llama_service.py': ('backend/app/services', 'llama_service.py'),
    'product_service': ('backend/app/services', 'product_service.py'),
    'product_service.py': ('backend/app/services', 'product_service.py'),
    'tryon_service': ('backend/app/services', 'tryon_service.py'),
    'tryon_service.py': ('backend/app/services', 'tryon_service.py'),
    
    # Frontend files
    'package.json': ('frontend', 'package.json'),
    'vite.config.js': ('frontend', 'vite.config.js'),
    'index': ('frontend', 'index.html'),
    'index.html': ('frontend', 'index.html'),
    
    # Frontend src files
    'main.jsx': ('frontend/src', 'main.jsx'),
    'App.jsx': ('frontend/src', 'App.jsx'),
    'App.css': ('frontend/src', 'App.css'),
    'index.css': ('frontend/src', 'index.css'),
    
    # Frontend services
    'api.js': ('frontend/src/services', 'api.js'),
    'api': ('frontend/src/services', 'api.js'),
    
    # Database
    'schema.sql': ('database', 'schema.sql'),
    'schema': ('database', 'schema.sql'),
    
    # Docs
    'SETUP.md': ('docs', 'SETUP.md'),
    'DEPLOYMENT.md': ('docs', 'DEPLOYMENT.md'),
    'API_DOCS.md': ('docs', 'API_DOCS.md'),
}


def create_folder_structure():
    """Create the complete folder structure"""
    folders = [
        'backend/app/services',
        'frontend/src/services',
        'database',
        'docs'
    ]
    
    for folder in folders:
        Path(folder).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created folder: {folder}")


def organize_files(source_dir='.'):
    """Organize all files into proper structure"""
    source_path = Path(source_dir)
    moved_count = 0
    skipped_count = 0
    
    # Get all files in source directory
    all_files = [f for f in source_path.iterdir() if f.is_file()]
    
    print(f"\n📁 Found {len(all_files)} files to organize\n")
    
    for file_path in all_files:
        filename = file_path.name
        
        # Skip this script itself
        if filename == 'organize_files.py' or filename == __file__:
            continue
        
        # Check if file is in mapping
        if filename in FILE_MAPPING:
            dest_folder, dest_name = FILE_MAPPING[filename]
            
            # Create full destination path
            if dest_folder:
                dest_path = Path(dest_folder) / dest_name
            else:
                dest_path = Path(dest_name)
            
            # Move file
            try:
                # Create parent directory if needed
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move and rename file
                shutil.move(str(file_path), str(dest_path))
                print(f"✅ Moved: {filename} → {dest_path}")
                moved_count += 1
                
            except Exception as e:
                print(f"❌ Error moving {filename}: {e}")
                skipped_count += 1
        else:
            print(f"⚠️  Skipped: {filename} (not in mapping)")
            skipped_count += 1
    
    return moved_count, skipped_count


def create_env_file():
    """Create .env file from .env.example if it exists"""
    env_example = Path('backend/.env.example')
    env_file = Path('backend/.env')
    
    if env_example.exists() and not env_file.exists():
        shutil.copy(str(env_example), str(env_file))
        print(f"\n✅ Created .env file from .env.example")
        print("   ⚠️  IMPORTANT: Edit backend/.env and add your database URL!")
        return True
    return False


def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "=" * 60)
    print("🎉 FILE ORGANIZATION COMPLETE!")
    print("=" * 60)
    
    print("\n📁 Your project structure is now:")
    print("""
ai-outfit-app/
├── README.md
├── QUICKSTART.md
├── START_HERE.md
├── backend/
│   ├── requirements.txt
│   ├── .env
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── models.py
│       ├── database.py
│       └── services/
│           ├── __init__.py
│           ├── llama_service.py
│           ├── product_service.py
│           └── tryon_service.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── App.css
│       ├── index.css
│       └── services/
│           └── api.js
├── database/
│   └── schema.sql
└── docs/
    └── SETUP.md
    """)
    
    print("🎯 NEXT STEPS:")
    print("=" * 60)
    print("1. ✅ Edit backend/.env file with your database URL")
    print("2. ✅ Open QUICKSTART.md and follow the setup steps")
    print("3. ✅ Install Ollama: https://ollama.ai")
    print("4. ✅ Pull Llama model: ollama pull llama3.1:8b-q4_0")
    print("5. ✅ Install Python dependencies: cd backend && pip install -r requirements.txt")
    print("6. ✅ Install Node dependencies: cd frontend && npm install")
    print("7. 🚀 Start building!")
    print("=" * 60)


def main():
    """Main execution"""
    print("=" * 60)
    print("🎨 AI OUTFIT APP - FILE ORGANIZER")
    print("=" * 60)
    
    # Step 1: Create folder structure
    print("\n📂 Step 1: Creating folder structure...")
    create_folder_structure()
    
    # Step 2: Organize files
    print("\n📦 Step 2: Organizing files...")
    moved, skipped = organize_files()
    
    # Step 3: Create .env file
    print("\n⚙️  Step 3: Setting up environment...")
    create_env_file()
    
    # Step 4: Print summary
    print("\n📊 SUMMARY:")
    print(f"   ✅ Files organized: {moved}")
    print(f"   ⚠️  Files skipped: {skipped}")
    
    # Step 5: Print next steps
    print_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Organization cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nIf you encounter issues, try:")
        print("1. Make sure all downloaded files are in the same folder as this script")
        print("2. Run the script from that folder")
        print("3. Check file permissions")
