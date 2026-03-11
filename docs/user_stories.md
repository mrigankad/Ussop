# Ussop — User Stories & Use Cases

> **"Sniper-precision defect detection for every manufacturer"**

---

## 1. User Personas

### 1.1 Maria — Quality Control Manager
- **Age:** 42
- **Role:** QC Manager at mid-size electronics manufacturer
- **Pain Points:** 
  - 3 shifts of manual inspectors, fatigue-related escapes
  - No data on defect trends, reactive not proactive
  - Budget rejected for $80K Cognex system
- **Goals:** Reduce escape rate, get visibility into quality trends, prove ROI to management
- **Tech Comfort:** Moderate (Excel power user, learns software quickly)

### 1.2 David — Manufacturing Engineer
- **Age:** 35
- **Role:** Process Engineer, automotive parts supplier
- **Pain Points:**
  - Current vision system too rigid — fails on new part variants
  - IT won't approve cloud-connected devices
  - Needs measurements, not just pass/fail
- **Goals:** Flexible inspection, precise measurements, on-premise deployment
- **Tech Comfort:** High (Python, SQL, PLC programming)

### 1.3 Sarah — Plant Manager
- **Age:** 48
- **Role:** Operations manager, food packaging facility
- **Pain Points:**
  - FDA compliance requires documentation
  - Manual inspection = labor cost + inconsistency
  - Needs solution deployed before next audit (6 weeks)
