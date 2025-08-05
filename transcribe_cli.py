#!/usr/bin/env python3
"""
CLI Whisper Meeting Transcriber
Simple command-line interface for transcribing videos
"""

import argparse
import requests
import os
import sys
import time
import subprocess
import tempfile
from datetime import datetime
import json

class ProgressBar:
    """Simple CLI progress bar"""
    def __init__(self, total=100, width=50):
        self.total = total
        self.width = width
        self.current = 0
        
    def update(self, current, text=""):
        self.current = current
        percent = self.current / self.total
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)
        sys.stdout.write(f"\r[{bar}] {self.current}% {text}")
        sys.stdout.flush()
        
    def complete(self, text="Complete!"):
        self.update(100, text)
        print()  # New line after completion

def extract_audio(input_file, progress_callback=None):
    """Extract audio from video file to WAV format"""
    print(f"\n📹 Extracting audio from: {os.path.basename(input_file)}")
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_file.close()
    temp_audio_file = temp_file.name
    
    try:
        # Get video duration first
        probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 
                    'format=duration', '-of', 'json', input_file]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        
        duration = None
        if probe_result.returncode == 0:
            probe_data = json.loads(probe_result.stdout)
            duration = float(probe_data.get('format', {}).get('duration', 0))
            print(f"Video duration: {duration:.1f} seconds")
        
        # Use ffmpeg to extract audio with progress
        cmd = [
            'ffmpeg', '-i', input_file,
            '-vn',  # No video
            '-ac', '1',  # Mono
            '-ar', '16000',  # 16kHz sample rate
            '-f', 'wav',
            '-y',  # Overwrite
            '-progress', 'pipe:1',  # Progress to stdout
            '-loglevel', 'error',  # Only show errors
            temp_audio_file
        ]
        
        # Run ffmpeg with progress monitoring
        progress_bar = ProgressBar(100)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                 universal_newlines=True)
        
        for line in process.stdout:
            if line.startswith('out_time_ms='):
                # Extract time in microseconds
                time_ms = int(line.split('=')[1]) / 1000000
                if duration and duration > 0:
                    progress = min(int((time_ms / duration) * 100), 99)
                    progress_bar.update(progress, "Extracting audio...")
        
        process.wait()
        
        if process.returncode != 0:
            error = process.stderr.read()
            raise Exception(f"FFmpeg error: {error}")
        
        progress_bar.complete("Audio extraction complete!")
        return temp_audio_file
        
    except Exception as e:
        if os.path.exists(temp_audio_file):
            os.unlink(temp_audio_file)
        raise e

def transcribe_audio(audio_file, whisper_url="http://localhost:9000", output_format="txt", 
                    diarize=False, min_speakers=None, max_speakers=None):
    """Transcribe audio file using Whisper service"""
    print(f"\n🎤 Transcribing audio...")
    
    # Display diarization settings if enabled
    if diarize:
        print(f"🔊 Speaker diarization: ENABLED")
        if min_speakers:
            print(f"   Min speakers: {min_speakers}")
        if max_speakers:
            print(f"   Max speakers: {max_speakers}")
    
    url = f"{whisper_url}/asr"
    file_size = os.path.getsize(audio_file)
    print(f"Audio file size: {file_size:,} bytes ({file_size / (1024*1024):.1f} MB)")
    
    progress_bar = ProgressBar(100)
    progress_bar.update(10, "Uploading to Whisper service...")
    
    try:
        with open(audio_file, 'rb') as file:
            files = {'audio_file': file}
            
            # Build query parameters
            params = {}
            if output_format != 'txt':
                params['output'] = output_format
            
            # Add diarization parameters
            if diarize:
                params['diarize'] = 'true'
                if min_speakers is not None:
                    params['min_speakers'] = str(min_speakers)
                if max_speakers is not None:
                    params['max_speakers'] = str(max_speakers)
            
            # Make the request
            start_time = time.time()
            progress_bar.update(20, "Processing transcription...")
            
            # Start request with params
            response = requests.post(url, files=files, params=params, 
                                   timeout=3600, stream=True)
            
            # Simulate progress (since we can't get real progress from the server)
            if response.status_code == 200:
                # Estimate time based on file size (rough estimate)
                estimated_time = max(10, file_size / (1024 * 1024) * 2)  # 2 seconds per MB
                start = time.time()
                
                while (time.time() - start) < estimated_time * 0.8:
                    elapsed = time.time() - start
                    progress = min(90, 20 + int(70 * (elapsed / estimated_time)))
                    progress_bar.update(progress, f"Transcribing... (~{int(estimated_time - elapsed)}s remaining)")
                    time.sleep(0.5)
                
                progress_bar.update(95, "Finalizing...")
                
                # Get the actual response
                if output_format == 'json':
                    result = json.dumps(response.json(), indent=2)
                else:
                    result = response.text
                
                elapsed_time = time.time() - start_time
                progress_bar.complete(f"Transcription completed in {elapsed_time:.1f} seconds!")
                
                return result
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
                
    except Exception as e:
        print(f"\n❌ Transcription failed: {str(e)}")
        raise

