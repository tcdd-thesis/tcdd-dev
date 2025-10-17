#include "camera.h"
#include "logging_flags.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <functional>

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
    // Try different approaches in order
    struct CameraBackend {
        std::string name;
        std::function<bool(cv::VideoCapture&)> openFunc;
    };
    
    std::vector<CameraBackend> backends = {
        // 1. Try GStreamer with simple libcamerasrc (best for Pi Camera V3)
        {"GStreamer-libcamera", [&](cv::VideoCapture& cap) {
            std::string pipeline = "libcamerasrc ! "
                                   "video/x-raw,width=" + std::to_string(width) + 
                                   ",height=" + std::to_string(height) + 
                                   ",format=I420 ! "
                                   "videoconvert ! "
                                   "appsink drop=1";
            std::cout << "    Pipeline: " << pipeline << std::endl;
            return cap.open(pipeline, cv::CAP_GSTREAMER);
        }},
        
        // 2. Try GStreamer with auto source (fallback)
        {"GStreamer-auto", [&](cv::VideoCapture& cap) {
            std::string pipeline = "autovideosrc ! "
                                   "video/x-raw,width=" + std::to_string(width) + 
                                   ",height=" + std::to_string(height) + " ! "
                                   "videoconvert ! "
                                   "appsink";
            std::cout << "    Pipeline: " << pipeline << std::endl;
            return cap.open(pipeline, cv::CAP_GSTREAMER);
        }},
        
        // 3. Try V4L2 backend
        {"V4L2", [&](cv::VideoCapture& cap) {
            return cap.open(cameraIndex, cv::CAP_V4L2);
        }},
        
        // 4. Try ANY backend (OpenCV default)
        {"ANY", [&](cv::VideoCapture& cap) {
            return cap.open(cameraIndex, cv::CAP_ANY);
        }}
    };
    
    for (const auto& backend : backends) {
        std::cout << "  Trying " << backend.name << " backend..." << std::endl;
        
        if (backend.openFunc(capture)) {
            std::cout << "    Camera opened, testing frame capture..." << std::endl;
            
            // Test if we can actually read a frame
            cv::Mat testFrame;
            bool canRead = false;
            
            // Try reading a few times (first frame might take time to initialize)
            for (int attempt = 0; attempt < 5; attempt++) {
                if (capture.read(testFrame) && !testFrame.empty()) {
                    canRead = true;
                    std::cout << "    ✓ Successfully captured test frame on attempt " << (attempt + 1) << std::endl;
                    break;
                }
                std::cout << "    Attempt " << (attempt + 1) << " failed, retrying..." << std::endl;
                std::this_thread::sleep_for(std::chrono::milliseconds(200));
            }
            
            if (canRead) {
                std::cout << "  ✓ " << backend.name << " backend works! (Frame: " 
                          << testFrame.cols << "x" << testFrame.rows << ")" << std::endl;
                
                // For V4L2/ANY backends, try to set properties
                if (backend.name == "V4L2" || backend.name == "ANY") {
                    capture.set(cv::CAP_PROP_FRAME_WIDTH, width);
                    capture.set(cv::CAP_PROP_FRAME_HEIGHT, height);
                    capture.set(cv::CAP_PROP_FPS, fps);
                    capture.set(cv::CAP_PROP_BUFFERSIZE, bufferSize);
                }
                
                // Verify actual settings
                int actualWidth = capture.get(cv::CAP_PROP_FRAME_WIDTH);
                int actualHeight = capture.get(cv::CAP_PROP_FRAME_HEIGHT);
                int actualFps = capture.get(cv::CAP_PROP_FPS);
                
                std::cout << "  Actual resolution: " << actualWidth << "x" << actualHeight 
                          << " @ " << actualFps << " FPS" << std::endl;
                
                opened = true;
                return true;
            } else {
                std::cout << "  ✗ " << backend.name << " opened but cannot read frames after 5 attempts" << std::endl;
                capture.release();
            }
        } else {
            std::cout << "  ✗ " << backend.name << " backend failed to open" << std::endl;
        }
    }
    
    std::cerr << "\n✗ All backends failed. Camera hardware detected but OpenCV cannot access it." << std::endl;
    std::cerr << "  This usually means OpenCV was not compiled with GStreamer support." << std::endl;
    std::cerr << "  Try using a video file instead: ./cpp_server --file video.mp4" << std::endl;
    
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
