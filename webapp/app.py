"""
SudoPHASE web app: serves the Sudoku UI and runs the C++ solver from the repo root.
Algorithms exposed in the UI: 0 (ACS), 3 (multi-colony), 4 (multi-thread multi-colony).
"""
from __future__ import annotations

import os
import re
import subprocess
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__)
REPO_ROOT = Path(__file__).resolve().parents[1]
INSTANCES_ROOT = REPO_ROOT / "instances"
# Puzzle library: one folder per UI size (paths under instances/).
LIBRARY_FOLDERS: dict[str, str] = {
    "9×9": "paquita-database",
    "16×16": "16x16-database",
    "25×25": "25x25",
}
ALLOWED_LIBRARY_DIRS = frozenset(LIBRARY_FOLDERS.values())
SIZES = [("9×9", 3, 81), ("16×16", 4, 256), ("25×25", 5, 625)]

# UI / API only allow these solver algorithms (matches user requirement).
ALLOWED_ALGORITHMS = frozenset({0, 3, 4})

_job_store: dict[str, dict] = {}
_job_store_lock = threading.Lock()

# Parallel ACS / MT multi-colony stderr (algorithms 2 & 4; UI uses 4).
PROGRESS_RE = re.compile(
    r"Progress:\s*iteration\s+(\d+)\s+\(Global best-so-far:\s+(\d+)/(\d+)\)"
)
BEST_GRID_RE = re.compile(r"^BEST_GRID\s+(\d+)\s+(\S+)")


