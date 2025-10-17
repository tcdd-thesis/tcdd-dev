# Deployment Checklist

Use this checklist when deploying the C++ server to Raspberry Pi.

## Pre-Deployment (Development Machine)

- [ ] **Model Conversion**
  - [ ] Export YOLOv8 to ONNX format
  - [ ] Convert ONNX to NCNN (.param + .bin)
  - [ ] Optimize with ncnnoptimize
  - [ ] Test model locally if possible
  - [ ] Create labels.txt with class names

- [ ] **Configuration**
  - [ ] Update `shared/config.json` with correct paths
  - [ ] Set appropriate `cppServerPort` (default: 5100)
  - [ ] Configure camera resolution and FPS
  - [ ] Set detection thresholds
  - [ ] Choose Vulkan setting

- [ ] **Code Review**
  - [ ] Commit all C++ source files
  - [ ] Update `.gitignore`
  - [ ] Push to repository
  - [ ] Tag release if appropriate

## Raspberry Pi Setup

- [ ] **System Preparation**
  - [ ] Raspberry Pi OS installed (64-bit recommended)
  - [ ] System updated: `sudo apt-get update && sudo apt-get upgrade`
  - [ ] SSH access configured
  - [ ] Camera module connected
  - [ ] Internet connection available

- [ ] **Enable Camera**
  - [ ] Run `sudo raspi-config`
  - [ ] Enable Legacy Camera interface
  - [ ] Reboot: `sudo reboot`
  - [ ] Test camera: `libcamera-hello --timeout 5000`

- [ ] **Install Dependencies**
  - [ ] Build tools: `sudo apt-get install build-essential cmake git`
  - [ ] OpenCV: `sudo apt-get install libopencv-dev`
  - [ ] Verify OpenCV: `pkg-config --modversion opencv4`
  - [ ] Vulkan (optional): `sudo apt-get install libvulkan-dev vulkan-tools`

- [ ] **Install NCNN**
  - [ ] Clone NCNN repository
  - [ ] Configure with CMake (enable Vulkan if needed)
  - [ ] Build with `make -j$(nproc)`
  - [ ] Install with `sudo make install`
  - [ ] Run `sudo ldconfig`
  - [ ] Verify: `ls /usr/local/include/ncnn/`

## Project Setup

- [ ] **Clone/Copy Project**
  - [ ] Clone repository: `git clone <repo-url>`
  - [ ] Or copy via scp/rsync
  - [ ] Navigate to project: `cd tcdd-dev`
  - [ ] Checkout correct branch if needed

- [ ] **Transfer Model Files**
  - [ ] Copy `model.ncnn.param` to `backend/model/`
  - [ ] Copy `model.ncnn.bin` to `backend/model/`
  - [ ] Copy `labels.txt` to `backend/model/`
  - [ ] Verify files exist and are readable

- [ ] **Configuration Check**
  - [ ] Review `shared/config.json`
  - [ ] Verify model paths are correct
  - [ ] Adjust camera settings if needed
  - [ ] Set logging path

## Build

- [ ] **Build C++ Server**
  - [ ] Navigate to: `cd backend/cpp`
  - [ ] Make scripts executable: `chmod +x build.sh download_deps.sh`
  - [ ] Run build: `./build.sh`
  - [ ] Check for errors
  - [ ] Verify executable: `ls -lh ../cpp_server`

- [ ] **Build Issues**
  - [ ] If NCNN not found, set `NCNN_DIR` in CMakeLists.txt
  - [ ] If OpenCV errors, check version compatibility
  - [ ] If build fails, try clean build: `rm -rf build && ./build.sh`

## Testing

- [ ] **Initial Test**
  - [ ] Navigate to project root: `cd ~/tcdd-dev`
  - [ ] Run server: `./backend/cpp_server`
  - [ ] Check initialization messages
  - [ ] Verify camera opens successfully
  - [ ] Verify model loads successfully
  - [ ] Verify HTTP server starts

- [ ] **Functional Tests**
  - [ ] Test health endpoint: `curl http://localhost:5100/health`
  - [ ] Test status endpoint: `curl http://localhost:5100/api/status`
  - [ ] Test detections endpoint: `curl http://localhost:5100/api/detections`
  - [ ] Test video stream in browser: `http://<pi-ip>:5100/video_feed`

- [ ] **Performance Tests**
  - [ ] Monitor FPS (should be 20-30)
  - [ ] Check CPU usage (should be 60-80%)
  - [ ] Check RAM usage (should be <1GB)
  - [ ] Verify inference time (30-50ms CPU, 15-25ms Vulkan)
  - [ ] Test with real camera in target environment

- [ ] **Log Verification**
  - [ ] Check log file created: `ls logs/`
  - [ ] View log contents: `cat logs/performance_*.csv`
  - [ ] Verify metrics are being recorded
  - [ ] Check for any error messages

## Integration

