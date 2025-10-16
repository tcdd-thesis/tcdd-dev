import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Settings.css';

export default function Settings() {
  const navigate = useNavigate();
  
  const [brightness, setBrightness] = useState(100);
  const [colorTheme, setColorTheme] = useState('light');
  const [language, setLanguage] = useState('en');

  const colorThemes = [
    { id: 'light', name: 'Light', icon: '☀️' },
    { id: 'dark', name: 'Dark', icon: '🌙' },
    { id: 'auto', name: 'Auto', icon: '🔄' }
  ];

  const languages = [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'fr', name: 'Français', flag: '🇫🇷' },
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
    { code: 'tl', name: 'Tagalog', flag: '🇵🇭' }
  ];

  const handleSave = () => {
    console.log('Saving settings:', { brightness, colorTheme, language });
    alert('Settings saved! (Placeholder - not yet implemented)');
  };

  return (
    <div className="settings-container">
      <header className="page-header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Back
        </button>
        <h1>Settings</h1>
      </header>

      <div className="settings-content">
        {/* Brightness Section */}
        <section className="settings-section">
          <h2>💡 Brightness</h2>
          <div className="brightness-control">
            <input
              type="range"
              min="0"
              max="100"
              value={brightness}
              onChange={(e) => setBrightness(e.target.value)}
              className="brightness-slider"
            />
            <span className="brightness-value">{brightness}%</span>
          </div>
          <div className="brightness-preview" style={{ opacity: brightness / 100 }}>
            Preview
          </div>
        </section>

        {/* Color Theme Section */}
        <section className="settings-section">
          <h2>🎨 Color Theme</h2>
          <div className="theme-options">
            {colorThemes.map((theme) => (
              <button
                key={theme.id}
                className={`theme-card ${colorTheme === theme.id ? 'selected' : ''}`}
                onClick={() => setColorTheme(theme.id)}
              >
                <span className="theme-icon">{theme.icon}</span>
                <span className="theme-name">{theme.name}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Language Section */}
        <section className="settings-section">
          <h2>🌍 Language</h2>
          <div className="language-options">
            {languages.map((lang) => (
              <button
                key={lang.code}
                className={`language-card ${language === lang.code ? 'selected' : ''}`}
                onClick={() => setLanguage(lang.code)}
              >
                <span className="language-flag">{lang.flag}</span>
                <span className="language-name">{lang.name}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Save Button */}
        <div className="settings-actions">
          <button className="save-button" onClick={handleSave}>
            Save Settings
          </button>
          <button className="reset-button" onClick={() => {
            setBrightness(100);
            setColorTheme('light');
            setLanguage('en');
          }}>
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  );
}
