# Configuration Usage Guide

## Overview

The C++ server uses a simplified, flexible configuration system that allows you to:
- **Add new config keys without modifying C++ code**
- **Change config structure without rebuilding**
- **Just edit `config.json` and restart the server**

## Using the Config Loader

### Basic Usage

```cpp
#include "config_loader.h"

auto& config = ConfigLoader::getInstance();
config.loadConfig("path/to/config.json");

// Get values with type and default
int port = config.get<int>("cppServerPort", 5100);
float threshold = config.get<float>("detection.confidenceThreshold", 0.5f);
std::string path = config.get<std::string>("logging.path", "logs/");
bool useGPU = config.get<bool>("performance.useVulkan", false);
```

### Nested Keys (Dot Notation)

```cpp
// Access nested config with dot notation
int width = config.get<int>("camera.width", 640);
float nms = config.get<float>("detection.nmsThreshold", 0.5f);
std::string format = config.get<std::string>("logging.format", "csv");
```

### Array Values

```cpp
// Get array values
auto modelPaths = config.getArray<std::string>("detection.modelPath");
auto inputSize = config.getArray<int>("detection.inputSize");

// Example use:
if (modelPaths.size() >= 2) {
    std::string paramFile = modelPaths[0];
    std::string binFile = modelPaths[1];
}
```

### Direct JSON Access

For complex operations, access the JSON object directly:

```cpp
const json& cfg = config.getConfig();

// Check if key exists
if (cfg.contains("myCustomKey")) {
    auto value = cfg["myCustomKey"];
}

// Iterate over nested objects
for (auto& [key, value] : cfg["detection"].items()) {
    std::cout << key << ": " << value << std::endl;
}
```

## Supported Types

The `get<T>()` method supports:
- `int`, `float`, `double`
- `bool`
- `std::string`
- Any type that nlohmann/json can deserialize

The `getArray<T>()` method supports:
- `std::vector<int>`
- `std::vector<float>`
- `std::vector<std::string>`

## Adding New Config Keys

### Step 1: Add to config.json

```json
{
  "myNewFeature": {
    "enabled": true,
    "timeout": 5000,
    "servers": ["server1", "server2"]
  }
}
```

### Step 2: Use in C++ (No rebuild needed!)

```cpp
bool enabled = config.get<bool>("myNewFeature.enabled", false);
int timeout = config.get<int>("myNewFeature.timeout", 3000);
auto servers = config.getArray<std::string>("myNewFeature.servers");
```

### That's it!

- No C++ code changes needed
- No recompilation required
- Just edit config.json and restart

## Example: Complete Configuration Usage

```cpp
int main() {
    auto& config = ConfigLoader::getInstance();
    
    if (!config.loadConfig("shared/config.json")) {
        std::cerr << "Failed to load config" << std::endl;
        return 1;
    }
    
    // Server settings
    int port = config.get<int>("cppServerPort", 5100);
    
    // Camera settings
    int width = config.get<int>("camera.width", 640);
    int height = config.get<int>("camera.height", 480);
    int fps = config.get<int>("camera.fps", 30);
    
    // Detection settings
    auto modelPaths = config.getArray<std::string>("detection.modelPath");
    std::string labelsPath = config.get<std::string>("detection.labelsPath", "backend/model/labels.txt");
    float confidence = config.get<float>("detection.confidenceThreshold", 0.5f);
    auto inputSize = config.getArray<int>("detection.inputSize");
    
    // Performance settings
    bool useVulkan = config.get<bool>("performance.useVulkan", false);
    
    // Logging settings
    std::string logPath = config.get<std::string>("logging.path", "logs/");
    int metricsInterval = config.get<int>("logging.metricsInterval", 1000);
    
    // Use the values...
}
```

## Default Values

Always provide sensible default values in case:
- The key doesn't exist in config.json
- The config file is partially invalid
- You want backward compatibility

```cpp
// Good: Provides fallback
int timeout = config.get<int>("network.timeout", 5000);

// Bad: No fallback (will use type's default: 0 for int)
int timeout = config.get<int>("network.timeout", 0);
```

## Error Handling

The config loader will:
- Return `false` from `loadConfig()` if file not found or invalid
- Return default values from `get<T>()` if key doesn't exist
- Return empty vector from `getArray<T>()` if key doesn't exist

```cpp
if (!config.loadConfig()) {
    // Config failed to load - program should exit
    return 1;
}

// If key doesn't exist, uses default (no error thrown)
int value = config.get<int>("nonexistent.key", 100); // Returns 100
```

## Best Practices

### ✅ Do

```cpp
// Use descriptive keys
int timeout = config.get<int>("network.connectionTimeout", 5000);

// Always provide defaults
bool enabled = config.get<bool>("feature.enabled", false);

// Check array size before accessing
auto paths = config.getArray<std::string>("model.paths");
if (paths.size() >= 2) {
    use(paths[0], paths[1]);
}
```

### ❌ Don't

```cpp
// Don't assume keys exist
auto value = config.getConfig()["key"]["nested"]; // May throw!

// Don't use magic numbers as defaults
int val = config.get<int>("timeout", 42); // What does 42 mean?

// Don't access arrays without size check
auto arr = config.getArray<int>("values");
int first = arr[0]; // May crash if empty!
```

## Migration from Old Code

If you have old code using specific getters:

```cpp
// Old way
int port = config.getCppServerPort();
float conf = config.getConfidenceThreshold();

// New way
int port = config.get<int>("cppServerPort", 5100);
float conf = config.get<float>("detection.confidenceThreshold", 0.5f);
```

## Config Schema Reference

Current config.json structure:

```json
{
  "cppServerPort": 5100,
  "camera": {
    "width": 640,
    "height": 480,
    "fps": 30,
    "bufferSize": 1
  },
  "detection": {
    "modelFormat": "ncnn",
    "modelPath": ["param.file", "bin.file"],
    "labelsPath": "backend/model/labels.txt",
    "confidenceThreshold": 0.5,
    "nmsThreshold": 0.5,
    "iouThreshold": 0.5,
    "inputSize": [640, 480],
    "jpegQuality": 80
  },
  "performance": {
    "useVulkan": false
  },
  "logging": {
    "format": "csv",
    "path": "logs/",
    "metricsInterval": 1000
  }
}
```

You can add any new keys at any level without modifying C++ code!

## Summary

**Key Benefits:**
- ✅ No C++ recompilation for config changes
- ✅ Easy to add new features via config
- ✅ Type-safe with compile-time checks
- ✅ Graceful fallback with default values
- ✅ Supports nested keys with dot notation
- ✅ Works with arrays and complex types

**Remember:**
- Edit config.json
- Restart the server
- Done! 🎉
