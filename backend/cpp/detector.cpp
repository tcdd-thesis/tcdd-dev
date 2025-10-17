#include "detector.h"
#include <iostream>
#include <fstream>
#include <algorithm>
#include <chrono>

Detector::Detector() {}

Detector::~Detector() {
    net.clear();
}

bool Detector::initialize(
    const std::string& paramPath,
    const std::string& binPath,
    const std::vector<int>& inputSize,
    float confThreshold,
    float nmsThreshold,
    float iouThreshold,
    bool useVulkan
) {
    this->inputSize = inputSize;
    this->confThreshold = confThreshold;
    this->nmsThreshold = nmsThreshold;
    this->iouThreshold = iouThreshold;
    
    std::cout << "Initializing NCNN detector..." << std::endl;
    std::cout << "  Param: " << paramPath << std::endl;
    std::cout << "  Bin: " << binPath << std::endl;
    std::cout << "  Input size: " << inputSize[0] << "x" << inputSize[1] << std::endl;
    std::cout << "  Confidence: " << confThreshold << std::endl;
    std::cout << "  NMS: " << nmsThreshold << std::endl;
    std::cout << "  IoU: " << iouThreshold << std::endl;
    std::cout << "  Vulkan: " << (useVulkan ? "enabled" : "disabled") << std::endl;
    
    // Set Vulkan if requested
    if (useVulkan) {
        net.opt.use_vulkan_compute = true;
        std::cout << "  Using Vulkan compute" << std::endl;
    }
    
    // Load model
    int ret = net.load_param(paramPath.c_str());
    if (ret != 0) {
        std::cerr << "✗ Failed to load param file: " << paramPath << std::endl;
        return false;
    }
    
    ret = net.load_model(binPath.c_str());
    if (ret != 0) {
        std::cerr << "✗ Failed to load model file: " << binPath << std::endl;
        return false;
    }
    
    initialized = true;
    std::cout << "✓ Detector initialized successfully" << std::endl;
    return true;
}

bool Detector::loadClassNames(const std::string& labelsPath) {
    std::ifstream file(labelsPath);
    if (!file.is_open()) {
        std::cerr << "✗ Failed to open labels file: " << labelsPath << std::endl;
        return false;
    }
    
    classNames.clear();
    std::string line;
    while (std::getline(file, line)) {
        if (!line.empty()) {
            classNames.push_back(line);
        }
    }
    
    std::cout << "✓ Loaded " << classNames.size() << " class names" << std::endl;
    return true;
}

ncnn::Mat Detector::preprocess(const cv::Mat& frame) {
    // Resize to input size
    cv::Mat resized;
    cv::resize(frame, resized, cv::Size(inputSize[0], inputSize[1]));
    
    // Convert to RGB (NCNN expects RGB)
    cv::cvtColor(resized, resized, cv::COLOR_BGR2RGB);
    
    // Convert to NCNN Mat
    ncnn::Mat in = ncnn::Mat::from_pixels(
        resized.data,
        ncnn::Mat::PIXEL_RGB,
        resized.cols,
        resized.rows
    );
    
    // Normalize (YOLOv8 uses 0-1 normalization)
    const float norm_vals[3] = {1.0f / 255.0f, 1.0f / 255.0f, 1.0f / 255.0f};
    in.substract_mean_normalize(0, norm_vals);
    
    return in;
}

std::vector<Detection> Detector::detect(const cv::Mat& frame) {
    if (!initialized || frame.empty()) {
        return {};
    }
    
    auto start = std::chrono::high_resolution_clock::now();
    
    // Preprocess
    ncnn::Mat in = preprocess(frame);
    
    // Run inference
    ncnn::Extractor ex = net.create_extractor();
    ex.input("in0", in);  // YOLOv8 input name is typically "in0" or "images"
    
    ncnn::Mat out;
    ex.extract("out0", out);  // YOLOv8 output name is typically "out0" or "output0"
    
    // Postprocess
    std::vector<Detection> detections = postprocess(out, frame.cols, frame.rows);
    
    // Apply NMS
    nms(detections);
    
    auto end = std::chrono::high_resolution_clock::now();
    inferenceTimeMs = std::chrono::duration<double, std::milli>(end - start).count();
    
    return detections;
}

