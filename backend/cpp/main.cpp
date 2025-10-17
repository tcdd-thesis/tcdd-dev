#include <iostream>
#include <csignal>
#include <thread>
#include <chrono>
#include <atomic>
#include "config_loader.h"
#include "logger.h"
#include "camera.h"
#include "detector.h"
#include "http_server.h"
#include "logging_flags.h"

// Global flag for graceful shutdown
std::atomic<bool> g_running{true};

void signalHandler(int signum) {
    std::cout << "\n\nInterrupt signal (" << signum << ") received. Shutting down..." << std::endl;
    g_running = false;
}

void printBanner() {
    std::cout << "\n";
    std::cout << "╔════════════════════════════════════════════════╗\n";
    std::cout << "║   TCDD C++ Server - Traffic Sign Detection     ║\n";
    std::cout << "║   Real-time Object Detection on Raspberry Pi   ║\n";
    std::cout << "╚════════════════════════════════════════════════╝\n";
    std::cout << "\n";
}

void printUsage(const char* progName) {
    std::cout << "Usage: " << progName << " [OPTIONS]\n\n";
    std::cout << "Options:\n";
    std::cout << "  -h, --help        Show this help message\n";
    std::cout << "  -v, --vulkan      Enable Vulkan compute (if available)\n";
    std::cout << "  --verbose         Enable verbose logging\n";
    std::cout << "  --no-ml           Disable ML detection (camera feed only)\n";
    std::cout << "  -f, --file PATH   Use video file instead of camera\n";
    std::cout << "  -c, --config PATH Specify custom config file path\n";
    std::cout << "\n";
}

