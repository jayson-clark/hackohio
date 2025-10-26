#!/bin/bash

echo "🔄 Resetting database and rebuilding RAG indices..."

# Stop the backend if running
echo "Stopping backend..."
pkill -f "python.*main.py" || true
sleep 2

# Reset database
echo "Resetting database..."
cd /Users/jalenfrancis/calhacks/backend
rm -f synapse_mapper.db
python3 -c "from app.models.database import init_db; init_db()"

# Delete old RAG indices
echo "Deleting old RAG indices..."
rm -f uploads/*_rag_index.pkl

# Delete cached embeddings
echo "Cleaning upload directory..."
find uploads -type f -name "*.txt" -size 0 -delete 2>/dev/null || true

echo "✅ Database reset complete!"
echo ""
echo "Now you need to:"
echo "1. Restart the backend"
echo "2. Log in through the frontend"
echo "3. Upload your PDFs again"
echo "4. The RAG indices will be rebuilt automatically with proper entity indexing"
echo ""
echo "To start backend: cd backend && python3 app/main.py"
