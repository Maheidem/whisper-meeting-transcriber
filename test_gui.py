#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk

# Test basic tkinter
root = tk.Tk()
root.title("Test Window")
root.geometry("400x300")
root.configure(bg='lightblue')

# Add a basic label with tk (not ttk)
label = tk.Label(root, text="Can you see this text?", bg='yellow', fg='black', font=('Arial', 20))
label.pack(pady=20)

# Add a basic button with tk (not ttk)
button = tk.Button(root, text="Click Me", bg='green', fg='white', command=lambda: print("Button clicked!"))
button.pack(pady=10)

# Try ttk widgets
ttk_label = ttk.Label(root, text="TTK Label Test")
ttk_label.pack(pady=10)

root.mainloop()