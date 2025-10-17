#pragma once

#include <opencv2/opencv.hpp>
#include <net.h>
#include <string>
#include <vector>

/**
 * Detection - Represents a single object detection
 */
struct Detection {
    int classId;
    std::string className;
    float confidence;
    cv::Rect box;
};

/**
 * Detector - Handles YOLOv8 inference using NCNN
 */
class Detector {
public:
    Detector();
    ~Detector();
    
    // Initialize detector with NCNN model
    bool initialize(
        const std::string& paramPath,
        const std::string& binPath,
        const std::vector<int>& inputSize,
        float confThreshold,
        float nmsThreshold,
        float iouThreshold,
        bool useVulkan = false
    );
    
    // Run detection on a frame
    std::vector<Detection> detect(const cv::Mat& frame);
    
    // Draw detections on frame
    static void drawDetections(cv::Mat& frame, const std::vector<Detection>& detections);
    
    // Get inference time in milliseconds
    double getInferenceTime() const { return inferenceTimeMs; }
    
    // Load class names from file
    bool loadClassNames(const std::string& labelsPath);
    
private:
    ncnn::Net net;
    std::vector<std::string> classNames;
    std::vector<int> inputSize{640, 480};
    float confThreshold = 0.5f;
    float nmsThreshold = 0.5f;
    float iouThreshold = 0.5f;
    double inferenceTimeMs = 0.0;
    bool initialized = false;
    
    // Preprocess image for NCNN
    ncnn::Mat preprocess(const cv::Mat& frame);
    
    // Postprocess NCNN output
    std::vector<Detection> postprocess(const ncnn::Mat& output, int imgWidth, int imgHeight);
    
    // Non-maximum suppression
    void nms(std::vector<Detection>& detections);
    
    // Calculate IoU between two boxes
    static float calculateIoU(const cv::Rect& box1, const cv::Rect& box2);
};
