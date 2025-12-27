import tkinter as tk
from tkinter import messagebox
import urllib.request
import re

class ChanMediaScanner(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("4Chan Media Scanner")
        self.geometry("500x250")
        self.configure(bg="#f0f0f0")

        self.create_widgets()

    def create_widgets(self):
        # Instruction Label
        lbl_instruction = tk.Label(self, text="Enter 4Chan Thread URL:", font=("Arial", 12), bg="#f0f0f0")
        lbl_instruction.pack(pady=(20, 5))

        # URL Entry
        self.entry_url = tk.Entry(self, width=60, font=("Arial", 10))
        self.entry_url.pack(pady=5, padx=20)
        # Bind Enter key to scan function
        self.entry_url.bind('<Return>', lambda event: self.scan_media())

        # Scan Button
        btn_scan = tk.Button(self, text="Scan Media", command=self.scan_media, 
                             bg="#007bff", fg="white", font=("Arial", 11, "bold"),
                             padx=20, pady=5, relief=tk.FLAT)
        btn_scan.pack(pady=15)

        # Result Label
        self.lbl_result = tk.Label(self, text="Ready to scan...", font=("Arial", 12, "bold"), bg="#f0f0f0", fg="#333333")
        self.lbl_result.pack(pady=10)

    def scan_media(self):
        url = self.entry_url.get().strip()
        
        if not url:
            messagebox.showwarning("Input Error", "Please enter a valid URL.")
            return

        self.lbl_result.config(text="Scanning...", fg="blue")
        self.update()

        try:
            # 4chan checks User-Agent, so we mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html_code = response.read().decode('utf-8', errors='ignore')

            # The user wants to count media inside <div class="fileText">
            # Pattern matches: <div class="fileText" ... > ... <a href="(url)" ... >
            # We specifically look for the href inside that div structure
            media_pattern = re.compile(r'<div class="fileText"[^>]*>.*?<a\s+[^>]*href=["\'](.*?)["\']', re.IGNORECASE | re.DOTALL)
            
            matches = media_pattern.findall(html_code)
            count = len(matches)

            self.lbl_result.config(text=f"Total Media Found: {count}", fg="green")
            
        except Exception as e:
            self.lbl_result.config(text="Error occurred", fg="red")
            messagebox.showerror("Connection Error", f"Could not scan URL.\nError: {str(e)}")

if __name__ == "__main__":
    app = ChanMediaScanner()
    app.mainloop()
