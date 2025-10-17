#pragma once

#include <string>
#include <vector>
#include <memory>
#include "third_party/json.hpp"

using json = nlohmann::json;

/**
 * ConfigLoader - Loads and provides access to shared/config.json
 * C++ equivalent of backend/python/config_loader.py
 */
class ConfigLoader {
public:
    static ConfigLoader& getInstance();
    
    // Delete copy constructor and assignment operator
    ConfigLoader(const ConfigLoader&) = delete;
    ConfigLoader& operator=(const ConfigLoader&) = delete;
    
    // Load configuration from file
    bool loadConfig(const std::string& configPath = "");
    
    // Generic getter with dot notation support for nested keys
    // Example: get<int>("cppServerPort", 5100)
    //          get<float>("detection.confidenceThreshold", 0.5f)
    //          get<std::string>("logging.path", "logs/")
    template<typename T>
    T get(const std::string& key, const T& defaultValue) const;
    
    // Special getter for array types (returns empty vector if not found)
    template<typename T>
    std::vector<T> getArray(const std::string& key) const;
    
    // Get the full config object for direct access
    const json& getConfig() const { return config; }
    
private:
    ConfigLoader() = default;
    json config;
    std::string configPath;
    
    // Helper to get nested values
    json getNestedValue(const std::string& key) const;
};