- [ ] **Node.js Backend**
  - [ ] Update `backend/server.js` proxy configuration
  - [ ] Point to `cppServerPort: 5100`
  - [ ] Test proxy: `curl http://localhost:5000/video_feed`
  - [ ] Restart Node backend: `pm2 restart backend`

- [ ] **Frontend Integration**
  - [ ] Start frontend: `cd frontend && npm start`
  - [ ] Test live feed component
  - [ ] Test status display
  - [ ] Test detection logs
  - [ ] Verify data updates in real-time

- [ ] **End-to-End Test**
  - [ ] Full system running (C++, Node, Frontend)
  - [ ] Navigate to http://<pi-ip>:3000
  - [ ] Verify video stream displays
  - [ ] Verify detections show in UI
  - [ ] Verify status metrics update
  - [ ] Test for 10+ minutes continuous operation

## Production Setup

- [ ] **Systemd Service**
  - [ ] Create service file: `/etc/systemd/system/tcdd-cpp.service`
  - [ ] Set correct paths and user
  - [ ] Reload daemon: `sudo systemctl daemon-reload`
  - [ ] Enable service: `sudo systemctl enable tcdd-cpp`
  - [ ] Start service: `sudo systemctl start tcdd-cpp`
  - [ ] Check status: `sudo systemctl status tcdd-cpp`

- [ ] **Auto-Start on Boot**
  - [ ] Verify service enabled: `systemctl is-enabled tcdd-cpp`
  - [ ] Reboot Pi: `sudo reboot`
  - [ ] After reboot, check service: `sudo systemctl status tcdd-cpp`
  - [ ] Test endpoints after boot

- [ ] **Monitoring**
  - [ ] Set up log rotation if needed
  - [ ] Configure alerts for service failures
  - [ ] Set up remote monitoring (optional)
  - [ ] Document monitoring procedures

## Performance Tuning

- [ ] **Initial Benchmarks**
  - [ ] Record baseline FPS
  - [ ] Record baseline inference time
  - [ ] Record baseline CPU/RAM usage
  - [ ] Document in project notes

- [ ] **Optimization (if needed)**
  - [ ] Try Vulkan: Edit config `"useVulkan": true`
  - [ ] Adjust resolution if FPS too low
  - [ ] Adjust detection interval
  - [ ] Lower JPEG quality if bandwidth limited
  - [ ] Re-benchmark after each change

- [ ] **Performance Targets Met**
  - [ ] FPS >= 20
  - [ ] Inference time <= 50ms (CPU) or <= 25ms (Vulkan)
  - [ ] End-to-end latency <= 150ms
  - [ ] CPU usage <= 85%
  - [ ] No memory leaks (stable over time)

## Documentation

- [ ] **Update Docs**
  - [ ] Document any config changes
  - [ ] Note any issues encountered
  - [ ] Record performance numbers
  - [ ] Update README if needed

- [ ] **Create Runbook**
  - [ ] Document start/stop procedures
  - [ ] Document troubleshooting steps
  - [ ] Document backup procedures
  - [ ] Document rollback procedures

## Backup & Recovery

- [ ] **Backup**
  - [ ] Backup config files
  - [ ] Backup model files
  - [ ] Backup custom code changes
  - [ ] Document backup location

- [ ] **Recovery Test**
  - [ ] Test restore procedure
  - [ ] Document restore steps
  - [ ] Verify system works after restore

## Security

- [ ] **Basic Security**
  - [ ] Change default Pi password
  - [ ] Enable firewall if needed
  - [ ] Restrict API access if needed
  - [ ] Keep system updated

## Final Checks

- [ ] **System Stability**
  - [ ] Run for 24 hours continuously
  - [ ] Monitor for crashes
  - [ ] Monitor for memory leaks
  - [ ] Check log files for errors

- [ ] **Sign-Off**
  - [ ] All tests passed
  - [ ] Performance targets met
  - [ ] Documentation complete
  - [ ] Team notified
  - [ ] Deployment complete ✅

## Post-Deployment

- [ ] **Week 1 Monitoring**
  - [ ] Check daily for issues
  - [ ] Review logs
  - [ ] Monitor performance
  - [ ] Address any issues

- [ ] **Month 1 Review**
  - [ ] Analyze performance trends
  - [ ] Review log data
  - [ ] Plan optimizations if needed
  - [ ] Update documentation

## Rollback Plan

If deployment fails:

1. **Stop C++ Server**
   ```bash
   sudo systemctl stop tcdd-cpp
   ```

2. **Revert Node Proxy**
   - Change back to Python server port
   - Restart Node: `pm2 restart backend`

3. **Start Python Server**
   ```bash
   cd backend/python
   python camera_server.py
   ```

4. **Document Issues**
   - Record what went wrong
   - Save logs
   - Create issue/ticket

## Support Contacts

- **Technical Lead**: _________________
- **DevOps**: _________________
- **On-Call**: _________________

## Notes

_Use this section for deployment-specific notes_

---

**Deployment Date**: _________________
**Deployed By**: _________________
**Version/Commit**: _________________
**Status**: ☐ Success ☐ Failed ☐ Partial
