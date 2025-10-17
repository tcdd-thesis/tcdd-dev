#pragma once

#include <string>
#include <fstream>
#include <mutex>
#include <chrono>

/**
 * Logger - Handles CSV logging of performance metrics
 * Logs metrics like FPS, inference time, CPU/RAM usage, etc.
 */
class Logger {
public:
    struct Metrics {
        double fps = 0.0;
        double inference_time_ms = 0.0;
        int detections_count = 0;
        double cpu_usage_percent = 0.0;
        double ram_usage_mb = 0.0;
        double camera_frame_time_ms = 0.0;
        double jpeg_encode_time_ms = 0.0;
        int total_detections = 0;
        int dropped_frames = 0;
        int queue_size = 0;
    };

    static Logger& getInstance();
    
    // Delete copy constructor and assignment operator
    Logger(const Logger&) = delete;
    Logger& operator=(const Logger&) = delete;
    
    // Initialize logger with config
    bool initialize(const std::string& logPath);
    
    // Log metrics to CSV
    void logMetrics(const Metrics& metrics);
    
    // Close the log file
    void close();
    
    // Get current timestamp in ISO 8601 format
    static std::string getTimestamp();
    
    // Get system metrics
    static double getCpuUsage();
    static double getRamUsageMB();

private:
    Logger() = default;
    ~Logger() { close(); }
    
    std::ofstream logFile;
    std::mutex logMutex;
    std::string logFilePath;
    bool initialized = false;
    
    // Create log file with timestamp
    std::string createLogFilePath(const std::string& logPath);
    
    // Write CSV header
    void writeHeader();
};
