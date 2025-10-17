#include "camera.h"
#include "logging_flags.h"
#include <iostream>

Camera::Camera() {}

Camera::~Camera() {
    release();
}

bool Camera::initialize(int width, int height, int fps, int bufferSize) {
    this->width = width;
    this->height = height;
    this->fps = fps;
    this->bufferSize = bufferSize;
    this->usingFile = false;
    
    std::cout << "Initializing camera: " << width << "x" << height 
              << " @ " << fps << " FPS" << std::endl;
    
    // Try different camera backends in order of preference
    // 1. Try libcamera (Raspberry Pi Camera Module V3)
    if (tryOpenCamera(0)) {
        std::cout << "✓ Camera opened successfully" << std::endl;
        return true;
    }
    
    std::cerr << "✗ Failed to open camera" << std::endl;
    return false;
}

bool Camera::tryOpenCamera(int cameraIndex) {
    // Try different backends in order
    std::vector<std::pair<std::string, int>> backends = {
        {"GStreamer", cv::CAP_GSTREAMER},
        {"V4L2", cv::CAP_V4L2},
        {"ANY", cv::CAP_ANY}
    };
    
    for (const auto& [name, backend] : backends) {
        std::cout << "  Trying " << name << " backend..." << std::endl;
        
        if (backend == cv::CAP_GSTREAMER) {
            // GStreamer pipeline for libcamera (Raspberry Pi Camera Module V3)
            std::string pipeline = "libcamerasrc ! video/x-raw,width=" + std::to_string(width) + 
                                   ",height=" + std::to_string(height) + 
                                   ",framerate=" + std::to_string(fps) + "/1 ! videoconvert ! appsink";
            capture.open(pipeline, cv::CAP_GSTREAMER);
        } else {
            capture.open(cameraIndex, backend);
        }
        
        if (capture.isOpened()) {
            // Test if we can actually read a frame
            cv::Mat testFrame;
            if (capture.read(testFrame) && !testFrame.empty()) {
                std::cout << "  ✓ " << name << " backend works!" << std::endl;
                
                // Set camera properties (may not work for all backends)
                capture.set(cv::CAP_PROP_FRAME_WIDTH, width);
                capture.set(cv::CAP_PROP_FRAME_HEIGHT, height);
                capture.set(cv::CAP_PROP_FPS, fps);
                capture.set(cv::CAP_PROP_BUFFERSIZE, bufferSize);
                
                // Verify settings
                int actualWidth = capture.get(cv::CAP_PROP_FRAME_WIDTH);
                int actualHeight = capture.get(cv::CAP_PROP_FRAME_HEIGHT);
                int actualFps = capture.get(cv::CAP_PROP_FPS);
                
                std::cout << "  Actual resolution: " << actualWidth << "x" << actualHeight 
                          << " @ " << actualFps << " FPS" << std::endl;
                
                opened = true;
                return true;
            } else {
                std::cout << "  ✗ " << name << " opened but cannot read frames" << std::endl;
                capture.release();
            }
        } else {
            std::cout << "  ✗ " << name << " backend failed to open" << std::endl;
        }
    }
    
    return false;
}

bool Camera::initializeFromFile(const std::string& videoPath) {
    std::cout << "Initializing from video file: " << videoPath << std::endl;
    
    capture.open(videoPath);
    if (!capture.isOpened()) {
        std::cerr << "✗ Failed to open video file: " << videoPath << std::endl;
        return false;
    }
    
    // Get video properties
    width = capture.get(cv::CAP_PROP_FRAME_WIDTH);
    height = capture.get(cv::CAP_PROP_FRAME_HEIGHT);
    fps = capture.get(cv::CAP_PROP_FPS);
    
    std::cout << "✓ Video opened: " << width << "x" << height 
              << " @ " << fps << " FPS" << std::endl;
    
    usingFile = true;
    opened = true;
    return true;
}

bool Camera::captureFrame(cv::Mat& frame) {
    if (!opened) {
        if (Logging::verbose) {
            std::cout << "[CAMERA] Error: Camera not opened" << std::endl;
        }
        return false;
    }
    
    std::lock_guard<std::mutex> lock(frameMutex);
    
    static int captureCount = 0;
    captureCount++;
    
    if (!capture.read(frame)) {
        // If using video file, loop back to start
        if (usingFile) {
            if (Logging::verbose) {
                std::cout << "[CAMERA] Video file ended, looping back to start" << std::endl;
            }
            capture.set(cv::CAP_PROP_POS_FRAMES, 0);
            if (!capture.read(frame)) {
                if (Logging::verbose) {
                    std::cout << "[CAMERA] Error: Failed to read from video file after loop" << std::endl;
                }
                return false;
            }
        } else {
            if (Logging::verbose) {
                std::cout << "[CAMERA] Error: Failed to read from camera" << std::endl;
            }
            return false;
        }
    }
    
    if (frame.empty()) {
        if (Logging::verbose) {
            std::cout << "[CAMERA] Error: Captured frame is empty" << std::endl;
        }
        return false;
    }
    
    if (Logging::verbose && captureCount % 100 == 1) {
        std::cout << "[CAMERA] Captured frame #" << captureCount 
                  << " (" << frame.cols << "x" << frame.rows << ")" << std::endl;
    }
    
    // Store current frame
    currentFrame = frame.clone();
    
    return true;
}

bool Camera::getCurrentFrame(cv::Mat& frame) {
    std::lock_guard<std::mutex> lock(frameMutex);
    
    if (currentFrame.empty()) {
        return false;
    }
    
    frame = currentFrame.clone();
    return true;
}

bool Camera::isOpened() const {
    return opened;
}

void Camera::release() {
    if (opened) {
        std::lock_guard<std::mutex> lock(frameMutex);
        capture.release();
        opened = false;
        std::cout << "✓ Camera released" << std::endl;
    }
}
