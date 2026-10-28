/* Admin Settings — backend pairing + personalised node infrastructure.
   Pairing: reads/writes the SAME browser-local store as Connect
   (localStorage 'wi_backend': platform, hub, forecasting, copilot,
   contamination, kg, platformKey, copilotKey). Keys are masked here and
   are never sent anywhere except to the backend URL you configured.
   Node designs live in 'wip_node_designs' (this browser only).
   Firmware is GENERATED IN THIS BROWSER from the design — no server
   compiles it, no credentials are stored by the app. WiFi/MQTT
   credentials you type go ONLY into the downloaded sketch file, which
   you control. Flashing is via Arduino IDE / arduino-cli with that
   file; this page does not flash hardware over the web (Web Serial
   cannot flash AVR/ESP firmware from a static page), and that limit
   is stated in the deploy checklist rather than hidden.
   Telemetry endpoint: the sketch posts/publishes to the backend URL
   you configured + '/telemetry' by default — adjust TELEMETRY_URL in
   the sketch to your hub's actual ingestion endpoint if it differs.
   Sensor values that need calibration (MQ-4 gas, HX711 weight) are
   labelled uncalibrated in the sketch until you calibrate them. */
(function(){
'use strict';
const $a = s => document.querySelector(s);
const $$a = s => [...document.querySelectorAll(s)];
const escA = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const BORO_A = {Manhattan:[40.7831,-73.9712],Brooklyn:[40.6782,-73.9442],Queens:[40.7282,-73.7949],Bronx:[40.8448,-73.8648],'Staten Island':[40.5795,-74.1502]};
const BOARDS = {
  esp32: {label:'ESP32 (WiFi, Arduino C++)', lang:'arduino', wifi:'esp32', pins:{hc_sr04:[5,18], dht22:4, mq4:36, hx711:[19,21], ds18b20:15, soil:34, pir:13, gps:[16,17]}},
  esp8266: {label:'ESP8266 / NodeMCU (WiFi, Arduino C++)', lang:'arduino', wifi:'esp8266', pins:{hc_sr04:[5,6], dht22:4, mq4:0, hx711:[12,13], ds18b20:14, soil:0, pir:12, gps:[13,15]}},
  uno: {label:'Arduino Uno (LoRa or serial; WiFi needs a shield/module)', lang:'arduino', wifi:'none', pins:{hc_sr04:[9,10], dht22:2, mq4:0, hx711:[4,5], ds18b20:7, soil:1, pir:8, gps:[10,11]}},
  nano33: {label:'Arduino Nano 33 IoT (WiFi, Arduino C++)', lang:'arduino', wifi:'nano33', pins:{hc_sr04:[9,10], dht22:2, mq4:0, hx711:[4,5], ds18b20:7, soil:1, pir:8, gps:[10,11]}},
  pico: {label:'Raspberry Pi Pico W (MicroPython)', lang:'micropython', wifi:'pico', pins:{hc_sr04:[2,3], dht22:4, mq4:26, hx711:[5,6], ds18b20:7, soil:27, pir:8, gps:[0,1]}},
  stm32: {label:'STM32 / Blue Pill (Arduino core, generic)', lang:'arduino', wifi:'none', pins:{hc_sr04:[9,10], dht22:2, mq4:0, hx711:[4,5], ds18b20:7, soil:1, pir:8, gps:[10,11]}},
  esp32py: {label:'ESP32 (MicroPython — direct USB/WiFi flash)', lang:'micropython', wifi:'esp32', pins:{hc_sr04:[5,18], dht22:4, mq4:36, hx711:[19,21], ds18b20:15, soil:34, pir:13, gps:[16,17]}},
  esp8266py: {label:'ESP8266 (MicroPython — direct USB/WiFi flash)', lang:'micropython', wifi:'esp8266', pins:{hc_sr04:[14,12], dht22:4, mq4:0, hx711:[12,13], ds18b20:14, soil:0, pir:5, gps:[13,15]}}
};
const SENSORS = {
  hc_sr04: {label:'HC-SR04 ultrasonic — bin fill %', field:'fill_pct', lib:'(none — pulse timing)'},
  dht22: {label:'DHT22 — temperature + humidity', field:'temperature_c, humidity_pct', lib:'DHT sensor library'},
  mq4: {label:'MQ-4 gas — methane (uncalibrated ppm estimate)', field:'methane_ppm', lib:'(none — analog read, calibrate!)'},
  hx711: {label:'HX711 load cell — weight kg (uncalibrated)', field:'weight_kg', lib:'HX711_ADC or HX711 library'},
  ds18b20: {label:'DS18B20 — temperature (waterproof)', field:'temperature_c', lib:'OneWire + DallasTemperature'},
  soil: {label:'Capacitive soil moisture — garden/soil %', field:'soil_moisture_pct', lib:'(none — analog read)'},
  pir: {label:'PIR motion — activity flag', field:'motion', lib:'(none — digital read)'},
  gps: {label:'NEO-6M GPS — latitude/longitude', field:'latitude, longitude', lib:'TinyGPSPlus'},
  battery: {label:'Battery voltage divider — battery_v', field:'battery_v', lib:'(none — analog read)'}
};
const TEMPLATES = {
  compost: {name:'Smart Compost Bin', board:'esp32', conn:'mqtt', sensors:['hc_sr04','dht22','mq4'], kind:'collection bin', stream:'organics'},
  fillbin: {name:'Fill-Level Bin', board:'esp32', conn:'http', sensors:['hc_sr04'], kind:'collection bin', stream:'organics'},
  garden: {name:'Community Garden Soil Node', board:'pico', conn:'http', sensors:['soil','ds18b20'], kind:'garden', stream:'organics'},
  methane: {name:'Methane Monitor', board:'esp32', conn:'mqtt', sensors:['mq4','dht22'], kind:'collection node', stream:'organics'},
  hubnode: {name:'Transfer Hub Node', board:'esp32', conn:'mqtt', sensors:['hx711','hc_sr04','gps'], kind:'hub', stream:'organics'}
};
function backendLoad(){ try{ return JSON.parse(localStorage.getItem('wi_backend')||'{}'); }catch(e){ return {}; } }
function backendSave(cfg){ try{ localStorage.setItem('wi_backend', JSON.stringify(cfg)); }catch(e){} }
function settingsLoad(){ try{ return Object.assign({tonnesPerFull:0.5, basemap:'osm', stream:'organics', process:'AerobicComposting', retentionDays:90}, JSON.parse(localStorage.getItem('wip_admin_settings')||'{}')); }catch(e){ return {tonnesPerFull:0.5, basemap:'osm', stream:'organics', process:'AerobicComposting', retentionDays:90}; } }
function designsLoad(){ try{ return JSON.parse(localStorage.getItem('wip_node_designs')||'[]'); }catch(e){ return []; } }
function designsSave(a){ try{ localStorage.setItem('wip_node_designs', JSON.stringify(a)); }catch(e){} }
function nodesLoad(){ try{ return JSON.parse(localStorage.getItem('wip_network_nodes')||'[]'); }catch(e){ return []; } }
function currentDesign(){
  const sensors = $$a('.admSensor:checked').map(c=>c.value);
  return {
    id: ($a('#admNodeId').value||'').trim(), name: ($a('#admNodeName').value||'').trim(),
    kind: $a('#admKind').value, stream: $a('#admStream').value, host: $a('#admHost').value,
    borough: $a('#admBorough').value, lat: +$a('#admLat').value || BORO_A[$a('#admBorough').value][0],
    lon: +$a('#admLon').value || BORO_A[$a('#admBorough').value][1],
    board: $a('#admBoard').value, conn: $a('#admConn').value, interval: Math.max(10, +$a('#admInterval').value || 300),
    depthCm: Math.max(10, +$a('#admDepth').value || 80), sensors,
    ssid: $a('#admSsid').value.trim(), mqttHost: $a('#admMqtt').value.trim(),
    backend: (backendLoad().platform||backendLoad().hub||'').replace(/\/$/,'')
  };
}
function pinConflicts(d){
  const used = {}, warn = [];
  const pins = BOARDS[d.board].pins;
  d.sensors.forEach(s=>{
    const p = pins[s]; if(p==null) return;
    const arr = Array.isArray(p)?p:[p];
    arr.forEach(x=>{ if(used[x]) warn.push(`${s} shares pin ${x} with ${used[x]} — reassign pins in the sketch before flashing.`); else used[x]=s; });
  });
  return warn;
}
function genArduino(d){
  const b = BOARDS[d.board], P = b.pins;
  const wifiInc = b.wifi==='esp32' ? '#include <WiFi.h>' : b.wifi==='esp8266' ? '#include <ESP8266WiFi.h>' : b.wifi==='nano33' ? '#include <WiFiNINA.h>' : '';
  const lines = [];
  lines.push(`// ${d.name||d.id} — generated by Waste Intelligence Admin (browser, no server compile).`);
  lines.push(`// Board: ${b.label} | Node: ${d.id} | Stream: ${d.stream} | Interval: ${d.interval}s`);
  lines.push(`// Credentials below are ONLY in this file — never commit it with real passwords.`);
  lines.push(`// Telemetry: ${d.conn==='mqtt' ? 'MQTT topic waste/nodes/' + d.id + '/telemetry' : (d.backend||'<your-backend>') + '/telemetry'} — adjust to your hub's ingestion endpoint.`);
  if(d.sensors.includes('mq4')) lines.push('// MQ-4 methane_ppm is an UNCALIBRATED estimate from the analog value — calibrate against a known gas source before trusting it.');
  if(d.sensors.includes('hx711')) lines.push('// HX711 weight_kg is UNCALIBRATED until you set the calibration factor with a known weight.');
  lines.push('');
  if(wifiInc) lines.push(wifiInc);
  if(d.conn==='mqtt' && b.wifi!=='none') lines.push('#include <PubSubClient.h>');
  if(b.wifi!=='none') lines.push('#include <ArduinoOTA.h>  // wireless re-flashing: after the first USB flash, this node appears as a Network Port in Arduino IDE');
  if(d.conn==='http' && b.wifi!=='none') lines.push('#include <HTTPClient.h>');
  if(d.sensors.includes('dht22')) lines.push('#include <DHT.h>');
  if(d.sensors.includes('ds18b20')) lines.push('#include <OneWire.h>\n#include <DallasTemperature.h>');
  if(d.sensors.includes('hx711')) lines.push('#include "HX711.h"  // install the HX711 library first');
  if(d.sensors.includes('gps')) lines.push('#include <TinyGPSPlus.h>\n#include <SoftwareSerial.h>');
  lines.push('');
  lines.push(`const char* NODE_ID = "${d.id}";`);
  if(b.wifi!=='none'){ lines.push(`const char* WIFI_SSID = "${d.ssid||'YOUR_WIFI_SSID'}";`); lines.push(`const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";`); }
  if(d.conn==='mqtt'){ lines.push(`const char* MQTT_HOST = "${d.mqttHost||'YOUR_MQTT_BROKER'}";`); lines.push('const int MQTT_PORT = 1883;'); }
  if(d.conn==='http') lines.push(`const char* TELEMETRY_URL = "${d.backend? d.backend + '/telemetry' : 'http://YOUR_BACKEND/telemetry'}";`);
  lines.push(`const unsigned long INTERVAL_MS = ${d.interval*1000}UL;`);
  lines.push(`const float BIN_DEPTH_CM = ${d.depthCm};`);
  if(d.sensors.includes('dht22')) lines.push(`#define DHTPIN ${P.dht22}\n#define DHTTYPE DHT22\nDHT dht(DHTPIN, DHTTYPE);`);
  if(d.sensors.includes('hc_sr04')) lines.push(`#define TRIG_PIN ${P.hc_sr04[0]}\n#define ECHO_PIN ${P.hc_sr04[1]}`);
  if(d.sensors.includes('mq4')) lines.push(`#define MQ4_PIN ${P.mq4}`);
  if(d.sensors.includes('hx711')) lines.push(`HX711 scale;`);
  if(d.sensors.includes('ds18b20')) lines.push(`#define ONE_WIRE_BUS ${P.ds18b20}\nOneWire oneWire(ONE_WIRE_BUS);\nDallasTemperature dsTemp(&oneWire);`);
  if(d.sensors.includes('soil')) lines.push(`#define SOIL_PIN ${P.soil}`);
  if(d.sensors.includes('pir')) lines.push(`#define PIR_PIN ${P.pir}`);
  if(d.sensors.includes('gps')) lines.push(`SoftwareSerial gpsSerial(${P.gps[0]}, ${P.gps[1]});\nTinyGPSPlus gps;`);
  if(d.sensors.includes('battery')) lines.push(`#define BATT_PIN 35  // ESP32 ADC pin — change per board`);
  if(d.conn==='mqtt' && b.wifi!=='none') lines.push('WiFiClient espClient;\nPubSubClient mqtt(espClient);');
  lines.push('');
  lines.push('float readFillPct(){');
  if(d.sensors.includes('hc_sr04')){
    lines.push('  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2); digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10); digitalWrite(TRIG_PIN, LOW);');
    lines.push('  long dur = pulseIn(ECHO_PIN, HIGH, 30000); if(dur==0) return -1;');
    lines.push('  float dist = dur * 0.0343 / 2.0; float fill = (BIN_DEPTH_CM - dist) / BIN_DEPTH_CM * 100.0; return constrain(fill, 0, 100);');
  } else lines.push('  return -1; // no fill sensor selected');
  lines.push('}');
  lines.push('');
  lines.push('String buildPayload(){');
  lines.push('  String j = "{";');
  lines.push('  j += "\\"node_id\\":\\"" + String(NODE_ID) + "\\"";');
  if(d.sensors.includes('hc_sr04')) lines.push('  j += ",\\"fill_pct\\":" + String(readFillPct(), 1);');
  if(d.sensors.includes('dht22')) lines.push('  j += ",\\"temperature_c\\":" + String(dht.readTemperature(), 1) + ",\\"humidity_pct\\":" + String(dht.readHumidity(), 1);');
  if(d.sensors.includes('ds18b20')) lines.push('  dsTemp.requestTemperatures(); j += ",\\"temperature_c\\":" + String(dsTemp.getTempCByIndex(0), 1);');
  if(d.sensors.includes('mq4')) lines.push('  int mq = analogRead(MQ4_PIN); j += ",\\"methane_raw\\":" + String(mq) + ",\\"methane_ppm\\":" + String(mq * 0.5, 1); // UNCALIBRATED placeholder factor');
  if(d.sensors.includes('hx711')) lines.push('  j += ",\\"weight_kg\\":" + String(scale.get_units(5), 2); // set scale.set_scale(factor) after calibration');
  if(d.sensors.includes('soil')) lines.push('  int sv = analogRead(SOIL_PIN); j += ",\\"soil_moisture_pct\\":" + String(map(sv, 4095, 0, 0, 100));');
  if(d.sensors.includes('pir')) lines.push('  j += ",\\"motion\\":" + String(digitalRead(PIR_PIN));');
  if(d.sensors.includes('gps')) lines.push('  while(gpsSerial.available()) gps.encode(gpsSerial.read()); if(gps.location.isValid()){ j += ",\\"latitude\\":" + String(gps.location.lat(), 5) + ",\\"longitude\\":" + String(gps.location.lng(), 5); }');
  else lines.push(`  j += ",\\"latitude\\":${d.lat.toFixed(5)},\\"longitude\\":${d.lon.toFixed(5)}; // fixed node position from Admin`);
  if(d.sensors.includes('battery')) lines.push('  j += ",\\"battery_v\\":" + String(analogRead(BATT_PIN) * 3.3 / 4095.0 * 2.0, 2);');
  lines.push('  j += "}"; return j;');
  lines.push('}');
  lines.push('');
  lines.push('void setup(){');
  lines.push('  Serial.begin(115200);');
  if(d.sensors.includes('hc_sr04')) lines.push('  pinMode(TRIG_PIN, OUTPUT); pinMode(ECHO_PIN, INPUT);');
  if(d.sensors.includes('dht22')) lines.push('  dht.begin();');
  if(d.sensors.includes('ds18b20')) lines.push('  dsTemp.begin();');
  if(d.sensors.includes('hx711')) lines.push(`  scale.begin(${P.hx711[0]}, ${P.hx711[1]}); scale.tare(); // TODO: scale.set_scale(YOUR_CALIBRATION_FACTOR);`);
  if(d.sensors.includes('pir')) lines.push('  pinMode(PIR_PIN, INPUT);');
  if(d.sensors.includes('gps')) lines.push('  gpsSerial.begin(9600);');
  if(b.wifi!=='none'){ lines.push('  WiFi.begin(WIFI_SSID, WIFI_PASS); while(WiFi.status()!=WL_CONNECTED){ delay(500); Serial.print("."); } Serial.println("\\nWiFi connected");'); lines.push('  ArduinoOTA.setHostname(NODE_ID); ArduinoOTA.begin(); // wireless flash: Arduino IDE > Tools > Port > Network Ports > NODE_ID'); }
  if(d.conn==='mqtt' && b.wifi!=='none') lines.push('  mqtt.setServer(MQTT_HOST, MQTT_PORT);');
  lines.push('}');
  lines.push('');
  lines.push('void loop(){');
  if(b.wifi!=='none') lines.push('  ArduinoOTA.handle(); // wireless re-flash handler — keep this in loop()');
  if(b.wifi!=='none' && d.conn==='mqtt') lines.push('  if(!mqtt.connected()){ while(!mqtt.connected()){ if(mqtt.connect(NODE_ID)) break; delay(2000); } } mqtt.loop();');
  lines.push('  String payload = buildPayload(); Serial.println(payload);');
  if(d.conn==='mqtt' && b.wifi!=='none') lines.push(`  mqtt.publish(("waste/nodes/" + String(NODE_ID) + "/telemetry").c_str(), payload.c_str());`);
  else if(d.conn==='http' && b.wifi!=='none') lines.push('  HTTPClient http; http.begin(TELEMETRY_URL); http.addHeader("Content-Type", "application/json"); int code = http.POST(payload); Serial.println(code); http.end();');
  else lines.push('  // No network selected: payload goes to Serial only. Attach a radio/WiFi module or log it from a gateway.');
  lines.push('  delay(INTERVAL_MS);');
  lines.push('}');
  return lines.join('\n');
}
function genMicroPython(d){
  const P = BOARDS[d.board].pins;
  const lines = [];
  lines.push(`# ${d.name||d.id} — ${BOARDS[d.board].label}. Generated by Waste Intelligence Admin.`);
  lines.push(`# Credentials below are ONLY in this file — never commit it with real passwords.`);
  lines.push(`# Telemetry: ${d.conn==='mqtt' ? 'MQTT waste/nodes/' + d.id + '/telemetry' : (d.backend||'<your-backend>') + '/telemetry'} — adjust to your hub.`);
  lines.push('import network, time, machine');
  if(d.conn==='mqtt') lines.push('from umqtt.simple import MQTTClient');
  if(d.conn==='http') lines.push('import urequests');
  if(d.sensors.includes('dht22')) lines.push('import dht');
  lines.push('');
  lines.push(`NODE_ID = "${d.id}"`);
  lines.push(`WIFI_SSID = "${d.ssid||'YOUR_WIFI_SSID'}"`);
  lines.push(`WIFI_PASS = "YOUR_WIFI_PASSWORD"`);
  if(d.conn==='mqtt') lines.push(`MQTT_HOST = "${d.mqttHost||'YOUR_MQTT_BROKER'}"`);
  if(d.conn==='http') lines.push(`TELEMETRY_URL = "${d.backend? d.backend + '/telemetry' : 'http://YOUR_BACKEND/telemetry'}"`);
  lines.push(`INTERVAL_S = ${d.interval}`);
  lines.push(`BIN_DEPTH_CM = ${d.depthCm}`);
  if(d.sensors.includes('dht22')) lines.push(`dht_sensor = dht.DHT22(machine.Pin(${P.dht22}))`);
  if(d.sensors.includes('hc_sr04')) lines.push(`trig = machine.Pin(${P.hc_sr04[0]}, machine.Pin.OUT); echo = machine.Pin(${P.hc_sr04[1]}, machine.Pin.IN)`);
  if(d.sensors.includes('mq4')) lines.push(`mq4 = machine.ADC(${P.mq4})  # UNCALIBRATED — calibrate before trusting ppm`);
  if(d.sensors.includes('soil')) lines.push(`soil = machine.ADC(${P.soil})`);
  if(d.sensors.includes('pir')) lines.push(`pir = machine.Pin(${P.pir}, machine.Pin.IN)`);
  lines.push('');
  lines.push('def read_fill():');
  if(d.sensors.includes('hc_sr04')){
    lines.push('    trig.low(); time.sleep_us(2); trig.high(); time.sleep_us(10); trig.low()');
    lines.push('    dur = machine.time_pulse_us(echo, 1, 30000)');
    lines.push('    if dur < 0: return -1');
    lines.push('    dist = dur * 0.0343 / 2; return max(0, min(100, (BIN_DEPTH_CM - dist) / BIN_DEPTH_CM * 100))');
  } else lines.push('    return -1');
  lines.push('');
  lines.push('def wifi_connect():');
  lines.push('    wlan = network.WLAN(network.STA_IF); wlan.active(True)');
  lines.push('    if not wlan.isconnected(): wlan.connect(WIFI_SSID, WIFI_PASS)');
  lines.push('    for _ in range(20):');
  lines.push('        if wlan.isconnected(): break');
  lines.push('        time.sleep(1)');
  lines.push('    return wlan.isconnected()');
  lines.push('');
  lines.push('while True:');
  lines.push('    payload = {"node_id": NODE_ID}');
  if(d.sensors.includes('hc_sr04')) lines.push('    payload["fill_pct"] = round(read_fill(), 1)');
  if(d.sensors.includes('dht22')) lines.push('    try:\n        dht_sensor.measure(); payload["temperature_c"] = dht_sensor.temperature(); payload["humidity_pct"] = dht_sensor.humidity()\n    except Exception as e: print("DHT error", e)');
  if(d.sensors.includes('mq4')) lines.push('    payload["methane_raw"] = mq4.read_u16()  # UNCALIBRATED');
  if(d.sensors.includes('soil')) lines.push('    payload["soil_moisture_pct"] = round((65535 - soil.read_u16()) / 65535 * 100, 1)');
  if(d.sensors.includes('pir')) lines.push('    payload["motion"] = pir.value()');
  lines.push(`    payload["latitude"] = ${d.lat.toFixed(5)}; payload["longitude"] = ${d.lon.toFixed(5)}`);
  lines.push('    print(payload)');
  lines.push('    if wifi_connect():');
  if(d.conn==='mqtt') lines.push('        try:\n            c = MQTTClient(NODE_ID, MQTT_HOST); c.connect(); c.publish(b"waste/nodes/" + NODE_ID.encode() + b"/telemetry", str(payload).encode()); c.disconnect()\n        except Exception as e: print("MQTT error", e)');
  else if(d.conn==='http') lines.push('        try:\n            urequests.post(TELEMETRY_URL, json=payload).close()\n        except Exception as e: print("HTTP error", e)');
  lines.push('    time.sleep(INTERVAL_S)');
  return lines.join('\n');
}
function generateFirmware(){
  const d = currentDesign();
  const code = BOARDS[d.board].lang==='micropython' ? genMicroPython(d) : genArduino(d);
  const warns = pinConflicts(d);
  const board = BOARDS[d.board];
  let libNote = 'Libraries: ';
  if(board.lang==='micropython') libNote += 'built-in network/machine/dht only (umqtt/urequests are in MicroPython firmware or install via mip).';
  else {
    const libs = new Set();
    if(d.sensors.includes('dht22')) libs.add('DHT sensor library');
    if(d.sensors.includes('ds18b20')) libs.add('OneWire + DallasTemperature');
    if(d.sensors.includes('hx711')) libs.add('HX711 library');
    if(d.sensors.includes('gps')) libs.add('TinyGPSPlus');
    if(d.conn==='mqtt') libs.add('PubSubClient');
    libNote += libs.size? [...libs].join(', ') + '.' : 'none beyond the board core.';
  }
  $a('#admFirmware').textContent = code;
  $a('#admFirmwareMeta').innerHTML = `<p class="muted small">${escA(libNote)} Board: ${escA(board.label)} · Connectivity: ${escA(d.conn)} · Sensors: ${escA(d.sensors.join(', ')||'none')}.</p>` +
    (warns.length? `<p class="muted small" style="color:#b42318"><strong>Pin warnings:</strong> ${escA(warns.join(' '))}</p>` : `<p class="muted small">No pin conflicts in the default mapping.</p>`) +
    `<p class="muted small">Deploy: download the file, open it in Arduino IDE (or Thonny / arduino-cli for Pico — see checklist), set your WiFi/MQTT credentials in the file, install the libraries above, pick the board + port, and upload. This page does not flash hardware.</p>`;
  return {design:d, code};
}
function renderDesigns(){
  const list = designsLoad();
  $a('#admDesignList').innerHTML = list.map((x,i)=>`<li><strong>${escA(x.name||x.id)}</strong> — ${escA(x.board)} · ${escA(x.conn)} · ${(x.sensors||[]).join(', ')} · ${escA(x.kind)} <button class="btn" data-load="${i}">Load</button> <button class="btn" data-del="${i}">Delete</button></li>`).join('') || '<li>No saved node designs yet.</li>';
  $$a('#admDesignList [data-load]').forEach(b=>b.addEventListener('click',()=>{
    const x = list[+b.dataset.load]; if(!x) return;
    $a('#admNodeId').value = x.id||''; $a('#admNodeName').value = x.name||''; $a('#admKind').value = x.kind||'collection bin';
    $a('#admStream').value = x.stream||'organics'; $a('#admHost').value = x.host||'DSNY'; $a('#admBorough').value = x.borough||'Brooklyn';
    $a('#admLat').value = x.lat||''; $a('#admLon').value = x.lon||''; $a('#admBoard').value = x.board||'esp32'; $a('#admConn').value = x.conn||'mqtt';
    $a('#admInterval').value = x.interval||300; $a('#admDepth').value = x.depthCm||80;
    $$a('.admSensor').forEach(c=>c.checked = (x.sensors||[]).includes(c.value));
    generateFirmware();
  }));
  $$a('#admDesignList [data-del]').forEach(b=>b.addEventListener('click',()=>{
    const all = designsLoad(); all.splice(+b.dataset.del,1); designsSave(all); renderDesigns();
  }));
}
function renderBackend(){
  const cfg = backendLoad();
  ['platform','hub','forecasting','copilot','contamination','kg'].forEach(k=>{ const el = $a('#admBe'+k[0].toUpperCase()+k.slice(1)); if(el) el.value = cfg[k]||''; });
  $a('#admBeStatus').textContent = cfg.platform||cfg.hub ? 'Backend configured in this browser (keys masked, values never shown here).' : 'No backend URLs saved yet — set them here or in Connect; both views share the same browser store.';
}
async function probeBackends(){
  const cfg = backendLoad(); const out = $a('#admProbeOut'); out.textContent = 'Probing…';
  const checks = [['Platform',cfg.platform],['Hub',cfg.hub],['Forecasting',cfg.forecasting],['KG',cfg.kg],['Copilot',cfg.copilot],['Contamination',cfg.contamination]];
  const rows = [];
  for(const [name, base] of checks){
    if(!base){ rows.push(`${name}: not configured`); continue; }
    try{
      const ctrl = new AbortController(); setTimeout(()=>ctrl.abort(), 6000);
      const r = await fetch(base.replace(/\/$/,'') + '/health', {signal: ctrl.signal});
      rows.push(`${name}: HTTP ${r.status}`);
    }catch(e){ rows.push(`${name}: unreachable (${e.name||'error'}) — check URL / CORS / that the service is running`); }
  }
  out.innerHTML = rows.map(r=>`<li>${escA(r)}</li>`).join('');
}
/* ---------- Direct Flash: MicroPython boards over USB Serial or WiFi WebREPL ----------
   Protocol: MicroPython raw REPL. Ctrl-A enters raw REPL, the file is written
   in small chunks (open 'w' once, then 'a' appends), Ctrl-D executes, Ctrl-B
   exits raw REPL, Ctrl-D again soft-resets so main.py runs on boot.
   Transports: Web Serial (USB, navigator.serial — Chrome/Edge, secure context)
   and WebSocket WebREPL (ws://<device-ip>:8266, device must run webrepl with
   a password set). C++ boards are NOT flashed here: they need a compiler.
   For them Admin shows the arduino-cli USB package + ArduinoOTA wireless path. */
let flashTransport = null;
function flashLog(msg){ const el = $a('#flashLog'); if(el){ el.textContent += msg + '\n'; el.scrollTop = el.scrollHeight; } }
class SerialTransport {
  async open(){ this.port = await navigator.serial.requestPort(); await this.port.open({baudRate:115200}); this.buf=''; this.reader = this.port.readable.getReader(); this.pump(); }
  async pump(){ try{ while(true){ const {value, done} = await this.reader.read(); if(done) break; this.buf += new TextDecoder().decode(value); } }catch(e){} }
  async write(str){ const w = this.port.writable.getWriter(); await w.write(new TextEncoder().encode(str)); w.releaseLock(); }
  async readUntil(pat, ms){ const t0 = Date.now(); while(Date.now()-t0 < ms){ const i = this.buf.indexOf(pat); if(i>=0){ const out = this.buf.slice(0, i+pat.length); this.buf = this.buf.slice(i+pat.length); return out; } await new Promise(r=>setTimeout(r,50)); } throw new Error('timeout waiting for ' + pat); }
  async close(){ try{ await this.reader.cancel(); }catch(e){} try{ await this.port.close(); }catch(e){} }
}
class WsTransport {
  constructor(url, password){ this.url=url; this.password=password; this.buf=''; }
  open(){ return new Promise((res, rej)=>{ this.ws = new WebSocket(this.url); this.ws.onmessage = e=>{ this.buf += e.data; }; this.ws.onerror = ()=>rej(new Error('WebSocket error — is WebREPL running on the device at ' + this.url + '?')); this.ws.onopen = async ()=>{ try{ await this.readUntil('Password:', 5000); await this.send(this.password + '\r\n'); await this.readUntil('>>>', 5000); res(); }catch(e){ rej(e); } }; }); }
  async send(str){ this.ws.send(str); }
  async write(str){ this.ws.send(str); }
  async readUntil(pat, ms){ const t0 = Date.now(); while(Date.now()-t0 < ms){ const i = this.buf.indexOf(pat); if(i>=0){ const out = this.buf.slice(0, i+pat.length); this.buf = this.buf.slice(i+pat.length); return out; } await new Promise(r=>setTimeout(r,50)); } throw new Error('timeout waiting for ' + pat); }
  async close(){ try{ this.ws.close(); }catch(e){} }
}
async function flashMicroPython(){
  const out = $a('#flashLog'); out.textContent = '';
  const {design, code} = generateFirmware();
  const board = BOARDS[design.board];
  if(board.lang!=='micropython'){ out.textContent = 'Direct in-browser flash is for MicroPython boards only (Pico W, ESP32 MicroPython, ESP8266 MicroPython).\nYour design uses a C++ board — use the C++ flash path below (arduino-cli USB package + ArduinoOTA wireless), or switch the board to a MicroPython variant and regenerate.'; return; }
  const transportKind = $a('#flashTransport').value;
  try{
    if(transportKind==='usb'){
      if(!('serial' in navigator)){ out.textContent = 'Web Serial is not available in this browser. Use Chrome or Edge over HTTPS (or localhost), then retry.'; return; }
      flashLog('Opening USB serial port picker — pick your board…');
      flashTransport = new SerialTransport(); await flashTransport.open(); flashLog('Serial port open at 115200 baud.');
    } else {
      const ip = ($a('#flashDeviceIp').value||'').trim(), pw = $a('#flashWebreplPass').value||'';
      if(!ip){ out.textContent = 'Enter the device IP for WiFi WebREPL first (device must run webrepl.start() with a password).'; return; }
      flashLog('Connecting WebREPL to ws://' + ip + ':8266 …');
      flashTransport = new WsTransport('ws://' + ip + ':8266', pw); await flashTransport.open(); flashLog('WebREPL connected and authenticated.');
    }
    flashLog('Interrupting any running program (Ctrl-C) and entering raw REPL (Ctrl-A)…');
    await flashTransport.write('\x03'); await new Promise(r=>setTimeout(r,300));
    await flashTransport.write('\x01'); await flashTransport.readUntil('raw REPL', 5000); await flashTransport.readUntil('>', 5000);
    const chunks = []; for(let i=0;i<code.length;i+=400) chunks.push(code.slice(i, i+400));
    flashLog('Writing main.py in ' + chunks.length + ' chunks…');
    for(let i=0;i<chunks.length;i++){
      const mode = i===0 ? 'w' : 'a';
      const cmd = `f=open('main.py','${mode}');f.write(${JSON.stringify(chunks[i])});f.close()\n`;
      await flashTransport.write(cmd); await flashTransport.readUntil('>', 5000);
      if(i%10===0) flashLog('  chunk ' + (i+1) + '/' + chunks.length);
    }
    flashLog('Verifying file…');
    await flashTransport.write(`import os;print('MAINPY_BYTES', os.stat('main.py')[6])\n`);
    const ver = await flashTransport.readUntil('>', 5000); flashLog('  device replied: ' + ver.replace(/\r/g,'').split('\n').filter(x=>x.includes('MAINPY_BYTES')||x.includes('Traceback')).join(' '));
    flashLog('Exiting raw REPL and soft-resetting so main.py runs on boot…');
    await flashTransport.write('\x04'); await new Promise(r=>setTimeout(r,300));
    await flashTransport.write('\x02'); await flashTransport.write('\x04');
    flashLog('DONE — main.py flashed to the device. Watch the device serial output / telemetry to confirm it reports as ' + design.id + '.');
    flashLog('Note: this wrote the MicroPython program file. It does not replace the MicroPython firmware itself — install MicroPython on the board once first (Pico: drag the UF2; ESP32/ESP8266: esptool flash of the MicroPython .bin), then this flash updates the program any number of times.');
  }catch(e){
    flashLog('FLASH FAILED: ' + (e.message||e) + ' — check cable/port, that the board runs MicroPython, and (for WiFi) that WebREPL is started with the right password.');
  } finally {
    try{ if(flashTransport) await flashTransport.close(); }catch(e){}
    flashTransport = null;
  }
}
function flashCppPackage(){
  const {design, code} = generateFirmware();
  const board = BOARDS[design.board];
  if(board.lang==='micropython'){ $a('#flashLog').textContent = 'This design is MicroPython — use Direct Flash above instead of the C++ package.'; return; }
  const fqbn = {esp32:'esp32:esp32:esp32', esp8266:'esp8266:esp8266:nodemcuv2', uno:'arduino:avr:uno', nano33:'arduino:mbed_nano:nano33ble', stm32:'STM32:stm32:GenF1'}[design.board] || '<board-fqbn>';
  const core = fqbn.split(':').slice(0,2).join(':');
  const script = '# Flash ' + design.id + ' over USB with arduino-cli (run on your machine, board connected by USB)\n# 1) Install the core once: arduino-cli core install ' + core + '\n# 2) Install libraries listed in Admin (Library Manager or: arduino-cli lib install "PubSubClient" "DHT sensor library" "TinyGPSPlus")\n# 3) Put your WiFi password in ' + design.id + '.ino, then:\narduino-cli compile --fqbn ' + fqbn + ' ' + design.id + '.ino\narduino-cli upload -p /dev/ttyUSB0 --fqbn ' + fqbn + ' ' + design.id + '.ino   # Windows: -p COM3, macOS: -p /dev/cu.usbserial-*\n# Wireless re-flash after this first USB flash: the sketch includes ArduinoOTA,\n# so the node appears in Arduino IDE under Tools > Port > Network Ports as ' + design.id + ' — upload to it over WiFi, no cable.\n';
  const blob = new Blob([script], {type:'text/plain'}); const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = design.id + '-flash.sh'; a.click();
  const b2 = new Blob([code], {type:'text/plain'}); const a2 = document.createElement('a');
  a2.href = URL.createObjectURL(b2); a2.download = design.id + '.ino'; a2.click();
  $a('#flashLog').textContent = 'Downloaded ' + design.id + '.ino + ' + design.id + '-flash.sh (arduino-cli USB flash script). Run the script on your machine with the board connected by USB; wireless re-flashes then go via ArduinoOTA network port ' + design.id + '.';
}
/* ---------- Install MicroPython (section 6) ----------
   Pico: BOOTSEL drive write via File System Access (Chrome/Edge), with a
   manual drag-and-drop download as fallback. ESP: esptool-js in the browser
   (loaded on demand from unpkg via the page importmap), erase + writeFlash.
   Firmware fetch: micropython.org -latest files first, then a known-good
   versioned file. If the site blocks direct page fetches (CORS), the log
   says so and the user can download + pick the file instead — the install
   still runs locally, nothing is uploaded to a server. */
const MP_FAMILIES = {
  picow: {kind:'uf2', drive:'RPI-RP2', urls:['https://micropython.org/download/rp2-pico-w/rp2-pico-w-latest.uf2','https://micropython.org/resources/firmware/RPI_PICO_W-20250415-v1.25.0.uf2'], page:'https://micropython.org/download/rp2-pico-w/'},
  pico: {kind:'uf2', drive:'RPI-RP2', urls:['https://micropython.org/download/rp2-pico/rp2-pico-latest.uf2','https://micropython.org/resources/firmware/RPI_PICO-20250415-v1.25.0.uf2'], page:'https://micropython.org/download/rp2-pico/'},
  pico2w: {kind:'uf2', drive:'RP2350', urls:['https://micropython.org/download/rp2-pico2-w/rp2-pico2-w-latest.uf2','https://micropython.org/resources/firmware/RPI_PICO2_W-20250911-v1.26.1.uf2','https://micropython.org/resources/firmware/RPI_PICO2_W-20250415-v1.25.0.uf2'], page:'https://micropython.org/download/rp2-pico2-w/'},
  pico2: {kind:'uf2', drive:'RP2350', urls:['https://micropython.org/download/rp2-pico2/rp2-pico2-latest.uf2','https://micropython.org/resources/firmware/RPI_PICO2-20250415-v1.25.0.uf2'], page:'https://micropython.org/download/rp2-pico2/'},
  esp32: {kind:'bin', address:0x1000, urls:['https://micropython.org/download/ESP32_GENERIC/ESP32_GENERIC-latest.bin','https://micropython.org/resources/firmware/esp32-20250910-v1.26.0.bin'], page:'https://micropython.org/download/ESP32_GENERIC/'},
  esp32s3: {kind:'bin', address:0x1000, urls:['https://micropython.org/download/ESP32_GENERIC_S3/ESP32_GENERIC_S3-latest.bin','https://micropython.org/resources/firmware/esp32s3-20250910-v1.26.0.bin'], page:'https://micropython.org/download/ESP32_GENERIC_S3/'},
  esp8266: {kind:'bin', address:0x0, urls:['https://micropython.org/download/esp8266/esp8266-latest.bin','https://micropython.org/resources/firmware/esp8266-20250910-v1.26.0.bin'], page:'https://micropython.org/download/esp8266/'}
};
function mpLog(msg){ const el = $a('#mpLog'); if(el){ el.textContent += msg + '\n'; el.scrollTop = el.scrollHeight; } }
async function mpGetFirmware(fam){
  const file = $a('#mpFile').files && $a('#mpFile').files[0];
  if(file){ mpLog('Using your file: ' + file.name + ' (' + file.size + ' bytes).'); return {bytes: new Uint8Array(await file.arrayBuffer()), name: file.name}; }
  for(const url of fam.urls){
    try{
      mpLog('Fetching ' + url + ' …');
      const r = await fetch(url);
      if(!r.ok){ mpLog('  HTTP ' + r.status + ' — trying next source.'); continue; }
      const buf = new Uint8Array(await r.arrayBuffer());
      if(buf.length < 10000){ mpLog('  File too small (' + buf.length + ' bytes) — not firmware, trying next source.'); continue; }
      mpLog('  Got ' + buf.length + ' bytes.');
      return {bytes: buf, name: url.split('/').pop()};
    }catch(e){ mpLog('  Fetch failed (' + (e.message||e) + ') — trying next source.'); }
  }
  return null;
}
async function mpDownloadOnly(){
  const fam = MP_FAMILIES[$a('#mpFamily').value];
  $a('#mpLog').textContent = '';
  const fw = await mpGetFirmware(fam);
  if(!fw){ mpLog('Could not fetch firmware directly (micropython.org may block page fetches). Download it manually from ' + fam.page + ' and pick it with the file input, then click Install.'); return; }
  const blob = new Blob([fw.bytes], {type:'application/octet-stream'}); const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = fw.name; a.click();
  mpLog('Downloaded ' + fw.name + ' — for a Pico, drag it onto the ' + (fam.drive||'') + ' drive; for ESP, pick it with the file input and click Install.');
}
async function mpInstallPico(fam, fw){
  if(!('showDirectoryPicker' in window)){ mpLog('File System Access is not available in this browser (needs Chrome/Edge). Use "Download firmware file only" and drag the UF2 onto the ' + fam.drive + ' drive manually.'); return; }
  mpLog('Pick the ' + fam.drive + ' drive in the folder picker (put the Pico in BOOTSEL mode first: hold BOOTSEL, plug in USB, release).');
  const dir = await window.showDirectoryPicker({mode:'readwrite'});
  const handle = await dir.getFileHandle(fw.name, {create:true});
  const w = await handle.createWritable();
  await w.write(fw.bytes); await w.close();
  mpLog('Wrote ' + fw.name + ' (' + fw.bytes.length + ' bytes) to the drive. The drive should disappear as the Pico reboots into MicroPython — unplug and replug USB if the serial port does not appear, then use section 5 Direct Flash to write main.py.');
}
async function mpInstallEsp(fam, fw){
  if(!('serial' in navigator)){ mpLog('Web Serial is not available in this browser. Use Chrome or Edge over HTTPS (or localhost) for ESP flashing, or flash with Python esptool: esptool.py --baud 460800 write_flash ' + (fam.address===0?'0x0':'0x1000') + ' <file>.bin'); return; }
  mpLog('Loading esptool-js (Espressif\'s browser flasher)…');
  let mod = null;
  try{ mod = await import('esptool-js'); }
  catch(e){
    mpLog('Import-map load failed (' + (e.message||e) + ') — trying the single-file bundle…');
    await new Promise((res, rej)=>{ const s = document.createElement('script'); s.src = 'https://unpkg.com/esptool-js/bundle.js'; s.onload = res; s.onerror = ()=>rej(new Error('bundle load failed')); document.head.appendChild(s); });
    mod = window.ESPLoader ? {ESPLoader: window.ESPLoader, Transport: window.Transport} : null;
    if(!mod) throw new Error('esptool-js did not expose ESPLoader/Transport after bundle load.');
  }
  mpLog('Pick the ESP serial port (hold BOOT on the board if it fails to connect)…');
  const port = await navigator.serial.requestPort();
  const transport = new mod.Transport(port, true);
  const terminal = {clean(){}, writeLine(d){ mpLog('  esptool: ' + d); }, write(d){}};
  const loader = new mod.ESPLoader({transport, baudrate:115200, terminal});
  const chip = await loader.main();
  mpLog('Connected: ' + chip + '. Erasing flash…');
  await loader.eraseFlash();
  mpLog('Flashing ' + fw.name + ' (' + fw.bytes.length + ' bytes) at 0x' + fam.address.toString(16) + '…');
  await loader.writeFlash({fileArray:[{data: fw.bytes, address: fam.address}], flashMode:'dio', flashFreq:'40m', flashSize:'4MB', eraseAll:false, compress:true, reportProgress:(i, written, total)=>{ const p = Math.floor(written/total*100); if(p%25===0) mpLog('  flash ' + p + '%'); }});
  mpLog('Flash complete. Resetting…');
  await loader.after('hard_reset');
  try{ await transport.disconnect(); }catch(e){}
  mpLog('DONE — MicroPython is installed. Unplug/replug if needed, then use section 5 Direct Flash to write your node design\'s main.py to the board.');
}
async function mpInstall(){
  const fam = MP_FAMILIES[$a('#mpFamily').value];
  const log = $a('#mpLog'); log.textContent = '';
  try{
    mpLog('Installing MicroPython for ' + $a('#mpFamily').selectedOptions[0].text + '…');
    const fw = await mpGetFirmware(fam);
    if(!fw){ mpLog('FAILED: could not fetch firmware and no file was picked. Download the firmware from ' + fam.page + ', pick it with the file input above, and click Install again.'); return; }
    if(fam.kind==='uf2') await mpInstallPico(fam, fw); else await mpInstallEsp(fam, fw);
  }catch(e){
    mpLog('INSTALL FAILED: ' + (e.message||e) + ' — check the cable (data cable, not charge-only), the board mode (BOOTSEL for Pico, BOOT held for ESP if needed), and that no other app (Thonny, Arduino IDE, serial monitor) is holding the port.');
  }
}
function init(){
  if(!$a('#view-admin')) return;
  // Sensor checkboxes
  $a('#admSensors').innerHTML = Object.entries(SENSORS).map(([k,v])=>`<label><input type="checkbox" class="admSensor" value="${k}"> ${escA(v.label)} <span class="muted small">(${escA(v.field)}; ${escA(v.lib)})</span></label>`).join('');
  // Board + template selects
  $a('#admBoard').innerHTML = Object.entries(BOARDS).map(([k,v])=>`<option value="${k}">${escA(v.label)}</option>`).join('');
  $a('#admTemplate').innerHTML = '<option value="">— start from blank —</option>' + Object.entries(TEMPLATES).map(([k,v])=>`<option value="${k}">${escA(v.name)}</option>`).join('');
  renderBackend(); renderDesigns();
  const st = settingsLoad();
  $a('#admTonnes').value = st.tonnesPerFull; $a('#admBasemapDef').value = st.basemap; $a('#admStreamDef').value = st.stream; $a('#admProcessDef').value = st.process; $a('#admRetention').value = st.retentionDays;
  $$a('.admSensor, #admBoard, #admConn, #admInterval, #admDepth, #admNodeId, #admNodeName').forEach(el=>el.addEventListener('change', generateFirmware));
  $a('#admTemplate')?.addEventListener('change', e=>{
    const t = TEMPLATES[e.target.value]; if(!t) return;
    $a('#admNodeName').value = t.name; $a('#admBoard').value = t.board; $a('#admConn').value = t.conn; $a('#admKind').value = t.kind; $a('#admStream').value = t.stream;
    $$a('.admSensor').forEach(c=>c.checked = t.sensors.includes(c.value));
    generateFirmware();
  });
  $a('#admGenBtn')?.addEventListener('click', generateFirmware);
  $a('#admDownloadBtn')?.addEventListener('click', ()=>{
    const {design, code} = generateFirmware(); if(!design.id){ alert('Enter a Node ID first.'); return; }
    const ext = BOARDS[design.board].lang==='micropython' ? 'py' : 'ino';
    const blob = new Blob([code], {type:'text/plain'}); const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = `${design.id}.${ext}`; a.click();
  });
  $a('#admCopyBtn')?.addEventListener('click', async ()=>{
    const {code} = generateFirmware();
    try{ await navigator.clipboard.writeText(code); $a('#admCopyNote').textContent = 'Copied to clipboard.'; }catch(e){ $a('#admCopyNote').textContent = 'Copy failed — select the code manually.'; }
  });
  $a('#admSaveDesignBtn')?.addEventListener('click', ()=>{
    const d = currentDesign(); if(!d.id){ alert('Enter a Node ID first.'); return; }
    const all = designsLoad(); const i = all.findIndex(x=>x.id===d.id);
    if(i>=0) all[i]=d; else all.unshift(d); designsSave(all); renderDesigns(); generateFirmware();
  });
  $a('#admRegisterBtn')?.addEventListener('click', ()=>{
    const d = currentDesign(); if(!d.id || !d.name){ alert('Enter Node ID and name first.'); return; }
    const nodes = nodesLoad();
    if(!nodes.find(x=>x.id===d.id)) nodes.unshift({id:d.id, site:d.name, kind:d.kind, stream:d.stream, host:d.host, borough:d.borough, lat:d.lat, lon:d.lon, fill:60, source:'admin node design (firmware-ready)'});
    try{ localStorage.setItem('wip_network_nodes', JSON.stringify(nodes)); }catch(e){}
    $a('#admRegisterNote').textContent = `Registered ${d.id} in Collection Network (this browser). Open #network to see it on the real map; its firmware design is saved in Admin.`;
  });
  $a('#admGeoBtn')?.addEventListener('click', async ()=>{
    const q = ($a('#admAddress').value||'').trim(); const out = $a('#admGeoNote'); if(!q){ out.textContent = 'Enter an address first.'; return; }
    out.textContent = 'Geocoding via OpenStreetMap Nominatim…';
    try{
      const j = await (await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q + ', New York, NY')}&format=json&limit=1`)).json();
      if(!j.length){ out.textContent = 'No match — try a street address or place name in NYC.'; return; }
      $a('#admLat').value = (+j[0].lat).toFixed(5); $a('#admLon').value = (+j[0].lon).toFixed(5);
      out.textContent = `Found: ${j[0].display_name}`;
    }catch(e){ out.textContent = 'Geocoding failed — retry.'; }
  });
  $a('#admBeSaveBtn')?.addEventListener('click', ()=>{
    const cfg = backendLoad();
    ['platform','hub','forecasting','copilot','contamination','kg'].forEach(k=>{ const el = $a('#admBe'+k[0].toUpperCase()+k.slice(1)); if(el) cfg[k] = el.value.trim(); });
    backendSave(cfg); renderBackend(); $a('#admBeSaveNote').textContent = 'Backend URLs saved in this browser (shared with Connect).';
  });
  $a('#admProbeBtn')?.addEventListener('click', probeBackends);
  $a('#mpInstallBtn')?.addEventListener('click', mpInstall);
  $a('#mpDownloadBtn')?.addEventListener('click', mpDownloadOnly);
  $a('#mpFile')?.addEventListener('change', ()=>{ const f = $a('#mpFile').files[0]; if(f) $a('#mpFileNote').textContent = 'File chosen: ' + f.name + ' (' + f.size + ' bytes) — Install will use this instead of fetching.'; });
  $a('#flashBtn')?.addEventListener('click', flashMicroPython);
  $a('#flashCppBtn')?.addEventListener('click', flashCppPackage);
  $a('#flashTransport')?.addEventListener('change', ()=>{
    const wifi = $a('#flashTransport').value==='wifi';
    $a('#flashWifiFields').style.display = wifi ? '' : 'none';
  });
  $a('#admSettingsSaveBtn')?.addEventListener('click', ()=>{
    const st = {tonnesPerFull: +$a('#admTonnes').value||0.5, basemap: $a('#admBasemapDef').value, stream: $a('#admStreamDef').value, process: $a('#admProcessDef').value, retentionDays: +$a('#admRetention').value||90};
    try{ localStorage.setItem('wip_admin_settings', JSON.stringify(st)); }catch(e){}
    $a('#admSettingsNote').textContent = 'Network defaults saved in this browser. The Collection Network view reads tonnes-per-full and basemap from these defaults on its next load (defaults are applied when you open #network after a reload).';
  });
  window.addEventListener('hashchange', ()=>{ if((location.hash||'').startsWith('#admin')){ renderBackend(); renderDesigns(); } });
  generateFirmware();
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
