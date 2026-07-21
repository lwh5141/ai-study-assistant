"""应用入口 — python run.py"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 backend/ 目录下的 .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from app import create_app

env = os.getenv('FLASK_ENV', 'development')
app = create_app(env)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=(env == 'development'))
