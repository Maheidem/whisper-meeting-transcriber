#!/bin/bash

# Script to manage Whisper services using docker-compose

ACTION=$1

case "$ACTION" in
    start)
        echo "🚀 Starting Whisper services with docker-compose..."
        docker-compose up -d
        echo ""
        echo "✅ All services started!"
        echo ""
        echo "Checking service status..."
        docker-compose ps
        ;;
    
    stop)
        echo "🛑 Stopping Whisper services..."
        docker-compose down
        echo "✅ All services stopped!"
        ;;
    
    restart)
        echo "🔄 Restarting Whisper services..."
        docker-compose restart
        echo "✅ All services restarted!"
        ;;
    
    logs)
        echo "📋 Showing logs (Ctrl+C to exit)..."
        docker-compose logs -f
        ;;
    
    status)
        echo "📊 Service Status:"
        docker-compose ps
        echo ""
        echo "🔍 Model Download Progress:"
        docker-compose logs | grep -E "(Downloading|Download|MB|GB)" | tail -20
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|logs|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all Whisper services"
        echo "  stop    - Stop all Whisper services"
        echo "  restart - Restart all Whisper services"
        echo "  logs    - Show service logs (live)"
        echo "  status  - Show service status and download progress"
        exit 1
        ;;
esac