from tkinter import *
from tkinter import ttk
import os
import re
import subprocess

# Define token types and their associated colors
TOKEN_TYPES = {
    'keyword': '#FF79C6',      # Pink
    'identifier': '#F8F8F2',   # Light text
    'number': '#BD93F9',       # Purple
    'string': '#F1FA8C',       # Yellow
    'operator': '#FF5555',     # Red
    'comment': '#6272A4',      # Grey-blue
    'bracket': '#8BE9FD',      # Cyan
}

# List of C keywords
C_KEYWORDS = [
    'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum',
    'extern', 'float', 'for', 'goto', 'if', 'int', 'long', 'register', 'return', 'short', 'signed',
    'sizeof', 'static', 'struct', 'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while'
]

# Regex patterns
TOKEN_PATTERNS = {
    'comment': r'//.*?$|/\*[\s\S]*?\*/',
    'string': r'"(?:\\.|[^"\\])*?"',
    'keyword': r'\b(?:' + '|'.join(C_KEYWORDS) + r')\b',
    'number': r'\b\d+(\.\d+)?\b',
    'operator': r'==|!=|<=|>=|\+\+|--|&&|\|\||\+=|-=|\*=|/=|[%&|^!<>]=?|[+\-*/%=]',
    'bracket': r'[\{\}\[\]\(\)]',
    'identifier': r'\b(?!' + '|'.join(C_KEYWORDS) + r'\b)[a-zA-Z_][a-zA-Z0-9_]*\b'
}

def get_tkinter_index(text_widget, char_index):
    line = text_widget.index(f"1.0+{char_index}c").split(".")
    return f"{line[0]}.{line[1]}"

def highlight_code(text_widget, code):
    for token in TOKEN_TYPES.keys():
        text_widget.tag_remove(token, "1.0", END)

    for token_type, pattern in TOKEN_PATTERNS.items():
        for match in re.finditer(pattern, code, re.MULTILINE):
            start, end = match.span()
            start_index = get_tkinter_index(text_widget, start)
            end_index = get_tkinter_index(text_widget, end)
            text_widget.tag_add(token_type, start_index, end_index)
            text_widget.tag_configure(token_type, foreground=TOKEN_TYPES[token_type])
    return code

