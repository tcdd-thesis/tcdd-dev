#pragma once

#include <string>
#include <vector>
#include <memory>
#include <thread>
#include <atomic>
#include <mutex>
#include <opencv2/opencv.hpp>
#include "detector.h"
#include "third_party/json.hpp"

using json = nlohmann::json;

/**
 * HttpServer - Handles HTTP API endpoints
 * Serves MJPEG video stream and detection data
 */
class HttpServer {
public:
    HttpServer();
    ~HttpServer();
    
    // Initialize server
    bool initialize(int port);
    
    // Start server (non-blocking)
    bool start();
    
    // Stop server
    void stop();
    
    // Update current frame (thread-safe)
    void updateFrame(const cv::Mat& frame);
    
    // Update detections (thread-safe)
    void updateDetections(const std::vector<Detection>& detections);
    
    // Update status metrics (thread-safe)
    void updateStatus(const json& status);
    
    // Set verbose logging
    static void setVerbose(bool enabled) { verboseLogging = enabled; }
    
    // Check if server is running
    bool isRunning() const { return running; }

private:
    int port = 5100;
    std::atomic<bool> running{false};
    std::unique_ptr<std::thread> serverThread;
    
    // Verbose logging flag
    static bool verboseLogging;
    
    // Shared data (protected by mutexes)
    cv::Mat currentFrame;
    std::mutex frameMutex;
    
    std::vector<Detection> currentDetections;
    std::mutex detectionsMutex;
    
    json currentStatus;
    std::mutex statusMutex;
    
    // JPEG encoding quality
    int jpegQuality = 80;
    
    // Server thread function
    void serverLoop();
    
    // Endpoint handlers
    std::string handleVideoFeed();
    std::string handleGetDetections();
    std::string handleGetStatus();
    std::string handleHealth();
    
    // Helper to encode frame as JPEG
    std::vector<uchar> encodeJpeg(const cv::Mat& frame);
    
    // Helper to build MJPEG boundary
    std::string buildMjpegBoundary(const std::vector<uchar>& jpegData);
};
