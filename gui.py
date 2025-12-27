import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import urllib.request
import re
import os
import threading
from PIL import Image, ImageTk
from io import BytesIO

# Set theme and color
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ChanMediaScanner(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("4Chan Media Hub")
        self.geometry("900x600")
        
        # Configure layout (2 columns: Sidebar, Main Content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # State
        self.download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads")
        if not os.path.exists(self.download_path):
            try:
                os.makedirs(self.download_path)
            except:
                self.download_path = os.getcwd()

        self.url_cache = {}  # URL -> list of media links
        self.current_media = []
        self.current_page = 0
        self.items_per_page = 5
        self.placeholder_img = None
        
        # UI Setup
        self.create_sidebar()
        self.create_media_frame()
        self.create_settings_frame()

        # Start at Media Scanner
        self.select_frame("media")

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="4Chan Hub", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_media = ctk.CTkButton(self.sidebar_frame, text="Media Scanner", 
                                       command=lambda: self.select_frame("media"))
        self.btn_media.grid(row=1, column=0, padx=20, pady=10)

        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="Settings", 
                                          command=lambda: self.select_frame("settings"))
        self.btn_settings.grid(row=2, column=0, padx=20, pady=10)

    def create_media_frame(self):
        self.media_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.media_frame.grid_columnconfigure(0, weight=1)
        self.media_frame.grid_rowconfigure(2, weight=1) # Preview expands

        # Input Section
        self.input_frame = ctk.CTkFrame(self.media_frame, fg_color="transparent")
        self.input_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)  # Entry expands

        self.entry_url = ctk.CTkEntry(self.input_frame, placeholder_text="Enter 4Chan Thread URL...")
        self.entry_url.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="ew")
        self.entry_url.bind('<Return>', lambda event: self.start_scan())

        self.btn_scan = ctk.CTkButton(self.input_frame, text="Scan Media", width=120, command=self.start_scan)
        self.btn_scan.grid(row=0, column=1, padx=0, pady=0)

        # Status Label
        self.lbl_status = ctk.CTkLabel(self.media_frame, text="Ready to scan...", text_color="gray")
        self.lbl_status.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        # Preview Section (Scrollable Frame)
        self.preview_frame = ctk.CTkScrollableFrame(self.media_frame, label_text="Media Preview")
        self.preview_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.preview_frame.grid_columnconfigure(1, weight=1)

        # Pagination Controls
        self.controls_frame = ctk.CTkFrame(self.media_frame, fg_color="transparent")
        self.controls_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        
        self.btn_prev = ctk.CTkButton(self.controls_frame, text="<< Previous", width=100, command=self.prev_page, state="disabled")
        self.btn_prev.pack(side="left")
        
        self.lbl_page = ctk.CTkLabel(self.controls_frame, text="Page 1", text_color="gray")
        self.lbl_page.pack(side="left", padx=20, expand=True)

        self.btn_next = ctk.CTkButton(self.controls_frame, text="Next >>", width=100, command=self.next_page, state="disabled")
        self.btn_next.pack(side="right")

    def create_settings_frame(self):
        self.settings_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
        self.lbl_settings = ctk.CTkLabel(self.settings_frame, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_settings.pack(pady=20, padx=20, anchor="w")

        self.lbl_path = ctk.CTkLabel(self.settings_frame, text="Download Path:")
        self.lbl_path.pack(pady=(10, 5), padx=20, anchor="w")

        self.entry_path = ctk.CTkEntry(self.settings_frame, width=400)
        self.entry_path.insert(0, self.download_path)
        self.entry_path.pack(pady=5, padx=20, anchor="w")
        
        self.btn_browse = ctk.CTkButton(self.settings_frame, text="Browse Folder", command=self.choose_directory)
        self.btn_browse.pack(pady=10, padx=20, anchor="w")

    def select_frame(self, name):
        # Update button states
        self.btn_media.configure(fg_color=("gray75", "gray25") if name == "media" else "transparent")
        self.btn_settings.configure(fg_color=("gray75", "gray25") if name == "settings" else "transparent")

        # Show frame
        if name == "media":
            self.settings_frame.grid_forget()
            self.media_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.media_frame.grid_forget()
            self.settings_frame.grid(row=0, column=1, sticky="nsew")

    def choose_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.download_path = directory
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, directory)

    def start_scan(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a valid URL.")
            return

        self.lbl_status.configure(text="Scanning...", text_color="cyan")
        self.btn_scan.configure(state="disabled")
        
        # Reset View
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # Run in thread
        threading.Thread(target=self.perform_scan, args=(url,), daemon=True).start()

    def perform_scan(self, url):
        # Check Cache
        if url in self.url_cache:
            self.current_media = self.url_cache[url]
            cached = True
        else:
            cached = False
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    html_code = response.read().decode('utf-8', errors='ignore')

                media_pattern = re.compile(r'<div class="fileText"[^>]*>.*?<a\s+[^>]*href=["\'](.*?)["\']', re.IGNORECASE | re.DOTALL)
                matches = media_pattern.findall(html_code)
                
                # Normalize URLs
                full_urls = []
                for m in matches:
                    if m.startswith("//"):
                        full_urls.append("https:" + m)
                    elif m.startswith("http"):
                        full_urls.append(m)
                    else:
                        full_urls.append(m) # Backup, though unlikely on 4chan
                
                self.current_media = full_urls
                self.url_cache[url] = full_urls
            except Exception as e:
                self.after(0, lambda: self.show_error(str(e)))
                return

        self.after(0, lambda: self.scan_completed(cached))

    def show_error(self, msg):
        self.lbl_status.configure(text=f"Error: {msg}", text_color="red")
        self.btn_scan.configure(state="normal")
        messagebox.showerror("Error", msg)

    def scan_completed(self, cached):
        count = len(self.current_media)
        source = " (Cached)" if cached else ""
        self.lbl_status.configure(text=f"Found {count} media files{source}.", text_color="green")
        self.btn_scan.configure(state="normal")
        
        self.current_page = 0
        self.update_preview_page()

    def update_preview_page(self):
        # Clear existing
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.current_media[start_idx:end_idx]

        # Update controls
        self.lbl_page.configure(text=f"Page {self.current_page + 1}")
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(state="normal" if end_idx < len(self.current_media) else "disabled")

        if not page_items:
            ctk.CTkLabel(self.preview_frame, text="No media to display.").pack(pady=20)
            return

        # Load thumbnails for this page in a thread
        threading.Thread(target=self.load_thumbnails, args=(page_items,), daemon=True).start()

    def load_thumbnails(self, items):
        # We need to perform network I/O, so do it here, but update UI in main thread
        import time
        
        for index, url in enumerate(items):
            try:
                # Try to guess thumbnail URL (replace extension with s.jpg)
                # Typical: https://i.4cdn.org/wsg/1735... .webm -> ... s.jpg
                base, ext = os.path.splitext(url)
                thumb_url = base + "s.jpg"

                headers = {'User-Agent': 'Mozilla/5.0'}
                req = urllib.request.Request(thumb_url, headers=headers)
                
                with urllib.request.urlopen(req) as response:
                    data = response.read()
                
                img_data = BytesIO(data)
                pil_image = Image.open(img_data)
                
                # Resize specifically for preview (height ~150)
                pil_image.thumbnail((200, 200))
                
                ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)
                
                # Pass to UI
                self.after(0, lambda u=url, i=ctk_image, n=index: self.add_preview_item(u, i, n))
                
                # Small delay to keep UI responsive if many items (though 5 is small)
                time.sleep(0.05)

            except Exception as e:
                print(f"Failed to load thumb for {url}: {e}")
                self.after(0, lambda u=url: self.add_preview_item(u, None, -1))

    def add_preview_item(self, url, ctk_img, index):
        # Create a container for the item
        frame = ctk.CTkFrame(self.preview_frame)
        frame.pack(fill="x", pady=5, padx=5)
        
        # Image
        if ctk_img:
            lbl_img = ctk.CTkLabel(frame, text="", image=ctk_img)
            lbl_img.pack(side="left", padx=10, pady=5)
        else:
            lbl_img = ctk.CTkLabel(frame, text="[No Preview]", width=100, height=100, fg_color="gray20")
            lbl_img.pack(side="left", padx=10, pady=5)

        # Info & Details
        info_frame = ctk.CTkFrame(frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        filename = url.split('/')[-1]
        ctk.CTkLabel(info_frame, text=filename, font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=url, font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")

        # Actions (e.g. Download this specific one? User didn't ask but "preview" implies interaction)
        # User asked for "Download path" setting, implying global download. 
        # But showing a download button for individual items is nice UX.
        # I'll add a simple "Open" or "Download" button.
        btn_dl = ctk.CTkButton(info_frame, text="Download", height=24, width=80, 
                               command=lambda u=url: self.download_single(u))
        btn_dl.pack(anchor="w", pady=5)

    def download_single(self, url):
        threading.Thread(target=self._download_worker, args=(url,), daemon=True).start()

    def _download_worker(self, url):
        try:
            filename = url.split('/')[-1]
            path = os.path.join(self.download_path, filename)
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = response.read()
            
            with open(path, 'wb') as f:
                f.write(data)
                
            print(f"Downloaded {path}")
            # Optional: Notify user (toaster or log)
        except Exception as e:
            print(f"Download error: {e}")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_preview_page()

    def next_page(self):
        if (self.current_page + 1) * self.items_per_page < len(self.current_media):
            self.current_page += 1
            self.update_preview_page()

if __name__ == "__main__":
    app = ChanMediaScanner()
    app.mainloop()
