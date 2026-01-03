import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
from tkinter import messagebox
import sqlite3
import os

from ai_response import get_ai_response
from db_handler import DB_PATH
from db_handler import lookup_acronym
from db_handler import init_db

DB_PATH = os.path.join(os.path.dirname(__file__), "acronyms.db")
init_db()

def on_send(event=None):
 
    user_input = entry.get().strip()
    if not user_input:
        return
    chat_window.insert(tk.END, f"You: {user_input}\n")

    # get_ai_response now handles extraction, DB lookup, and LLM fallback
    response = get_ai_response(user_input)

    chat_window.insert(tk.END, f"Bot: {response}\n\n")

    entry.delete(0, tk.END)

def handleInput(self):
        try:
            user_input = self.inputBox.toPlainText().strip()

            if not user_input:
                self.resultLabel.setText("❗ Please enter a question or acronym.")
                return

            # Naive extraction of acronym: last word in sentence
            acronym = user_input.split()[-1].strip(" ?!.").upper()

            if not acronym.isalpha():
                self.resultLabel.setText("❗ That doesn't seem like a valid acronym.")
                return

            # Try to look up acronym in DB
            meaning = lookup_acronym(acronym)

            if meaning:
                self.resultLabel.setText(f"✅ {acronym}: {meaning}")
            else:
                # Use LLM to generate fallback response
                ai_reply = get_ai_response(f"What could '{acronym}' mean in a tech context?")
                self.resultLabel.setText(
                    f"🤔 I couldn't find '{acronym}' in my knowledge base.\n\nHere's my best guess:\n\n{ai_reply}"
                )

        except Exception as e:
            # Graceful error handling — shows error in message box
            messagebox.showerror("Unexpected Error", f"Something went wrong.\n\n{str(e)}")
    
#== Add to pending suggestion queue ===
def add_to_pending(acronym, meaning, teams, project, notes, additionalMeaning):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_acronyms (
                acronym TEXT PRIMARY KEY,
                meaning TEXT NOT NULL,
                teams TEXT,
                project TEXT,
                notes TEXT,
                additionalMeaning TEXT
            )
        """)
        cursor.execute("""
            INSERT OR REPLACE INTO pending_acronyms
            (acronym, meaning, teams, project, notes, additionalMeaning)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (acronym.upper(), meaning, teams, project, notes, additionalMeaning))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return f"Database Error: {e}"

# === Add suggestion window ===
def on_add():
    add_window = tk.Toplevel(root)
    add_window.title("Suggest Acronym")

    labels = ["Acronym", "Meaning", "Teams (comma-separated)", "Related Projects", "Notes", "Additional Meanings"]
    entries = []

    for i, label_text in enumerate(labels):
        tk.Label(add_window, text=label_text + ":").grid(row=i, column=0, padx=5, pady=5, sticky='e', background="#C8EAAC", foreground="#3C6E04")
        entry = tk.Entry(add_window, width=40, background="#C8EAAC", foreground="#3C6E04")
        entry.grid(row=i, column=1, padx=5, pady=5)
        entries.append(entry)

    def submit():
        acronym, primary, teams, project, notes, additionalMeaning = [e.get().strip() for e in entries]
        if acronym and primary:
            result = add_to_pending(acronym, primary, teams, project, notes, additionalMeaning)
            if result == True:
                chat_window.insert(tk.END, f"Suggestion submitted: '{acronym.upper()}' will be reviewed.\n\n")
            else:
                chat_window.insert(tk.END, f"Bot: {result}\n\n")
            add_window.destroy()
        else:
            chat_window.insert(tk.END, "Bot: Acronym and primary meaning are required.\n\n")

    tk.Button(add_window, text="Submit", command=submit).grid(row=len(labels), column=0, columnspan=2, pady=10)

# === GUI Setup ===
root = tk.Tk()
style = ttk.Style(root)
style.theme_use('alt')
try:
    style.theme_use('alt')   
except Exception:
    pass
style.configure('Accent.TButton',
                background="#9EE04D",
                foreground="#080E02",
                font=('Roboto', 11, 'bold'),
                padding=3,
                relief='flat')
style.map('Accent.TButton',
          background=[('active', "#C8EAAC")],
          foreground=[('active', "#3C6E04")])

root.title("DigiCat")
# add_button = ttk.Button(root, text="Add", command=on_add, style='Accent.TButton')
# add_button.pack(side=tk.LEFT, padx=10, pady=(0, 0))

chat_window = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=40, height=40, font=('Roboto', 12), background="#C8EAAC", foreground="#3C6E04")
chat_window.pack(padx=10, pady=10)

entry = ttk.Entry(root, width=30, font=('Roboto', 12), style='Accent.TButton', background="#C8EAAC", foreground="#3C6E04")
entry.pack(side=tk.LEFT, padx=(10, 0), pady=(0, 10))
entry.bind('<Return>', lambda e: on_send())

send_button = ttk.Button(root, text="Send", command=on_send, style='Accent.TButton')
send_button.pack(side=tk.LEFT, padx=(5, 5), pady=(0, 10))

root.mainloop()