"""Build script for native 60 FPS Win32/OpenGL visualizer executable (sph_viewer.exe)."""

import os
import subprocess
import sys
from pathlib import Path

def build_viewer():
    script_dir = Path(__file__).resolve().parent
    vcvars_path = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat"
    
    bin_dir = script_dir / "bin"
    bin_dir.mkdir(exist_ok=True)
    exe_target = bin_dir / ("sph_viewer.exe" if sys.platform == "win32" else "sph_viewer")
    
    src_files = [
        str(script_dir / "src" / "kernels.cpp"),
        str(script_dir / "src" / "spatial_hash.cpp"),
        str(script_dir / "src" / "rigid_ellipse.cpp"),
        str(script_dir / "src" / "sph_solver.cpp"),
        str(script_dir / "src" / "software_renderer.cpp"),
        str(script_dir / "src" / "main_viewer.cpp"),
    ]
    
    include_dirs = [
        f"/I{script_dir / 'include'}",
        f"/I{script_dir / 'third_party'}",
    ]
    
    if sys.platform == "win32" and os.path.exists(vcvars_path):
        print(f"[Build Viewer] Using MSVC via {vcvars_path}...")
        sources_str = " ".join(f'"{f}"' for f in src_files)
        inc_str = " ".join(f'"{d}"' for d in include_dirs)
        out_str = f'/Fe:"{exe_target}"'
        libs = "user32.lib gdi32.lib"
        
        cmd = f'call "{vcvars_path}" x64 && cl /nologo /std:c++20 /O2 /openmp /EHsc /utf-8 /DNOMINMAX /D_USE_MATH_DEFINES {inc_str} {sources_str} {libs} {out_str}'
        res = subprocess.run(cmd, shell=True, cwd=str(script_dir))
        if res.returncode != 0:
            print("[Build Error] MSVC viewer build failed.")
            sys.exit(res.returncode)
        print(f"[Build Success] Compiled executable: {exe_target}")
        return exe_target
    else:
        print("[Build] Fallback build...")
        compiler = "g++"
        libs = ["-luser32", "-lgdi32"] if sys.platform == "win32" else []
        cmd = [compiler, "-std=c++20", "-O3", "-fopenmp", "-Wall"] + [f"-I{script_dir / 'include'}", f"-I{script_dir / 'third_party'}"] + src_files + libs + ["-o", str(exe_target)]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print("[Build Error] Fallback compiler failed.")
            sys.exit(res.returncode)
        print(f"[Build Success] Compiled executable: {exe_target}")
        return exe_target

if __name__ == "__main__":
    build_viewer()
