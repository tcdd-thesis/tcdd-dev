#include "config_loader.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <filesystem>

namespace fs = std::filesystem;

ConfigLoader& ConfigLoader::getInstance() {
    static ConfigLoader instance;
    return instance;
}

bool ConfigLoader::loadConfig(const std::string& configPath) {
    std::string path = configPath;
    
    if (path.empty()) {
        // Default path: ../../shared/config.json relative to executable
        path = "../../shared/config.json";
    }
    
    // Try to resolve the path
    try {
        fs::path absPath = fs::absolute(path);
        if (!fs::exists(absPath)) {
            std::cerr << "✗ Config file not found: " << absPath << std::endl;
            std::cerr << "✗ Please ensure the config file exists at the specified location." << std::endl;
            return false;
        }
        
        std::ifstream file(absPath);
        if (!file.is_open()) {
            std::cerr << "✗ Failed to open config file: " << absPath << std::endl;
            std::cerr << "✗ Check file permissions and path." << std::endl;
            return false;
        }
        
        try {
            file >> config;
        } catch (const json::exception& je) {
            std::cerr << "✗ Failed to parse config file: " << je.what() << std::endl;
            std::cerr << "✗ Please check JSON syntax in config file." << std::endl;
            return false;
        }
        
        this->configPath = absPath.string();
        std::cout << "✓ Configuration loaded from: " << absPath << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "✗ Error loading config: " << e.what() << std::endl;
        return false;
    }
}

json ConfigLoader::getNestedValue(const std::string& key) const {
    std::istringstream iss(key);
    std::string token;
    json value = config;
    
    while (std::getline(iss, token, '.')) {
        if (value.contains(token)) {
            value = value[token];
        } else {
            return json();
        }
    }
    
    return value;
}

template<typename T>
T ConfigLoader::get(const std::string& key, const T& defaultValue) const {
    json value = getNestedValue(key);
    if (value.is_null()) {
        return defaultValue;
    }
    return value.get<T>();
}

// Explicit template instantiations for common types
template int ConfigLoader::get<int>(const std::string&, const int&) const;
template float ConfigLoader::get<float>(const std::string&, const float&) const;
template bool ConfigLoader::get<bool>(const std::string&, const bool&) const;
template std::string ConfigLoader::get<std::string>(const std::string&, const std::string&) const;

// Special getter for arrays
template<typename T>
std::vector<T> ConfigLoader::getArray(const std::string& key) const {
    json value = getNestedValue(key);
    if (value.is_array()) {
        return value.get<std::vector<T>>();
    }
    return std::vector<T>();
}

// Explicit template instantiations for array types
template std::vector<int> ConfigLoader::getArray<int>(const std::string&) const;
template std::vector<float> ConfigLoader::getArray<float>(const std::string&) const;
template std::vector<std::string> ConfigLoader::getArray<std::string>(const std::string&) const;
