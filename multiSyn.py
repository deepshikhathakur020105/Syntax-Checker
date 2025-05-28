from tkinter import *
from tkinter import ttk, filedialog, messagebox
import os
import re
import subprocess
import webbrowser

# Token type colors
TOKEN_TYPES = {
    'keyword': '#FF69B4',
    'identifier': '#FFFFFF',
    'number': '#90EE90',
    'string': '#FFFF00',
    'operator': '#9B30FF',
    'comment': '#808080',
    'bracket': '#00FFFF',
    'error': '#FF0000'
}

LANGUAGE_EXTENSIONS = {
    'C': 'c',
    'C++': 'cpp',
    'Python': 'py',
    'Java': 'java',
    'HTML': 'html'
}

SYNTAX_COMMANDS = {
    'C': lambda filename: subprocess.run(["gcc", "-fsyntax-only", filename], capture_output=True, text=True),
    'C++': lambda filename: subprocess.run(["g++", "-fsyntax-only", filename], capture_output=True, text=True),
    'Python': lambda filename: subprocess.run(["python", "-m", "py_compile", filename], capture_output=True, text=True),
    'Java': lambda filename: subprocess.run(["javac", filename], capture_output=True, text=True),
    'HTML': lambda filename: subprocess.CompletedProcess(args=[], returncode=0, stdout='', stderr='HTML is not compiled.')
}

# Keywords per language
LANGUAGE_KEYWORDS = {
    'C': ['auto','break','case','char','const','continue','default','do','double','else','enum','extern','float','for','goto','if','int','long','register','return','short','signed','sizeof','static','struct','switch','typedef','union','unsigned','void','volatile','while'],
    'C++': ['class','namespace','template','public','private','protected','virtual','friend','try','catch','throw','new','delete'],  # Will extend later below
    'Python': ['def','return','if','elif','else','for','while','import','from','as','class','try','except','finally','raise','with','pass','yield','lambda','global','nonlocal','assert','del','is','in','not','and','or','True','False','None'],
    'Java': ['class','public','static','void','main','String','new','return','if','else','while','for','int','float','double','char','boolean','try','catch','throw','throws','finally','package','import','this','super'],
    'HTML': ['<!DOCTYPE','<html','<head','<title','<body','<h1','<div','<span','<a','<p','<br','<hr','<input','<form','<table','<tr','<td','<th','<ul','<li','<ol','<script','<style']
}

# Add C keywords to C++ keywords (extend)
LANGUAGE_KEYWORDS['C++'].extend(LANGUAGE_KEYWORDS['C'])

# Dynamic token patterns
TOKEN_PATTERNS = lambda lang: {
    'comment': r'#.*|//.*|/\*[\s\S]*?\*/',
    'string': r'"(?:\\.|[^"\\])*?"|\'.*?\'',
    'keyword': r'\b(?:' + '|'.join(LANGUAGE_KEYWORDS[lang]) + r')\b',
    'number': r'\b\d+(\.\d+)?\b',
    'operator': r'==|!=|<=|>=|\+\+|--|&&|\|\||\+=|-=|=|/=|[%&|^!<>]=?|[+\-/%=]',
    'bracket': r'[\{\}\[\]\(\)]',
    'identifier': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
}

class SyntaxChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-language Syntax Checker")
        self.language = StringVar(value='C')
        self.current_theme = 'dark'

        self.setup_ui()

    def setup_ui(self):
        self.menu = Menu(self.root)
        self.root.config(menu=self.menu)

        file_menu = Menu(self.menu, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu.add_cascade(label="File", menu=file_menu)

        theme_menu = Menu(self.menu, tearoff=0)
        theme_menu.add_command(label="Toggle Theme", command=self.toggle_theme)
        self.menu.add_cascade(label="Theme", menu=theme_menu)

        ttk.Label(self.root, text="Select Language:", background='#2e2e2e', foreground='white').pack(anchor=W)
        OptionMenu(self.root, self.language, *LANGUAGE_EXTENSIONS.keys(), command=self.language_changed).pack(anchor=W)

        # Run button
        run_button = Button(self.root, text="Run", command=self.run_code, bg="green", fg="white")
        run_button.pack(anchor=W, padx=10, pady=5)

        self.text_area = Text(self.root, wrap=NONE, bg='#2e2e2e', fg='white', insertbackground='white')
        self.text_area.pack(fill=BOTH, expand=True)
        self.text_area.bind("<KeyRelease>", self.on_text_change)

        self.error_output = Text(self.root, height=8, bg='#1e1e1e', fg='red', state=DISABLED)
        self.error_output.pack(fill=X, side=BOTTOM)

    def get_token_patterns(self):
        return TOKEN_PATTERNS(self.language.get())

    def on_text_change(self, event=None):
        code = self.text_area.get("1.0", END)
        self.highlight_code(code)
        self.check_syntax(code)

    def highlight_code(self, code):
        for tag in TOKEN_TYPES:
            self.text_area.tag_remove(tag, "1.0", END)

        patterns = self.get_token_patterns()
        for token_type, pattern in patterns.items():
            for match in re.finditer(pattern, code, re.MULTILINE):
                start, end = match.span()
                start_index = self.get_index(start)
                end_index = self.get_index(end)
                self.text_area.tag_add(token_type, start_index, end_index)
                self.text_area.tag_configure(token_type, foreground=TOKEN_TYPES[token_type])

    def get_index(self, index):
        return self.text_area.index(f"1.0+{index}c")

    def check_syntax(self, code):
        filename = f"temp.{LANGUAGE_EXTENSIONS[self.language.get()]}"
        with open(filename, 'w') as f:
            f.write(code)
        result = SYNTAX_COMMANDS[self.language.get()](filename)
        self.display_errors(result.stderr)

    def display_errors(self, errors):
        self.error_output.config(state=NORMAL)
        self.error_output.delete("1.0", END)
        self.error_output.insert(END, errors)
        self.error_output.config(state=DISABLED)

    def open_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            with open(file_path, 'r') as file:
                code = file.read()
                self.text_area.delete("1.0", END)
                self.text_area.insert(END, code)
            self.on_text_change()

    def save_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=f".{LANGUAGE_EXTENSIONS[self.language.get()]}")
        if file_path:
            with open(file_path, 'w') as file:
                file.write(self.text_area.get("1.0", END))

    def toggle_theme(self):
        if self.current_theme == 'dark':
            self.text_area.config(bg='white', fg='black', insertbackground='black')
            self.error_output.config(bg='lightgray', fg='black')
            self.current_theme = 'light'
        else:
            self.text_area.config(bg='#2e2e2e', fg='white', insertbackground='white')
            self.error_output.config(bg='#1e1e1e', fg='red')
            self.current_theme = 'dark'

    def language_changed(self, lang):
        self.on_text_change()

    def run_code(self):
        code = self.text_area.get("1.0", END)
        lang = self.language.get()
        ext = LANGUAGE_EXTENSIONS[lang]
        filename = f"temp_run.{ext}"
        with open(filename, "w") as f:
            f.write(code)

        try:
            if lang == "Python":
                result = subprocess.run(["python", filename], capture_output=True, text=True)
            elif lang == "C":
                exe = "a.out"
                subprocess.run(["gcc", filename, "-o", exe], check=True)
                result = subprocess.run([f"./{exe}"], capture_output=True, text=True)
            elif lang == "C++":
                exe = "a.out"
                subprocess.run(["g++", filename, "-o", exe], check=True)
                result = subprocess.run([f"./{exe}"], capture_output=True, text=True)
            elif lang == "Java":
                subprocess.run(["javac", filename], check=True)
                class_name = os.path.splitext(os.path.basename(filename))[0]
                result = subprocess.run(["java", class_name], capture_output=True, text=True)
            elif lang == "HTML":
                webbrowser.open(f"file://{os.path.abspath(filename)}")
                self.display_errors("Opened in browser.")
                return
            else:
                self.display_errors("Run not supported for this language.")
                return

            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            self.display_errors(output)
        except subprocess.CalledProcessError as e:
            self.display_errors(e.stderr if hasattr(e, 'stderr') else str(e))
        except Exception as e:
            self.display_errors(str(e))


if __name__ == "__main__":
    root = Tk()
    root.geometry("1000x700")
    app = SyntaxChecker(root)
    root.mainloop()
