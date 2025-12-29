#!/usr/bin/env python3
"""
AI Outfit App - Automated Setup Script (FIXED VERSION)
Handles spaces in paths correctly
"""
import os
import sys
import subprocess
import platform
import time
from pathlib import Path


class Colors:
    """Terminal colors for pretty output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print colored header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}\n")


def print_step(step_num, text):
    """Print step number"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}[STEP {step_num}] {text}{Colors.END}")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def run_command(command, shell=True, check=True, capture=False):
    """Run a shell command"""
    try:
        if capture:
            result = subprocess.run(
                command,
                shell=shell,
                check=check,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        else:
            subprocess.run(command, shell=shell, check=check)
            return True
    except subprocess.CalledProcessError as e:
        return False


def check_command_exists(command):
    """Check if a command exists"""
    if platform.system() == "Windows":
        result = run_command(f'where {command}', capture=True)
    else:
        result = run_command(f'which {command}', capture=True)
    return result is not False and result


def check_python():
    """Check Python installation"""
    print("Checking Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} installed")
        return True
    else:
        print_error(f"Python 3.11+ required, found {version.major}.{version.minor}")
        print("Install from: https://python.org")
        return False


def check_node():
    """Check Node.js installation"""
    print("Checking Node.js...")
    if check_command_exists('node'):
        version = run_command('node --version', capture=True)
        print_success(f"Node.js {version} installed")
        return True
    else:
        print_error("Node.js not found")
        print("Install from: https://nodejs.org")
        return False


def check_ollama():
    """Check Ollama installation"""
    print("Checking Ollama...")
    if check_command_exists('ollama'):
        print_success("Ollama installed")
        return True
    else:
        print_warning("Ollama not found")
        return False


def install_ollama():
    """Install Ollama"""
    print_step("1A", "Installing Ollama...")
    
    system = platform.system()
    
    if system == "Windows":
        print("Please install Ollama manually:")
        print("1. Open PowerShell as Administrator")
        print("2. Run: iex (irm https://ollama.ai/install.ps1)")
        print("\nOr download from: https://ollama.ai")
        input("\nPress Enter after installing Ollama...")
        
    elif system == "Linux":
        print("Installing Ollama for Linux...")
        if run_command("curl -fsSL https://ollama.ai/install.sh | sh"):
            print_success("Ollama installed")
        else:
            print_error("Failed to install Ollama")
            return False
            
    elif system == "Darwin":  # macOS
        print("Please install Ollama manually:")
        print("Download from: https://ollama.ai")
        input("\nPress Enter after installing Ollama...")
    
    return check_ollama()


def check_existing_models():
    """Check if Llama model already exists"""
    print("Checking for existing Llama models...")
    result = run_command("ollama list", capture=True)
    
    if result and "llama3.1" in result:
        print_success("Llama 3.1 model already exists!")
        print(result)
        return True
    return False


def pull_llama_model():
    """Pull Llama 3.1 model"""
    print_step("1B", "Setting up Llama 3.1 model...")
    
    # Check if model already exists
    if check_existing_models():
        print_success("Skipping download - model already available")
        return True
    
    print("Downloading Llama 3.1 model (~4.6GB). Please wait...")
    
    # Try different model tags
    model_tags = [
        "llama3.1:latest",
        "llama3.1",
        "llama3.1:8b"
    ]
    
    for tag in model_tags:
        print(f"Trying: {tag}...")
        if run_command(f"ollama pull {tag}"):
            print_success(f"Llama model downloaded: {tag}")
            return True
        else:
            print_warning(f"Failed to pull {tag}, trying next...")
    
    print_error("Failed to download model with all tags")
    print("\nManual fix:")
    print("1. Open a new terminal")
    print("2. Run: ollama serve")
    print("3. In another terminal, run: ollama pull llama3.1")
    print("4. Then re-run this script")
    return False


def setup_database_instructions():
    """Show database setup instructions"""
    print_step("2", "Database Setup")
    print("\n" + "="*60)
    print("MANUAL STEP REQUIRED: Setup Supabase Database")
    print("="*60)
    print("\n1. Go to: https://supabase.com")
    print("2. Sign up for FREE account")
    print("3. Create new project:")
    print("   - Project name: ai-outfit-app")
    print("   - Choose a password (save it!)")
    print("   - Select region closest to you")
    print("   - Wait 2 minutes for setup")
    print("\n4. Get connection string:")
    print("   - Settings → Database → SCROLL DOWN")
    print("   - Find 'Connection string' section")
    print("   - Click 'URI' tab")
    print("   - Copy the string")
    print("   - Replace [YOUR-PASSWORD] with your database password")
    print("   - Example: postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres")
    print("\n5. Enable pgvector:")
    print("   - Go to SQL Editor")
    print("   - Run this SQL:")
    print("   CREATE EXTENSION IF NOT EXISTS vector;")
    
    print("\n" + "="*60)
    connection_string = input("\nPaste your Supabase connection string here: ").strip()
    
    if not connection_string or not connection_string.startswith('postgresql://'):
        print_error("Invalid connection string")
        return None
    
    return connection_string


def update_env_file(database_url):
    """Update .env file with database URL"""
    print("Updating .env file...")
    
    env_path = Path('backend/.env')
    
    if not env_path.exists():
        # Copy from example
        example_path = Path('backend/.env.example')
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
    
    # Read current content
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update DATABASE_URL and OLLAMA_MODEL
    with open(env_path, 'w') as f:
        for line in lines:
            if line.startswith('DATABASE_URL='):
                f.write(f'DATABASE_URL={database_url}\n')
            elif line.startswith('OLLAMA_MODEL='):
                f.write('OLLAMA_MODEL=llama3.1:latest\n')
            else:
                f.write(line)
    
    print_success(".env file updated")


def install_backend_dependencies():
    """Install Python backend dependencies"""
    print_step("3A", "Installing Backend Dependencies...")
    
    os.chdir('backend')
    
    # Create virtual environment with quoted path
    print("Creating virtual environment...")
    # Quote the python executable path to handle spaces
    python_exe = f'"{sys.executable}"'
    if not run_command(f'{python_exe} -m venv venv'):
        print_error("Failed to create virtual environment")
        return False
    
    print_success("Virtual environment created")
    
    # Determine pip path and quote it
    if platform.system() == "Windows":
        pip_path = '"venv\\Scripts\\pip"'
        python_path = '"venv\\Scripts\\python"'
    else:
        pip_path = '"venv/bin/pip"'
        python_path = '"venv/bin/python"'
    
    # Upgrade pip
    print("Upgrading pip...")
    run_command(f'{pip_path} install --upgrade pip', check=False)
    
    # Install requirements
    print("Installing packages (this may take 3-5 minutes)...")
    if not run_command(f'{pip_path} install -r requirements.txt'):
        print_error("Failed to install backend dependencies")
        return False
    
    print_success("Backend dependencies installed")
    os.chdir('..')
    return True


def install_frontend_dependencies():
    """Install Node.js frontend dependencies"""
    print_step("3B", "Installing Frontend Dependencies...")
    
    os.chdir('frontend')
    
    # Create .env file
    with open('.env', 'w') as f:
        f.write('VITE_API_URL=http://localhost:8000/api/v1\n')
    
    print("Installing packages (this may take 2-3 minutes)...")
    if not run_command('npm install'):
        print_error("Failed to install frontend dependencies")
        return False
    
    print_success("Frontend dependencies installed")
    os.chdir('..')
    return True


def initialize_database():
    """Initialize database tables"""
    print_step("4", "Initializing Database...")
    
    os.chdir('backend')
    
    # Determine python path with quotes
    if platform.system() == "Windows":
        python_path = '"venv\\Scripts\\python"'
    else:
        python_path = '"venv/bin/python"'
    
    # Initialize database
    init_script = 'from app.database import init_db, create_indexes; init_db(); create_indexes(); print(\\"Database initialized successfully\\")'
    
    if not run_command(f'{python_path} -c "{init_script}"'):
        print_error("Failed to initialize database")
        print("\nTroubleshooting:")
        print("1. Check your Supabase connection string is correct")
        print("2. Make sure pgvector extension is enabled")
        print("3. Check your internet connection")
        return False
    
    print_success("Database initialized")
    os.chdir('..')
    return True


def create_start_script():
    """Create a script to start all services"""
    print_step("5", "Creating Start Script...")
    
    if platform.system() == "Windows":
        script_content = """@echo off
echo Starting AI Outfit App...
echo.
echo Starting Ollama...
start "Ollama" cmd /k ollama serve
timeout /t 3 /nobreak > nul

echo Starting Backend...
start "Backend" cmd /k "cd backend && venv\\Scripts\\activate && uvicorn app.main:app --reload"
timeout /t 5 /nobreak > nul

echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================================
echo All services started!
echo ============================================================
echo.
echo Open http://localhost:5173 in your browser
echo.
echo To stop: Close all terminal windows
echo ============================================================
pause
"""
        with open('start_app.bat', 'w') as f:
            f.write(script_content)
        print_success("Created start_app.bat")
        
    else:  # Linux/Mac
        script_content = """#!/bin/bash
echo "Starting AI Outfit App..."
echo ""

echo "Starting Ollama..."
ollama serve > /dev/null 2>&1 &
sleep 3

echo "Starting Backend..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload > ../backend.log 2>&1 &
cd ..
sleep 5

echo "Starting Frontend..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
cd ..

echo ""
echo "============================================================"
echo "All services started!"
echo "============================================================"
echo ""
echo "Open http://localhost:5173 in your browser"
echo ""
echo "Logs:"
echo "  Backend: backend.log"
echo "  Frontend: frontend.log"
echo ""
echo "To stop: Run: ./stop_app.sh"
echo "============================================================"
"""
        with open('start_app.sh', 'w') as f:
            f.write(script_content)
        os.chmod('start_app.sh', 0o755)
        print_success("Created start_app.sh")
        
        # Create stop script
        stop_content = """#!/bin/bash
echo "Stopping AI Outfit App..."
pkill -f "ollama serve"
pkill -f "uvicorn app.main:app"
pkill -f "npm run dev"
echo "All services stopped"
"""
        with open('stop_app.sh', 'w') as f:
            f.write(stop_content)
        os.chmod('stop_app.sh', 0o755)
        print_success("Created stop_app.sh")


def print_final_instructions():
    """Print final instructions"""
    print_header("🎉 SETUP COMPLETE!")
    
    print(f"\n{Colors.BOLD}Your AI Outfit App is ready!{Colors.END}\n")
    
    print("🚀 TO START THE APP:")
    print("="*60)
    
    if platform.system() == "Windows":
        print("Double-click: start_app.bat")
        print("Or run: start_app.bat")
    else:
        print("Run: ./start_app.sh")
    
    print("\n📱 TO USE THE APP:")
    print("="*60)
    print("1. Wait 10 seconds for all services to start")
    print("2. Open browser: http://localhost:5173")
    print("3. Type a prompt: 'Beach party, colorful and relaxed'")
    print("4. Click 'Generate Outfits'")
    print("5. Wait ~10-15 seconds")
    print("6. Swipe through AI-generated outfits!")
    
    print("\n🛑 TO STOP THE APP:")
    print("="*60)
    if platform.system() == "Windows":
        print("Close all command prompt windows")
    else:
        print("Run: ./stop_app.sh")
    
    print("\n📚 DOCUMENTATION:")
    print("="*60)
    print("- QUICKSTART.md - Quick reference")
    print("- README.md - Full documentation")
    print("- docs/SETUP.md - Detailed setup guide")
    
    print("\n💰 CURRENT STATUS:")
    print("="*60)
    print("✅ Running locally - $0/month")
    print("ℹ️  Using simple image compositing (not real virtual try-on)")
    print("ℹ️  To add real AI try-on, see docs/SETUP.md (Production)")
    
    print("\n" + "="*60)
    print(f"{Colors.GREEN}{Colors.BOLD}Happy building! 🚀{Colors.END}")
    print("="*60 + "\n")


def main():
    """Main setup flow"""
    print_header("🎨 AI OUTFIT APP - AUTOMATED SETUP")
    
    print("This script will:")
    print("1. Check/install prerequisites")
    print("2. Setup database (with your help)")
    print("3. Install all dependencies")
    print("4. Initialize database")
    print("5. Create start scripts")
    print("\nEstimated time: 15-20 minutes")
    
    input("\nPress Enter to start...")
    
    # Check prerequisites
    print_header("CHECKING PREREQUISITES")
    
    if not check_python():
        print_error("Please install Python 3.11+ and run again")
        sys.exit(1)
    
    if not check_node():
        print_error("Please install Node.js and run again")
        sys.exit(1)
    
    # Check/install Ollama
    if not check_ollama():
        if not install_ollama():
            print_error("Ollama installation required")
            sys.exit(1)
    
    # Pull/check Llama model
    if not pull_llama_model():
        print_error("Llama model setup failed")
        print("\nYou can continue manually if you already have the model.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Database setup
    database_url = setup_database_instructions()
    if not database_url:
        print_error("Database setup required")
        sys.exit(1)
    
    update_env_file(database_url)
    
    # Install dependencies
    if not install_backend_dependencies():
        sys.exit(1)
    
    if not install_frontend_dependencies():
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        sys.exit(1)
    
    # Create start scripts
    create_start_script()
    
    # Done!
    print_final_instructions()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Setup cancelled by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)