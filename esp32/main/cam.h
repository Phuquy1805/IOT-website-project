#ifndef CAM_H
#define CAM_H

#include "esp_camera.h"
#include <PubSubClient.h>
#include "header.h"

bool cameraSetup() {
  bool has_psram = psramFound();
  Serial.printf("PSRAM found: %s\n", has_psram ? "yes" : "no");

  camera_config_t camera_config = {
    .pin_pwdn       = 32,
    .pin_reset      = -1,
    .pin_xclk       = 0,
    .pin_sccb_sda   = 26,
    .pin_sccb_scl   = 27,
    .pin_d7         = 35,
    .pin_d6         = 34,
    .pin_d5         = 39,
    .pin_d4         = 36,
    .pin_d3         = 21,
    .pin_d2         = 19,
    .pin_d1         = 18,
    .pin_d0         = 5,
    .pin_vsync      = 25,
    .pin_href       = 23,
    .pin_pclk       = 22,
    .xclk_freq_hz   = 20000000,
    .ledc_timer     = LEDC_TIMER_0,
    .ledc_channel   = LEDC_CHANNEL_0,
    .pixel_format   = PIXFORMAT_JPEG,
    // Defaults below are overwritten right after:
    .frame_size     = FRAMESIZE_VGA,
    .jpeg_quality   = 20,
    .fb_count       = 1,
    .fb_location    = CAMERA_FB_IN_PSRAM,
    .grab_mode      = CAMERA_GRAB_WHEN_EMPTY
  };

  if (has_psram) {
    camera_config.fb_location = CAMERA_FB_IN_PSRAM;
    camera_config.fb_count    = 2;             // smoother if memory allows
    camera_config.frame_size  = FRAMESIZE_SVGA;// or UXGA later
  } else {
    camera_config.fb_location = CAMERA_FB_IN_DRAM;
    camera_config.fb_count    = 1;             // must be 1 in DRAM
    camera_config.frame_size  = FRAMESIZE_VGA; // stay at VGA or lower
    // Optional: increase compression a bit to save RAM/bandwidth
    camera_config.jpeg_quality = 22;           // higher number = more compression
  }

  esp_err_t err = esp_camera_init(&camera_config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }
  return true;
}


// ---------- Small stream to send head + jpeg + tail without big buffer ----------
class MultiPartMemStream : public Stream
{
public:
  MultiPartMemStream(const uint8_t *p1, size_t l1,
                     const uint8_t *p2, size_t l2,
                     const uint8_t *p3, size_t l3)
      : p1_(p1), l1_(l1), p2_(p2), l2_(l2), p3_(p3), l3_(l3),
        i1_(0), i2_(0), i3_(0) {}

  // Read side
  int available() override
  {
    return (int)((l1_ - i1_) + (l2_ - i2_) + (l3_ - i3_));
  }
  int read() override
  {
    int c = -1;
    if (i1_ < l1_)
      c = p1_[i1_++];
    else if (i2_ < l2_)
      c = p2_[i2_++];
    else if (i3_ < l3_)
      c = p3_[i3_++];
    return c;
  }
  int peek() override
  {
    if (i1_ < l1_)
      return p1_[i1_];
    else if (i2_ < l2_)
      return p2_[i2_];
    else if (i3_ < l3_)
      return p3_[i3_];
    return -1;
  }
  void flush() override {}
  size_t readBytes(uint8_t *buffer, size_t length) override
  {
    size_t n = 0;
    while (n < length)
    {
      int c = read();
      if (c < 0)
        break;
      buffer[n++] = (uint8_t)c;
      if ((n & 0x3FF) == 0)
        yield();
    }
    return n;
  }

  // Stubs to satisfy Print/Stream (not used)
  size_t write(uint8_t) override { return 0; }
  size_t write(const uint8_t *buffer, size_t size) override
  {
    (void)buffer;
    return size ? 0 : 0;
  }

private:
  const uint8_t *p1_;
  size_t l1_;
  size_t i1_;
  const uint8_t *p2_;
  size_t l2_;
  size_t i2_;
  const uint8_t *p3_;
  size_t l3_;
  size_t i3_;
};