def save_transcription(content, original_file, output_format="txt", output_path=None):
    """Save transcription to file"""
    if output_path:
        output_file = output_path
    else:
        base_name = os.path.splitext(os.path.basename(original_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{base_name}_transcription_{timestamp}.{output_format}"
        output_file = os.path.join(os.path.dirname(original_file), output_file)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ Saved transcription to: {output_file}")
    return output_file

def test_connection(whisper_url):
    """Test connection to Whisper service"""
    print(f"🔌 Testing connection to {whisper_url}...")
    try:
        response = requests.get(f"{whisper_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Connection successful!")
            return True
        else:
            print(f"❌ Service returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Transcribe video/audio files using Whisper ASR')
    parser.add_argument('input_file', nargs='?', help='Path to the video or audio file')
    parser.add_argument('-o', '--output', help='Output file path (optional)')
    parser.add_argument('-f', '--format', choices=['txt', 'srt', 'vtt', 'json', 'tsv'], 
                       default='txt', help='Output format (default: txt)')
    parser.add_argument('-u', '--url', default='http://localhost:9000', 
                       help='Whisper service URL (default: http://localhost:9000)')
    parser.add_argument('--test', action='store_true', help='Test connection to Whisper service')
    parser.add_argument('--keep-audio', action='store_true', 
                       help='Keep extracted audio file (for video inputs)')
    
    # Speaker diarization options
    parser.add_argument('--diarize', action='store_true', 
                       help='Enable speaker diarization (identify different speakers)')
    parser.add_argument('--min-speakers', type=int, metavar='N',
                       help='Minimum number of speakers expected')
    parser.add_argument('--max-speakers', type=int, metavar='N',
                       help='Maximum number of speakers expected')
    
    args = parser.parse_args()
    
    # Validate speaker parameters
    if args.min_speakers is not None and args.min_speakers < 1:
        parser.error("--min-speakers must be at least 1")
    if args.max_speakers is not None and args.max_speakers < 1:
        parser.error("--max-speakers must be at least 1")
    if (args.min_speakers is not None and args.max_speakers is not None and 
        args.min_speakers > args.max_speakers):
        parser.error("--min-speakers cannot be greater than --max-speakers")
    
    # Test connection if requested
    if args.test:
        test_connection(args.url)
        return
    
    # Check if input file is provided for non-test mode
    if not args.input_file:
        parser.error("input_file is required unless using --test")
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"❌ Error: File not found: {args.input_file}")
        sys.exit(1)
    
    # Test connection first
    if not test_connection(args.url):
        print("\n⚠️  Warning: Could not connect to Whisper service!")
        print(f"Make sure the service is running at {args.url}")
        print("\nTo start Whisper service:")
        print("docker run -d -p 9000:9000 --name whisper onerahmet/openai-whisper-asr-webservice:latest")
        sys.exit(1)
    
    temp_audio_file = None
    
    try:
        # Check if it's a video file
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        is_video = any(args.input_file.lower().endswith(ext) for ext in video_extensions)
        
        if is_video:
            # Extract audio first
            temp_audio_file = extract_audio(args.input_file)
            audio_file = temp_audio_file
        else:
            audio_file = args.input_file
        
        # Transcribe with diarization options
        result = transcribe_audio(audio_file, args.url, args.format, 
                                diarize=args.diarize,
                                min_speakers=args.min_speakers,
                                max_speakers=args.max_speakers)
        
        # Save result
        output_path = save_transcription(result, args.input_file, args.format, args.output)
        
        # Show preview
        print("\n📄 Preview of transcription:")
        print("-" * 60)
        preview = result[:500] + "..." if len(result) > 500 else result
        print(preview)
        print("-" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Transcription cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
    finally:
        # Clean up temporary file
        if temp_audio_file and os.path.exists(temp_audio_file) and not args.keep_audio:
            os.unlink(temp_audio_file)
            print("\n🧹 Cleaned up temporary audio file")

if __name__ == "__main__":
    main()