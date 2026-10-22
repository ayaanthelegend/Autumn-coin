cmake_minimum_required(VERSION 3.20)
project(autumn_sph CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenMP REQUIRED)

include_directories(
    include
    third_party
)

set(SPH_SOURCES
    src/kernels.cpp
    src/spatial_hash.cpp
    src/rigid_ellipse.cpp
    src/sph_solver.cpp
    src/software_renderer.cpp
    src/validation_tests.cpp
)

add_library(sph_core STATIC ${SPH_SOURCES})
target_link_libraries(sph_core PUBLIC OpenMP::OpenMP_CXX)

add_executable(sph_runner src/main_cli.cpp)
target_link_libraries(sph_runner PRIVATE sph_core)

if (WIN32)
    add_executable(sph_viewer src/main_viewer.cpp)
    target_link_libraries(sph_viewer PRIVATE sph_core user32 gdi32)
endif ()
