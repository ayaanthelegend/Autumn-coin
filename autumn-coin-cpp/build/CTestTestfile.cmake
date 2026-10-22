# CMake generated Testfile for 
# Source directory: D:/Autumn coin/autumn-coin-cpp
# Build directory: D:/Autumn coin/autumn-coin-cpp/build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test([=[autumn_tests]=] "D:/Autumn coin/autumn-coin-cpp/build/autumn_tests.exe")
set_tests_properties([=[autumn_tests]=] PROPERTIES  _BACKTRACE_TRIPLES "D:/Autumn coin/autumn-coin-cpp/CMakeLists.txt;124;add_test;D:/Autumn coin/autumn-coin-cpp/CMakeLists.txt;0;")
subdirs("_deps/yaml-cpp-build")
subdirs("_deps/raylib-build")
