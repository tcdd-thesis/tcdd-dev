#include "logger.h"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <filesystem>
#include <ctime>

// Platform-specific includes for system metrics
#ifdef __linux__
#include <sys/sysinfo.h>
#include <unistd.h>
#include <fstream>
#endif

namespace fs = std::filesystem;

Logger& Logger::getInstance() {
    static Logger instance;
    return instance;
}

bool Logger::initialize(const std::string& logPath) {
    std::lock_guard<std::mutex> lock(logMutex);
    
    if (initialized) {
        std::cerr << "Logger already initialized." << std::endl;
        return true;
    }
    
    try {
        // Create log directory if it doesn't exist
        fs::path logDir(logPath);
        if (!fs::exists(logDir)) {
            fs::create_directories(logDir);
        }
        
        // Create log file with timestamp
        logFilePath = createLogFilePath(logPath);
        
        logFile.open(logFilePath, std::ios::out | std::ios::app);
        if (!logFile.is_open()) {
            std::cerr << "Failed to open log file: " << logFilePath << std::endl;
            return false;
        }
        
        // Write header if file is new
        logFile.seekp(0, std::ios::end);
        if (logFile.tellp() == 0) {
            writeHeader();
        }
        
        initialized = true;
        std::cout << "✓ Logger initialized: " << logFilePath << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Error initializing logger: " << e.what() << std::endl;
        return false;
    }
}

std::string Logger::createLogFilePath(const std::string& logPath) {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    
    std::ostringstream oss;
    oss << logPath;
    if (logPath.back() != '/') {
        oss << '/';
    }
    oss << "performance_"
        << std::put_time(std::localtime(&time_t), "%Y%m%d_%H%M%S")
        << ".csv";
    
    return oss.str();
}

void Logger::writeHeader() {
    logFile << "timestamp,fps,inference_time_ms,detections_count,"
            << "cpu_usage_percent,ram_usage_mb,camera_frame_time_ms,"
            << "jpeg_encode_time_ms,total_detections,dropped_frames,queue_size\n";
    logFile.flush();
}

std::string Logger::getTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;
    
    std::ostringstream oss;
    oss << std::put_time(std::localtime(&time_t), "%Y-%m-%dT%H:%M:%S")
        << '.' << std::setfill('0') << std::setw(3) << ms.count();
    
    return oss.str();
}

void Logger::logMetrics(const Metrics& metrics) {
    if (!initialized) {
        return;
    }
    
    std::lock_guard<std::mutex> lock(logMutex);
    
    logFile << getTimestamp() << ","
            << metrics.fps << ","
            << metrics.inference_time_ms << ","
            << metrics.detections_count << ","
            << metrics.cpu_usage_percent << ","
            << metrics.ram_usage_mb << ","
            << metrics.camera_frame_time_ms << ","
            << metrics.jpeg_encode_time_ms << ","
            << metrics.total_detections << ","
            << metrics.dropped_frames << ","
            << metrics.queue_size << "\n";
    
    logFile.flush();
}

void Logger::close() {
    std::lock_guard<std::mutex> lock(logMutex);
    
    if (logFile.is_open()) {
        logFile.close();
        initialized = false;
        std::cout << "✓ Logger closed." << std::endl;
    }
}

// Platform-specific system metrics
double Logger::getCpuUsage() {
#ifdef __linux__
    static unsigned long long lastTotalUser = 0, lastTotalUserLow = 0;
    static unsigned long long lastTotalSys = 0, lastTotalIdle = 0;
    
    std::ifstream file("/proc/stat");
    if (!file.is_open()) {
        return 0.0;
    }
    
    std::string line;
    std::getline(file, line);
    file.close();
    
    unsigned long long totalUser, totalUserLow, totalSys, totalIdle;
    std::istringstream iss(line);
    std::string cpu;
    iss >> cpu >> totalUser >> totalUserLow >> totalSys >> totalIdle;
    
    if (lastTotalUser == 0) {
        lastTotalUser = totalUser;
        lastTotalUserLow = totalUserLow;
        lastTotalSys = totalSys;
        lastTotalIdle = totalIdle;
        return 0.0;
    }
    
    unsigned long long total = (totalUser - lastTotalUser) + 
                                (totalUserLow - lastTotalUserLow) +
                                (totalSys - lastTotalSys);
    unsigned long long idle = totalIdle - lastTotalIdle;
    
    double percent = (total - idle) * 100.0 / total;
    
    lastTotalUser = totalUser;
    lastTotalUserLow = totalUserLow;
    lastTotalSys = totalSys;
    lastTotalIdle = totalIdle;
    
    return percent;
#else
    return 0.0; // Not implemented for non-Linux
#endif
}

double Logger::getRamUsageMB() {
#ifdef __linux__
    struct sysinfo memInfo;
    if (sysinfo(&memInfo) != 0) {
        return 0.0;
    }
    
    long long totalVirtualMem = memInfo.totalram;
    long long virtualMemUsed = memInfo.totalram - memInfo.freeram;
    
    // Convert to MB
    return (virtualMemUsed / 1024.0 / 1024.0);
#else
    return 0.0; // Not implemented for non-Linux
#endif
}
