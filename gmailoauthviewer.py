#!/usr/bin/env python3
"""
Gmail Client — Full-Featured GUI using Captured OAuth Token
- Read, send, reply, forward, delete, mark read/unread
- Label management, attachment download, search
- Auto token refresh, professional dark theme
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import requests
import json
import base64
import os
import re
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from email.header import decode_header


# ==================== COLOR THEME ====================
class Theme:
    BG = "#0b0f1a"
    BG_CARD = "#131a2b"
    BG_INPUT = "#0e1420"
    BG_HOVER = "#1a2540"
    BORDER = "#1f2a44"
    ACCENT = "#4f8cff"
    ACCENT_DIM = "#1e3a5f"
    ACCENT_HOVER = "#6ba1ff"
    SUCCESS = "#22c55e"
    DANGER = "#ef4444"
    DANGER_HOVER = "#f87171"
    WARNING = "#f59e0b"
    PURPLE = "#a855f7"
    TEXT = "#f1f5f9"
    TEXT_SEC = "#94a3b8"
    TEXT_DIM = "#64748b"
    UNREAD = "#1e293b"


class GmailClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Gmail Client — Token Access")
        self.root.geometry("1400x900")
        self.root.configure(bg=Theme.BG)
        self.root.minsize(1000, 600)

        # ── State ──
        self.access_token = ""
        self.refresh_token = ""
        self.client_id = ""
        self.client_secret = ""
        self.emails = []
        self.current_email = None
        self.current_folder = "INBOX"
        self.labels = []
        self.attachments = []

        self._build_ui()
        self._set_status("Ready — enter your token and click Connect")

    # ==================== UI BUILD ====================
    def _build_ui(self):
        # ============ TOP TOOLBAR ============
        toolbar = tk.Frame(self.root, bg=Theme.BG_CARD, height=60)
        toolbar.pack(fill='x', side='top')
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="✉ Gmail Client", font=('Segoe UI', 16, 'bold'),
                 fg=Theme.ACCENT, bg=Theme.BG_CARD).pack(side='left', padx=(20, 15))

        # Token inputs
        tk.Label(toolbar, text="Access Token:", font=('Segoe UI', 9),
                 fg=Theme.TEXT_SEC, bg=Theme.BG_CARD).pack(side='left', padx=(10, 3))
        self.token_entry = tk.Entry(toolbar, width=35, bg=Theme.BG_INPUT, fg=Theme.TEXT,
                                    font=('Consolas', 9), bd=0, highlightthickness=1,
                                    highlightbackground=Theme.BORDER, insertbackground=Theme.ACCENT)
        self.token_entry.pack(side='left', padx=3, ipady=5)

        tk.Label(toolbar, text="Refresh:", font=('Segoe UI', 9),
                 fg=Theme.TEXT_SEC, bg=Theme.BG_CARD).pack(side='left', padx=(8, 3))
        self.refresh_entry = tk.Entry(toolbar, width=25, bg=Theme.BG_INPUT, fg=Theme.TEXT,
                                      font=('Consolas', 9), bd=0, highlightthickness=1,
                                      highlightbackground=Theme.BORDER, insertbackground=Theme.ACCENT)
        self.refresh_entry.pack(side='left', padx=3, ipady=5)

        self.connect_btn = tk.Button(toolbar, text="Connect", command=self._connect,
                                     bg=Theme.ACCENT, fg='white', bd=0,
                                     font=('Segoe UI', 9, 'bold'), padx=15, pady=5,
                                     cursor='hand2', activebackground=Theme.ACCENT_HOVER)
        self.connect_btn.pack(side='left', padx=10)

        # Compose button (right side)
        self.compose_btn = tk.Button(toolbar, text="✏ Compose", command=self._compose_new,
                                     bg=Theme.SUCCESS, fg='white', bd=0,
                                     font=('Segoe UI', 9, 'bold'), padx=15, pady=5,
                                     cursor='hand2', state='disabled',
                                     activebackground='#4ade80')
        self.compose_btn.pack(side='right', padx=(0, 20))

        self.refresh_btn = tk.Button(toolbar, text="⟳ Refresh", command=self._refresh_inbox,
                                     bg=Theme.PURPLE, fg='white', bd=0,
                                     font=('Segoe UI', 9, 'bold'), padx=15, pady=5,
                                     cursor='hand2', state='disabled',
                                     activebackground='#c084fc')
        self.refresh_btn.pack(side='right', padx=5)

        # ============ MAIN LAYOUT ============
        main = tk.Frame(self.root, bg=Theme.BG)
        main.pack(fill='both', expand=True)

        # ============ SIDEBAR (FOLDERS) ============
        sidebar = tk.Frame(main, bg=Theme.BG_CARD, width=200)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="FOLDERS", font=('Segoe UI', 9, 'bold'),
                 fg=Theme.TEXT_DIM, bg=Theme.BG_CARD).pack(anchor='w', padx=15, pady=(15, 5))

        self.folder_buttons = {}
        folders = [
            ("📥 Inbox", "INBOX"),
            ("⭐ Starred", "STARRED"),
            ("📤 Sent", "SENT"),
            ("📝 Drafts", "DRAFT"),
            ("🗑 Trash", "TRASH"),
            ("🚫 Spam", "SPAM"),
            ("📁 All Mail", ""),
        ]

        for label, folder_id in folders:
            btn = tk.Button(sidebar, text=label, anchor='w', bd=0,
                           bg=Theme.BG_CARD, fg=Theme.TEXT_SEC,
                           font=('Segoe UI', 10), padx=15, pady=8,
                           cursor='hand2', activebackground=Theme.BG_HOVER,
                           activeforeground=Theme.TEXT,
                           command=lambda f=folder_id: self._switch_folder(f))
            btn.pack(fill='x')
            self.folder_buttons[folder_id] = btn

        # Highlight Inbox
        self.folder_buttons["INBOX"].config(bg=Theme.BG_HOVER, fg=Theme.ACCENT)

        # Labels section
        tk.Label(sidebar, text="LABELS", font=('Segoe UI', 9, 'bold'),
                 fg=Theme.TEXT_DIM, bg=Theme.BG_CARD).pack(anchor='w', padx=15, pady=(20, 5))

        self.label_frame = tk.Frame(sidebar, bg=Theme.BG_CARD)
        self.label_frame.pack(fill='x')

        # ============ EMAIL LIST ============
        list_frame = tk.Frame(main, bg=Theme.BG_CARD, width=380)
        list_frame.pack(side='left', fill='y')
        list_frame.pack_propagate(False)

        # Search bar
        search_frame = tk.Frame(list_frame, bg=Theme.BG_CARD)
        search_frame.pack(fill='x', padx=10, pady=10)

        self.search_entry = tk.Entry(search_frame, bg=Theme.BG_INPUT, fg=Theme.TEXT,
                                     font=('Segoe UI', 10), bd=0, highlightthickness=1,
                                     highlightbackground=Theme.BORDER, insertbackground=Theme.ACCENT)
        self.search_entry.pack(side='left', fill='x', expand=True, ipady=6)
        self.search_entry.bind('<Return>', lambda e: self._search())

        tk.Button(search_frame, text="🔍", command=self._search,
                  bg=Theme.ACCENT_DIM, fg=Theme.TEXT, bd=0, padx=10,
                  cursor='hand2', activebackground=Theme.ACCENT).pack(side='left', padx=(5, 0))

        # Email count
        self.count_label = tk.Label(list_frame, text="0 emails", font=('Segoe UI', 8),
                                    fg=Theme.TEXT_DIM, bg=Theme.BG_CARD, anchor='w')
        self.count_label.pack(fill='x', padx=15, pady=(0, 5))

        # Scrollable list
        list_container = tk.Frame(list_frame, bg=Theme.BG_CARD)
        list_container.pack(fill='both', expand=True, padx=5, pady=(0, 5))

        self.list_canvas = tk.Canvas(list_container, bg=Theme.BG_CARD, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient='vertical',
                                 command=self.list_canvas.yview, bg=Theme.BG_CARD,
                                 troughcolor=Theme.BG_INPUT, bd=0, width=6)
        self.email_list_frame = tk.Frame(self.list_canvas, bg=Theme.BG_CARD)

        self.email_list_frame.bind(
            "<Configure>",
            lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))
        )
        self.list_canvas.create_window((0, 0), window=self.email_list_frame, anchor='nw')
        self.list_canvas.configure(yscrollcommand=scrollbar.set)
        self.list_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # ============ EMAIL VIEWER ============
        viewer = tk.Frame(main, bg=Theme.BG_CARD)
        viewer.pack(side='right', fill='both', expand=True)

        # Viewer toolbar
        viewer_toolbar = tk.Frame(viewer, bg=Theme.BG_CARD, height=45)
        viewer_toolbar.pack(fill='x')
        viewer_toolbar.pack_propagate(False)

        self.action_buttons = {}
        actions = [
            ("↩ Reply", self._reply_email, Theme.ACCENT),
            ("↪ Forward", self._forward_email, Theme.PURPLE),
            ("⭐ Star", self._star_email, Theme.WARNING),
            ("📩 Unread", self._toggle_unread, Theme.TEXT_SEC),
            ("🗑 Delete", self._delete_email, Theme.DANGER),
        ]

        for label, cmd, color in actions:
            btn = tk.Button(viewer_toolbar, text=label, command=cmd,
                           bg=Theme.BG_INPUT, fg=color, bd=0,
                           font=('Segoe UI', 9, 'bold'), padx=12, pady=5,
                           cursor='hand2', state='disabled',
                           activebackground=Theme.BG_HOVER)
            btn.pack(side='left', padx=3, pady=8)
            self.action_buttons[label] = btn

        # Email header
        header_frame = tk.Frame(viewer, bg=Theme.BG_CARD)
        header_frame.pack(fill='x', padx=20, pady=(15, 0))

        self.subject_label = tk.Label(header_frame, text="Select an email to read",
                                      font=('Segoe UI', 16, 'bold'),
                                      fg=Theme.TEXT, bg=Theme.BG_CARD,
                                      anchor='w', justify='left', wraplength=700)
        self.subject_label.pack(fill='x')

        self.meta_label = tk.Label(header_frame, text="",
                                   font=('Segoe UI', 9), fg=Theme.TEXT_SEC,
                                   bg=Theme.BG_CARD, anchor='w', justify='left')
        self.meta_label.pack(fill='x', pady=(5, 0))

        # Attachments bar
        self.attach_frame = tk.Frame(viewer, bg=Theme.BG_CARD)
        self.attach_frame.pack(fill='x', padx=20, pady=(5, 0))

        # Email body
        self.body_text = scrolledtext.ScrolledText(viewer, bg=Theme.BG_INPUT,
                                                   fg=Theme.TEXT, font=('Segoe UI', 10),
                                                   bd=0, highlightthickness=0, wrap='word',
                                                   insertbackground=Theme.ACCENT,
                                                   padx=20, pady=15)
        self.body_text.pack(fill='both', expand=True, padx=20, pady=(10, 20))

        # ============ STATUS BAR ============
        self.status_bar = tk.Label(self.root, text="",
                                   font=('Segoe UI', 9), fg=Theme.TEXT_DIM,
                                   bg=Theme.BG_CARD, anchor='w', padx=15, pady=5)
        self.status_bar.pack(fill='x', side='bottom')

    # ==================== HELPERS ====================
    def _set_status(self, msg, color=Theme.TEXT_DIM):
        self.status_bar.config(text=msg, fg=color)

    def _enable_actions(self, enabled=True):
        state = 'normal' if enabled else 'disabled'
        for btn in self.action_buttons.values():
            btn.config(state=state)

    # ==================== TOKEN HANDLING ====================
    def _connect(self):
        token = self.token_entry.get().strip()
        refresh = self.refresh_entry.get().strip()

        if not token and not refresh:
            messagebox.showwarning("Missing Token", "Enter an access token or refresh token.")
            return

        self.access_token = token
        self.refresh_token = refresh

        self._set_status("Connecting...", Theme.WARNING)
        self.connect_btn.config(state='disabled', text='Connecting...')

        threading.Thread(target=self._initial_load, daemon=True).start()

    def _initial_load(self):
        """Load labels and inbox on first connect"""
        self._load_labels()
        self._load_folder("INBOX")
        self.root.after(0, lambda: self.compose_btn.config(state='normal'))
        self.root.after(0, lambda: self.refresh_btn.config(state='normal'))
        self.root.after(0, lambda: self.connect_btn.config(state='normal', text='Connect'))

    def _refresh_access_token(self):
        if not self.refresh_token:
            return False
        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        try:
            r = requests.post(url, data=data, timeout=10)
            if r.status_code == 200:
                new_token = r.json().get("access_token")
                if new_token:
                    self.access_token = new_token
                    self.root.after(0, lambda: (self.token_entry.delete(0, 'end'),
                                                self.token_entry.insert(0, new_token)))
                    return True
        except Exception:
            pass
        return False

    def _api_get(self, url):
        """GET request with auto-refresh on 401"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 401 and self._refresh_access_token():
            headers = {"Authorization": f"Bearer {self.access_token}"}
            r = requests.get(url, headers=headers, timeout=15)
        return r

    def _api_post(self, url, data=None, json_data=None):
        """POST request with auto-refresh on 401"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if json_data is not None:
            headers["Content-Type"] = "application/json"
            r = requests.post(url, headers=headers, json=json_data, timeout=15)
        else:
            r = requests.post(url, headers=headers, data=data, timeout=15)
        if r.status_code == 401 and self._refresh_access_token():
            headers = {"Authorization": f"Bearer {self.access_token}"}
            if json_data is not None:
                headers["Content-Type"] = "application/json"
                r = requests.post(url, headers=headers, json=json_data, timeout=15)
            else:
                r = requests.post(url, headers=headers, data=data, timeout=15)
        return r

    # ==================== LABELS ====================
    def _load_labels(self):
        r = self._api_get("https://gmail.googleapis.com/gmail/v1/users/me/labels")
        if r.status_code != 200:
            return
        data = r.json()
        self.labels = [l for l in data.get("labels", [])
                       if l.get("type") == "user"]
        self.root.after(0, self._render_labels)

    def _render_labels(self):
        for widget in self.label_frame.winfo_children():
            widget.destroy()
        for label in self.labels[:8]:
            btn = tk.Button(self.label_frame, text=f"🏷 {label['name']}",
                           anchor='w', bd=0, bg=Theme.BG_CARD, fg=Theme.TEXT_SEC,
                           font=('Segoe UI', 9), padx=15, pady=5, cursor='hand2',
                           activebackground=Theme.BG_HOVER,
                           command=lambda l=label['id']: self._load_folder(l))
            btn.pack(fill='x')

    # ==================== FOLDERS ====================
    def _switch_folder(self, folder_id):
        for fid, btn in self.folder_buttons.items():
            btn.config(bg=Theme.BG_CARD, fg=Theme.TEXT_SEC)
        self.folder_buttons[folder_id].config(bg=Theme.BG_HOVER, fg=Theme.ACCENT)
        self.current_folder = folder_id
        self._set_status(f"Loading {folder_id or 'All Mail'}...", Theme.WARNING)
        threading.Thread(target=self._load_folder, args=(folder_id,), daemon=True).start()

    def _load_folder(self, folder_id):
        label_ids = [folder_id] if folder_id else []
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=30"
        if label_ids:
            url += f"&labelIds={label_ids[0]}"
        r = self._api_get(url)
        if r.status_code != 200:
            self.root.after(0, lambda: self._set_status(f"Error {r.status_code}", Theme.DANGER))
            return
        messages = r.json().get("messages", [])
        self.emails = []
        for msg in messages:
            detail = self._get_message_meta(msg["id"])
            if detail:
                self.emails.append(detail)
        self.root.after(0, self._populate_list)
        self.root.after(0, lambda: self._set_status(f"Loaded {len(self.emails)} emails", Theme.SUCCESS))

    def _refresh_inbox(self):
        self._set_status("Refreshing...", Theme.WARNING)
        threading.Thread(target=self._load_folder, args=(self.current_folder,), daemon=True).start()

    # ==================== MESSAGE METADATA ====================
    def _get_message_meta(self, msg_id):
        url = (f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
               f"?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Date")
        r = self._api_get(url)
        if r.status_code != 200:
            return None
        data = r.json()
        headers = data.get("payload", {}).get("headers", [])
        meta = {h["name"]: h["value"] for h in headers}
        labels = data.get("labelIds", [])
        return {
            "id": msg_id,
            "from": meta.get("From", "Unknown"),
            "to": meta.get("To", ""),
            "subject": meta.get("Subject", "(no subject)"),
            "date": meta.get("Date", ""),
            "snippet": data.get("snippet", ""),
            "unread": "UNREAD" in labels,
            "starred": "STARRED" in labels,
            "labels": labels,
            "thread_id": data.get("threadId", "")
        }

    # ==================== EMAIL LIST RENDER ====================
    def _populate_list(self):
        for widget in self.email_list_frame.winfo_children():
            widget.destroy()

        self.count_label.config(text=f"{len(self.emails)} emails")

        if not self.emails:
            tk.Label(self.email_list_frame, text="No emails found",
                     font=('Segoe UI', 10), fg=Theme.TEXT_DIM,
                     bg=Theme.BG_CARD).pack(pady=30)
            return

        for em in self.emails:
            self._create_email_row(em)

    def _create_email_row(self, em):
        bg = Theme.UNREAD if em["unread"] else Theme.BG_INPUT
        row = tk.Frame(self.email_list_frame, bg=bg, cursor='hand2')
        row.pack(fill='x', pady=1, padx=2)

        inner = tk.Frame(row, bg=bg, padx=12, pady=8)
        inner.pack(fill='x')

        top = tk.Frame(inner, bg=bg)
        top.pack(fill='x')

        sender = em["from"].split("<")[0].strip() or em["from"]
        sender_lbl = tk.Label(top, text=sender[:28], font=('Segoe UI', 10, 'bold'),
                              fg=Theme.TEXT, bg=bg, anchor='w')
        sender_lbl.pack(side='left')

        date_lbl = tk.Label(top, text=em["date"][:16], font=('Segoe UI', 7),
                            fg=Theme.TEXT_DIM, bg=bg, anchor='e')
        date_lbl.pack(side='right')

        subj_lbl = tk.Label(inner, text=em["subject"][:45], font=('Segoe UI', 9),
                            fg=Theme.TEXT_SEC, bg=bg, anchor='w')
        subj_lbl.pack(fill='x')

        snip_lbl = tk.Label(inner, text=em["snippet"][:50], font=('Segoe UI', 8),
                            fg=Theme.TEXT_DIM, bg=bg, anchor='w')
        snip_lbl.pack(fill='x')

        widgets = [row, inner, top, sender_lbl, date_lbl, subj_lbl, snip_lbl]
        for w in widgets:
            w.bind("<Button-1>", lambda e, d=em: self._open_email(d))

        def on_enter(e):
            for w in widgets:
                w.config(bg=Theme.BG_HOVER)
        def on_leave(e):
            for w in widgets:
                w.config(bg=bg)

        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)

    # ==================== EMAIL READING ====================
    def _open_email(self, em):
        self.current_email = em
        self.subject_label.config(text=em["subject"])
        self.meta_label.config(
            text=f"From: {em['from']}\nTo: {em['to']}\nDate: {em['date']}"
        )
        self.body_text.delete('1.0', 'end')
        self.body_text.insert('1.0', "Loading...")
        self._enable_actions(True)

        for widget in self.attach_frame.winfo_children():
            widget.destroy()

        threading.Thread(target=self._load_full_message, args=(em["id"],), daemon=True).start()

        # Mark as read
        if em["unread"]:
            threading.Thread(target=self._mark_read, args=(em["id"],), daemon=True).start()

    def _load_full_message(self, msg_id):
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full"
        r = self._api_get(url)
        if r.status_code != 200:
            self.root.after(0, lambda: self._display_body("Failed to load message.", []))
            return
        data = r.json()
        payload = data.get("payload", {})
        body, attachments = self._extract_body_and_attachments(payload)
        self.root.after(0, lambda: self._display_body(body, attachments))

    def _extract_body_and_attachments(self, payload, attachments=None):
        if attachments is None:
            attachments = []

        mime = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data", "")
        filename = payload.get("filename", "")

        # Attachment
        if filename and body_data:
            attachments.append({
                "filename": filename,
                "mimeType": mime,
                "data": body_data,
                "size": payload.get("body", {}).get("size", 0)
            })

        # Body
        if mime == "text/plain" and body_data:
            try:
                return base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore'), attachments
            except Exception:
                pass
        if mime == "text/html" and body_data:
            try:
                html = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                text = re.sub(r'<[^>]+>', '', html)
                text = re.sub(r'\s+', ' ', text).strip()
                return text, attachments
            except Exception:
                pass

        for part in payload.get("parts", []):
            result, attachments = self._extract_body_and_attachments(part, attachments)
            if result:
                return result, attachments
        return "", attachments

    def _display_body(self, body, attachments):
        self.body_text.delete('1.0', 'end')
        self.body_text.insert('1.0', body if body else "(no content)")

        # Render attachment buttons
        for att in attachments:
            btn = tk.Button(self.attach_frame,
                           text=f"📎 {att['filename']} ({att['size']//1024}KB)",
                           bg=Theme.PURPLE, fg='white', bd=0,
                           font=('Segoe UI', 8, 'bold'), padx=10, pady=3,
                           cursor='hand2',
                           command=lambda a=att: self._download_attachment(a))
            btn.pack(side='left', padx=3)

    def _download_attachment(self, att):
        filename = filedialog.asksaveasfilename(initialfile=att["filename"])
        if not filename:
            return
        try:
            data = base64.urlsafe_b64decode(att["data"])
            with open(filename, 'wb') as f:
                f.write(data)
            messagebox.showinfo("Success", f"Downloaded: {att['filename']}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download: {e}")

    # ==================== ACTIONS ====================
    def _mark_read(self, msg_id):
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/modify"
        self._api_post(url, json_data={"removeLabelIds": ["UNREAD"]})
        self.root.after(0, self._refresh_inbox)

    def _toggle_unread(self):
        if not self.current_email:
            return
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{self.current_email['id']}/modify"
        if self.current_email["unread"]:
            self._api_post(url, json_data={"removeLabelIds": ["UNREAD"]})
        else:
            self._api_post(url, json_data={"addLabelIds": ["UNREAD"]})
        self._set_status("Toggled unread", Theme.SUCCESS)
        self._refresh_inbox()

    def _star_email(self):
        if not self.current_email:
            return
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{self.current_email['id']}/modify"
        if self.current_email["starred"]:
            self._api_post(url, json_data={"removeLabelIds": ["STARRED"]})
            self._set_status("Unstarred", Theme.SUCCESS)
        else:
            self._api_post(url, json_data={"addLabelIds": ["STARRED"]})
            self._set_status("Starred", Theme.SUCCESS)
        self._refresh_inbox()

    def _delete_email(self):
        if not self.current_email:
            return
        if not messagebox.askyesno("Delete", "Move this email to Trash?"):
            return
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{self.current_email['id']}/trash"
        self._api_post(url)
        self._set_status("Moved to Trash", Theme.SUCCESS)
        self.subject_label.config(text="Select an email to read")
        self.meta_label.config(text="")
        self.body_text.delete('1.0', 'end')
        self._refresh_inbox()

    # ==================== COMPOSE ====================
    def _compose_new(self):
        self._open_compose_window()

    def _reply_email(self):
        if not self.current_email:
            return
        to = self.current_email["from"]
        subject = f"Re: {self.current_email['subject']}"
        self._open_compose_window(to=to, subject=subject)

    def _forward_email(self):
        if not self.current_email:
            return
        subject = f"Fwd: {self.current_email['subject']}"
        body = self.body_text.get('1.0', 'end-1c')
        self._open_compose_window(subject=subject, body=f"\n\n---------- Forwarded ----------\n{body}")

    def _open_compose_window(self, to="", subject="", body=""):
        win = tk.Toplevel(self.root)
        win.title("Compose Email")
        win.geometry("700x600")
        win.configure(bg=Theme.BG_CARD)

        tk.Label(win, text="To:", font=('Segoe UI', 10), fg=Theme.TEXT,
                 bg=Theme.BG_CARD).pack(anchor='w', padx=20, pady=(15, 2))
        to_entry = tk.Entry(win, bg=Theme.BG_INPUT, fg=Theme.TEXT,
                            font=('Segoe UI', 10), bd=0, highlightthickness=1,
                            highlightbackground=Theme.BORDER, insertbackground=Theme.ACCENT)
        to_entry.pack(fill='x', padx=20, ipady=6)
        to_entry.insert(0, to)

        tk.Label(win, text="Subject:", font=('Segoe UI', 10), fg=Theme.TEXT,
                 bg=Theme.BG_CARD).pack(anchor='w', padx=20, pady=(10, 2))
        subj_entry = tk.Entry(win, bg=Theme.BG_INPUT, fg=Theme.TEXT,
                              font=('Segoe UI', 10), bd=0, highlightthickness=1,
                              highlightbackground=Theme.BORDER, insertbackground=Theme.ACCENT)
        subj_entry.pack(fill='x', padx=20, ipady=6)
        subj_entry.insert(0, subject)

        tk.Label(win, text="Message:", font=('Segoe UI', 10), fg=Theme.TEXT,
                 bg=Theme.BG_CARD).pack(anchor='w', padx=20, pady=(10, 2))
        body_text = scrolledtext.ScrolledText(win, bg=Theme.BG_INPUT, fg=Theme.TEXT,
                                              font=('Segoe UI', 10), bd=0,
                                              highlightthickness=0, wrap='word',
                                              insertbackground=Theme.ACCENT)
        body_text.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        body_text.insert('1.0', body)

        def send():
            to_addr = to_entry.get().strip()
            subj = subj_entry.get().strip()
            msg_body = body_text.get('1.0', 'end-1c').strip()

            if not to_addr or not subj:
                messagebox.showwarning("Missing", "To and Subject are required.")
                return

            threading.Thread(target=self._send_email,
                             args=(to_addr, subj, msg_body, win),
                             daemon=True).start()

        btn_frame = tk.Frame(win, bg=Theme.BG_CARD)
        btn_frame.pack(fill='x', padx=20, pady=(0, 15))

        tk.Button(btn_frame, text="Send", command=send,
                  bg=Theme.SUCCESS, fg='white', bd=0,
                  font=('Segoe UI', 10, 'bold'), padx=25, pady=8,
                  cursor='hand2').pack(side='right')

    def _send_email(self, to, subject, body, window):
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            r = self._api_post(url, json_data={"raw": raw})

            if r.status_code in (200, 202):
                self.root.after(0, lambda: messagebox.showinfo("Sent", "Email sent successfully!"))
                self.root.after(0, window.destroy)
                self.root.after(0, lambda: self._set_status("Email sent", Theme.SUCCESS))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed: {r.text[:200]}"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

    # ==================== SEARCH ====================
    def _search(self):
        query = self.search_entry.get().strip()
        if not query:
            self._refresh_inbox()
            return
        self._set_status(f"Searching: {query}", Theme.WARNING)
        threading.Thread(target=self._do_search, args=(query,), daemon=True).start()

    def _do_search(self, query):
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={requests.utils.quote(query)}&maxResults=30"
        r = self._api_get(url)
        if r.status_code != 200:
            self.root.after(0, lambda: self._set_status(f"Search error {r.status_code}", Theme.DANGER))
            return
        messages = r.json().get("messages", [])
        self.emails = []
        for msg in messages:
            detail = self._get_message_meta(msg["id"])
            if detail:
                self.emails.append(detail)
        self.root.after(0, self._populate_list)
        self.root.after(0, lambda: self._set_status(f"Found {len(self.emails)} results", Theme.SUCCESS))


# ==================== MAIN ====================
def main():
    root = tk.Tk()
    app = GmailClient(root)
    root.mainloop()


if __name__ == "__main__":
    main()
