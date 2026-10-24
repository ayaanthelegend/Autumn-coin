"""Build script for C++ SPH solver on Windows / Linux / macOS."""

import os
import subprocess
import sys
from pathlib import Path

def build_sph():
    script_dir = Path(__file__).resolve().parent
    vcvars_path = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat"
    
    bin_dir = script_dir / "bin"
    bin_dir.mkdir(exist_ok=True)
    build_dir = script_dir / "build"
    build_dir.mkdir(exist_ok=True)
    exe_target = bin_dir / ("sph_runner.exe" if sys.platform == "win32" else "sph_runner")
    viewer_target = bin_dir / ("sph_viewer.exe" if sys.platform == "win32" else "sph_viewer")
    
    src_files = [
        str(script_dir / "src" / "kernels.cpp"),
        str(script_dir / "src" / "spatial_hash.cpp"),
        str(script_dir / "src" / "rigid_ellipse.cpp"),
        str(script_dir / "src" / "sph_solver.cpp"),
        str(script_dir / "src" / "software_renderer.cpp"),
        str(script_dir / "src" / "validation_tests.cpp"),
        str(script_dir / "src" / "main_cli.cpp"),
    ]

    viewer_src_files = [
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
        print(f"[Build] Using MSVC via {vcvars_path}...")
        sources_str = " ".join(f'"{f}"' for f in src_files)
        inc_str = " ".join(f'"{d}"' for d in include_dirs)
        build_dir_str = str(build_dir).replace("\\", "/") + "/"
        out_str = f'/Fe:"{exe_target}" /Fo"{build_dir_str}"'
        
        cmd = f'call "{vcvars_path}" x64 && cl /nologo /std:c++20 /O2 /openmp /EHsc /utf-8 /DNOMINMAX /D_USE_MATH_DEFINES {inc_str} {sources_str} {out_str}'
        res = subprocess.run(cmd, shell=True, cwd=str(script_dir))
        if res.returncode != 0:
            print("[Build Error] MSVC runner build failed.")
            sys.exit(res.returncode)
        print(f"[Build Success] Compiled executable: {exe_target}")

        print(f"[Build] Compiling native Win32 60 FPS viewer: {viewer_target}...")
        v_sources_str = " ".join(f'"{f}"' for f in viewer_src_files)
        v_out_str = f'/Fe:"{viewer_target}" /Fo"{build_dir_str}"'
        v_libs = "user32.lib gdi32.lib"
        v_cmd = f'call "{vcvars_path}" x64 && cl /nologo /std:c++20 /O2 /openmp /EHsc /utf-8 /DNOMINMAX /D_USE_MATH_DEFINES {inc_str} {v_sources_str} {v_libs} {v_out_str}'
        res_v = subprocess.run(v_cmd, shell=True, cwd=str(script_dir))
        if res_v.returncode != 0:
            print("[Build Error] MSVC viewer build failed.")
            sys.exit(res_v.returncode)
        print(f"[Build Success] Compiled executable: {viewer_target}")
        return exe_target
    else:
        print("[Build] Attempting build with g++ / clang++...")
        compiler = "g++" if subprocess.run(["where", "g++"], shell=True, capture_output=True).returncode == 0 else "clang++"
        cmd = [compiler, "-std=c++20", "-O3", "-fopenmp", "-Wall"] + [f"-I{script_dir / 'include'}", f"-I{script_dir / 'third_party'}"] + src_files + ["-o", str(exe_target)]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print("[Build Error] Fallback compiler failed.")
            sys.exit(res.returncode)
        print(f"[Build Success] Compiled executable: {exe_target}")
        return exe_target

if __name__ == "__main__":
    build_sph()
