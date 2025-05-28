import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import subprocess
import os
import threading
import time

# --------------------
# Keywords by language
# --------------------
C_KEYWORDS = [
    'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do', 'double',
    'else', 'enum', 'extern', 'float', 'for', 'goto', 'if', 'int', 'long', 'register',
    'return', 'short', 'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef',
    'union', 'unsigned', 'void', 'volatile', 'while'
]

PYTHON_KEYWORDS = [
    'False', 'class', 'finally', 'is', 'return', 'None', 'continue', 'for', 'lambda',
    'try', 'True', 'def', 'from', 'nonlocal', 'while', 'and', 'del', 'global', 'not',
    'with', 'as', 'elif', 'if', 'or', 'yield', 'assert', 'else', 'import', 'pass',
    'break', 'except', 'in', 'raise'
]

# ----------------
# Syntax colors
# ----------------
SYNTAX_COLORS = {
    'keyword': '#569CD6',       # Blue
    'string': '#D69D85',        # Light red
    'comment': '#6A9955',       # Green
    'number': '#B5CEA8',        # Light green
    'error': '#FF0000',         # Red underline
}

# Supported languages for simplicity
LANGUAGES = {
    'C': {
        'keywords': C_KEYWORDS,
        'filetypes': [('C Files', '*.c')],
        'compile_cmd': lambda src, exe: ['gcc', src, '-o', exe],
        'run_cmd': lambda exe: [exe],
        'extension': '.c',
    },
    'Python': {
        'keywords': PYTHON_KEYWORDS,
        'filetypes': [('Python Files', '*.py')],
        'compile_cmd': None,
        'run_cmd': lambda src: ['python', src],
        'extension': '.py',
    }
}

AUTO_SAVE_INTERVAL = 60  # seconds

