#!/usr/bin/env python3
"""Test progress bar visibility"""

import tkinter as tk
import time

class TestProgressBar:
    def __init__(self, root):
        self.root = root
        self.root.title("Progress Bar Test")
        self.root.geometry("500x300")
        
        # Create main frame
        main_frame = tk.Frame(root, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Method 1: Canvas progress bar (like in the app)
        tk.Label(main_frame, text="Canvas Progress Bar:", font=('Arial', 12)).pack(pady=5)
        
        canvas_container = tk.Frame(main_frame, bg='gray', relief=tk.SOLID, borderwidth=2)
        canvas_container.pack(fill=tk.X, pady=5)
        
        self.canvas_bar = tk.Canvas(canvas_container, height=25, bg='lightgray', highlightthickness=0)
        self.canvas_bar.pack(fill=tk.X, padx=2, pady=2)
        
        # Method 2: ttk.Progressbar
        tk.Label(main_frame, text="TTK Progress Bar:", font=('Arial', 12)).pack(pady=(20, 5))
        
        from tkinter import ttk
        self.ttk_bar = ttk.Progressbar(main_frame, length=400, mode='determinate')
        self.ttk_bar.pack(pady=5)
        
        # Progress text
        self.progress_text = tk.Label(main_frame, text="0%", font=('Arial', 10))
        self.progress_text.pack(pady=5)
        
        # Test button
        tk.Button(main_frame, text="Test Progress", command=self.test_progress, 
                 bg='blue', fg='white', padx=20, pady=10).pack(pady=20)
        
    def update_canvas_progress(self, percentage):
        """Update canvas progress bar"""
        self.canvas_bar.delete("all")
        
        # Get canvas dimensions
        self.canvas_bar.update_idletasks()
        width = self.canvas_bar.winfo_width()
        height = self.canvas_bar.winfo_height()
        
        print(f"Canvas dimensions: {width}x{height}")
        
        if width > 1 and percentage > 0:
            fill_width = int((width - 4) * percentage / 100)
            # Draw the green progress bar
            self.canvas_bar.create_rectangle(2, 2, fill_width + 2, height - 2, 
                                           fill='#4CAF50', outline='#4CAF50')
            # Draw percentage text on the bar
            self.canvas_bar.create_text(width // 2, height // 2, 
                                      text=f"{percentage}%", 
                                      font=('Arial', 10, 'bold'))
        
        # Update ttk bar too
        self.ttk_bar['value'] = percentage
        
        # Update text
        self.progress_text.config(text=f"Progress: {percentage}%")
        
        # Force update
        self.root.update()
        
    def test_progress(self):
        """Simulate progress"""
        for i in range(0, 101, 5):
            self.update_canvas_progress(i)
            time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = TestProgressBar(root)
    root.mainloop()