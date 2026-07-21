@echo off
cd /d "%~dp0backend"
echo ============================================
echo   Install Hybrid Retrieval Dependencies
echo   Packages: jieba, rank-bm25
echo ============================================
echo.
call .venv\Scripts\activate.bat
pip install jieba rank-bm25
echo.
echo Done. You can now run the tests:
echo   python -m pytest tests/test_keyword_search.py -v
echo   python -m pytest tests/test_hybrid_search.py -v
echo.
pause
