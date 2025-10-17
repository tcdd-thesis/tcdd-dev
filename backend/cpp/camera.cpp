#include "camera.h"
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
    // Try V4L2 backend (common on Linux/Pi)
    capture.open(cameraIndex, cv::CAP_V4L2);
    
    if (!capture.isOpened()) {
        // Fallback to default backend
        capture.open(cameraIndex);
    }
    
    if (!capture.isOpened()) {
        return false;
    }
    
    // Set camera properties
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
        return false;
    }
    
    std::lock_guard<std::mutex> lock(frameMutex);
    
    if (!capture.read(frame)) {
        // If using video file, loop back to start
        if (usingFile) {
            capture.set(cv::CAP_PROP_POS_FRAMES, 0);
            if (!capture.read(frame)) {
                return false;
            }
        } else {
            return false;
        }
    }
    
    if (frame.empty()) {
        return false;
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
