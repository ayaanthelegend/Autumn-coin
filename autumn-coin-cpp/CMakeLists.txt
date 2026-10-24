cmake_minimum_required(VERSION 3.20)
set(CMAKE_POLICY_VERSION_MINIMUM 3.5 CACHE STRING "" FORCE)
project(autumn_coin_cpp VERSION 1.0.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(AUTUMN_BUILD_VIZ "Build the GUI visualizer (requires OpenGL/X11 on Linux)" ON)

# Dependencies via FetchContent
include(FetchContent)

# 1. yaml-cpp (Required for autumn_core)
FetchContent_Declare(
    yaml-cpp
    GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
    GIT_TAG 0.8.0
)
set(YAML_CPP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(YAML_CPP_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(yaml-cpp)

# -------------------------------------------------------------
# Optional GUI Dependencies (raylib + Dear ImGui + ImPlot)
# -------------------------------------------------------------
if(AUTUMN_BUILD_VIZ)
    # 2. raylib
    FetchContent_Declare(
        raylib
        GIT_REPOSITORY https://github.com/raysan5/raylib.git
        GIT_TAG 5.5
    )
    set(BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(raylib)

    # 3. Dear ImGui
    FetchContent_Declare(
        imgui
        GIT_REPOSITORY https://github.com/ocornut/imgui.git
        GIT_TAG v1.91.5
    )
    FetchContent_GetProperties(imgui)
    if(NOT imgui_POPULATED)
        FetchContent_Populate(imgui)
        add_library(imgui STATIC
            ${imgui_SOURCE_DIR}/imgui.cpp
            ${imgui_SOURCE_DIR}/imgui_draw.cpp
            ${imgui_SOURCE_DIR}/imgui_tables.cpp
            ${imgui_SOURCE_DIR}/imgui_widgets.cpp
        )
        target_include_directories(imgui PUBLIC ${imgui_SOURCE_DIR})
        if(MSVC)
            target_compile_definitions(imgui PUBLIC NOMINMAX _USE_MATH_DEFINES)
        endif()
    endif()

    # 4. ImPlot
    FetchContent_Declare(
        implot
        GIT_REPOSITORY https://github.com/epezent/implot.git
        GIT_TAG v0.16
    )
    FetchContent_GetProperties(implot)
    if(NOT implot_POPULATED)
        FetchContent_Populate(implot)
        add_library(implot STATIC
            ${implot_SOURCE_DIR}/implot.cpp
            ${implot_SOURCE_DIR}/implot_items.cpp
        )
        target_include_directories(implot PUBLIC ${implot_SOURCE_DIR})
        target_link_libraries(implot PUBLIC imgui)
        if(MSVC)
            target_compile_definitions(implot PUBLIC NOMINMAX _USE_MATH_DEFINES)
        endif()
    endif()
endif()

# -------------------------------------------------------------
# autumn_core Static Library (Zero Graphics Dependencies)
# -------------------------------------------------------------
add_library(autumn_core STATIC
    src/model.cpp
    src/integrator.cpp
    src/config.cpp
    src/regime.cpp
    src/tank.cpp
    src/sweep.cpp
)

target_include_directories(autumn_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(autumn_core PUBLIC
    yaml-cpp
)

if(MSVC)
    target_compile_definitions(autumn_core PUBLIC NOMINMAX _USE_MATH_DEFINES _CRT_SECURE_NO_WARNINGS)
    target_compile_options(autumn_core PUBLIC /W3 /permissive- /we4062)
else()
    target_compile_options(autumn_core PUBLIC -Wall -Wextra -Wswitch -Werror)
endif()

# -------------------------------------------------------------
# autumn_tests Executable (Unit Tests 1 - 9)
# -------------------------------------------------------------
enable_testing()

add_executable(autumn_tests
    tests/test_main.cpp
    tests/test_model.cpp
    tests/test_symmetries.cpp
    tests/test_energy.cpp
    tests/test_python_parity.cpp
)

target_include_directories(autumn_tests PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party
)

target_link_libraries(autumn_tests PRIVATE
    autumn_core
)

if(MSVC)
    target_compile_definitions(autumn_tests PRIVATE NOMINMAX _USE_MATH_DEFINES _CRT_SECURE_NO_WARNINGS)
endif()

add_test(NAME autumn_tests COMMAND autumn_tests)

# -------------------------------------------------------------
# autumn_viz Executable (raylib + Dear ImGui + ImPlot)
# -------------------------------------------------------------
if(AUTUMN_BUILD_VIZ)
    add_executable(autumn_viz
        src/main.cpp
        src/render.cpp
        src/plots.cpp
        src/ui.cpp
        third_party/rlImGui/rlImGui.cpp
    )

    target_include_directories(autumn_viz PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/rlImGui
    )

    target_compile_definitions(autumn_viz PRIVATE
        NO_FONT_AWESOME
    )

    target_link_libraries(autumn_viz PRIVATE
        autumn_core
        raylib
        imgui
        implot
    )

    if(MSVC)
        target_compile_definitions(autumn_viz PRIVATE NOMINMAX _USE_MATH_DEFINES _CRT_SECURE_NO_WARNINGS)
    endif()
endif()
