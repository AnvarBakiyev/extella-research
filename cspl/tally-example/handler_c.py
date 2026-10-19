def c(code = "", filtered_source_code = "", func_name = "", **extra):
    # Handler of the language "c": compiles the expert's source with the device's C compiler and runs the binary.
    import os, platform, shutil, socket, subprocess, tempfile
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        return {"status": "failed", "reason": "no C compiler on this device"}
    work = tempfile.mkdtemp(prefix="cspl_c_")
    src, exe = os.path.join(work, "main.c"), os.path.join(work, "main")
    open(src, "w").write(code or filtered_source_code or "")
    build = subprocess.run([cc, src, "-O2", "-o", exe], capture_output=True, text=True, timeout=60)
    if build.returncode != 0:
        return {"status": "failed", "stage": "compile", "stderr": build.stderr[-400:]}
    run = subprocess.run([exe], capture_output=True, text=True, timeout=30)
    shutil.rmtree(work, ignore_errors=True)
    return {"status": "success" if run.returncode == 0 else "failed", "language": "c", "expert": func_name, "stdout": run.stdout[-2000:], "returncode": run.returncode,
            "compiler": cc, "host": socket.gethostname(), "os": platform.system() + " " + platform.machine()}