def run(code):
    terminal_output.config(state=NORMAL)
    terminal_output.delete("1.0", END)
    terminal_output.config(state=DISABLED)

    if code.strip():
        with open("temp.c", "w") as fp:
            fp.write(code)

        compile_process = subprocess.run(
            ["gcc", "temp.c", "-o", "a.exe"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        terminal_output.config(state=NORMAL)
        if compile_process.returncode != 0:
            terminal_output.insert(END, "Compilation Error:\n" + compile_process.stderr)
            terminal_output.config(state=DISABLED)
            return

        try:
            run_process = subprocess.run(
                ["a.exe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            terminal_output.insert(END, "Output:\n" + run_process.stdout)
            if run_process.stderr:
                terminal_output.insert(END, "\nErrors:\n" + run_process.stderr)
        except subprocess.TimeoutExpired:
            terminal_output.insert(END, "Execution timed out.")
        terminal_output.config(state=DISABLED)

def detect_errors(code):
    highlight_code(text_area, code)
    text_area.tag_remove("error_line", "1.0", END)
    terminal_output.config(state=NORMAL)
    terminal_output.delete("1.0", END)

    # Save code to temp file
    with open("temp_live.c", "w") as f:
        f.write(code)

    # Run GCC to check for syntax errors
    process = subprocess.run(
        ["gcc", "-fsyntax-only", "temp_live.c"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Display and highlight errors
    if process.stderr:
        error_lines = set()
        for line in process.stderr.splitlines():
            match = re.search(r"temp_live\.c:(\d+):", line)
            if match:
                error_lines.add(int(match.group(1)))

        terminal_output.insert(END, process.stderr)

        for line_num in error_lines:
            index_start = f"{line_num}.0"
            index_end = f"{line_num}.end"
            text_area.tag_add("error_line", index_start, index_end)

        text_area.tag_configure("error_line", background="#FF5555") 
    else:
        terminal_output.insert(END, "No syntax errors detected.")

    terminal_output.config(state=DISABLED)

def update_line_numbers(event=None):
    line_count_widget.config(state=NORMAL)
    line_count_widget.delete(1.0, END)
    lines = text_area.index('end-1c').split('.')[0]
    line_numbers = "\n".join(str(i) for i in range(1, int(lines) + 1))
    line_count_widget.insert(END, line_numbers)
    line_count_widget.config(state=DISABLED)
    scroll_line_numbers()

def sync_scroll(*args):
    text_area.yview(*args)
    line_count_widget.yview(*args)

def on_text_scroll(event):
    text_area.yview_scroll(-1 * (event.delta // 120), "units")
    line_count_widget.yview_scroll(-1 * (event.delta // 120), "units")

def scroll_line_numbers(*args):
    line_count_widget.yview_moveto(text_area.yview()[0])

def on_cursor_move(event=None):
    cursor_line = int(text_area.index(INSERT).split('.')[0])
    visible_first, visible_last = text_area.yview()
    total_lines = int(text_area.index('end-1c').split('.')[0])
    first_visible_line = int(visible_first * total_lines)
    last_visible_line = int(visible_last * total_lines)

    if cursor_line > last_visible_line - 3:
        text_area.yview_scroll(1, "units")
        line_count_widget.yview_scroll(1, "units")
    elif cursor_line < first_visible_line + 3:
        text_area.yview_scroll(-1, "units")
        line_count_widget.yview_scroll(-1, "units")

from tkinter import filedialog, messagebox


current_file = None  # Global variable to store current file path


def new_file():
    global current_file
    file_path = filedialog.asksaveasfilename(
        defaultextension=".c",
        filetypes=[("C Files", "*.c"), ("Text Files", "*.txt"), ("All Files", "*.*")],
        title="Create New File"
    )
    if file_path:
        with open(file_path, "w") as f:
            f.write("")  
        current_file = file_path
        text_area.delete("1.0", END)

def open_file():
    global current_file
    file_path = filedialog.askopenfilename(filetypes=[("C Files", "*.c"), ("Text Files", "*.txt"), ("All Files", "*.*")])
    if file_path:
        with open(file_path, "r") as f:
            text_area.delete("1.0", END)
            text_area.insert("1.0", f.read())
        current_file = file_path

def save_file():
    global current_file
    if current_file:
        with open(current_file, "w") as f:
            f.write(text_area.get("1.0", END))
    else:
        save_as_file()

def save_as_file():
    global current_file
    file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("C Files", "*.c"), ("Text Files", "*.txt"), ("All Files", "*.*")])
    if file_path:
        with open(file_path, "w") as f:
            f.write(text_area.get("1.0", END))
        current_file = file_path



# GUI Setup
root = Tk()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.resizable(True, True)
root.geometry(f"{screen_width}x{screen_height}")
root.title("C Code Editor")

root.configure(bg='#1e1e1e')
font_config = ('Fira Code', 20)

# --- FILE MENU DROPDOWN ---
file_menu = Menu(root, tearoff=0, bg='#44475a', fg='#f8f8f2', activebackground='#6272a4', activeforeground='#f8f8f2', font=('Fira Code', 10))
file_menu.add_command(label="New File", command=new_file)
file_menu.add_command(label="Open", command=open_file)
file_menu.add_command(label="Save", command=save_file)
file_menu.add_command(label="Save As", command=save_as_file)

def show_file_menu(event):
    try:
        file_menu.tk_popup(event.x_root, event.y_root)
    finally:
        file_button.configure(bg='#50fa7b')

style = ttk.Style()
style.theme_use('clam')
style.configure("TScrollbar", gripcount=0,
                background="#44475a", darkcolor="#44475a", lightcolor="#44475a",
                troughcolor="#282a36", bordercolor="#282a36", arrowcolor="#f8f8f2")

scrollbar = ttk.Scrollbar(root, command=sync_scroll)
scrollbar.place(x=screen_width - 40, y=40, height=screen_height - 250)

frame = Frame(root, bg='#282a36')
frame.place(x=10, y=40, width=screen_width - 80, height=screen_height - 250)

line_count_widget = Text(frame, width=5, padx=10, pady=10, bg='#1e1e1e', fg='#6272a4',
                         insertbackground='white', font=font_config, state=DISABLED)
line_count_widget.pack(side=LEFT, fill=Y)

text_area = Text(frame, padx=10, pady=10, bg='#1e1e1e', fg='#f8f8f2', insertbackground='white',
                 selectbackground='#44475a', font=font_config, wrap="none",
                 yscrollcommand=lambda *args: (scrollbar.set(*args), scroll_line_numbers(*args)))
text_area.pack(side=RIGHT, fill=BOTH, expand=True)

file_button = Button(root, text="FILE", padx=20, pady=2, bg='#50fa7b', fg='#282a36', activebackground='#8be9fd',
       activeforeground='#282a36', borderwidth=0, font=('Helvetica', 12, 'bold'),
       )
file_button.place(x=15, y=5)

Button(root, text="RUN", padx=20, pady=2, bg='#50fa7b', fg='#282a36', activebackground='#8be9fd',
       activeforeground='#282a36', borderwidth=0, font=('Helvetica', 12, 'bold'),
       command=lambda: run(text_area.get("1.0", END))).place(x= screen_width - 160, y=5)

terminal_output = Text(root, height=6, bg='#1e1e1e', fg='#f8f8f2', insertbackground='white',
                       font=('Courier', 12), wrap="word")
terminal_output.place(x=10, y=screen_height - 200, width=screen_width - 80, height=150)
terminal_output.config(state=DISABLED)

terminal_scroll = ttk.Scrollbar(root, command=terminal_output.yview)
terminal_scroll.place(x=screen_width - 40, y=screen_height - 200, height=150)
terminal_output.config(yscrollcommand=terminal_scroll.set)

text_area.config(yscrollcommand=sync_scroll)
text_area.tag_configure("error_line", underline=True, background="#FF5555")
line_count_widget.config(yscrollcommand=sync_scroll)
text_area.bind("<KeyRelease>", lambda e: (update_line_numbers(), detect_errors(text_area.get("1.0", END))))
text_area.bind("<MouseWheel>", on_text_scroll)
line_count_widget.bind("<MouseWheel>", on_text_scroll)
text_area.bind("<KeyPress>", on_cursor_move)
file_button.bind("<Button-1>", show_file_menu)

update_line_numbers()
root.mainloop()