import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from pypdf import PdfWriter, PdfReader
import re
import os

class DnDApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

class PDFTool(DnDApp):
    def __init__(self):
        super().__init__()
        self.title("PDF Splice and Slice")
        self.geometry("700x850")
        ctk.set_appearance_mode("dark")
        
        self.merge_list = []
        self.selected_split_file = None
        self.ghost_window = None 

        # --- DYNAMIC SCALING CONFIGURATION ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) 

        self.header = ctk.CTkLabel(self, text="PDF Splice and Slice", font=("Arial", 26, "bold"), text_color="#3498db")
        self.header.grid(row=0, column=0, pady=20)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Renamed Tabs
        self.tabview.add("Merge PDFs")
        self.tabview.add("Split a PDF")

        self.setup_merge_tab()
        self.setup_split_tab()

    def setup_merge_tab(self):
        tab = self.tabview.tab("Merge PDFs")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1) 

        self.add_btn = ctk.CTkButton(tab, text="+ Select Files to Merge", command=self.browse_merge_files, 
                                     fg_color="#34495e", hover_color="#2c3e50")
        self.add_btn.grid(row=0, column=0, pady=15)

        self.hint = ctk.CTkLabel(tab, text="Drag items UP or DOWN to change order.", text_color="gray")
        self.hint.grid(row=1, column=0)

        self.scroll_frame = ctk.CTkScrollableFrame(tab, border_width=2, border_color="#333")
        self.scroll_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        
        self.scroll_frame.drop_target_register(DND_FILES)
        self.scroll_frame.dnd_bind('<<Drop>>', self.handle_file_drop)

        self.final_merge_btn = ctk.CTkButton(tab, text="Merge and Save PDF", command=self.execute_merge, 
                                             fg_color="#27ae60", height=45, font=("Arial", 14, "bold"))
        self.final_merge_btn.grid(row=3, column=0, pady=20)

    def setup_split_tab(self):
        tab = self.tabview.tab("Split a PDF")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1) 

        self.split_sel_btn = ctk.CTkButton(tab, text="Select PDF to Split", command=self.load_split_file)
        self.split_sel_btn.grid(row=0, column=0, pady=20)
        
        self.split_info = ctk.CTkLabel(tab, text="No file selected", text_color="gray")
        self.split_info.grid(row=1, column=0)

        # Added Instructions for the Range
        instruction_text = (
            "Enter ranges below (one per line or separated by commas).\n"
            "Example: 1-5, 8-12, 15-20\n"
            "This will create 3 separate PDFs with those page ranges."
        )
        self.range_instruct = ctk.CTkLabel(tab, text=instruction_text, text_color="#abb2bf", font=("Arial", 11), justify="left")
        self.range_instruct.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")

        self.range_box = ctk.CTkTextbox(tab, border_width=2)
        self.range_box.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.range_box.insert("0.0", "1-5\n6-10")

        self.execute_split_btn = ctk.CTkButton(tab, text="Execute Split", command=self.execute_split, 
                                               fg_color="#27ae60", state="disabled", height=40)
        self.execute_split_btn.grid(row=4, column=0, pady=20)

    # --- CORE LOGIC ---
    def browse_merge_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if files:
            for f in files: self.merge_list.append(f)
            self.refresh_merge_list()

    def handle_file_drop(self, event):
        files = self.scroll_frame.tk.splitlist(event.data)
        for f in files:
            if f.lower().endswith(".pdf"): self.merge_list.append(f)
        self.refresh_merge_list()

    def refresh_merge_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        for i, path in enumerate(self.merge_list):
            item = ctk.CTkFrame(self.scroll_frame, fg_color="#2b2b2b", corner_radius=6)
            item.pack(fill="x", pady=4, padx=5)
            
            handle = ctk.CTkLabel(item, text=" ☰ ", text_color="#555", cursor="fleur")
            handle.pack(side="left", padx=5)

            lbl = ctk.CTkLabel(item, text=f"{os.path.basename(path)}", anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=5)

            del_btn = ctk.CTkButton(item, text="✕", width=30, height=25, fg_color="transparent", 
                                    hover_color="#e74c3c", command=lambda p=path: self.remove_file(p))
            del_btn.pack(side="right", padx=10)

            for w in [item, handle, lbl]:
                w.bind("<ButtonPress-1>", lambda e, idx=i, p=path: self.start_drag(e, idx, p))
                w.bind("<B1-Motion>", lambda e, idx=i: self.on_drag(e, idx))
                w.bind("<ButtonRelease-1>", lambda e: self.stop_drag(e))

    def start_drag(self, event, index, path):
        if self.ghost_window: self.ghost_window.destroy()
        self.ghost_window = ctk.CTkToplevel(self)
        self.ghost_window.overrideredirect(True)
        self.ghost_window.attributes("-alpha", 0.7)
        self.ghost_window.attributes("-topmost", True)
        g_lbl = ctk.CTkLabel(self.ghost_window, text=f" Moving: {os.path.basename(path)} ", 
                             fg_color="#3498db", text_color="white", corner_radius=5)
        g_lbl.pack()
        self.update_ghost_pos(event)

    def on_drag(self, event, index):
        if self.ghost_window: self.update_ghost_pos(event)
        y = event.y_root - self.scroll_frame.winfo_rooty()
        new_index = max(0, min(len(self.merge_list) - 1, int(y // 48)))
        if new_index != index:
            self.merge_list[index], self.merge_list[new_index] = self.merge_list[new_index], self.merge_list[index]
            self.refresh_merge_list()

    def stop_drag(self, event):
        if self.ghost_window:
            self.ghost_window.destroy()
            self.ghost_window = None

    def update_ghost_pos(self, event):
        if self.ghost_window:
            self.ghost_window.geometry(f"+{event.x_root + 20}+{event.y_root + 10}")

    def remove_file(self, path):
        self.merge_list.remove(path)
        self.refresh_merge_list()

    def execute_merge(self):
        if not self.merge_list: return
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if save_path:
            merger = PdfWriter()
            for pdf in self.merge_list: merger.append(pdf)
            merger.write(save_path)
            merger.close()
            messagebox.showinfo("Success", "Merged!")

    def load_split_file(self):
        self.selected_split_file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if self.selected_split_file:
            reader = PdfReader(self.selected_split_file)
            self.split_info.configure(text=f"Total Pages: {len(reader.pages)}", text_color="white")
            self.execute_split_btn.configure(state="normal")

    def execute_split(self):
        raw = self.range_box.get("0.0", "end").strip()
        out_f = filedialog.askdirectory()
        if not out_f or not raw: return
        try:
            reader = PdfReader(self.selected_split_file)
            ranges = re.findall(r"(\d+)\s*-\s*(\d+)", raw)
            for idx, (s, e) in enumerate(ranges):
                writer = PdfWriter()
                for p in range(int(s)-1, int(e)): writer.add_page(reader.pages[p])
                writer.write(os.path.join(out_f, f"Split_Part_{idx+1}.pdf"))
            messagebox.showinfo("Done", "Split complete.")
        except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = PDFTool()
    app.mainloop()