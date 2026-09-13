cmake_minimum_required(VERSION 3.16)
set(CMAKE_POLICY_VERSION_MINIMUM 3.5)
project(neon_pong VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(BUILD_GAMES OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
add_subdirectory(vendor/raylib)

add_executable(pong main.cpp)
target_link_libraries(pong PRIVATE raylib)

if(MSVC)
    set_property(TARGET pong PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
    target_compile_options(pong PRIVATE /W4 /permissive-)
else()
    target_compile_options(pong PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(APPLE)
    target_link_libraries(pong PRIVATE "-framework IOKit" "-framework Cocoa" "-framework OpenGL")
endif()

# Windows frame transport avoids PNG compression.
target_compile_definitions(raylib PRIVATE SUPPORT_FILEFORMAT_BMP)
