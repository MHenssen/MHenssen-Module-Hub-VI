"""Tkinter setup window: settings editor, sync launcher with live log, dashboard launcher."""
import os
import sys
import datetime as dt

from .config import app_base_dir, DEFAULT_DATA_XLSX, DEFAULT_SETTINGS_JSON
from .settings import (
    settings_path,
    default_ui_settings,
    save_app_settings,
    normalize_app_settings,
    apply_app_settings_to_env,
)
from .excel_io import data_excel_path


def launch_setup_ui():
    """Setup UI: settings, sync launcher with live log, dashboard launcher."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
        import subprocess, threading, socket, webbrowser
    except Exception as e:
        raise SystemExit(f"Tkinter UI is not available in this Python installation: {e}")

    settings = default_ui_settings()
    proc_state = {"sync": None, "serve": None, "serve_url": ""}

    root = tk.Tk()
    root.title("PI Portfolio Explorer — all teams")
    root.geometry("920x900")
    root.minsize(860, 760)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # ------------------------------------------------------------- palette
    INK = "#23262e"; BG = "#f6f5f1"; CARD = "#ffffff"; LINE = "#e4e2da"; LABEL = "#6a6f7b"
    ACCENT = "#5b50e6"; GREEN = "#16a87a"; AMBER = "#c8821f"; RED = "#d64545"
    CONSOLE_BG = "#1b1d23"; CONSOLE_FG = "#d7dae2"
    FONT = "Segoe UI"; MONO = "Consolas"
    root.configure(bg=BG)
    style.configure("App.TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD, relief="flat")
    style.configure("TLabel", background=BG, foreground=INK, font=(FONT, 9))
    style.configure("Card.TLabel", background=CARD, foreground=INK, font=(FONT, 9))
    style.configure("Card.Muted.TLabel", background=CARD, foreground=LABEL, font=(FONT, 8))
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", font=(FONT, 9, "bold"), padding=(14, 8), foreground=LABEL)
    style.map("TNotebook.Tab", foreground=[("selected", INK)], background=[("selected", CARD)])
    style.configure("Primary.TButton", font=(FONT, 9, "bold"), foreground="#ffffff", background=ACCENT, padding=(14, 7), borderwidth=0)
    style.map("Primary.TButton", background=[("active", "#4a40d6"), ("disabled", "#9aa0ab")])
    style.configure("Success.TButton", font=(FONT, 9, "bold"), foreground="#ffffff", background=GREEN, padding=(14, 7), borderwidth=0)
    style.map("Success.TButton", background=[("active", "#128a64"), ("disabled", "#9aa0ab")])
    style.configure("Warning.TButton", font=(FONT, 9, "bold"), foreground="#ffffff", background=AMBER, padding=(14, 7), borderwidth=0)
    style.map("Warning.TButton", background=[("active", "#a66b18"), ("disabled", "#9aa0ab")])
    style.configure("Danger.TButton", font=(FONT, 9, "bold"), foreground="#ffffff", background=RED, padding=(12, 7), borderwidth=0)
    style.map("Danger.TButton", background=[("active", "#b93737"), ("disabled", "#9aa0ab")])
    style.configure("Secondary.TButton", font=(FONT, 9, "bold"), foreground=INK, background="#edece6", padding=(12, 7), borderwidth=0)
    style.map("Secondary.TButton", background=[("active", "#dedbd2"), ("disabled", "#f0eee8")])
    style.configure("Card.TCheckbutton", background=CARD, foreground=INK, font=(FONT, 9))
    style.map("Card.TCheckbutton", background=[("active", CARD)], foreground=[("disabled", LABEL), ("active", INK)])

    vars_ = {}

    def var(key):
        if key not in vars_:
            val = settings.get(key, "")
            vars_[key] = (tk.BooleanVar(value=bool(val)) if isinstance(val, bool)
                          else tk.StringVar(value=str(val)))
        return vars_[key]

    # -------------------------------------------------------------- layout
    main = ttk.Frame(root, padding=14, style="App.TFrame")
    main.pack(fill="both", expand=True)
    header = tk.Frame(main, bg=INK, bd=0, highlightthickness=0)
    header.pack(fill="x", pady=(0, 12))
    hleft = tk.Frame(header, bg=INK)
    hleft.pack(side="left", fill="x", expand=True, padx=16, pady=14)
    tk.Label(hleft, text="PI Portfolio Explorer", bg=INK, fg="#ffffff", font=(FONT, 17, "bold")).pack(anchor="w")
    tk.Label(hleft, text="All teams · Parent Link & Epic progress · Jira Kanban", bg=INK, fg="#cfd3dc", font=(FONT, 9)).pack(anchor="w", pady=(2, 0))
    tk.Label(header, text="Output folder\n" + app_base_dir(), bg=INK, fg="#cfd3dc", justify="right", font=(FONT, 8)).pack(side="right", padx=16, pady=14)

    nb = ttk.Notebook(main)
    nb.pack(fill="both", expand=True)
    cfg_tab = ttk.Frame(nb, padding=12, style="Card.TFrame")
    help_tab = ttk.Frame(nb, padding=12, style="Card.TFrame")
    nb.add(cfg_tab, text="Settings")
    nb.add(help_tab, text="How to run")

    buttons = ttk.Frame(main, style="App.TFrame")
    buttons.pack(fill="x", pady=(12, 0))
    save_button = ttk.Button(buttons, text="Save settings", style="Secondary.TButton")
    save_button.pack(side="left")
    sync_button = ttk.Button(buttons, text="Sync all teams", style="Primary.TButton")
    sync_button.pack(side="left", padx=8)
    stop_sync_button = ttk.Button(buttons, text="Stop sync", style="Danger.TButton")
    stop_sync_button.pack(side="left", padx=(0, 8))
    stop_sync_button.configure(state="disabled")
    serve_button = ttk.Button(buttons, text="Serve dashboard", style="Success.TButton")
    serve_button.pack(side="left")
    stop_button = ttk.Button(buttons, text="Stop dashboard", style="Warning.TButton")
    stop_button.pack(side="left", padx=8)
    close_button = ttk.Button(buttons, text="Close", style="Secondary.TButton")
    close_button.pack(side="right")

    def add_entry(parent, row, label, key, width=58, show=None, help_text=None):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        ent = ttk.Entry(parent, textvariable=var(key), width=width, show=show)
        ent.grid(row=row, column=1, sticky="ew", pady=5, padx=(8, 0))
        if help_text:
            ttk.Label(parent, text=help_text, style="Card.Muted.TLabel").grid(row=row + 1, column=1, sticky="w", padx=(8, 0))
        return ent

    def add_inline_check(parent, row, text, key, note):
        line = tk.Frame(parent, bg=CARD, bd=0, highlightthickness=0)
        line.grid(row=row, column=1, columnspan=2, sticky="w", pady=6, padx=(8, 0))
        ttk.Checkbutton(line, text=text, variable=var(key), style="Card.TCheckbutton").pack(side="left")
        tk.Label(line, text=note, bg=CARD, fg=LABEL, activebackground=CARD, font=(FONT, 8)).pack(side="left", padx=(10, 0))

    cfg_tab.columnconfigure(1, weight=1)
    add_entry(cfg_tab, 0, "Jira URL", "jiraUrl", help_text="Default: https://devtrack.vanderlande.com")
    add_entry(cfg_tab, 2, "Jira email", "jiraEmail")
    token_entry = add_entry(cfg_tab, 3, "Jira token", "jiraToken", show="*")
    show_token = tk.BooleanVar(value=False)
    ttk.Checkbutton(cfg_tab, text="Show token", variable=show_token,
                    command=lambda: token_entry.configure(show="" if show_token.get() else "*"),
                    style="Card.TCheckbutton").grid(row=3, column=2, sticky="w", padx=8)
    add_entry(cfg_tab, 4, "Kanban board ID", "kanbanBoardId", help_text="Board holding the PI epics for ALL teams. Default: 17289")
    add_entry(cfg_tab, 6, "PI name", "piName", help_text="Example: 26.3 — every Epic on the board whose Planned PI matches is included, whatever its team.")
    add_entry(cfg_tab, 8, "Number of sprints in PI", "numSprints", help_text="Used for the Epic progress Gantt columns, e.g. 6.")
    add_entry(cfg_tab, 10, "Commitment date", "commitmentDate", help_text="Historical cutoff in YYYY-MM-DD format, normally the final planning day before the PI starts.")
    add_inline_check(cfg_tab, 12, "Force commitment refresh", "forceCommitmentRefresh", "Rebuild on the next Sync; resets automatically afterward.")
    add_inline_check(cfg_tab, 13, "Full Sync from Jira", "includeProgress", "Checked: reload everything from Jira. Unchecked: instant mode with zero Jira calls, reusing all current Excel data.")

    # ---------------------------------------------------------- How to run
    help_text_str = (
        "All-teams portfolio usage:\n\n"
        "1. Fill the Jira settings once and click Save settings.\n"
        "2. Click Sync all teams. The tool reads EVERY Epic on the Kanban board whose\n"
        "   Planned PI matches, for all teams, plus their child tickets and Parent Links.\n"
        "3. Click Serve dashboard and open the link that appears below.\n\n"
        "The dashboard classifies everything by Parent Link, Epic progress and Team:\n"
        "  - Overview: global KPIs, per-team progress, per-parent-link progress\n"
        "  - Parent links: expandable Parent Link -> Epics (filterable per team)\n"
        "  - Teams: one card per team with its parent links\n"
        "  - Epic progress: actual sprint movement Gantt per Epic\n\n"
        "Files created next to this script:\n  "
        f"{DEFAULT_DATA_XLSX}, {DEFAULT_SETTINGS_JSON}\n\n"
        "From PowerShell you can also run:\n"
        "  python this_script.py sync\n"
        "  python this_script.py serve --port 8010\n"
    )
    txt = tk.Text(help_tab, wrap="word", height=20, borderwidth=0, relief="flat",
                  background=CARD, foreground=INK, font=(FONT, 9), padx=10, pady=10)
    txt.insert("1.0", help_text_str)
    txt.configure(state="disabled")
    txt.pack(fill="both", expand=True)

    status = tk.StringVar(value="Ready")
    running_box = tk.Text(main, height=1, wrap="none", borderwidth=0, relief="flat",
                          background=BG, foreground=GREEN, font=(FONT, 9, "bold"),
                          cursor="arrow", padx=0, pady=0)
    running_box.pack(anchor="w", fill="x", pady=(8, 0))
    running_box.tag_configure("base", foreground=GREEN)
    running_box.tag_configure("url", foreground=ACCENT, underline=True)
    running_box.configure(state="disabled")
    ttk.Label(main, text="Execution log", font=(FONT, 10, "bold"), background=BG, foreground=INK).pack(anchor="w", pady=(10, 2))
    progress = ttk.Progressbar(main, mode="indeterminate")
    progress.pack(fill="x")
    log_box = tk.Text(main, height=15, wrap="word", borderwidth=0, relief="flat",
                      background=CONSOLE_BG, foreground=CONSOLE_FG, insertbackground=CONSOLE_FG,
                      font=(MONO, 9), padx=10, pady=8)
    log_box.pack(fill="both", expand=False, pady=(6, 0))
    log_box.tag_configure("ts", foreground="#7f8795")
    log_box.tag_configure("info", foreground=CONSOLE_FG)
    log_box.tag_configure("ok", foreground="#6ee7b7")
    log_box.tag_configure("warn", foreground="#f6c267")
    log_box.tag_configure("err", foreground="#ff8a8a")
    log_box.tag_configure("cmd", foreground="#9ba7ff")
    log_box.tag_configure("url", foreground="#8fd3ff", underline=True)
    log_box.configure(state="disabled")

    import webbrowser as _wb

    def _open_url_at_event(widget, event):
        try:
            idx = widget.index(f"@{event.x},{event.y}")
            ranges = widget.tag_ranges("url")
            for start, end in zip(ranges[0::2], ranges[1::2]):
                if widget.compare(start, "<=", idx) and widget.compare(idx, "<", end):
                    _wb.open(widget.get(start, end))
                    break
        except Exception:
            pass
        return "break"

    for w in (running_box, log_box):
        w.tag_bind("url", "<Enter>", lambda e, w=w: w.configure(cursor="hand2"))
        w.tag_bind("url", "<Leave>", lambda e, w=w: w.configure(cursor="arrow"))
        w.tag_bind("url", "<Button-1>", lambda e, w=w: _open_url_at_event(w, e))

    import re as _re
    URL_RE = _re.compile(r"https?://[^\s]+")

    def log_line(text):
        text = str(text or "").rstrip("\n")
        tag = "info"
        low = text.lower()
        if low.startswith("[done]") or "wrote" in low:
            tag = "ok"
        elif "error" in low or "failed" in low or "traceback" in low:
            tag = "err"
        elif "warning" in low or low.startswith("[sp] warning"):
            tag = "warn"
        elif low.startswith("$") or low.startswith("[cmd]"):
            tag = "cmd"

        def _do():
            log_box.configure(state="normal")
            log_box.insert("end", dt.datetime.now().strftime("%H:%M:%S "), "ts")
            pos = 0
            for m in URL_RE.finditer(text):
                if m.start() > pos:
                    log_box.insert("end", text[pos:m.start()], tag)
                log_box.insert("end", m.group(0), "url")
                pos = m.end()
            log_box.insert("end", text[pos:] + "\n", tag)
            log_box.see("end")
            log_box.configure(state="disabled")

        root.after(0, _do)

    def refresh_running_label():
        running_box.configure(state="normal")
        running_box.delete("1.0", "end")
        if proc_state["serve"] is not None and proc_state["serve"].poll() is None and proc_state["serve_url"]:
            running_box.insert("end", "Dashboard running:  ", "base")
            running_box.insert("end", proc_state["serve_url"], "url")
        else:
            running_box.insert("end", "No dashboard running.", "base")
        running_box.configure(state="disabled")

    def collect_settings():
        s = dict(settings)
        for k, v in vars_.items():
            s[k] = bool(v.get()) if isinstance(v, tk.BooleanVar) else v.get()
        return normalize_app_settings(s)

    def save_clicked(show_message=True):
        s = collect_settings()
        settings.update(s)
        p = save_app_settings(s)
        log_line(f"[settings] saved {p}")
        if show_message:
            status.set(f"Settings saved to {p}")

    def _cli_base(unbuffered=False):
        if getattr(sys, "frozen", False):
            return [sys.executable]
        base = [sys.executable]
        if unbuffered:
            base.append("-u")
        entry = os.path.abspath(sys.argv[0])
        if entry.lower().endswith(".py") and os.path.exists(entry):
            return base + [entry]
        return base + ["-m", "pi_portfolio"]

    def run_sync():
        if proc_state["sync"] is not None and proc_state["sync"].poll() is None:
            messagebox.showinfo("Sync", "A sync is already running.")
            return
        save_clicked(show_message=False)
        env = apply_app_settings_to_env(collect_settings())
        env["PYTHONUNBUFFERED"] = "1"
        cmd = _cli_base(unbuffered=True) + ["sync"]
        log_line("[cmd] " + " ".join(cmd))
        creation = 0
        if os.name == "nt":
            creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.Popen(cmd, cwd=app_base_dir(), env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1, creationflags=creation)
        except Exception as e:
            log_line(f"[error] could not start sync: {e}")
            return
        proc_state["sync"] = proc
        sync_button.configure(state="disabled")
        stop_sync_button.configure(state="normal")
        progress.start(12)
        status.set("Sync running…")

        def finish_sync(code):
            progress.stop()
            sync_button.configure(state="normal")
            stop_sync_button.configure(state="disabled")
            status.set("Sync finished OK" if code == 0 else f"Sync exited with code {code}")
            log_line(f"[done] sync exited with code {code}" if code == 0 else f"[error] sync exited with code {code}")

        def worker():
            try:
                for line in proc.stdout:
                    log_line(line)
            except Exception:
                pass
            code = proc.wait()
            root.after(0, lambda: finish_sync(code))

        threading.Thread(target=worker, daemon=True).start()

    def stop_sync():
        proc = proc_state.get("sync")
        if proc is not None and proc.poll() is None:
            _kill_proc(proc)
            log_line("[warn] sync stopped by user")
        stop_sync_button.configure(state="disabled")
        sync_button.configure(state="normal")
        progress.stop()

    def find_free_port(start=8010):
        for port in range(start, start + 60):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    return port
            except OSError:
                continue
        return start

    def run_serve():
        if proc_state["serve"] is not None and proc_state["serve"].poll() is None:
            _wb.open(proc_state["serve_url"])
            status.set("Dashboard already running; opened in browser.")
            return
        save_clicked(show_message=False)
        if not os.path.exists(data_excel_path()):
            log_line(f"[warn] no Excel workbook yet ({DEFAULT_DATA_XLSX}); the dashboard will be empty until you Sync.")
        port = find_free_port()
        env = apply_app_settings_to_env(collect_settings())
        cmd = _cli_base() + ["serve", "--port", str(port)]
        log_line("[cmd] " + " ".join(cmd))
        creation = 0
        if os.name == "nt":
            creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.Popen(cmd, cwd=app_base_dir(), env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1, creationflags=creation)
        except Exception as e:
            log_line(f"[error] could not start dashboard: {e}")
            return
        proc_state["serve"] = proc
        proc_state["serve_url"] = f"http://127.0.0.1:{port}"
        refresh_running_label()
        log_line(f"[serve] dashboard on {proc_state['serve_url']}")
        status.set(f"Dashboard running on {proc_state['serve_url']}")

        def worker():
            try:
                for line in proc.stdout:
                    log_line(line)
            except Exception:
                pass
            proc.wait()
            root.after(0, refresh_running_label)

        threading.Thread(target=worker, daemon=True).start()
        root.after(700, lambda: _wb.open(proc_state["serve_url"]))

    def _kill_proc(proc):
        try:
            if os.name == "nt":
                import subprocess as sp
                sp.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=sp.DEVNULL, stderr=sp.DEVNULL)
            else:
                proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def stop_servers():
        proc = proc_state.get("serve")
        if proc is not None and proc.poll() is None:
            _kill_proc(proc)
            log_line("[warn] dashboard stopped")
        proc_state["serve"] = None
        proc_state["serve_url"] = ""
        refresh_running_label()
        status.set("Dashboard stopped")

    def on_close():
        for key in ("sync", "serve"):
            proc = proc_state.get(key)
            if proc is None or proc.poll() is not None:
                continue
            _kill_proc(proc)
        root.destroy()

    save_button.configure(command=save_clicked)
    sync_button.configure(command=run_sync)
    stop_sync_button.configure(command=stop_sync)
    serve_button.configure(command=run_serve)
    stop_button.configure(command=stop_servers)
    close_button.configure(command=on_close)
    root.protocol("WM_DELETE_WINDOW", on_close)
    ttk.Label(main, textvariable=status, style="TLabel").pack(anchor="w", pady=(6, 0))
    refresh_running_label()
    log_line(f"[info] settings file: {settings_path()}")
    log_line(f"[info] Excel data file: {data_excel_path()}")
    root.mainloop()