// ---------------- Upload & publish (binary multipart, streaming) ----------------
void uploadAndPublish(PubSubClient &mqttClient, const uint8_t *jpeg, size_t jpegLen)
{
  // 1) Filename from current time
  time_t now = time(nullptr);
  struct tm tmInfo;
  localtime_r(&now, &tmInfo);
  char filename[32];
  strftime(filename, sizeof(filename), "%Y%m%d-%H%M%S", &tmInfo);

  // 2) Build small head/tail strings for multipart (binary body in the middle)
  const String boundary = "----ESP32Boundary";
  String head =
      "--" + boundary + "\r\n"
                        "Content-Disposition: form-data; name=\"name\"\r\n\r\n" +
      String(filename) + "\r\n" +
      "--" + boundary + "\r\n"
                        "Content-Disposition: form-data; name=\"image\"; filename=\"" +
      String(filename) + "\"\r\n"
                         "Content-Type: image/jpeg\r\n\r\n";

  String tail = "\r\n--" + boundary + "--\r\n";
  const size_t totalLen = head.length() + jpegLen + tail.length();

  // 3) HTTPS client and headers
  WiFiClientSecure secureClient;
  secureClient.setInsecure(); // for dev; load CA for prod
  HTTPClient http;
  String endpoint = String("https://api.imgbb.com/1/upload?key=") + IMGBB_API_KEY;

  if (!http.begin(secureClient, endpoint))
  {
    Serial.println("HTTP begin() failed");
    return;
  }
  http.setTimeout(60000); // longer timeout for uploads
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  http.addHeader("Connection", "close");

  // 4) Create streaming body: head + jpeg + tail
  MultiPartMemStream bodyStream(
      (const uint8_t *)head.c_str(), head.length(),
      (const uint8_t *)jpeg, jpegLen,
      (const uint8_t *)tail.c_str(), tail.length());

  Serial.println("=== imgBB multipart upload ===");
  Serial.print("Filename: ");
  Serial.println(filename);
  Serial.print("Total body size: ");
  Serial.println(totalLen);

  // 5) Send request with stream
  int code = http.sendRequest("POST", &bodyStream, totalLen);
  Serial.print("HTTP response code: ");
  Serial.println(code);

  String resp = http.getString();
  Serial.println("=== imgBB response ===");
  Serial.println(resp);
  Serial.println("======================");
  http.end();

  if (code != HTTP_CODE_OK)
  {
    Serial.println("Upload failed, skipping MQTT publish.");
    return;
  }

  // 6) Parse and publish URL

  StaticJsonDocument<1024> doc;
  auto err = deserializeJson(doc, resp);
  if (err)
  {
    Serial.print("JSON parse error: ");
    Serial.println(err.c_str());
    return;
  }
  const char *url = doc["data"]["display_url"];
  const char *thumbUrl = doc["data"]["thumb"]["url"];
  Serial.print("Image URL: ");
  Serial.println(url);

  StaticJsonDocument<256> j;
  j["timestamp"] = (uint32_t)now;
  j["url"] = url;
  j["thumb_url"] = thumbUrl;
  j["description"] = "Scheduled capture";

  String payload;
  serializeJson(j, payload);

  String topic = String("/") + MQTT_TOPIC_PREFIX + "/camera-captures";
  if (!mqttClient.publish(topic.c_str(), payload.c_str(), true))
  {
    Serial.println("MQTT publish failed");
  }
}

void cameraCapture(PubSubClient &mqttClient)
{
  // 1) Capture frame
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb)
  {
    Serial.println("Camera capture failed");
    return;
  }

  // 2) Copy JPEG to heap, immediately release camera buffer
  size_t len = fb->len;
  uint8_t *bufCopy = (uint8_t *)malloc(len);
  if (bufCopy)
    memcpy(bufCopy, fb->buf, len);
  esp_camera_fb_return(fb);

  // 3) Upload & publish
  if (bufCopy)
  {
    uploadAndPublish(mqttClient, bufCopy, len);
    free(bufCopy);
  }
  else
  {
    Serial.println("malloc failed for JPEG copy");
  }
}

#endif