int main(int argc, char* argv[]) {
    // Parse command line arguments
    bool useVulkan = false;
    bool verboseLogging = false;
    bool disableML = false;
    std::string videoFile;
    std::string configPath;
    
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        
        if (arg == "-h" || arg == "--help") {
            printUsage(argv[0]);
            return 0;
        } else if (arg == "-v" || arg == "--vulkan") {
            useVulkan = true;
        } else if (arg == "--verbose") {
            verboseLogging = true;
        } else if (arg == "--no-ml") {
            disableML = true;
        } else if (arg == "-f" || arg == "--file") {
            if (i + 1 < argc) {
                videoFile = argv[++i];
            } else {
                std::cerr << "Error: --file requires a path argument" << std::endl;
                return 1;
            }
        } else if (arg == "-c" || arg == "--config") {
            if (i + 1 < argc) {
                configPath = argv[++i];
            } else {
                std::cerr << "Error: --config requires a path argument" << std::endl;
                return 1;
            }
        }
    }
    
    printBanner();
    
    // Set global verbose flag
    Logging::verbose = verboseLogging;
    HttpServer::setVerbose(verboseLogging);
    
    // Install signal handler
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    
    // Load configuration
    auto& config = ConfigLoader::getInstance();
    if (!config.loadConfig(configPath)) {
        std::cerr << "\n✗ Failed to load configuration file." << std::endl;
        std::cerr << "✗ The program cannot continue without a valid config file." << std::endl;
        
        if (configPath.empty()) {
            std::cerr << "\nExpected location: shared/config.json" << std::endl;
            std::cerr << "Or specify custom path: " << argv[0] << " --config /path/to/config.json" << std::endl;
        } else {
            std::cerr << "\nSpecified location: " << configPath << std::endl;
        }
        
        std::cerr << "\nPlease ensure:" << std::endl;
        std::cerr << "  1. The config file exists" << std::endl;
        std::cerr << "  2. The path is correct" << std::endl;
        std::cerr << "  3. The file has valid JSON syntax" << std::endl;
        std::cerr << "  4. You have read permissions\n" << std::endl;
        
        return 1;
    }
    
    // Initialize logger
    auto& logger = Logger::getInstance();
    std::string loggingPath = config.get<std::string>("logging.path", "logs/");
    if (!logger.initialize(loggingPath)) {
        std::cerr << "✗ Failed to initialize logger" << std::endl;
        return 1;
    }
    
    // Initialize camera
    Camera camera;
    if (!videoFile.empty()) {
        if (!camera.initializeFromFile(videoFile)) {
            std::cerr << "✗ Failed to initialize camera from file" << std::endl;
            return 1;
        }
    } else {
        if (!camera.initialize(
            config.get<int>("camera.width", 640),
            config.get<int>("camera.height", 480),
            config.get<int>("camera.fps", 30),
            config.get<int>("camera.bufferSize", 1)
        )) {
            std::cerr << "✗ Failed to initialize camera" << std::endl;
            return 1;
        }
    }
    
    // Initialize detector (skip if --no-ml flag is set)
    Detector detector;
    bool mlEnabled = !disableML;
    
    if (mlEnabled) {
        auto modelPaths = config.getArray<std::string>("detection.modelPath");
        if (modelPaths.size() < 2) {
            std::cerr << "✗ Invalid model path configuration. Need param and bin files." << std::endl;
            return 1;
        }
        
        if (!detector.initialize(
            modelPaths[0],  // param file
            modelPaths[1],  // bin file
            config.getArray<int>("detection.inputSize"),
            config.get<float>("detection.confidenceThreshold", 0.5f),
            config.get<float>("detection.nmsThreshold", 0.5f),
            config.get<float>("detection.iouThreshold", 0.5f),
            useVulkan || config.get<bool>("performance.useVulkan", false)
        )) {
            std::cerr << "✗ Failed to initialize detector" << std::endl;
            return 1;
        }
        
        // Try to load class names
        std::string labelsPath = config.get<std::string>("detection.labelsPath", "backend/model/labels.txt");
        if (!detector.loadClassNames(labelsPath)) {
            std::cerr << "⚠ Warning: Could not load class labels from: " << labelsPath << std::endl;
            std::cerr << "  Detections will use numeric class IDs instead of names." << std::endl;
        }
    } else {
        std::cout << "\n⚠ ML Detection DISABLED (--no-ml flag set)" << std::endl;
        std::cout << "  Camera feed will be shown without object detection\n" << std::endl;
    }
    
    // Initialize HTTP server
    HttpServer server;
    int serverPort = config.get<int>("cppServerPort", 5100);
    if (!server.initialize(serverPort)) {
        std::cerr << "✗ Failed to initialize HTTP server" << std::endl;
        return 1;
    }
    
    if (!server.start()) {
        std::cerr << "✗ Failed to start HTTP server" << std::endl;
        return 1;
    }
    
    std::cout << "\n✓ All systems initialized successfully\n";
    std::cout << "✓ Server running on port " << serverPort << "\n";
    std::cout << "✓ Press Ctrl+C to stop\n\n";
    
    if (verboseLogging) {
        std::cout << "════════════════════════════════════════════════\n";
        std::cout << "Verbose logging enabled:\n";
        std::cout << "  [HTTP]     - HTTP requests and responses\n";
        std::cout << "  [API]      - API endpoint calls\n";
        std::cout << "  [SERVER]   - Server data updates\n";
        std::cout << "  [CAMERA]   - Camera frame capture\n";
        std::cout << "  [DETECTOR] - Object detection operations\n";
        std::cout << "════════════════════════════════════════════════\n\n";
    }
    
    // Main processing loop
    Logger::Metrics metrics;
    int frameCount = 0;
    int totalDetections = 0;
    int droppedFrames = 0;
    
    auto fpsStart = std::chrono::high_resolution_clock::now();
    auto lastLogTime = std::chrono::high_resolution_clock::now();
    int metricsInterval = config.get<int>("logging.metricsInterval", 1000);
    
    while (g_running) {
        auto frameStart = std::chrono::high_resolution_clock::now();
        
        static int mainLoopCount = 0;
        mainLoopCount++;
        
        // Capture frame
        cv::Mat frame;
        if (!camera.captureFrame(frame)) {
            droppedFrames++;
            if (verboseLogging && droppedFrames % 10 == 1) {
                std::cout << "[CAMERA] Warning: Failed to capture frame (dropped: " 
                          << droppedFrames << ")" << std::endl;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }
        
        if (verboseLogging && mainLoopCount % 100 == 1) {
            std::cout << "[MAIN] Processing frame #" << mainLoopCount 
                      << " (" << frame.cols << "x" << frame.rows << ")" << std::endl;
        }
        
        auto captureEnd = std::chrono::high_resolution_clock::now();
        metrics.camera_frame_time_ms = 
            std::chrono::duration<double, std::milli>(captureEnd - frameStart).count();
        
        // Run detection (skip if --no-ml flag is set)
        std::vector<Detection> detections;
        if (mlEnabled) {
            detections = detector.detect(frame);
            metrics.inference_time_ms = detector.getInferenceTime();
            metrics.detections_count = detections.size();
            totalDetections += detections.size();
            metrics.total_detections = totalDetections;
            
            // Draw detections on frame
            Detector::drawDetections(frame, detections);
        } else {
            // ML disabled - no inference
            metrics.inference_time_ms = 0.0;
            metrics.detections_count = 0;
            metrics.total_detections = 0;
        }
        
        // Encode to JPEG (for timing)
        auto encodeStart = std::chrono::high_resolution_clock::now();
        std::vector<int> params = {cv::IMWRITE_JPEG_QUALITY, config.get<int>("detection.jpegQuality", 80)};
        std::vector<uchar> buffer;
        cv::imencode(".jpg", frame, buffer, params);
        auto encodeEnd = std::chrono::high_resolution_clock::now();
        metrics.jpeg_encode_time_ms = 
            std::chrono::duration<double, std::milli>(encodeEnd - encodeStart).count();
        
        // Update server
        server.updateFrame(frame);
        server.updateDetections(detections);
        
        // Calculate FPS
        frameCount++;
        auto now = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration<double>(now - fpsStart).count();
        
        if (elapsed >= 1.0) {
            metrics.fps = frameCount / elapsed;
            frameCount = 0;
            fpsStart = now;
        }
        
        // Get system metrics
        metrics.cpu_usage_percent = Logger::getCpuUsage();
        metrics.ram_usage_mb = Logger::getRamUsageMB();
        metrics.dropped_frames = droppedFrames;
        metrics.queue_size = 0; // Not implemented yet
        
        // Update server status
        json status = {
            {"fps", metrics.fps},
            {"inference_time_ms", metrics.inference_time_ms},
            {"detections_count", metrics.detections_count},
            {"total_detections", metrics.total_detections},
            {"cpu_usage_percent", metrics.cpu_usage_percent},
            {"ram_usage_mb", metrics.ram_usage_mb},
            {"camera_width", camera.getWidth()},
            {"camera_height", camera.getHeight()},
            {"running", true}
        };
        server.updateStatus(status);
        
        // Log metrics periodically
        auto logElapsed = std::chrono::duration<double, std::milli>(now - lastLogTime).count();
        if (logElapsed >= metricsInterval) {
            logger.logMetrics(metrics);
            lastLogTime = now;
            
            // Print to console
            std::cout << "\rFPS: " << std::fixed << std::setprecision(1) << metrics.fps
                     << " | Inference: " << std::setprecision(1) << metrics.inference_time_ms << "ms"
                     << " | Detections: " << metrics.detections_count
                     << " | CPU: " << std::setprecision(0) << metrics.cpu_usage_percent << "%"
                     << " | RAM: " << std::setprecision(0) << metrics.ram_usage_mb << "MB"
                     << std::flush;
        }
        
        // Small delay to prevent CPU saturation
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    
    std::cout << "\n\n";
    std::cout << "╔════════════════════════════════════════════════╗\n";
    std::cout << "║             Shutting down gracefully...        ║\n";
    std::cout << "╚════════════════════════════════════════════════╝\n";
    
    // Cleanup
    server.stop();
    camera.release();
    logger.close();
    
    std::cout << "\n✓ Shutdown complete\n\n";
    
    return 0;
}
