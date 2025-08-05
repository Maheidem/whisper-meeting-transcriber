#!/usr/bin/env python3
"""
Whisper Meeting Transcriber
A GUI application to transcribe meeting videos using Whisper ASR Docker service
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import json
import threading
import os
from datetime import datetime
import time
import subprocess
import tempfile

class WhisperTranscriber:
    def __init__(self, root):
        self.root = root
        self.root.title("Whisper Meeting Transcriber")
        self.root.geometry("700x600")
        self.root.configure(bg='#f0f0f0')
        
        # Variables
        self.file_path = tk.StringVar()
        self.output_format = tk.StringVar(value="txt")
        self.whisper_url = tk.StringVar(value="http://localhost:9000")
        self.is_processing = False
        self.stop_requested = False  # Flag to stop processing
        self.temp_audio_file = None
        self.current_request = None  # Track current HTTP request
        self.ffmpeg_process = None   # Track FFmpeg process
        
        # Speaker diarization variables
        self.diarize = tk.BooleanVar(value=False)
        self.min_speakers = tk.StringVar(value="")
        self.max_speakers = tk.StringVar(value="")
        
        self.setup_ui()
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        # Main frame
        main_frame = tk.Frame(self.root, bg='#f0f0f0', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Whisper Meeting Transcriber", 
                              font=('Arial', 18, 'bold'), bg='#f0f0f0')
        title_label.pack(pady=(0, 20))
        
        # Whisper URL
        url_frame = tk.Frame(main_frame, bg='#f0f0f0')
        url_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(url_frame, text="Whisper URL:", bg='#f0f0f0', width=15, anchor='w').pack(side=tk.LEFT)
        url_entry = tk.Entry(url_frame, textvariable=self.whisper_url, width=40)
        url_entry.pack(side=tk.LEFT, padx=5)
        
        # File selection
        file_frame = tk.Frame(main_frame, bg='#f0f0f0')
        file_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(file_frame, text="Select Video:", bg='#f0f0f0', width=15, anchor='w').pack(side=tk.LEFT)
        self.file_label = tk.Label(file_frame, text="No file selected", fg="gray", bg='#f0f0f0', 
                                  relief=tk.SUNKEN, width=35, anchor='w')
        self.file_label.pack(side=tk.LEFT, padx=5)
        tk.Button(file_frame, text="Browse", command=self.select_file, 
                 bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=5)
        
        # Output format
        format_frame = tk.Frame(main_frame, bg='#f0f0f0')
        format_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(format_frame, text="Output Format:", bg='#f0f0f0', width=15, anchor='w').pack(side=tk.LEFT)
        
        formats = [("Plain Text", "txt"), ("SubRip (SRT)", "srt"), 
                   ("WebVTT", "vtt"), ("JSON", "json"), ("TSV", "tsv")]
        
        for text, value in formats:
            tk.Radiobutton(format_frame, text=text, variable=self.output_format, 
                          value=value, bg='#f0f0f0').pack(side=tk.LEFT, padx=5)
        
        # Speaker diarization frame
        diarize_frame = tk.Frame(main_frame, bg='#f0f0f0')
        diarize_frame.pack(fill=tk.X, pady=10)
        
        # Diarization checkbox
        self.diarize_check = tk.Checkbutton(diarize_frame, text="Enable Speaker Diarization", 
                                           variable=self.diarize, bg='#f0f0f0',
                                           command=self.toggle_diarization)
        self.diarize_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # Min speakers
        tk.Label(diarize_frame, text="Min Speakers:", bg='#f0f0f0').pack(side=tk.LEFT, padx=(0, 5))
        self.min_speakers_entry = tk.Entry(diarize_frame, textvariable=self.min_speakers, 
                                          width=5, state='disabled')
        self.min_speakers_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Max speakers
        tk.Label(diarize_frame, text="Max Speakers:", bg='#f0f0f0').pack(side=tk.LEFT, padx=(0, 5))
        self.max_speakers_entry = tk.Entry(diarize_frame, textvariable=self.max_speakers, 
                                          width=5, state='disabled')
        self.max_speakers_entry.pack(side=tk.LEFT)
        
        # Progress bar frame
        progress_frame = tk.Frame(main_frame, bg='#f0f0f0')
        progress_frame.pack(fill=tk.X, pady=10)
        
        # Use ttk.Progressbar instead of Canvas for better compatibility
        from tkinter import ttk
        
        # Configure style for the progress bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("green.Horizontal.TProgressbar", 
                       background='#4CAF50',
                       troughcolor='#e0e0e0',
                       bordercolor='#cccccc',
                       lightcolor='#4CAF50',
                       darkcolor='#4CAF50')
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', 
                                           length=400, mode='determinate',
                                           maximum=100, 
                                           style="green.Horizontal.TProgressbar")
        self.progress_bar.pack(pady=5)
        
        # Progress text
        self.progress_text = tk.Label(progress_frame, text="", bg='#f0f0f0', font=('Arial', 9))
        self.progress_text.pack()
        
        # Status label
        self.status_label = tk.Label(main_frame, text="Ready to transcribe", fg="green", 
                                    bg='#f0f0f0', font=('Arial', 10))
        self.status_label.pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(pady=10)
        
        self.transcribe_btn = tk.Button(button_frame, text="Transcribe", 
                                       command=self.start_transcription, state="disabled",
                                       bg='#2196F3', fg='white', font=('Arial', 12, 'bold'),
                                       padx=20, pady=5)
        self.transcribe_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(button_frame, text="Stop", 
                                 command=self.stop_transcription, state="disabled",
                                 bg='#f44336', fg='white', font=('Arial', 12),
                                 padx=20, pady=5)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Test Connection", command=self.test_connection,
                 bg='#FF9800', fg='white', padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Results text area
        tk.Label(main_frame, text="Transcription Result:", bg='#f0f0f0', 
                font=('Arial', 12, 'bold')).pack(anchor='w', pady=(20, 5))
        
        # Text area with scrollbar
        text_frame = tk.Frame(main_frame, bg='#f0f0f0')
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.result_text = tk.Text(text_frame, wrap=tk.WORD, height=10, width=70)
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Save button
        self.save_btn = tk.Button(main_frame, text="Save Transcription", 
                                 command=self.save_transcription, state="disabled",
                                 bg='#4CAF50', fg='white', padx=20, pady=5)
        self.save_btn.pack(pady=10)
    
    def on_closing(self):
        """Handle application closing - cleanup resources"""
        if self.is_processing:
            if messagebox.askokcancel("Quit", "Transcription is in progress. Do you want to stop it and quit?"):
                self.cleanup_processes()
                self.root.destroy()
        else:
            self.cleanup_processes()
            self.root.destroy()
    
    def cleanup_processes(self):
        """Clean up any running processes"""
        # Stop FFmpeg process if running
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            print("Terminating FFmpeg process...")
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
        
        # Cancel HTTP request if possible
        # Note: requests doesn't support true cancellation, but we can try to close the connection
        if self.current_request:
            print("Attempting to cancel HTTP request...")
            # This is a best-effort attempt
            try:
                self.current_request.close()
            except:
                pass
        
        # Try to stop Whisper container processes
        if self.is_processing and self.stop_requested:
            # Only restart container if explicitly stopping (not on window close)
            try:
                print("Checking Whisper container CPU usage...")
                # Check if Whisper is actually processing (high CPU)
                result = subprocess.run(['docker', 'stats', '--no-stream', '--format', 
                                       '"{{.Container}}\t{{.CPUPerc}}"', 'whisper'], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout.strip().strip('"')
                    if output:
                        parts = output.split('\t')
                        if len(parts) >= 2:
                            cpu_percent = parts[1].rstrip('%')
                            try:
                                cpu_val = float(cpu_percent)
                                if cpu_val > 10.0:  # If CPU usage is high
                                    print(f"Whisper using {cpu_percent}% CPU - restarting container...")
                                    
                                    # Quick restart
                                    subprocess.run(['docker', 'restart', '-t', '2', 'whisper'], 
                                                 capture_output=True)
                                    print("Whisper container restarted")
                                    
                                    # Wait for service to be ready
                                    time.sleep(3)
                                else:
                                    print(f"Whisper CPU usage is low ({cpu_percent}%) - no restart needed")
                            except ValueError:
                                pass
            except Exception as e:
                print(f"Could not check/restart Whisper: {e}")
        
        # Clean up temporary files
        if self.temp_audio_file and os.path.exists(self.temp_audio_file):
            try:
                os.unlink(self.temp_audio_file)
                print(f"Cleaned up temporary file: {self.temp_audio_file}")
            except:
                pass
        
    def select_file(self):
        filename = filedialog.askopenfilename(
            title="Select Meeting Video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.webm"),
                ("Audio files", "*.mp3 *.wav *.m4a *.flac"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            self.file_path.set(filename)
            self.file_label.config(text=os.path.basename(filename), fg="black")
            self.transcribe_btn.config(state="normal")
            
            # Check file size
            file_size = os.path.getsize(filename) / (1024 * 1024)  # Convert to MB
            if file_size > 100:
                self.status_label.config(
                    text=f"Large file ({file_size:.1f} MB) - will extract audio first", 
                    fg="orange"
                )
            else:
                self.status_label.config(text="File selected, ready to transcribe", fg="green")
            
    def test_connection(self):
        try:
            response = requests.get(f"{self.whisper_url.get()}/docs", timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("Success", "Connected to Whisper service successfully!")
                self.status_label.config(text="Connection successful", fg="green")
            else:
                messagebox.showerror("Error", f"Service returned status code: {response.status_code}")
                self.status_label.config(text="Connection failed", fg="red")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Connection Error", 
                               f"Could not connect to Whisper service.\n\nError: {str(e)}")
            self.status_label.config(text="Connection failed", fg="red")
    
    def toggle_diarization(self):
        """Enable/disable speaker count fields based on diarization checkbox"""
        if self.diarize.get():
            self.min_speakers_entry.config(state='normal')
            self.max_speakers_entry.config(state='normal')
        else:
            self.min_speakers_entry.config(state='disabled')
            self.max_speakers_entry.config(state='disabled')
            self.min_speakers.set("")
            self.max_speakers.set("")
    
    def update_progress(self, percentage, text=""):
        """Update the progress bar and text"""
        # Update progress bar value
        self.progress_bar['value'] = percentage
        
        # Update progress text
        if text:
            self.progress_text.config(text=text)
        else:
            self.progress_text.config(text=f"{percentage}%")
            
        # Force GUI update to show changes immediately
        self.root.update_idletasks()
            
    def extract_audio(self, input_file):
        """Extract audio from video file to WAV format"""
        self.status_label.config(text="Extracting audio from video...", fg="blue")
        self.root.after(0, self.update_progress, 0, "Starting audio extraction...")
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()
        self.temp_audio_file = temp_file.name
        
        try:
            # Get video duration first
            probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 
                        'format=duration', '-of', 'json', input_file]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            
            duration = None
            if probe_result.returncode == 0:
                import json
                probe_data = json.loads(probe_result.stdout)
                duration = float(probe_data.get('format', {}).get('duration', 0))
            
            # Use ffmpeg to extract audio with progress
            cmd = [
                'ffmpeg', '-i', input_file,
                '-vn',  # No video
                '-ac', '1',  # Mono
                '-ar', '16000',  # 16kHz sample rate
                '-f', 'wav',
                '-y',  # Overwrite
                '-progress', 'pipe:1',  # Progress to stdout
                self.temp_audio_file
            ]
            
            # Run ffmpeg with progress monitoring
            self.ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                                  universal_newlines=True)
            process = self.ffmpeg_process  # Keep local reference for convenience
            
            current_time = 0
            for line in process.stdout:
                # Check if stop was requested
                if self.stop_requested:
                    process.terminate()
                    raise Exception("Extraction stopped by user")
                    
                if line.startswith('out_time_ms='):
                    # Extract time in microseconds
                    time_ms = int(line.split('=')[1]) / 1000000
                    if duration and duration > 0:
                        progress = min(int((time_ms / duration) * 100), 99)
                        self.root.after(0, self.update_progress, progress, f"Extracting audio: {progress}%")
            
            process.wait()
            
            if process.returncode != 0:
                error = process.stderr.read()
                raise Exception(f"FFmpeg error: {error}")
            
            self.root.after(0, self.update_progress, 100, "Audio extraction complete")
            return self.temp_audio_file
            
        except Exception as e:
            if os.path.exists(self.temp_audio_file):
                os.unlink(self.temp_audio_file)
            raise e
            
    def start_transcription(self):
        if self.is_processing:
            messagebox.showwarning("Processing", "Transcription already in progress!")
            return
            
        if not self.file_path.get():
            messagebox.showerror("Error", "Please select a file first!")
            return
        
        # Validate speaker parameters if diarization is enabled
        if self.diarize.get():
            error_msg = []
            
            # Validate min_speakers
            if self.min_speakers.get():
                try:
                    min_val = int(self.min_speakers.get())
                    if min_val < 1:
                        error_msg.append("Minimum speakers must be at least 1")
                except ValueError:
                    error_msg.append("Minimum speakers must be a number")
            
            # Validate max_speakers
            if self.max_speakers.get():
                try:
                    max_val = int(self.max_speakers.get())
                    if max_val < 1:
                        error_msg.append("Maximum speakers must be at least 1")
                except ValueError:
                    error_msg.append("Maximum speakers must be a number")
            
            # Check min <= max
            if self.min_speakers.get() and self.max_speakers.get():
                try:
                    min_val = int(self.min_speakers.get())
                    max_val = int(self.max_speakers.get())
                    if min_val > max_val:
                        error_msg.append("Minimum speakers cannot be greater than maximum speakers")
                except ValueError:
                    pass
            
            if error_msg:
                messagebox.showerror("Validation Error", "\n".join(error_msg))
                return
            
        # Reset stop flag
        self.stop_requested = False
        
        # Start transcription in a separate thread
        thread = threading.Thread(target=self.transcribe)
        thread.daemon = True
        thread.start()
    
    def stop_transcription(self):
        """Stop the current transcription process"""
        if not self.is_processing:
            return
            
        self.stop_requested = True
        self.status_label.config(text="Stopping transcription...", fg="orange")
        
        # Clean up processes
        self.cleanup_processes()
        
        # Reset UI
        self.root.after(0, self.update_progress, 0, "Transcription stopped")
        self.transcribe_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.is_processing = False
        
    def transcribe(self):
        self.is_processing = True
        self.transcribe_btn.config(state="disabled")
        self.stop_btn.config(state="normal")  # Enable stop button
        self.save_btn.config(state="disabled")
        self.result_text.delete(1.0, tk.END)
        
        # Reset progress
        self.root.after(0, self.update_progress, 0, "")
        
        audio_file_to_transcribe = self.file_path.get()
        
        try:
            # Check if file is a video format
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
            if any(audio_file_to_transcribe.lower().endswith(ext) for ext in video_extensions):
                # Extract audio first
                audio_file_to_transcribe = self.extract_audio(audio_file_to_transcribe)
                self.status_label.config(text="Audio extracted, starting transcription...", fg="blue")
            
            # Prepare the request
            url = f"{self.whisper_url.get()}/asr"
            
            # Get file info
            file_size = os.path.getsize(audio_file_to_transcribe)
            file_name = os.path.basename(audio_file_to_transcribe)
            print(f"Transcribing: {file_name}, Size: {file_size:,} bytes")
            
            # Prepare for streaming upload with progress
            file_size = os.path.getsize(audio_file_to_transcribe)
            
            self.root.after(0, self.update_progress, 5, "Uploading audio to server...")
            
            with open(audio_file_to_transcribe, 'rb') as file:
                # Read file content for progress tracking
                file_content = file.read()
                file.seek(0)
                
                files = {'audio_file': file}
                
                # Build query parameters
                params = {}
                if self.output_format.get() != 'txt':
                    params['output'] = self.output_format.get()
                
                # Add diarization parameters if enabled
                if self.diarize.get():
                    params['diarize'] = 'true'
                    
                    # Validate and add min_speakers
                    if self.min_speakers.get():
                        try:
                            min_val = int(self.min_speakers.get())
                            if min_val > 0:
                                params['min_speakers'] = str(min_val)
                        except ValueError:
                            pass
                    
                    # Validate and add max_speakers
                    if self.max_speakers.get():
                        try:
                            max_val = int(self.max_speakers.get())
                            if max_val > 0:
                                params['max_speakers'] = str(max_val)
                        except ValueError:
                            pass
                
                # Make the request
                start_time = time.time()
                self.root.after(0, self.update_progress, 10, "Processing transcription...")
                
                # Simulate progress during transcription
                # Note: Actual progress tracking would require server-side support
                response = None
                
                def make_request():
                    nonlocal response
                    # Use session for better control
                    session = requests.Session()
                    self.current_request = session
                    try:
                        response = session.post(url, files=files, params=params, timeout=3600)
                    finally:
                        session.close()
                        self.current_request = None
                
                # Run request in thread so we can update progress
                request_thread = threading.Thread(target=make_request)
                request_thread.start()
                
                # Update progress while waiting
                progress = 10
                while request_thread.is_alive():
                    # Check if stop was requested
                    if self.stop_requested:
                        # Try to stop the request
                        if self.current_request:
                            try:
                                self.current_request.close()
                            except:
                                pass
                        raise Exception("Transcription stopped by user")
                    
                    time.sleep(0.5)
                    if progress < 90:
                        progress += 2
                        # Use after to update GUI from main thread
                        self.root.after(0, self.update_progress, progress, f"Transcribing... {progress}%")
                
                request_thread.join()
                elapsed_time = time.time() - start_time
                
                self.root.after(0, self.update_progress, 95, "Finalizing transcription...")
                
            if response.status_code == 200:
                # Handle different output formats
                if self.output_format.get() == 'json':
                    result = json.dumps(response.json(), indent=2)
                else:
                    result = response.text
                
                self.root.after(0, self.update_progress, 100, "Transcription complete!")
                self.result_text.insert(1.0, result)
                self.status_label.config(
                    text=f"Transcription completed in {elapsed_time:.1f} seconds", 
                    fg="green"
                )
                self.save_btn.config(state="normal")
                
                # Auto-save option
                self.auto_save(result)
                
            else:
                self.root.after(0, self.update_progress, 0, "Error occurred")
                error_msg = f"Error: {response.status_code}\n{response.text}"
                self.result_text.insert(1.0, error_msg)
                self.status_label.config(text="Transcription failed", fg="red")
                messagebox.showerror("Transcription Error", error_msg)
                
        except subprocess.CalledProcessError as e:
            self.root.after(0, self.update_progress, 0, "Error: FFmpeg not found")
            error_msg = "FFmpeg not found. Please install FFmpeg to transcribe video files."
            self.result_text.insert(1.0, error_msg)
            self.status_label.config(text="FFmpeg required", fg="red")
            messagebox.showerror("FFmpeg Error", error_msg)
            
        except requests.exceptions.Timeout:
            self.root.after(0, self.update_progress, 0, "Error: Timeout")
            error_msg = "Request timed out. The file might be too large or the server is busy."
            self.result_text.insert(1.0, error_msg)
            self.status_label.config(text="Timeout error", fg="red")
            messagebox.showerror("Timeout Error", error_msg)
            
        except Exception as e:
            self.root.after(0, self.update_progress, 0, "Error occurred")
            error_msg = f"Error: {str(e)}"
            self.result_text.insert(1.0, error_msg)
            self.status_label.config(text="Transcription failed", fg="red")
            messagebox.showerror("Error", error_msg)
            
        finally:
            # Clean up temporary file
            if self.temp_audio_file and os.path.exists(self.temp_audio_file):
                try:
                    os.unlink(self.temp_audio_file)
                except:
                    pass
                self.temp_audio_file = None
                
            self.is_processing = False
            self.stop_requested = False
            self.transcribe_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.ffmpeg_process = None
            self.current_request = None
            
    def auto_save(self, content):
        """Automatically save transcription with timestamp"""
        try:
            base_name = os.path.splitext(os.path.basename(self.file_path.get()))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{base_name}_transcription_{timestamp}.{self.output_format.get()}"
            
            # Save in the same directory as the video
            output_path = os.path.join(os.path.dirname(self.file_path.get()), output_file)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.status_label.config(
                text=f"Saved to: {output_file}", 
                fg="green"
            )
        except Exception as e:
            print(f"Auto-save failed: {e}")
            
    def save_transcription(self):
        content = self.result_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "No transcription to save!")
            return
            
        default_name = os.path.splitext(os.path.basename(self.file_path.get()))[0]
        
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{self.output_format.get()}",
            initialfile=f"{default_name}_transcription",
            filetypes=[
                (f"{self.output_format.get().upper()} files", f"*.{self.output_format.get()}"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Transcription saved to:\n{filename}")
                self.status_label.config(text="Transcription saved", fg="green")
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save file:\n{str(e)}")

def main():
    root = tk.Tk()
    app = WhisperTranscriber(root)
    root.mainloop()

if __name__ == "__main__":
    main()