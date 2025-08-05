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
        
        self.setup_ui()
        
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
        
        # Status label
        self.status_label = tk.Label(main_frame, text="Ready to transcribe", fg="green", 
                                    bg='#f0f0f0', font=('Arial', 10))
        self.status_label.pack(pady=10)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(pady=10)
        
        self.transcribe_btn = tk.Button(button_frame, text="Transcribe", 
                                       command=self.start_transcription, state="disabled",
                                       bg='#2196F3', fg='white', font=('Arial', 12, 'bold'),
                                       padx=20, pady=5)
        self.transcribe_btn.pack(side=tk.LEFT, padx=5)
        
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
            
    def start_transcription(self):
        if self.is_processing:
            messagebox.showwarning("Processing", "Transcription already in progress!")
            return
            
        if not self.file_path.get():
            messagebox.showerror("Error", "Please select a file first!")
            return
            
        # Start transcription in a separate thread
        thread = threading.Thread(target=self.transcribe)
        thread.daemon = True
        thread.start()
        
    def transcribe(self):
        self.is_processing = True
        self.transcribe_btn.config(state="disabled")
        self.save_btn.config(state="disabled")
        self.result_text.delete(1.0, tk.END)
        
        try:
            self.status_label.config(text="Uploading file and transcribing...", fg="blue")
            
            # Prepare the request
            url = f"{self.whisper_url.get()}/asr"
            
            # Get file info for debugging
            file_size = os.path.getsize(self.file_path.get())
            file_name = os.path.basename(self.file_path.get())
            print(f"File: {file_name}, Size: {file_size:,} bytes")
            
            with open(self.file_path.get(), 'rb') as file:
                # Use the exact format that works with curl
                files = {'audio_file': (file_name, file)}
                
                # Only send parameters if they're not default
                data = {}
                if self.output_format.get() != 'txt':
                    data['output'] = self.output_format.get()
                
                print(f"Request URL: {url}")
                print(f"Request data: {data}")
                
                # Make the request
                start_time = time.time()
                response = requests.post(url, files=files, data=data, timeout=3600)
                elapsed_time = time.time() - start_time
                
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                
            if response.status_code == 200:
                # Handle different output formats
                if self.output_format.get() == 'json':
                    result = json.dumps(response.json(), indent=2)
                else:
                    result = response.text
                    
                self.result_text.insert(1.0, result)
                self.status_label.config(
                    text=f"Transcription completed in {elapsed_time:.1f} seconds", 
                    fg="green"
                )
                self.save_btn.config(state="normal")
                
                # Auto-save option
                self.auto_save(result)
                
            else:
                error_msg = f"Error: {response.status_code}\n{response.text}"
                self.result_text.insert(1.0, error_msg)
                self.status_label.config(text="Transcription failed", fg="red")
                
                # More detailed error info
                print(f"Error response text: {response.text}")
                try:
                    error_json = response.json()
                    print(f"Error JSON: {json.dumps(error_json, indent=2)}")
                except:
                    pass
                    
                messagebox.showerror("Transcription Error", error_msg)
                
        except requests.exceptions.Timeout:
            error_msg = "Request timed out. The file might be too large or the server is busy."
            self.result_text.insert(1.0, error_msg)
            self.status_label.config(text="Timeout error", fg="red")
            messagebox.showerror("Timeout Error", error_msg)
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.result_text.insert(1.0, error_msg)
            self.status_label.config(text="Transcription failed", fg="red")
            messagebox.showerror("Error", error_msg)
            
        finally:
            self.is_processing = False
            self.transcribe_btn.config(state="normal")
            
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