class CodeEditorTab:
    def __init__(self, parent, language='C', filename=None, content=''):
        self.language = language
        self.filename = filename
        self.frame = tk.Frame(parent)
        self.text = tk.Text(self.frame, undo=True, wrap='none', font=('Consolas', 12),
                            bg='#1e1e1e', fg='white', insertbackground='white', padx=5, pady=5)
        self.text.pack(fill='both', expand=True, side='right')

        # Line numbers canvas
        self.linenumbers = tk.Text(self.frame, width=5, padx=5, takefocus=0, border=0,
                                   background='#2c2f33', foreground='white', state='disabled',
                                   font=('Consolas', 12))
        self.linenumbers.pack(side='left', fill='y')

        self.text.bind('<KeyRelease>', self.on_key_release)
        self.text.bind('<ButtonRelease>', self.update_line_numbers)
        self.text.bind('<MouseWheel>', self.sync_scroll)
        self.text.bind('<FocusIn>', self.update_line_numbers)

        # Scroll sync
        self.text['yscrollcommand'] = self.on_textscroll
        self.linenumbers['yscrollcommand'] = self.on_linescroll

        self.autocomplete_listbox = None
        self.autocomplete_window = None

        self.error_lines = set()

        # Insert initial content if any
        self.text.insert(1.0, content)

        # Initial setup
        self.update_line_numbers()
        self.highlight_syntax()

    def on_textscroll(self, *args):
        self.linenumbers.yview(*args)
        self.text.yview(*args)

    def on_linescroll(self, *args):
        self.text.yview(*args)
        self.linenumbers.yview(*args)

    def sync_scroll(self, event):
        self.linenumbers.yview_moveto(self.text.yview()[0])
        return 'break'

    def update_line_numbers(self, event=None):
        self.linenumbers.config(state='normal')
        self.linenumbers.delete(1.0, 'end')
        line_count = int(self.text.index('end-1c').split('.')[0])
        line_numbers_string = "\n".join(str(i) for i in range(1, line_count + 1))
        self.linenumbers.insert(1.0, line_numbers_string)
        self.linenumbers.config(state='disabled')

    def on_key_release(self, event=None):
        self.update_line_numbers()
        self.highlight_syntax()
        self.try_autocomplete()

    def try_autocomplete(self):
        # Autocomplete popup for current word prefix
        if self.autocomplete_window:
            self.autocomplete_window.destroy()
            self.autocomplete_window = None

        cursor_index = self.text.index(tk.INSERT)
        line, col = map(int, cursor_index.split('.'))
        line_text = self.text.get(f"{line}.0", cursor_index)
        word_start = col
        while word_start > 0 and (line_text[word_start-1].isalnum() or line_text[word_start-1] == '_'):
            word_start -= 1
        prefix = line_text[word_start:col]
        if not prefix:
            return

        keywords = LANGUAGES[self.language]['keywords']
        matches = [kw for kw in keywords if kw.startswith(prefix) and kw != prefix]
        if not matches:
            return

        # Position autocomplete popup
        bbox = self.text.bbox(tk.INSERT)
        if not bbox:
            return
        x, y, width, height = bbox
        x += self.text.winfo_rootx()
        y += self.text.winfo_rooty() + height

        self.autocomplete_window = tk.Toplevel(self.text)
        self.autocomplete_window.wm_overrideredirect(True)
        self.autocomplete_window.wm_geometry(f"+{x}+{y}")

        self.autocomplete_listbox = tk.Listbox(self.autocomplete_window, bg='#2c2f33', fg='white',
                                               selectbackground='#569CD6', activestyle='none')
        self.autocomplete_listbox.pack()

        for m in matches:
            self.autocomplete_listbox.insert(tk.END, m)

        self.autocomplete_listbox.bind("<<ListboxSelect>>", self.autocomplete_select)
        self.autocomplete_listbox.bind("<Escape>", lambda e: self.autocomplete_window.destroy())
        self.autocomplete_listbox.bind("<Return>", self.autocomplete_select)
        self.autocomplete_listbox.focus_set()

    def autocomplete_select(self, event=None):
        if not self.autocomplete_listbox:
            return
        selection = self.autocomplete_listbox.curselection()
        if not selection:
            return
        word = self.autocomplete_listbox.get(selection[0])
        cursor_index = self.text.index(tk.INSERT)
        line, col = map(int, cursor_index.split('.'))
        line_text = self.text.get(f"{line}.0", cursor_index)
        word_start = col
        while word_start > 0 and (line_text[word_start-1].isalnum() or line_text[word_start-1] == '_'):
            word_start -= 1
        # Delete current incomplete word
        self.text.delete(f"{line}.{word_start}", cursor_index)
        # Insert full word
        self.text.insert(f"{line}.{word_start}", word)
        # Close popup
        if self.autocomplete_window:
            self.autocomplete_window.destroy()
            self.autocomplete_window = None

    def highlight_syntax(self):
        # Clear previous tags
        self.text.tag_remove('keyword', '1.0', 'end')
        self.text.tag_remove('string', '1.0', 'end')
        self.text.tag_remove('comment', '1.0', 'end')
        self.text.tag_remove('number', '1.0', 'end')
        self.text.tag_remove('error_line', '1.0', 'end')

        code = self.text.get('1.0', 'end-1c')
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            # simple tokenizer: split by spaces and symbols
            tokens = self.simple_tokenize(line)
            index = 0
            while index < len(line):
                for token in tokens:
                    start = line.find(token, index)
                    if start == -1:
                        continue
                    end = start + len(token)
                    tag_start = f"{i}.{start}"
                    tag_end = f"{i}.{end}"

                    # Keyword
                    if token in LANGUAGES[self.language]['keywords']:
                        self.text.tag_add('keyword', tag_start, tag_end)
                    # String literal
                    elif token.startswith('"') or token.startswith("'"):
                        self.text.tag_add('string', tag_start, tag_end)
                    # Comment for C (//)
                    elif self.language == 'C' and token.startswith('//'):
                        self.text.tag_add('comment', tag_start, f"{i}.end")
                        break
                    # Numbers
                    elif token.isdigit():
                        self.text.tag_add('number', tag_start, tag_end)

                    index = end
                    break
                else:
                    # no token matched, move forward
                    index += 1

        # Mark error lines
        for line_no in self.error_lines:
            self.text.tag_add('error_line', f"{line_no}.0", f"{line_no}.end")

        # Configure tags colors
        self.text.tag_config('keyword', foreground=SYNTAX_COLORS['keyword'])
        self.text.tag_config('string', foreground=SYNTAX_COLORS['string'])
        self.text.tag_config('comment', foreground=SYNTAX_COLORS['comment'])
        self.text.tag_config('number', foreground=SYNTAX_COLORS['number'])
        self.text.tag_config('error_line', background='#3E2F2F')

    def simple_tokenize(self, line):
        # A very naive tokenizer (no regex):
        tokens = []
        current = ''
        in_string = False
        string_char = ''
        i = 0
        while i < len(line):
            ch = line[i]
            if in_string:
                current += ch
                if ch == string_char:
                    tokens.append(current)
                    current = ''
                    in_string = False
                i += 1
                continue
            if ch in ['"', "'"]:
                if current:
                    tokens.append(current)
                    current = ''
                current = ch
                in_string = True
                string_char = ch
                i += 1
                continue
            if ch.isalnum() or ch == '_':
                current += ch
            else:
                if current:
                    tokens.append(current)
                    current = ''
                if ch.strip():
                    tokens.append(ch)
            i += 1
        if current:
            tokens.append(current)
        return tokens

    def set_error_lines(self, lines):
        self.error_lines = set(lines)
        self.highlight_syntax()

    def get_content(self):
        return self.text.get('1.0', 'end-1c')

    def set_content(self, text):
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', text)
        self.highlight_syntax()
        self.update_line_numbers()