std::vector<Detection> Detector::postprocess(const ncnn::Mat& output, int imgWidth, int imgHeight) {
    std::vector<Detection> detections;
    
    // YOLOv8 output shape: [1, 84, 8400] or [1, num_classes+4, num_anchors]
    // Format: [x, y, w, h, class_scores...]
    
    const float* data = (const float*)output.data;
    int num_proposals = output.w;  // 8400 for YOLOv8
    int num_values = output.h;     // 84 = 4 (bbox) + 80 (classes) for COCO
    
    float scaleX = (float)imgWidth / inputSize[0];
    float scaleY = (float)imgHeight / inputSize[1];
    
    for (int i = 0; i < num_proposals; i++) {
        // Get bbox coordinates
        float cx = data[i];
        float cy = data[i + num_proposals];
        float w = data[i + num_proposals * 2];
        float h = data[i + num_proposals * 3];
        
        // Find best class and confidence
        int bestClass = 0;
        float bestConf = 0.0f;
        
        for (int c = 0; c < (num_values - 4); c++) {
            float conf = data[i + num_proposals * (4 + c)];
            if (conf > bestConf) {
                bestConf = conf;
                bestClass = c;
            }
        }
        
        if (bestConf < confThreshold) {
            continue;
        }
        
        // Convert to corner coordinates and scale to original image
        int x1 = (int)((cx - w / 2) * scaleX);
        int y1 = (int)((cy - h / 2) * scaleY);
        int x2 = (int)((cx + w / 2) * scaleX);
        int y2 = (int)((cy + h / 2) * scaleY);
        
        // Clamp to image bounds
        x1 = std::max(0, std::min(x1, imgWidth - 1));
        y1 = std::max(0, std::min(y1, imgHeight - 1));
        x2 = std::max(0, std::min(x2, imgWidth - 1));
        y2 = std::max(0, std::min(y2, imgHeight - 1));
        
        Detection det;
        det.classId = bestClass;
        det.className = (bestClass < classNames.size()) ? classNames[bestClass] : std::to_string(bestClass);
        det.confidence = bestConf;
        det.box = cv::Rect(x1, y1, x2 - x1, y2 - y1);
        
        detections.push_back(det);
    }
    
    return detections;
}

void Detector::nms(std::vector<Detection>& detections) {
    // Sort by confidence (descending)
    std::sort(detections.begin(), detections.end(),
              [](const Detection& a, const Detection& b) {
                  return a.confidence > b.confidence;
              });
    
    std::vector<bool> suppressed(detections.size(), false);
    
    for (size_t i = 0; i < detections.size(); i++) {
        if (suppressed[i]) continue;
        
        for (size_t j = i + 1; j < detections.size(); j++) {
            if (suppressed[j]) continue;
            
            // Only apply NMS for same class
            if (detections[i].classId != detections[j].classId) continue;
            
            float iou = calculateIoU(detections[i].box, detections[j].box);
            if (iou > iouThreshold) {
                suppressed[j] = true;
            }
        }
    }
    
    // Remove suppressed detections
    detections.erase(
        std::remove_if(detections.begin(), detections.end(),
                      [&suppressed, &detections](const Detection& det) {
                          size_t idx = &det - &detections[0];
                          return suppressed[idx];
                      }),
        detections.end()
    );
}

float Detector::calculateIoU(const cv::Rect& box1, const cv::Rect& box2) {
    int x1 = std::max(box1.x, box2.x);
    int y1 = std::max(box1.y, box2.y);
    int x2 = std::min(box1.x + box1.width, box2.x + box2.width);
    int y2 = std::min(box1.y + box1.height, box2.y + box2.height);
    
    int intersectionArea = std::max(0, x2 - x1) * std::max(0, y2 - y1);
    int box1Area = box1.width * box1.height;
    int box2Area = box2.width * box2.height;
    int unionArea = box1Area + box2Area - intersectionArea;
    
    return (float)intersectionArea / unionArea;
}

void Detector::drawDetections(cv::Mat& frame, const std::vector<Detection>& detections) {
    for (const auto& det : detections) {
        // Draw bounding box
        cv::rectangle(frame, det.box, cv::Scalar(0, 255, 0), 2);
        
        // Draw label
        std::string label = det.className + ": " + 
                           std::to_string((int)(det.confidence * 100)) + "%";
        
        int baseline;
        cv::Size textSize = cv::getTextSize(label, cv::FONT_HERSHEY_SIMPLEX, 0.5, 1, &baseline);
        
        cv::rectangle(frame,
                     cv::Point(det.box.x, det.box.y - textSize.height - 5),
                     cv::Point(det.box.x + textSize.width, det.box.y),
                     cv::Scalar(0, 255, 0), -1);
        
        cv::putText(frame, label,
                   cv::Point(det.box.x, det.box.y - 5),
                   cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(0, 0, 0), 1);
    }
}
