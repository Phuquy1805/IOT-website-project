#ifndef WIFI_H
#define WIFI_H

#include <WiFi.h>

#define CONFIG_TIMEOUT 180

void wifiSetup()
{   
    const char *apName = "SmartDoor-Setup";
    const char *apPassword = "12345678";

    WiFiManager wifiManager;
    Serial.println("\n=== SMARTDOOR CAM KHỞI ĐỘNG ===");
    Serial.println("Phiên bản: 1.0");
    Serial.println("Nhóm: IoT-Group08");

    wifiManager.resetSettings();
    wifiManager.setConfigPortalTimeout(CONFIG_TIMEOUT);

    wifiManager.setCustomHeadElement(R"rawliteral(
  <style>
    body {
      background: linear-gradient(135deg, #74ebd5 0%, #9face6 100%);
      font-family: 'Segoe UI', Tahoma, sans-serif;
      color: #333;
      text-align: center;
      padding: 20px;
      margin: 0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }
    .container {
      max-width: 450px;
      margin: 0 auto;
    }
    h1 {
      color: #2c3e50;
      font-size: 32px;
      margin-bottom: 10px;
      text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .info {
      font-size: 16px;
      color: #555;
      margin-bottom: 25px;
      line-height: 1.5;
    }
    .version {
      font-size: 12px;
      color: #777;
      margin-bottom: 20px;
    }
    form {
      background: rgba(255,255,255,0.95);
      backdrop-filter: blur(10px);
      padding: 30px;
      border-radius: 20px;
      box-shadow: 0 15px 35px rgba(0,0,0,0.1);
      border: 1px solid rgba(255,255,255,0.2);
    }
    label {
      display: block;
      text-align: left;
      font-weight: 600;
      margin-bottom: 5px;
      color: #2c3e50;
    }
    input[type='text'], input[type='password'] {
      width: calc(100% - 20px);
      padding: 12px 10px;
      margin-bottom: 20px;
      border: 2px solid #e0e0e0;
      border-radius: 10px;
      font-size: 14px;
      transition: border-color 0.3s ease;
    }
    input[type='text']:focus, input[type='password']:focus {
      outline: none;
      border-color: #3498db;
      box-shadow: 0 0 10px rgba(52, 152, 219, 0.2);
    }
    input[type='submit'] {
      background: linear-gradient(135deg, #3498db, #2980b9);
      color: white;
      border: none;
      padding: 12px 30px;
      border-radius: 10px;
      cursor: pointer;
      font-size: 16px;
      font-weight: 600;
      width: 100%;
      transition: transform 0.2s ease;
    }
    input[type='submit']:hover {
      transform: translateY(-2px);
      box-shadow: 0 5px 15px rgba(52, 152, 219, 0.4);
    }
    .footer {
      margin-top: 20px;
      font-size: 12px;
      color: #666;
    }
    @media (max-width: 480px) {
      body { padding: 10px; }
      h1 { font-size: 24px; }
      form { padding: 20px; }
    }
  </style>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <div class="container">
    <h1>🚪 SmartDoor CAM</h1>
    <p class="version">IoT-Group08 | Version 1.0</p>
    <p class="info">
      Vui lòng kết nối WiFi để sử dụng thiết bị.<br>
      Thiết bị sẽ tự động khởi động lại sau khi kết nối thành công.
    </p>
  </div>
  )rawliteral");

    wifiManager.setCustomMenuHTML(R"rawliteral(
    <div class="footer">
      <p>💡 Mẹo: Hãy chắc chắn rằng mật khẩu WiFi chính xác</p>
      <p>🔧 Cần hỗ trợ? Liên hệ nhóm IoT-Group08</p>
    </div>
  )rawliteral");

    // Set callback for AP mode
    wifiManager.setAPCallback([](WiFiManager *myWiFiManager)
                              {
                                  Serial.println("\n=== CHUYỂN VÀO CHẾ ĐỘ CẤU HÌNH ===");
                                  Serial.print("Tên WiFi (SSID): ");
                                  Serial.println(myWiFiManager->getConfigPortalSSID());
                                  Serial.println("Mật khẩu WiFi: 12345678");
                                  Serial.print("Địa chỉ web cấu hình: http://");
                                  Serial.println(WiFi.softAPIP());
                                  Serial.println("=====================================");
                              });

    // Set callback for save config
    wifiManager.setSaveConfigCallback([](){Serial.println("Cấu hình WiFi đã được lưu!");});

    // Try to connect to WiFi
    Serial.println("Đang thử kết nối WiFi...");

    if (!wifiManager.autoConnect(apName, apPassword))
    {
        Serial.println("Timeout trong chế độ cấu hình WiFi.");
        Serial.println("Khởi động lại thiết bị...");
        delay(3000);
        ESP.restart();
    }

    // WiFi connected successfully
    Serial.println("\n=============================================");
    Serial.println("ĐÃ KẾT NỐI WIFI THÀNH CÔNG!");
    Serial.print("Tên WiFi (SSID): ");
    Serial.println(WiFi.SSID());
    Serial.print("IP ESP32-CAM: ");
    Serial.println(WiFi.localIP());
    Serial.print("Cường độ tín hiệu: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    Serial.print("MAC Address: ");
    Serial.println(WiFi.macAddress());
    Serial.println("=============================================");
}
#endif