def _read_instance_file(path: Path) -> tuple[int, str]:
    """Read instance .txt; returns (order, puzzle_string)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [L.strip() for L in text.splitlines() if L.strip()]
    if len(lines) < 2:
        raise ValueError("Invalid instance file: need at least order and idum line")
    order = int(lines[0])
    if order not in (3, 4, 5):
        raise ValueError(f"Unsupported order {order}; use 3, 4, or 5")
    num_cells = order**4
    values = []
    for L in lines[2:]:
        for part in L.split():
            try:
                values.append(int(part))
            except ValueError:
                pass
    if len(values) < num_cells:
        raise ValueError(f"Instance has {len(values)} values, need {num_cells}")
    values = values[:num_cells]
    out = []
    for v in values:
        if v == -1:
            out.append(".")
        elif order == 3:
            out.append(chr(ord("1") + v - 1) if 1 <= v <= 9 else ".")
        elif order == 4:
            if 1 <= v <= 10:
                out.append(chr(ord("0") + v - 1))
            elif 11 <= v <= 16:
                out.append(chr(ord("a") + v - 11))
            else:
                out.append(".")
        else:
            out.append(chr(ord("a") + v - 1) if 1 <= v <= 25 else ".")
    return order, "".join(out)


def _list_library() -> dict:
    """List .txt puzzles per size from instances/{paquita-database,16x16-database,25x25}."""
    by_size: dict[str, list[dict]] = {label: [] for label, _, _ in SIZES}
    label_by_order = {3: "9×9", 4: "16×16", 5: "25×25"}
    for label, _, _ in SIZES:
        folder_name = LIBRARY_FOLDERS[label]
        folder = INSTANCES_ROOT / folder_name
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.txt")):
            try:
                file_order, _ = _read_instance_file(path)
                if label_by_order.get(file_order) != label:
                    continue
                by_size[label].append(
                    {"name": path.name, "path": f"{folder_name}/{path.name}"}
                )
            except Exception:
                pass
    return by_size


def find_solver() -> Path:
    if os.name == "nt":
        candidates = [
            REPO_ROOT / "sudoku_ants.exe",
            REPO_ROOT / "vs2017" / "x64" / "Release" / "sudoku_ants.exe",
            REPO_ROOT / "vs2017" / "sudoku_ants" / "x64" / "Release" / "sudoku_ants.exe",
            REPO_ROOT / "vs2017" / "Release" / "sudoku_ants.exe",
        ]
    else:
        candidates = [
            REPO_ROOT / "sudokusolver",
            REPO_ROOT / "sudoku_ants",
        ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "Solver binary not found. Build the VS project (Release x64) or place sudoku_ants.exe in the repo root."
    )


def parse_verbose_stdout(stdout: str, order: int = 3) -> dict:
    """Parse solver verbose output for success, time, iterations, communication, solution grid."""
    out = {
        "success": None,
        "time": None,
        "iterations": None,
        "communication": None,
        "solution": None,
        "raw_error": None,
    }
    num_cells = order**4
    if order == 3:
        cell_pattern = re.compile(r"[1-9]")
    elif order == 4:
        cell_pattern = re.compile(r"[0-9a-fA-F]")
    else:
        cell_pattern = re.compile(r"[a-yA-Y]")

    lines = stdout.splitlines()

    for line in lines:
        m = re.search(r"solved in ([0-9]*\.?[0-9]+)", line, re.I)
        if m:
            out["success"] = True
            out["time"] = float(m.group(1))
        m = re.search(r"failed in time ([0-9]*\.?[0-9]+)", line, re.I)
        if m:
            out["success"] = False
            out["time"] = float(m.group(1))
        m = re.search(r"Failed to solve in ([0-9]*\.?[0-9]+)", line, re.I)
        if m:
            out["success"] = False
            out["time"] = float(m.group(1))
        m = re.search(r"iterations:\s*([0-9]+)", line, re.I)
        if m:
            out["iterations"] = int(m.group(1))
        m = re.search(r"communication:\s*(yes|no)", line, re.I)
        if m:
            out["communication"] = m.group(1).lower() == "yes"

    if out["success"] is None:
        for i, line in enumerate(lines):
            line = line.strip()
            if line in ("0", "1"):
                out["success"] = line == "0"
                if i + 1 < len(lines):
                    try:
                        out["time"] = float(lines[i + 1].strip())
                    except ValueError:
                        pass
                break

    def extract_grid_from_block(block: str) -> str | None:
        if order == 3:
            cells = cell_pattern.findall(block)
            if len(cells) >= num_cells:
                return "".join(cells[:num_cells])
        else:
            all_nums = re.findall(r"\d+", block)
            max_val = order * order
            values = [int(s) for s in all_nums if 1 <= int(s) <= max_val][:num_cells]
            if len(values) == num_cells:
                if order == 4:
                    return "".join(
                        chr(ord("0") + v - 1) if v <= 10 else chr(ord("a") + v - 11)
                        for v in values
                    )
                return "".join(chr(ord("a") + v - 1) for v in values)
        return None

    def extract_partial_grid(block: str) -> str | None:
        if order == 3:
            pat = re.compile(r"[1-9.]")
        elif order == 4:
            pat = re.compile(r"[0-9a-fA-F.]")
        else:
            pat = re.compile(r"[a-yA-Y.]")
        chars = pat.findall(block)[:num_cells]
        if not chars:
            return None
        return ("".join(chars) + "." * num_cells)[:num_cells]

    for i, line in enumerate(lines):
        if "BestSoFar:" in line:
            end = i + 1
            while end < len(lines) and lines[end].strip() != "---":
                end += 1
            block = " ".join(lines[i + 1 : end])
            sol = extract_partial_grid(block)
            if sol:
                out["solution"] = sol

    solution_start = None
    solution_end = None
    for i, line in enumerate(lines):
        if "Solution:" in line:
            solution_start = i + 1
        if solution_start is not None and "solved in" in line.lower():
            solution_end = i
            break
    if solution_start is not None and solution_end is not None:
        block = " ".join(lines[solution_start:solution_end])
        sol = extract_grid_from_block(block)
        if sol:
            out["solution"] = sol

    return out


def _build_cmd_extras(data: dict) -> list[str]:
    """Append C++ CLI flags from JSON body using solvermain.cpp argument names."""
    extra: list[str] = []

    def take_float(key: str) -> None:
        if key not in data:
            return
        extra.extend([f"--{key}", str(float(data[key]))])

    def take_int(key: str) -> None:
        if key not in data:
            return
        extra.extend([f"--{key}", str(int(data[key]))])

    take_int("ants")
    take_float("evap")
    take_float("q0")
    take_float("rho")
    take_float("xi")
    take_int("numacs")
    take_float("convthreshold")
    take_float("entropythreshold")
    take_int("numcolonies")

    if "commThreshold" in data:
        extra.extend(["--comm-threshold", str(int(data["commThreshold"]))])
    if "commEarly" in data:
        extra.extend(["--comm-early-interval", str(int(data["commEarly"]))])
    if "commLate" in data:
        extra.extend(["--comm-late-interval", str(int(data["commLate"]))])

    return extra


def _run_solver_sync(
    job_id: str | None,
    puzzle: str,
    timeout: int,
    threads: int,
    alg: int,
    order: int,
    cmd_extras: list[str],
) -> dict:
    try:
        solver_path = find_solver()
    except FileNotFoundError as e:
        return {"status": "error", "result": {"error": str(e)}}

    cmd: list[str] = [
        str(solver_path),
        "--puzzle",
        puzzle,
        "--alg",
        str(alg),
        "--timeout",
        str(timeout),
        "--verbose",
        "--threads",
        str(threads),
    ]
    cmd.extend(cmd_extras)

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )
        buffer_lines: list[str] = []

        def stdout_reader() -> None:
            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    buffer_lines.append(line)
                    m = BEST_GRID_RE.match(line)
                    if m and job_id is not None:
                        flat = m.group(2)
                        with _job_store_lock:
                            job = _job_store.get(job_id)
                            if job and job.get("status") == "pending":
                                _job_store[job_id] = {**job, "best_solution": flat}

        def stderr_reader() -> None:
            if proc.stderr:
                for line in iter(proc.stderr.readline, ""):
                    m = PROGRESS_RE.search(line)
                    if m and job_id is not None:
                        with _job_store_lock:
                            job = _job_store.get(job_id)
                            if job and job.get("status") == "pending":
                                _job_store[job_id] = {
                                    **job,
                                    "progress": {
                                        "iteration": int(m.group(1)),
                                        "filled": int(m.group(2)),
                                        "total": int(m.group(3)),
                                    },
                                }

        t_out = threading.Thread(target=stdout_reader, daemon=True)
        t_err = threading.Thread(target=stderr_reader, daemon=True)
        t_out.start()
        t_err.start()

        try:
            proc.wait(timeout=timeout + 15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise

        t_out.join(timeout=2.0)
        t_err.join(timeout=2.0)

        buffer = "".join(buffer_lines)
        stderr_tail = ""
        if proc.stderr:
            try:
                stderr_tail = proc.stderr.read() or ""
            except OSError:
                pass

        parsed = parse_verbose_stdout(buffer, order=order)

        if proc.returncode != 0 and parsed["success"] is None:
            parsed["raw_error"] = stderr_tail.strip() or f"Exit code {proc.returncode}"

        return {
            "status": "done",
            "result": {
                "success": parsed["success"],
                "solution": parsed["solution"],
                "time": parsed["time"],
                "iterations": parsed["iterations"],
                "communication": parsed["communication"],
                "error": parsed.get("raw_error"),
            },
            "best_solution": parsed["solution"],
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "result": {"error": "Solver timeout"}}
    except Exception as e:
        return {"status": "error", "result": {"error": str(e)}}


def _worker(
    job_id: str,
    puzzle: str,
    timeout: int,
    threads: int,
    alg: int,
    order: int,
    cmd_extras: list[str],
) -> None:
    try:
        outcome = _run_solver_sync(job_id, puzzle, timeout, threads, alg, order, cmd_extras)
    except Exception as e:
        outcome = {"status": "error", "result": {"error": str(e)}}
    with _job_store_lock:
        existing = _job_store.get(job_id, {})
        _job_store[job_id] = {
            "status": outcome["status"],
            "result": outcome.get("result"),
            "best_solution": outcome.get("best_solution") or existing.get("best_solution"),
            "progress": existing.get("progress"),
        }


@app.route("/")
def menu():
    return render_template("menu.html")


@app.route("/play")
def play_page():
    return render_template("index.html")


@app.route("/create")
def create_page():
    return render_template("create.html")


@app.route("/about")
def about_page():
    return render_template("about.html")


@app.route("/logo")
def logo():
    directory = Path(app.root_path)
    for name in ("SudoPhase_Logo.png", "templates/SudoPhase_Logo.png"):
        path = directory / name
        if path.is_file():
            return send_from_directory(directory, name)
    return send_from_directory(directory, "static/logo.png")


@app.route("/api/library", methods=["GET"])
def library():
    """GET /api/library — instances under paquita-database, 16x16-database, 25x25."""
    return jsonify(_list_library())


@app.route("/api/instance/<path:filename>", methods=["GET"])
def get_instance(filename: str):
    """GET /api/instance/<folder>/<file>.txt — folder must be an allowed library directory."""
    parts = filename.replace("\\", "/").strip("/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        return jsonify({"error": "Invalid filename"}), 400
    if len(parts) != 2:
        return jsonify({"error": "Invalid path; expected folder/file.txt"}), 400
    folder, basename = parts[0], parts[1]
    if folder not in ALLOWED_LIBRARY_DIRS:
        return jsonify({"error": "Unknown library folder"}), 400
    if Path(basename).name != basename:
        return jsonify({"error": "Invalid filename"}), 400

    allowed_root = (INSTANCES_ROOT / folder).resolve()
    path = (INSTANCES_ROOT / folder / basename).resolve()
    try:
        path.relative_to(allowed_root)
    except ValueError:
        return jsonify({"error": "Instance not found"}), 404
    if not path.is_file():
        return jsonify({"error": "Instance not found"}), 404
    try:
        order, puzzle = _read_instance_file(path)
        return jsonify({"order": order, "puzzle": puzzle})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/solve", methods=["POST"])
def solve():
    """
    POST JSON: puzzle, order, timeout, threads, alg (0|3|4), plus optional ACO / comm fields.
    """
    try:
        data = request.get_json() or {}
        puzzle = (data.get("puzzle") or "").strip()
        if not puzzle:
            return jsonify({"error": "Missing or empty 'puzzle'"}), 400
        order = int(data.get("order", 3))
        expected_len = order**4
        if len(puzzle) != expected_len:
            return jsonify({"error": f"Puzzle must be {expected_len} characters for order {order}"}), 400
        timeout = int(data.get("timeout", 120))
        threads = int(data.get("threads", 5))
        alg = int(data.get("alg", 4))
        if alg not in ALLOWED_ALGORITHMS:
            return jsonify({"error": "Invalid algorithm; allowed values are 0, 3, and 4."}), 400

        cmd_extras = _build_cmd_extras(data)

        job_id = str(uuid.uuid4())
        with _job_store_lock:
            _job_store[job_id] = {
                "status": "pending",
                "result": None,
                "best_solution": None,
                "progress": None,
            }

        t = threading.Thread(
            target=_worker,
            args=(job_id, puzzle, timeout, threads, alg, order, cmd_extras),
            daemon=True,
        )
        t.start()

        return jsonify({"job_id": job_id}), 202
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status/<job_id>", methods=["GET"])
def status(job_id: str):
    with _job_store_lock:
        job = _job_store.get(job_id)
    if not job:
        return jsonify({"error": "Unknown job_id"}), 404
    return jsonify(job)


if __name__ == "__main__":
    import sys

    host = "0.0.0.0" if "--public" in sys.argv else "127.0.0.1"
    app.run(host=host, port=5000, debug=False)
