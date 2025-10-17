#pragma once

#include <opencv2/opencv.hpp>
#include <string>
#include <memory>
#include <mutex>
#include <atomic>

/**
 * Camera - Handles video capture from Raspberry Pi camera or video file
 * Uses OpenCV VideoCapture with libcamera backend on Pi
 */
class Camera {
public:
    Camera();
    ~Camera();
    
    // Initialize camera with config
    bool initialize(int width, int height, int fps, int bufferSize = 1);
    
    // Initialize with video file for testing
    bool initializeFromFile(const std::string& videoPath);
    
    // Capture a frame (thread-safe)
    bool captureFrame(cv::Mat& frame);
    
    // Get current frame (non-blocking)
    bool getCurrentFrame(cv::Mat& frame);
    
    // Check if camera is opened
    bool isOpened() const;
    
    // Release camera resources
    void release();
    
    // Get camera properties
    int getWidth() const { return width; }
    int getHeight() const { return height; }
    int getFps() const { return fps; }
    
private:
    cv::VideoCapture capture;
    cv::Mat currentFrame;
    std::mutex frameMutex;
    std::atomic<bool> opened{false};
    
    int width = 640;
    int height = 480;
    int fps = 30;
    int bufferSize = 1;
    bool usingFile = false;
    
    // Try different camera backends
    bool tryOpenCamera(int cameraIndex);
};
