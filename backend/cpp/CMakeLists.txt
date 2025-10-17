cmake_minimum_required(VERSION 3.10)
project(tcdd_cpp_server)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Output executable to backend/ directory
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/..)

# Find required packages
find_package(OpenCV REQUIRED)
find_package(Threads REQUIRED)

# NCNN (you may need to specify NCNN_DIR if not in standard path)
# set(NCNN_DIR "/path/to/ncnn")
find_package(ncnn REQUIRED)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${OpenCV_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party
)

# Source files
set(SOURCES
    main.cpp
    camera.cpp
    detector.cpp
    http_server.cpp
    config_loader.cpp
    logger.cpp
    logging_flags.cpp
)

set(HEADERS
    camera.h
    detector.h
    http_server.h
    config_loader.h
    logger.h
    logging_flags.h
)

# Create executable
add_executable(cpp_server ${SOURCES} ${HEADERS})

# Link libraries
target_link_libraries(cpp_server
    ${OpenCV_LIBS}
    ncnn
    Threads::Threads
)

# Platform-specific libraries
if(UNIX AND NOT APPLE)
    target_link_libraries(cpp_server pthread dl)
endif()

# Compiler flags
if(CMAKE_BUILD_TYPE MATCHES Debug)
    target_compile_options(cpp_server PRIVATE -g -O0 -Wall -Wextra)
else()
    target_compile_options(cpp_server PRIVATE -O3 -march=native)
endif()

# Install target
install(TARGETS cpp_server DESTINATION ${CMAKE_SOURCE_DIR}/..)