class FindReplaceDialog(tk.Toplevel):
    def __init__(self, parent, text_widget):
        super().__init__(parent)
        self.text_widget = text_widget
        self.title("Find and Replace")
        self.geometry("400x150")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.label_find = tk.Label(self, text="Find:")
        self.label_find.pack(pady=5)
        self.entry_find = tk.Entry(self, width=40)
        self.entry_find.pack()

        self.label_replace = tk.Label(self, text="Replace:")
        self.label_replace.pack(pady=5)
        self.entry_replace = tk.Entry(self, width=40)
        self.entry_replace.pack()

        self.case_var = tk.IntVar()
        self.checkbox_case = tk.Checkbutton(self, text="Case Sensitive", variable=self.case_var)
        self.checkbox_case.pack(pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        self.btn_find = tk.Button(btn_frame, text="Find Next", command=self.find_next)
        self.btn_find.pack(side='left', padx=5)
        self.btn_replace = tk.Button(btn_frame, text="Replace", command=self.replace_one)
        self.btn_replace.pack(side='left', padx=5)
        self.btn_replace_all = tk.Button(btn_frame, text="Replace All", command=self.replace_all)
        self.btn_replace_all.pack(side='left', padx=5)

        self.last_found = None

    def find_next(self):
        needle = self.entry_find.get()
        if not needle:
            return
        start = '1.0' if not self.last_found else self.last_found
        case_sensitive = self.case_var.get()

        pos = self.text_widget.search(needle, start, nocase=not case_sensitive, stopindex='end')
        if not pos:
            messagebox.showinfo("Find", f"'{needle}' not found.")
            self.last_found = None
            return
        end_pos = f"{pos}+{len(needle)}c"
        self.text_widget.tag_remove('search_highlight', '1.0', 'end')
        self.text_widget.tag_add('search_highlight', pos, end_pos)
        self.text_widget.tag_config('search_highlight', background='yellow', foreground='black')
        self.text_widget.mark_set(tk.INSERT, end_pos)
        self.text_widget.see(pos)
        self.last_found = end_pos

    def replace_one(self):
        if self.last_found:
            start = self.last_found
            needle = self.entry_find.get()
            replace_text = self.entry_replace.get()
            # Delete old and insert new
            pos_start = f"{start}-{len(needle)}c"
            self.text_widget.delete(pos_start, start)
            self.text_widget.insert(pos_start, replace_text)
            self.last_found = None
            self.find_next()

    def replace_all(self):
        needle = self.entry_find.get()
        replace_text = self.entry_replace.get()
        if not needle:
            return
        case_sensitive = self.case_var.get()
        content = self.text_widget.get('1.0', 'end')
        if not case_sensitive:
            new_content = content.replace(needle, replace_text)
        else:
            # Case sensitive replace all
            new_content = ''
            i = 0
            while i < len(content):
                if content[i:i+len(needle)] == needle:
                    new_content += replace_text
                    i += len(needle)
                else:
                    new_content += content[i]
                    i += 1
        self.text_widget.delete('1.0', 'end')
        self.text_widget.insert('1.0', new_content)

class ConsoleWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Console Output")
        self.geometry("700x400")
        self.text = tk.Text(self, bg='black', fg='white', state='disabled')
        self.text.pack(fill='both', expand=True)

    def write(self, message):
        self.text.config(state='normal')
        self.text.insert('end', message)
        self.text.see('end')
        self.text.config(state='disabled')

    def clear(self):
        self.text.config(state='normal')
        self.text.delete('1.0', 'end')
        self.text.config(state='disabled')

class CodeEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced Multi-language Code Editor")
        self.geometry("900x700")

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both', expand=True)

        # Store tabs: list of CodeEditorTab objects
        self.editor_tabs = []

        self.current_language = tk.StringVar(value='C')
        self.create_menu()
        self.create_toolbar()

        # Console window for run/debug output
        self.console = ConsoleWindow(self)
        self.console.withdraw()

        # Auto save thread
        self.auto_save_enabled = True
        self.start_auto_save_thread()

        # Open initial blank tab
        self.new_file()

        # Bind tab change event
        self.tabs.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New File", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open File", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As", accelerator="Ctrl+Shift+S", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Find and Replace", accelerator="Ctrl+F", command=self.find_replace)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Compile & Run", accelerator="F5", command=self.compile_and_run)
        run_menu.add_command(label="Debug (GDB)", accelerator="F6", command=self.debug_code)
        menubar.add_cascade(label="Run", menu=run_menu)

        lang_menu = tk.Menu(menubar, tearoff=0)
        for lang in LANGUAGES.keys():
            lang_menu.add_radiobutton(label=lang, variable=self.current_language, value=lang, command=self.switch_language)
        menubar.add_cascade(label="Language", menu=lang_menu)

        self.config(menu=menubar)

        # Keyboard shortcuts
        self.bind_all("<Control-n>", lambda e: self.new_file())
        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_file())
        self.bind_all("<Control-S>", lambda e: self.save_file_as())
        self.bind_all("<Control-f>", lambda e: self.find_replace())
        self.bind_all("<F5>", lambda e: self.compile_and_run())
        self.bind_all("<F6>", lambda e: self.debug_code())

    def create_toolbar(self):
        toolbar = tk.Frame(self, bd=1, relief=tk.RAISED)
        toolbar.pack(side='top', fill='x')

        new_btn = tk.Button(toolbar, text="New", command=self.new_file)
        new_btn.pack(side='left', padx=2, pady=2)

        open_btn = tk.Button(toolbar, text="Open", command=self.open_file)
        open_btn.pack(side='left', padx=2, pady=2)

        save_btn = tk.Button(toolbar, text="Save", command=self.save_file)
        save_btn.pack(side='left', padx=2, pady=2)

        run_btn = tk.Button(toolbar, text="Run", command=self.compile_and_run)
        run_btn.pack(side='left', padx=2, pady=2)

        debug_btn = tk.Button(toolbar, text="Debug", command=self.debug_code)
        debug_btn.pack(side='left', padx=2, pady=2)

        find_btn = tk.Button(toolbar, text="Find/Replace", command=self.find_replace)
        find_btn.pack(side='left', padx=2, pady=2)

        self.language_label = tk.Label(toolbar, text="Language:")
        self.language_label.pack(side='left', padx=5)
        lang_combo = ttk.Combobox(toolbar, values=list(LANGUAGES.keys()), textvariable=self.current_language, state='readonly', width=8)
        lang_combo.pack(side='left', padx=2)
        lang_combo.bind('<<ComboboxSelected>>', lambda e: self.switch_language())

    def current_editor(self):
        if not self.editor_tabs:
            return None
        index = self.tabs.index(self.tabs.select())
        return self.editor_tabs[index]

    def new_file(self):
        lang = self.current_language.get()
        new_tab = CodeEditorTab(self.tabs, language=lang)
        self.editor_tabs.append(new_tab)
        self.tabs.add(new_tab.frame, text=f"Untitled{LANGUAGES[lang]['extension']}")
        self.tabs.select(len(self.editor_tabs) - 1)

    def open_file(self):
        lang = self.current_language.get()
        filetypes = []
        for ext in LANGUAGES.values():
            filetypes.extend(ext['filetypes'])
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if not filename:
            return
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        ext = os.path.splitext(filename)[1]
        # Detect language by extension
        lang = 'C'
        for k, v in LANGUAGES.items():
            if ext == v['extension']:
                lang = k
                break
        new_tab = CodeEditorTab(self.tabs, language=lang, filename=filename, content=content)
        self.editor_tabs.append(new_tab)
        tab_name = os.path.basename(filename)
        self.tabs.add(new_tab.frame, text=tab_name)
        self.tabs.select(len(self.editor_tabs) - 1)
        self.current_language.set(lang)

    def save_file(self):
        editor = self.current_editor()
        if not editor:
            return
        if not editor.filename:
            return self.save_file_as()
        try:
            with open(editor.filename, 'w', encoding='utf-8') as f:
                f.write(editor.get_content())
            messagebox.showinfo("Save", f"File saved: {editor.filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    def save_file_as(self):
        editor = self.current_editor()
        if not editor:
            return
        lang = editor.language
        filetypes = LANGUAGES[lang]['filetypes']
        filename = filedialog.asksaveasfilename(defaultextension=LANGUAGES[lang]['extension'], filetypes=filetypes)
        if not filename:
            return
        editor.filename = filename
        self.tabs.tab(self.tabs.select(), text=os.path.basename(filename))
        self.save_file()

    def find_replace(self):
        editor = self.current_editor()
        if not editor:
            return
        FindReplaceDialog(self, editor.text)

    def compile_and_run(self):
        editor = self.current_editor()
        if not editor:
            return
        content = editor.get_content()
        lang = editor.language
        if not editor.filename:
            save_first = messagebox.askyesno("Save file", "You need to save the file before running. Save now?")
            if save_first:
                self.save_file_as()
            else:
                return
        else:
            self.save_file()

        self.console.clear()
        self.console.deiconify()
        self.console.lift()

        if lang == 'C':
            # Compile with gcc
            exe_path = os.path.splitext(editor.filename)[0]
            compile_cmd = LANGUAGES['C']['compile_cmd'](editor.filename, exe_path)
            try:
                # Compile
                proc = subprocess.run(compile_cmd, capture_output=True, text=True)
                if proc.returncode != 0:
                    self.console.write("Compilation failed:\n")
                    self.console.write(proc.stderr)
                    self.highlight_errors_from_gcc(proc.stderr)
                    return
                else:
                    self.console.write("Compilation successful.\n")
                # Run executable
                run_cmd = LANGUAGES['C']['run_cmd'](exe_path)
                run_proc = subprocess.run(run_cmd, capture_output=True, text=True)
                self.console.write("Program output:\n")
                self.console.write(run_proc.stdout)
                if run_proc.stderr:
                    self.console.write("\nErrors:\n")
                    self.console.write(run_proc.stderr)
            except Exception as e:
                self.console.write(f"Error: {e}")
        elif lang == 'Python':
            # Run Python file
            run_cmd = LANGUAGES['Python']['run_cmd'](editor.filename)
            try:
                run_proc = subprocess.run(run_cmd, capture_output=True, text=True)
                self.console.write(run_proc.stdout)
                if run_proc.stderr:
                    self.console.write("\nErrors:\n")
                    self.console.write(run_proc.stderr)
            except Exception as e:
                self.console.write(f"Error: {e}")

    def highlight_errors_from_gcc(self, gcc_output):
        # Clear error highlights on all tabs
        for tab in self.editor_tabs:
            tab.set_error_lines([])

        editor = self.current_editor()
        if not editor:
            return

        error_lines = []
        # Parse gcc error messages to find line numbers
        for line in gcc_output.split('\n'):
            # GCC error format: filename:line:column: error: message
            if editor.filename and line.startswith(editor.filename):
                parts = line.split(':')
                if len(parts) > 3:
                    try:
                        line_no = int(parts[1])
                        error_lines.append(line_no)
                    except:
                        pass
        editor.set_error_lines(error_lines)

    def debug_code(self):
        # Basic GDB launch for C files - runs gdb and shows output in console
        editor = self.current_editor()
        if not editor or editor.language != 'C':
            messagebox.showinfo("Debug", "Debugging is only supported for C language in this editor.")
            return
        if not editor.filename:
            messagebox.showwarning("Debug", "Save your C file before debugging.")
            return
        exe_path = os.path.splitext(editor.filename)[0]
        if not os.path.exists(exe_path):
            messagebox.showwarning("Debug", "Executable not found. Compile first.")
            return
        self.console.clear()
        self.console.deiconify()
        self.console.lift()

        try:
            # Run gdb -q exe_path -ex run -ex quit
            gdb_cmd = ["gdb", "-q", exe_path, "-ex", "run", "-ex", "quit"]
            proc = subprocess.run(gdb_cmd, capture_output=True, text=True)
            self.console.write(proc.stdout)
            if proc.stderr:
                self.console.write("\nErrors:\n")
                self.console.write(proc.stderr)
        except Exception as e:
            self.console.write(f"Error running debugger: {e}")

    def switch_language(self):
        editor = self.current_editor()
        if editor:
            new_lang = self.current_language.get()
            editor.set_language(new_lang)
            tab_index = self.tabs.index(self.tabs.select())
            self.tabs.tab(tab_index, text=f"Untitled{LANGUAGES[new_lang]['extension']}")

    def on_tab_change(self, event):
        editor = self.current_editor()
        if editor:
            self.current_language.set(editor.language)

    def start_auto_save_thread(self):
        def auto_save_loop():
            while self.auto_save_enabled:
                time.sleep(60)
                for editor in self.editor_tabs:
                    if editor.filename:
                        with open(editor.filename, 'w', encoding='utf-8') as f:
                            f.write(editor.get_content())
        threading.Thread(target=auto_save_loop, daemon=True).start()

    def on_close(self):
        self.auto_save_enabled = False
        self.destroy()

class CodeEditorTab:
    def __init__(self, parent_notebook, language='C', filename=None, content=''):
        self.language = language
        self.filename = filename
        self.frame = tk.Frame(parent_notebook)
        self.text = tk.Text(self.frame, undo=True, wrap='none', font=('Consolas', 12))
        self.text.pack(side='right', fill='both', expand=True)

        # Line numbers widget
        self.linenumbers = tk.Text(self.frame, width=4, padx=4, takefocus=0, border=0,
                                   background='lightgrey', state='disabled', font=('Consolas', 12))
        self.linenumbers.pack(side='left', fill='y')

        # Scrollbar linked to text and line numbers
        self.v_scroll = ttk.Scrollbar(self.frame, orient='vertical', command=self.on_vscroll)
        self.v_scroll.pack(side='right', fill='y')
        self.text.config(yscrollcommand=self.on_yscroll)

        # Configure horizontal scrollbar for text
        self.h_scroll = ttk.Scrollbar(self.frame, orient='horizontal', command=self.text.xview)
        self.h_scroll.pack(side='bottom', fill='x')
        self.text.config(xscrollcommand=self.h_scroll.set)

        # Bind events for line numbers update
        self.text.bind('<KeyRelease>', self.update_line_numbers)
        self.text.bind('<MouseWheel>', self.update_line_numbers)
        self.text.bind('<Button-1>', self.update_line_numbers)
        self.text.bind('<Configure>', self.update_line_numbers)

        self.text.insert('1.0', content)

        self.error_lines = []

        self.update_line_numbers()
        self.apply_syntax_highlighting()

        # Autocomplete popup
        self.autocomplete_popup = None
        self.text.bind('<KeyRelease>', self.handle_autocomplete)

    def on_vscroll(self, *args):
        self.text.yview(*args)
        self.linenumbers.yview(*args)

    def on_yscroll(self, *args):
        self.v_scroll.set(*args)
        self.linenumbers.yview_moveto(args[0])

    def update_line_numbers(self, event=None):
        self.linenumbers.config(state='normal')
        self.linenumbers.delete('1.0', 'end')
        line_count = self.text.index('end-1c').split('.')[0]
        line_numbers_string = "\n".join(str(i) for i in range(1, int(line_count) + 1))
        self.linenumbers.insert('1.0', line_numbers_string)
        self.linenumbers.config(state='disabled')

        # Update error highlights for lines with errors
        self.highlight_error_lines()

    def get_content(self):
        return self.text.get('1.0', 'end-1c')

    def set_language(self, language):
        self.language = language
        self.apply_syntax_highlighting()

    def apply_syntax_highlighting(self):
        # Remove previous tags
        for tag in self.text.tag_names():
            self.text.tag_delete(tag)

        # Define simple keywords and patterns per language
        lang_info = LANGUAGES.get(self.language, {})
        keywords = lang_info.get('keywords', [])
        comments = lang_info.get('comment_patterns', [])
        strings = lang_info.get('string_patterns', [])

        content = self.get_content()

        # Basic keyword highlighting
        for kw in keywords:
            start = '1.0'
            while True:
                pos = self.text.search(r'\b' + kw + r'\b', start, stopindex='end', regexp=True)
                if not pos:
                    break
                end_pos = f"{pos}+{len(kw)}c"
                self.text.tag_add('keyword', pos, end_pos)
                start = end_pos
        self.text.tag_config('keyword', foreground='blue')

        # Comments highlighting
        for pattern in comments:
            start = '1.0'
            while True:
                pos = self.text.search(pattern, start, stopindex='end', regexp=True)
                if not pos:
                    break
                # Highlight till end of line for single-line comments
                line_end = self.text.index(f"{pos} lineend")
                self.text.tag_add('comment', pos, line_end)
                start = line_end
        self.text.tag_config('comment', foreground='green')

        # Strings highlighting
        for pattern in strings:
            start = '1.0'
            while True:
                pos = self.text.search(pattern, start, stopindex='end', regexp=True)
                if not pos:
                    break
                # Find closing quote
                quote_char = pattern[0]
                end_pos = self.text.search(quote_char, pos + '+1c', stopindex='end')
                if not end_pos:
                    break
                end_pos = f"{end_pos}+1c"
                self.text.tag_add('string', pos, end_pos)
                start = end_pos
        self.text.tag_config('string', foreground='orange')

    def set_error_lines(self, lines):
        self.error_lines = lines
        self.highlight_error_lines()

    def highlight_error_lines(self):
        self.text.tag_remove('error_line', '1.0', 'end')
        for line in self.error_lines:
            start = f"{line}.0"
            end = f"{line}.end"
            self.text.tag_add('error_line', start, end)
        self.text.tag_config('error_line', background='red')

    def handle_autocomplete(self, event):
        # Simple autocomplete based on keywords of current language
        if event.keysym == 'space' or event.keysym == 'Return' or event.keysym == 'Tab':
            if self.autocomplete_popup:
                self.autocomplete_popup.destroy()
                self.autocomplete_popup = None
            return

        word = self.get_current_word()
        if not word:
            if self.autocomplete_popup:
                self.autocomplete_popup.destroy()
                self.autocomplete_popup = None
            return

        lang_info = LANGUAGES.get(self.language, {})
        keywords = lang_info.get('keywords', [])
        suggestions = [kw for kw in keywords if kw.startswith(word) and kw != word]

        if not suggestions:
            if self.autocomplete_popup:
                self.autocomplete_popup.destroy()
                self.autocomplete_popup = None
            return

        if self.autocomplete_popup:
            self.autocomplete_popup.destroy()

        x, y, cx, cy = self.text.bbox("insert")
        x += self.text.winfo_rootx()
        y += self.text.winfo_rooty() + cy

        self.autocomplete_popup = tk.Toplevel(self.text)
        self.autocomplete_popup.wm_overrideredirect(True)
        self.autocomplete_popup.geometry(f"+{x}+{y}")

        listbox = tk.Listbox(self.autocomplete_popup, height=5)
        listbox.pack()
        for suggestion in suggestions:
            listbox.insert('end', suggestion)

        def on_select(event):
            selection = listbox.get(listbox.curselection())
            self.replace_current_word(selection)
            self.autocomplete_popup.destroy()
            self.autocomplete_popup = None
            self.text.focus_set()

        listbox.bind('<<ListboxSelect>>', on_select)

    def get_current_word(self):
        pos = self.text.index("insert wordstart")
        end = self.text.index("insert wordend")
        if pos == end:
            return ''
        return self.text.get(pos, end)

    def replace_current_word(self, word):
        pos = self.text.index("insert wordstart")
        end = self.text.index("insert wordend")
        self.text.delete(pos, end)
        self.text.insert(pos, word)

class FindReplaceDialog(tk.Toplevel):
    def __init__(self, parent, text_widget):
        super().__init__(parent)
        self.title("Find and Replace")
        self.text_widget = text_widget
        self.geometry("400x120")
        self.transient(parent)
        self.resizable(False, False)

        tk.Label(self, text="Find:").grid(row=0, column=0, sticky='w', padx=4, pady=4)
        self.find_entry = tk.Entry(self, width=30)
        self.find_entry.grid(row=0, column=1, padx=4, pady=4)
        self.find_entry.focus_set()

        tk.Label(self, text="Replace:").grid(row=1, column=0, sticky='w', padx=4, pady=4)
        self.replace_entry = tk.Entry(self, width=30)
        self.replace_entry.grid(row=1, column=1, padx=4, pady=4)

        self.match_case = tk.BooleanVar()
        tk.Checkbutton(self, text="Match case", variable=self.match_case).grid(row=2, column=1, sticky='w', padx=4, pady=4)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=4)

        tk.Button(btn_frame, text="Find Next", command=self.find_next).pack(side='left', padx=4)
        tk.Button(btn_frame, text="Replace", command=self.replace).pack(side='left', padx=4)
        tk.Button(btn_frame, text="Replace All", command=self.replace_all).pack(side='left', padx=4)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side='left', padx=4)

        self.last_search_index = '1.0'

    def find_next(self):
        find_text = self.find_entry.get()
        if not find_text:
            return
        start_pos = self.text_widget.index(self.last_search_index)
        if self.match_case.get():
            pos = self.text_widget.search(find_text, start_pos, nocase=0, stopindex='end')
        else:
            pos = self.text_widget.search(find_text, start_pos, nocase=1, stopindex='end')

        if not pos:
            messagebox.showinfo("Find", "No more occurrences found.")
            self.last_search_index = '1.0'
            return
        end_pos = f"{pos}+{len(find_text)}c"
        self.text_widget.tag_remove('search_highlight', '1.0', 'end')
        self.text_widget.tag_add('search_highlight', pos, end_pos)
        self.text_widget.tag_config('search_highlight', background='yellow')
        self.text_widget.mark_set('insert', end_pos)
        self.text_widget.see(pos)
        self.last_search_index = end_pos

    def replace(self):
        find_text = self.find_entry.get()
        replace_text = self.replace_entry.get()
        if not find_text:
            return
        pos = self.text_widget.search(find_text, '1.0', stopindex='end')
        if not pos:
            messagebox.showinfo("Replace", "Text not found.")
            return
        end_pos = f"{pos}+{len(find_text)}c"
        self.text_widget.delete(pos, end_pos)
        self.text_widget.insert(pos, replace_text)

    def replace_all(self):
        find_text = self.find_entry.get()
        replace_text = self.replace_entry.get()
        if not find_text:
            return
        start_pos = '1.0'
        count = 0
        while True:
            pos = self.text_widget.search(find_text, start_pos, stopindex='end')
            if not pos:
                break
            end_pos = f"{pos}+{len(find_text)}c"
            self.text_widget.delete(pos, end_pos)
            self.text_widget.insert(pos, replace_text)
            start_pos = f"{pos}+{len(replace_text)}c"
            count += 1
        messagebox.showinfo("Replace All", f"Replaced {count} occurrences.")

if __name__ == '__main__':
    app = CodeEditorApp()
    app.mainloop()
