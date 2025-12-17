#!/bin/bash

# Start both frontend and backend servers

echo "========================================="
echo "LinkedIn Automation System"
echo "========================================="
echo ""
echo "Starting servers..."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "🚀 Starting Backend (http://localhost:5000)..."
cd linkedin-automation/backend
python3 app.py &
BACKEND_PID=$!
cd ../..

# Wait a moment for backend to start
sleep 2

# Start frontend
echo "🚀 Starting Frontend (http://localhost:8080)..."
cd pro-pulse-studio
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Servers are running!"
echo ""
echo "Backend:  http://localhost:5000"
echo "Frontend: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for both processes
wait

