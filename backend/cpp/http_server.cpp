#include "http_server.h"
#include <iostream>
#include <sstream>
#include <cstring>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

// Initialize static verbose flag
bool HttpServer::verboseLogging = false;

HttpServer::HttpServer() {}

HttpServer::~HttpServer() {
    stop();
}

bool HttpServer::initialize(int port) {
    this->port = port;
    std::cout << "Initializing HTTP server on port " << port << std::endl;
    return true;
}

bool HttpServer::start() {
    if (running) {
        std::cerr << "Server is already running" << std::endl;
        return false;
    }
    
    running = true;
    serverThread = std::make_unique<std::thread>(&HttpServer::serverLoop, this);
    
    std::cout << "✓ HTTP server started on port " << port << std::endl;
    return true;
}

void HttpServer::stop() {
    if (running) {
        running = false;
        if (serverThread && serverThread->joinable()) {
            serverThread->join();
        }
        std::cout << "✓ HTTP server stopped" << std::endl;
    }
}

void HttpServer::updateFrame(const cv::Mat& frame) {
    std::lock_guard<std::mutex> lock(frameMutex);
    currentFrame = frame.clone();
    if (verboseLogging) {
        static int frameUpdateCount = 0;
        frameUpdateCount++;
        if (frameUpdateCount % 100 == 0) {
            std::cout << "[SERVER] Updated " << frameUpdateCount << " frames (" 
                      << frame.cols << "x" << frame.rows << ")" << std::endl;
        }
    }
}

void HttpServer::updateDetections(const std::vector<Detection>& detections) {
    std::lock_guard<std::mutex> lock(detectionsMutex);
    currentDetections = detections;
    if (verboseLogging) {
        static int detectionUpdateCount = 0;
        detectionUpdateCount++;
        if (detectionUpdateCount % 100 == 0 || !detections.empty()) {
            std::cout << "[SERVER] Detection update #" << detectionUpdateCount 
                      << ": " << detections.size() << " objects" << std::endl;
        }
    }
}

void HttpServer::updateStatus(const json& status) {
    std::lock_guard<std::mutex> lock(statusMutex);
    currentStatus = status;
    if (verboseLogging) {
        static int statusUpdateCount = 0;
        statusUpdateCount++;
        if (statusUpdateCount % 100 == 0) {
            std::cout << "[SERVER] Status update #" << statusUpdateCount << std::endl;
        }
    }
}

std::vector<uchar> HttpServer::encodeJpeg(const cv::Mat& frame) {
    std::vector<uchar> buffer;
    std::vector<int> params = {cv::IMWRITE_JPEG_QUALITY, jpegQuality};
    cv::imencode(".jpg", frame, buffer, params);
    return buffer;
}

std::string HttpServer::buildMjpegBoundary(const std::vector<uchar>& jpegData) {
    std::ostringstream oss;
    oss << "--frame\r\n";
    oss << "Content-Type: image/jpeg\r\n";
    oss << "Content-Length: " << jpegData.size() << "\r\n\r\n";
    oss << std::string(jpegData.begin(), jpegData.end());
    oss << "\r\n";
    return oss.str();
}

std::string HttpServer::handleGetDetections() {
    std::lock_guard<std::mutex> lock(detectionsMutex);
    
    if (verboseLogging) {
        std::cout << "[API] handleGetDetections called - " << currentDetections.size() << " detections" << std::endl;
    }
    
    json result = json::array();
    for (const auto& det : currentDetections) {
        result.push_back({
            {"class", det.className},
            {"confidence", det.confidence},
            {"bbox", {det.box.x, det.box.y, det.box.width, det.box.height}}
        });
    }
    
    json response = {
        {"success", true},
        {"detections", result},
        {"count", currentDetections.size()}
    };
    
    return response.dump();
}

std::string HttpServer::handleGetStatus() {
    std::lock_guard<std::mutex> lock(statusMutex);
    if (verboseLogging) {
        std::cout << "[API] handleGetStatus called - Status: " 
                  << (currentStatus.empty() ? "EMPTY" : "OK") << std::endl;
        if (currentStatus.empty()) {
            std::cout << "[API] WARNING: currentStatus is empty, returning empty JSON object" << std::endl;
        }
    }
    if (currentStatus.empty()) {
        return "{}";
    }
    return currentStatus.dump();
}

std::string HttpServer::handleHealth() {
    if (verboseLogging) {
        std::cout << "[API] handleHealth called" << std::endl;
    }
    json response = {
        {"status", "ok"},
        {"server", "cpp"},
        {"port", port}
    };
    return response.dump();
}