- **Goals:** Compliance-ready inspection, fast deployment, cost reduction
- **Tech Comfort:** Low (uses systems, doesn't configure them)

### 1.4 Alex — System Integrator
- **Age:** 31
- **Role:** Industrial automation consultant
- **Pain Points:**
  - Clients want AI vision but sticker shock on solutions
  - Projects delayed waiting for GPU hardware
  - Complex solutions = complex support calls
- **Goals:** Profitable implementations, repeatable deployments, minimal support
- **Tech Comfort:** Expert (industrial networks, vision systems, robotics)

---

## 2. Epic: Core Inspection Workflow

### Epic 1.1: Image Capture & Setup

```
As Maria (QC Manager)
I want to set up a camera station in under 30 minutes
So that I can start inspecting parts without IT or vendor help
```

**Acceptance Criteria:**
- [ ] Camera connects via USB3 or GigE with auto-discovery
- [ ] Lighting configuration wizard with preview
- [ ] Positioning guide overlay shows optimal part placement
- [ ] Save/load station configurations
- [ ] Calibration tool for pixel-to-real-world measurements

**Story Points:** 8
**Priority:** P0 (Critical Path)

---

```
As David (Manufacturing Engineer)
I want to trigger inspection via multiple methods
So that Ussop integrates with my existing automation
```

**Acceptance Criteria:**
- [ ] Software trigger (manual button click)
- [ ] Hardware trigger (digital input from PLC)
- [ ] Free-run mode (continuous inspection at set FPS)
- [ ] API trigger (HTTP POST with image)
- [ ] Configurable debounce and trigger delay

**Story Points:** 5
**Priority:** P0

---

### Epic 1.2: Detection & Segmentation

```
As Maria (QC Manager)
I want the system to automatically detect and segment defects
So that I don't need to manually inspect every part
```

**Acceptance Criteria:**
- [ ] Detect pre-trained defect types with >85% accuracy
- [ ] Generate precise segmentation masks (not just boxes)
- [ ] Process single image in < 1 second on i5 CPU
- [ ] Handle multiple defects per part
- [ ] Assign confidence score to each detection

**Story Points:** 13
**Priority:** P0

---

```
As David (Manufacturing Engineer)
I want to measure defect dimensions from segmentation masks
So that I can reject parts based on quantitative criteria
```

**Acceptance Criteria:**
- [ ] Calculate defect area (mm²)
- [ ] Measure maximum length/width of defect
- [ ] Measure distance from defect to part edges
- [ ] Export measurements to CSV/JSON
- [ ] Set pass/fail thresholds per measurement

**Story Points:** 8
**Priority:** P1

---

### Epic 1.3: Decision & Action

```
As Sarah (Plant Manager)
I want automatic pass/fail decisions with configurable rules
So that operators know immediately what to do with each part
```

**Acceptance Criteria:**
- [ ] Set confidence threshold for detection (default 0.5)
- [ ] Set measurement thresholds (e.g., scratch > 2mm = fail)
- [ ] Combine multiple criteria with AND/OR logic
- [ ] Visual pass/fail indicator (green/red overlay)
- [ ] Override capability for operator with reason code

**Story Points:** 5
**Priority:** P0

---

```
As David (Manufacturing Engineer)
I want digital I/O signals for pass/fail
So that Ussop controls my reject mechanism
```

**Acceptance Criteria:**
- [ ] Configurable digital outputs (pass/fail/noresult)
- [ ] Pulse width configuration
- [ ] Relay output support (24V industrial)
- [ ] Safe state configuration (fail-safe on disconnect)
- [ ] Signal timing diagnostics

**Story Points:** 5
**Priority:** P1

---

## 3. Epic: Model Training & Improvement

### Epic 2.1: Transfer Learning

```
As Maria (QC Manager)
I want to train the system on my specific defects
So that detection improves for my unique parts
```

**Acceptance Criteria:**
- [ ] Upload 20+ example images of each defect type
- [ ] Web-based annotation tool (draw boxes/polygons)
- [ ] Train new model in < 2 hours
- [ ] A/B test new vs. existing model
- [ ] Rollback to previous model version

**Story Points:** 13
**Priority:** P1

---

```
As David (Manufacturing Engineer)
I want active learning suggestions
So that I focus labeling effort on uncertain predictions
```

**Acceptance Criteria:**
- [ ] Flag predictions with confidence 0.3-0.7 for review
- [ ] Queue of uncertain images for operator review
- [ ] One-click promote to training set
- [ ] Model improvement metrics over time
- [ ] Alert when model performance degrades

**Story Points:** 8
**Priority:** P2

---

### Epic 2.2: Model Management

```
As Alex (System Integrator)
I want to manage models across multiple customer sites
So that I can maintain deployments efficiently
```

**Acceptance Criteria:**
- [ ] Model versioning (semantic versioning)
- [ ] Deploy model to specific station remotely
- [ ] Compare model performance across sites
- [ ] Model repository with search/filter
- [ ] Export/import models for offline transfer

**Story Points:** 8
**Priority:** P2

---

## 4. Epic: Analytics & Reporting

### Epic 3.1: Real-Time Dashboard

```
As Sarah (Plant Manager)
I want a dashboard showing current production quality
So that I can spot issues immediately
```

**Acceptance Criteria:**
- [ ] Parts inspected count (shift/day/week)
- [ ] Pass/fail rate with trend
- [ ] Defect type breakdown (pie/bar chart)
- [ ] Station status (online/offline/idle)
- [ ] Auto-refresh every 30 seconds

**Story Points:** 8
**Priority:** P1

---

```
As Maria (QC Manager)
I want to view inspection history with images
So that I can investigate quality issues
```

**Acceptance Criteria:**
- [ ] Search by date/time range
- [ ] Filter by pass/fail/defect type
- [ ] View full-resolution image with overlays
- [ ] Download individual or batch results
- [ ] Side-by-side compare two inspections

**Story Points:** 5
**Priority:** P1

---

### Epic 3.2: Trend Analysis

```
As Maria (QC Manager)
I want to see defect trends over time
So that I can identify process improvements
```

**Acceptance Criteria:**
- [ ] Pareto chart of defect types (80/20 rule)
- [ ] Control charts (SPC) for key metrics
- [ ] Compare shifts/operators/lines
- [ ] Export reports to PDF/Excel
- [ ] Scheduled email reports (daily/weekly)

**Story Points:** 8
**Priority:** P2

---

```
As Sarah (Plant Manager)
I want integration with OEE calculations
So that quality impacts on productivity are visible
```

**Acceptance Criteria:**
- [ ] API to fetch quality data for OEE systems
- [ ] First-pass yield metric
- [ ] Rework rate tracking
- [ ] Correlation with downtime events
- [ ] Benchmark vs. industry standards

**Story Points:** 5
**Priority:** P2

---

## 5. Epic: Integration & Deployment

### Epic 4.1: Industrial Integration

```
As David (Manufacturing Engineer)
I want Modbus TCP communication
So that Ussop talks to my PLC
```

**Acceptance Criteria:**
- [ ] Modbus TCP server (slave) mode
- [ ] Configurable register map
- [ ] Read: trigger inspection, get results
- [ ] Write: pass/fail signal, station status
- [ ] Support for Modbus polling and async updates

**Story Points:** 8
**Priority:** P1

---

```
As Alex (System Integrator)
I want MQTT support for IoT architectures
So that Ussop fits modern connected factories
```

**Acceptance Criteria:**
- [ ] MQTT client with configurable broker
- [ ] JSON payload format
- [ ] Topics: inspection/results, station/status, alerts
- [ ] TLS/SSL encryption support
- [ ] Last will and testament

**Story Points:** 5
**Priority:** P2

---

```
As David (Manufacturing Engineer)
I want a REST API for custom integrations
So that I can build my own workflows
```

**Acceptance Criteria:**
- [ ] Swagger/OpenAPI documentation
- [ ] Endpoints: inspect, get results, manage models
- [ ] Authentication (API keys)
- [ ] Rate limiting
- [ ] Webhook support for async results

**Story Points:** 8
**Priority:** P1

---

### Epic 4.2: Deployment & Operations

```
As Alex (System Integrator)
I want Docker deployment
So that installation is consistent across sites
```

**Acceptance Criteria:**
- [ ] Single Docker Compose file
- [ ] Environment variable configuration
- [ ] Volume mounts for models and data
- [ ] Health check endpoints
- [ ] Graceful shutdown handling

**Story Points:** 5
**Priority:** P1

---

```
As Sarah (Plant Manager)
I want automatic backup of inspection data
So that I don't lose records for compliance
```

**Acceptance Criteria:**
- [ ] Scheduled local backups
- [ ] Cloud sync option (S3/Azure Blob)
- [ ] Backup verification
- [ ] Point-in-time restore
- [ ] Retention policy configuration

**Story Points:** 5
**Priority:** P2

---

## 6. Epic: User Management & Security

### Epic 5.1: Access Control

```
As Sarah (Plant Manager)
I want role-based access control
So that operators can't accidentally change configurations
```

**Acceptance Criteria:**
- [ ] Roles: Admin, Engineer, Operator, Viewer
- [ ] Permission matrix (view, inspect, configure, train, admin)
- [ ] LDAP/Active Directory integration
- [ ] Audit log of user actions
- [ ] Session timeout configuration

**Story Points:** 8
**Priority:** P2

---

```
As David (Manufacturing Engineer)
I want audit trails for all inspections
So that we meet FDA/ISO compliance requirements
```

**Acceptance Criteria:**
- [ ] Tamper-proof inspection records
- [ ] User attribution for all actions
- [ ] Before/after images for model changes
- [ ] Export audit trail for inspection
- [ ] 21 CFR Part 11 electronic signature support

**Story Points:** 8
**Priority:** P2

---

## 7. Use Case Scenarios

### Scenario 1: Electronics PCB Inspection

**Context:** Electronics manufacturer inspecting circuit boards for soldering defects

**Workflow:**
1. Operator places PCB in fixture under camera
2. Hardware trigger from fixture initiates inspection
3. Ussop detects: cold solder joints, bridging, missing components
4. Segmentation masks show exact defect boundaries
5. Decision: Pass (green light) or Fail (red light + air blast reject)
6. Results logged with serial number from PLC
7. Trend analysis shows defect spike on Line 3 → investigation finds worn reflow oven

**Key Ussop Features:**
- Small defect detection (0.5mm solder bridges)
- High throughput (1 part every 3 seconds)
- Integration with existing conveyor and reject mechanism

---

### Scenario 2: Food Packaging Seal Inspection

**Context:** Food packager checking heat-seal integrity on snack bags

**Workflow:**
1. Bags pass under camera on conveyor (free-run mode)
2. Ussop segments seal region and checks for wrinkles/gaps
3. Failed bags tracked to specific station for rework
4. Daily report shows seal quality by sealing head
5. Predictive maintenance alert when seal quality trends down

**Key Ussop Features:**
- Continuous inspection mode
- Hygienic design (IP65 camera housing)
- FDA-compliant audit trail

---

### Scenario 3: Automotive Part Dimensional Check

**Context:** Tier-2 automotive supplier checking cast aluminum parts

**Workflow:**
1. Robot places part in inspection station
2. Multiple cameras capture different surfaces
3. Ussop segments casting and measures critical dimensions
4. Measurement data sent to QMS via API
5. Parts outside tolerance routed to rework
6. CPK calculations updated automatically

**Key Ussop Features:**
- Multi-camera support
- Precise measurements from segmentation
- Direct QMS integration

---

### Scenario 4: Textile Defect Detection

**Context:** Fabric mill inspecting rolls for weaving defects

**Workflow:**
1. Line scan camera captures continuous fabric image
2. Ussop detects knots, holes, color variations
3. Defects mapped to roll position (meter marking)
4. Operator console shows defect preview and location
5. Roll cut and splice decisions based on defect map

**Key Ussop Features:**
- Line scan camera support
- Long image stitching
- Position tracking on continuous material

---

## 8. Non-Functional Requirements

### Performance
- Single image inference: < 1s on Intel i5-10400
- Throughput: 30+ parts/minute with async processing
- Dashboard load time: < 3s
- API response time (p99): < 500ms

### Reliability
- System uptime: 99.5%
- Mean Time Between Failures: > 720 hours
- Automatic recovery from camera disconnect
- Data integrity: zero unlogged inspections

### Scalability
- Support up to 4 cameras per station
- Support up to 100 stations per deployment
- Database: 1M+ inspections without performance degradation
- Model repository: 100+ model versions

### Security
- Role-based access control
- API authentication
- Encrypted data transmission (TLS 1.3)
- No data leakage between customers (multi-tenant)
- Regular security updates

### Usability
- Operator training: < 30 minutes
- First inspection within 1 hour of installation
- Contextual help throughout UI
- Error messages in plain language
- Keyboard shortcuts for common actions

---

## 9. Story Map & Prioritization

### Release 1: MVP (Month 1-3)
| Priority | Story | Points |
|----------|-------|--------|
| P0 | Camera setup wizard | 8 |
| P0 | Basic detection & segmentation | 13 |
| P0 | Pass/fail decision | 5 |
| P0 | Manual trigger | 3 |
| P1 | Web dashboard | 8 |
| P1 | Inspection history | 5 |

### Release 2: Production (Month 4-6)
| Priority | Story | Points |
|----------|-------|--------|
| P0 | Hardware trigger | 5 |
| P1 | Measurements | 8 |
| P1 | Modbus TCP | 8 |
| P1 | REST API | 8 |
| P1 | Docker deployment | 5 |
| P2 | Transfer learning | 13 |
| P2 | Trend analysis | 8 |

### Release 3: Enterprise (Month 7-12)
| Priority | Story | Points |
|----------|-------|--------|
| P2 | Model management | 8 |
| P2 | Active learning | 8 |
| P2 | MQTT | 5 |
| P2 | RBAC | 8 |
| P2 | Audit trails | 8 |
| P2 | Multi-station analytics | 5 |

---

## 10. Success Metrics by Story

| Story | Success Metric | Target |
|-------|----------------|--------|
| Camera setup | Time to first inspection | < 30 min |
| Detection | Accuracy on customer defects | > 85% mAP |
| Segmentation | Mask IoU | > 0.80 |
| Measurements | Dimensional accuracy | ±0.1mm |
| Dashboard | Daily active users | 100% of operators |
| Training | Time to new model | < 2 hours |
| Integration | API uptime | 99.9% |

---

*"8000 shooters, fire!"* — Ussop's army is ready to find every defect.

**Document Version:** 1.0  
**Last Updated:** March 2026  
**Owner:** The Ussop Product Team
