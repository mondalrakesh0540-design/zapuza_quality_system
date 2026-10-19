import os
import sys
from pathlib import Path

# Add project root to sys.path so zapuza_core and apps can be imported
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zapuza_core.settings')

# Copy SQLite db to /tmp on Vercel serverless environment (read-only filesystem)
if os.environ.get('VERCEL'):
    import shutil
    tmp_db = Path('/tmp') / 'db.sqlite3'
    src_db = BASE_DIR / 'db.sqlite3'
    if not tmp_db.exists():
        if src_db.exists():
            try:
                shutil.copy2(src_db, tmp_db)
            except Exception as e:
                print(f"Error copying sqlite db: {e}")
        else:
            try:
                import django
                django.setup()
                from django.core.management import call_command
                call_command('migrate', interactive=False)
                call_command('seed_phase1_data')
                call_command('seed_phase2_data')
                call_command('seed_phase3_data')
                call_command('seed_phase4_data')
            except Exception as e:
                print(f"Error auto-initializing db: {e}")

from zapuza_core.wsgi import application

# Vercel Python serverless handler
app = application
