@echo off
echo Adding all changes to git...
git add .

echo Committing changes...
git commit -m "feat: Major update - Frontend UI improvements and backend enhancements

Frontend changes:
- Update React dependencies and package configuration
- Enhance UI components (button, card) with modern styling
- Improve MarkdownRenderer for better text display
- Update Sidebar with improved navigation
- Enhance SmartProjectManagement interface
- Improve UploadTab functionality and UX
- Update login component with better auth flow
- Refine responsive design in App.css

Backend changes:
- Update internal_assistant_app.py with new features
- Enhance projectProgress_modul.py functionality
- Improve rag_modul.py with better RAG implementation
- Update requirements.txt with new dependencies
- Add new debug and document management modules"

echo Done! Changes have been committed.
pause