void HttpServer::serverLoop() {
    int server_fd, client_fd;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);
    
    // Create socket
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        std::cerr << "✗ Socket creation failed" << std::endl;
        running = false;
        return;
    }
    
    // Set socket options
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
        std::cerr << "✗ setsockopt failed" << std::endl;
        close(server_fd);
        running = false;
        return;
    }
    
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(port);
    
    // Bind socket
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        std::cerr << "✗ Bind failed on port " << port << std::endl;
        close(server_fd);
        running = false;
        return;
    }
    
    // Listen
    if (listen(server_fd, 3) < 0) {
        std::cerr << "✗ Listen failed" << std::endl;
        close(server_fd);
        running = false;
        return;
    }
    
    std::cout << "✓ Server listening on port " << port << std::endl;
    
    // Accept loop
    while (running) {
        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(server_fd, &readfds);
        
        struct timeval timeout;
        timeout.tv_sec = 1;
        timeout.tv_usec = 0;
        
        int activity = select(server_fd + 1, &readfds, NULL, NULL, &timeout);
        
        if (activity < 0 || !running) {
            break;
        }
        
        if (activity == 0) {
            continue; // Timeout, check running flag
        }
        
        if ((client_fd = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen)) < 0) {
            continue;
        }
        
        // Get client IP address
        char clientIP[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &(address.sin_addr), clientIP, INET_ADDRSTRLEN);
        int clientPort = ntohs(address.sin_port);
        
        // Read request (simplified - just read first line)
        char buffer[4096] = {0};
        ssize_t valread = read(client_fd, buffer, sizeof(buffer) - 1);
        
        if (valread > 0) {
            std::string request(buffer);
            std::string response;
            
            // Parse request line
            size_t endLine = request.find("\r\n");
            if (endLine != std::string::npos) {
                std::string requestLine = request.substr(0, endLine);
                
                // Log incoming request
                if (verboseLogging) {
                    std::cout << "\n[HTTP] " << clientIP << ":" << clientPort 
                              << " -> " << requestLine << std::endl;
                }
                
                // Simple routing
                if (requestLine.find("GET /video_feed") != std::string::npos) {
                    if (verboseLogging) {
                        std::cout << "[HTTP] Starting MJPEG stream for " << clientIP << std::endl;
                    }
                    
                    // MJPEG stream - send headers and start streaming
                    std::string headers = 
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n"
                        "Cache-Control: no-cache\r\n"
                        "Connection: close\r\n\r\n";
                    
                    send(client_fd, headers.c_str(), headers.length(), 0);
                    
                    int framesSent = 0;
                    // Stream frames
                    while (running) {
                        cv::Mat frame;
                        {
                            std::lock_guard<std::mutex> lock(frameMutex);
                            if (!currentFrame.empty()) {
                                frame = currentFrame.clone();
                            }
                        }
                        
                        if (!frame.empty()) {
                            std::vector<uchar> jpegData = encodeJpeg(frame);
                            std::string boundary = buildMjpegBoundary(jpegData);
                            
                            if (send(client_fd, boundary.c_str(), boundary.length(), MSG_NOSIGNAL) < 0) {
                                if (verboseLogging) {
                                    std::cout << "[HTTP] Client " << clientIP << " disconnected after " 
                                              << framesSent << " frames" << std::endl;
                                }
                                break; // Client disconnected
                            }
                            framesSent++;
                            
                            if (verboseLogging && framesSent % 100 == 0) {
                                std::cout << "[HTTP] Streamed " << framesSent << " frames to " 
                                          << clientIP << std::endl;
                            }
                        } else {
                            if (verboseLogging) {
                                std::cout << "[HTTP] Warning: Empty frame, waiting..." << std::endl;
                            }
                        }
                        
                        usleep(33000); // ~30 FPS
                    }
                    
                } else if (requestLine.find("GET /api/detections") != std::string::npos) {
                    if (verboseLogging) {
                        std::cout << "[HTTP] Serving detections to " << clientIP << std::endl;
                    }
                    std::string jsonResponse = handleGetDetections();
                    if (verboseLogging) {
                        std::cout << "[HTTP] Response: " << jsonResponse.substr(0, 100) 
                                  << (jsonResponse.length() > 100 ? "..." : "") << std::endl;
                    }
                    
                    response = 
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: application/json\r\n"
                        "Access-Control-Allow-Origin: *\r\n"
                        "Connection: close\r\n\r\n" +
                        jsonResponse;
                    send(client_fd, response.c_str(), response.length(), 0);
                    
                } else if (requestLine.find("GET /api/status") != std::string::npos) {
                    if (verboseLogging) {
                        std::cout << "[HTTP] Serving status to " << clientIP << std::endl;
                    }
                    std::string jsonResponse = handleGetStatus();
                    if (verboseLogging) {
                        std::cout << "[HTTP] Status response: " << jsonResponse << std::endl;
                    }
                    
                    response = 
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: application/json\r\n"
                        "Access-Control-Allow-Origin: *\r\n"
                        "Connection: close\r\n\r\n" +
                        jsonResponse;
                    send(client_fd, response.c_str(), response.length(), 0);
                    
                } else if (requestLine.find("GET /health") != std::string::npos) {
                    if (verboseLogging) {
                        std::cout << "[HTTP] Health check from " << clientIP << std::endl;
                    }
                    std::string jsonResponse = handleHealth();
                    if (verboseLogging) {
                        std::cout << "[HTTP] Health response: " << jsonResponse << std::endl;
                    }
                    
                    response = 
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: application/json\r\n"
                        "Access-Control-Allow-Origin: *\r\n"
                        "Connection: close\r\n\r\n" +
                        jsonResponse;
                    send(client_fd, response.c_str(), response.length(), 0);
                    
                } else {
                    if (verboseLogging) {
                        std::cout << "[HTTP] 404 Not Found for " << clientIP << ": " << requestLine << std::endl;
                    }
                    
                    response = 
                        "HTTP/1.1 404 Not Found\r\n"
                        "Content-Type: text/plain\r\n"
                        "Connection: close\r\n\r\n"
                        "404 Not Found";
                    send(client_fd, response.c_str(), response.length(), 0);
                }
            }
        }
        
        close(client_fd);
    }
    
    close(server_fd);
}
