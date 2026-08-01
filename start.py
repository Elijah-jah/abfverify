import subprocess, sys
subprocess.run([sys.executable, "manage.py", "loaddata", "admin_user.json"])
subprocess.run(["gunicorn", "config.wsgi:application"])