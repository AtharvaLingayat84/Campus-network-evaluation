# Analysis & Visualization Guide

## Understanding the Visualizations

This guide explains what each of the 8 visualizations shows and how to interpret the data.

### 1. Per-VLAN Traffic Volume (Stacked Bar Chart)

**What it shows**: Packet count per VLAN, split between delivered and lost

**Axes**:
- X-axis: VLAN names (Main_F1...F8, Campus2_F1...F4, SERVERS)
- Y-axis: Packet count (stacked)
- Green bars: Successfully delivered packets
- Red bars: Dropped packets

**How to interpret**:
- **Tall bars**: High-traffic VLANs (usually floors near servers)
- **High red %**: VLAN experiencing congestion or ACL issues
- **Flat distribution**: Balanced load across floors
- **Spikes**: Certain VLANs generating or receiving heavy traffic

**What to look for**:
- Are all VLANs generating traffic? (Should see all bars)
- Is delivery rate consistent? (Red % similar across VLANs?)
- Normal mode vs Exam mode: Expect significant difference in exam mode
  - Normal: ~40% exam, 20% email, 10% cloud, 20% P2P, 10% internet
  - Exam: ~50% exam, 50% email (others blocked)

**Example insight**: "VLAN 101 shows 5000 packets (90% delivered) while VLAN 108 shows only 2000 packets (85% delivered). This suggests non-uniform traffic distribution or floor-specific congestion."

---

### 2. Device Type Performance (Grouped Bar Chart)

**What it shows**: Delivery rate percentage by device type

**Axes**:
- X-axis: Device types (Router, Switch, Server, PC, Printer, AP, Phone/Laptop)
- Y-axis: Delivery rate (%)
- Bars colored by performance (green=good, yellow=warning, red=poor)

**How to interpret**:
- **High bars (>95%)**: Device type performing well
- **Low bars (<85%)**: Device type struggling (likely bottleneck)
- **95% line**: Typical target for enterprise networks

**What to look for**:
- **Server devices**: Should have nearly 100% delivery (they receive)
- **Router/Switch**: Should have high rates (they forward)
- **End devices**: May have lower rates (they send)
- **Consistency**: Similar rates across same device type indicate fair treatment

**Example insight**: "Servers show 98% delivery while PCs show 85%. Servers are well-positioned; PC traffic is facing congestion, likely due to WAN or core link saturation."

**Note**: In this simulation, all end devices have similar characteristics, so you'll see similar bars. Real networks would show more variation.

---

### 3. Traffic Type Distribution (Pie Chart)

**What it shows**: Percentage of total traffic destined for each server/destination

**Slices**: 
- Exam Server (typically 40%)
- Email Server (typically 20%)
- Cloud Server (typically 10%)
- Internet (typically 10%)
- P2P (typically 20%)

**How to interpret**:
- **Size of slice**: Relative traffic volume to that destination
- **Exam mode vs normal**: Should see different percentages
  - Exam: 50/50 (Exam/Email), others blocked
  - Normal: 40/20/10/10/20 (Exam/Email/Cloud/Internet/P2P)

**What to look for**:
- **Does distribution match config?** Check against traffic_weights in config.yaml
- **Exam mode enforcement**: Pie should show only Exam + Email
- **Outliers**: Unexpected destinations indicate misconfigurations

**Example insight**: "In exam mode, 100% of traffic goes to Exam+Email servers (50/50 split), confirming ACL is working correctly. Normal mode shows 35% exam, 22% email, 11% cloud, 12% internet, 20% P2P - matches expected weights."

---

### 4. Delay Distribution by VLAN (Box Plots)

**What it shows**: Latency statistics for each VLAN

**Box plot elements**:
- **Box**: Interquartile range (middle 50% of values)
  - Lower edge: 25th percentile (Q1)
  - Line in box: Median (50th percentile)
  - Upper edge: 75th percentile (Q3)
- **Whiskers**: Min and max delay (or 1.5×IQR)
- **Dots**: Outliers (very high delays)

**How to interpret**:
- **Tall boxes**: High latency variance in that VLAN
- **Flat boxes**: Consistent latency
- **Position**:  Higher = more delay
- **Outliers (dots)**: Packets taking unusually long paths

**What to look for**:
- **Which VLANs have highest median?** These are furthest from servers
- **Consistent pattern?** Should see increasing delay with distance from core
- **Outliers**: Few dots are expected; many dots indicate congestion or routing issues
- **VLAN 128 comparison**: Server VLAN should have low consistent latency

**Example insight**: "VLAN 108 (top floor) has median ~45ms with range 20-80ms. VLAN 101 (bottom) has median ~30ms with range 15-50ms. Longer paths to server from top floor confirmed."

**Diagnosis**:
- **High median + outliers**: Congestion + packet reordering
- **High variance but no outliers**: Normal variation over 60s
- **Consistent high values**: Baseline latency from path length

---

### 5. Packet Loss Root Cause Breakdown (Stacked Bar)

**What it shows**: Total packets categorized by outcome

**Categories** (left to right in stacked bar):
- **Delivered** (green): Successfully arrived
- **Link Loss** (red): Dropped due to congestion
- **TTL Exceeded** (orange): Hop limit reached
- **ACL Blocked** (purple): Policy denied
- **Timeout** (yellow): Connection timeout
- **Other** (gray): Miscellaneous drops

**How to interpret**:
- **Proportions**: What % of packets fall into each category?
- **Total height**: Total packets sent in simulation
- **Exam vs Normal comparison**:
  - Normal: Low ACL, some link loss
  - Exam: High ACL (20-30%), rest link loss
- **Healthy network**: >95% delivered, <1% link loss, <2% other

**What to look for**:
- **Dominant loss category**: Which is biggest non-delivered bar?
  - Link loss → Congestion issue
  - TTL → Routing issue
  - ACL → Policy enforcement (expected in exam)
- **Delivered rate**: Should be >95% in both modes
- **Consistency**: Normal and exam should have similar delivered rates (ACL blocks pre-routing)

**Example insight**: "Normal mode: 9500 delivered (95.2%), 400 link loss (4%), 100 TTL (1%). Exam mode: 8000 delivered (94.1%), 200 link loss (1.9%), 50 TTL (0.5%), 350 ACL (3.3%). Exam mode slightly better due to less total traffic, but ACL blocks as expected."

**Root cause diagnosis**:
- **High link loss**: Oversubscribed links, increase bandwidth
- **High TTL**: Misconfigured paths, check routing
- **High ACL**: Expected in exam mode; indicates policy working
- **High timeout**: Rare; indicates protocol issues

---

### 6. Network Path Efficiency (Histogram)

**What it shows**: Distribution of hop counts for packets

**Axes**:
- X-axis: Hop count (1, 2, 3, 4, 5, 6, ...)
- Y-axis: Number of packets with that hop count
- Height of bar: Frequency of that hop count

**How to interpret**:
- **Most packets at 3-4 hops**: Efficient multi-VLAN routing
- **Tail toward 6+**: Some inefficient paths
- **Concentration**: Should see most packets in similar hop range (narrow distribution)

**What to look for**:
- **Average hop count**: Calculate weighted average
- **Outliers (bars far right)**: Packets taking long paths
- **Single hop**: Same-VLAN communication (should exist for P2P)
- **Symmetry**: Should see expected distribution for your topology

**Example insight**: "60% of packets at 3 hops (typical inter-VLAN), 30% at 4 hops (far VLAN), 5% at 5 hops (campus-to-campus), 5% at 1-2 hops (P2P same VLAN). Distribution matches expected topology."

**Diagnosis**:
- **Clustered around 3-4**: Good efficiency
- **Wide spread**: Mix of short P2P and long inter-campus
- **Unexpectedly high**: Check routing (possible loops or suboptimal paths)
- **All single-hop**: Unusual; indicates all traffic local

---

### 7. Temporal Analysis (Line Chart)

**What it shows**: Cumulative packet delivery over 60-second simulation time

**Axes**:
- X-axis: Time (0-60 seconds)
- Y-axis: Cumulative packets delivered (total increases over time)
- Line: Smooth growth from 0 to total delivered count

**How to interpret**:
- **Slope**: Rate of packet delivery
- **Steep slope**: Many packets delivered per second
- **Flat sections**: Saturation or bottleneck
- **Final height**: Total delivered packets

**What to look for**:
- **Linear growth**: Steady packet delivery throughout
- **Steep then flat**: Fast initial delivery, then saturation
- **Gradual curve**: Increasing delivery rate over time
- **Comparison normal vs exam**: Should see different final heights (exam fewer total packets)

**Example insight**: "Normal mode: Linear growth from 0 to 9500 packets over 60s (~160 pkt/s). Exam mode: Similar slope but ends at 8000 packets due to ACL blocking. Both show steady delivery without saturation events."

**Diagnosis**:
- **Linear**: Network not saturated, balanced load
- **Logarithmic curve**: Initial burst, then saturation
- **Steps/plateaus**: Intermittent congestion
- **Decreasing slope**: Worsening conditions over time

---

### 8. Device Pair Communication Heatmap (Optional Matrix)

**What it shows**: Packet volume between each device pair (if enabled)

**Matrix**:
- Rows: Source devices
- Columns: Destination devices
- Color intensity: Packet count (darker = more packets)

**How to interpret**:
- **Dark cells**: Heavy communication pairs
- **Light cells**: Minimal communication
- **Patterns**:
  - Vertical line at "EXAM_SERVER" column: Many devices sending to exam server
  - Diagonal: Unlikely (same device can't send to itself)
  - Clustered patterns: Indicate communication bottlenecks

**What to look for**:
- **Servers dark column**: Servers receiving traffic (expected)
- **Even distribution**: Balanced server load
- **Spikes**: Certain device pair dominating traffic
- **Patterns**: Temporal behavior (if visualization captured over time)

**Example insight**: "Exam Server column is darkest (40% of traffic). Email Server column is second darkest (20%). P2P traffic scattered across rows and columns. Heatmap confirms traffic distribution matches configuration."

**Note**: This chart shows top 15 communicators to avoid 250×250 matrix (too large to read). Full data available in CSV export.

---

## Metrics Reference

### Global Metrics

| Metric | Unit | Good | Warning | Critical |
|--------|------|------|---------|----------|
| Delivery Rate | % | >95% | 85-95% | <85% |
| Avg Delay | ms | <50 | 50-100 | >100 |
| Avg Hop Count | hops | 3-5 | 5-7 | >7 |
| Link Loss % | % | <2% | 2-5% | >5% |

### Per-VLAN Metrics

| Metric | Meaning |
|--------|---------|
| packets_total | Sum of packets from/to this VLAN |
| packets_delivered | Count successfully reached destination |
| packets_lost | Count that failed to deliver |
| delivery_rate | (delivered/total) × 100% |
| avg_delay_ms | Mean latency for VLAN packets |
| avg_hops | Average hop count for paths involving VLAN |
| loss_reasons | Breakdown: link_loss, ttl_exceeded, acl_blocked |

### Per-Device Metrics

| Metric | Meaning |
|--------|---------|
| packets_sent | Total packets originated from device |
| packets_delivered | Sent packets successfully delivered |
| delivery_rate | (delivered/sent) × 100% |
| avg_delay_ms | Mean latency from this device |
| primary_destinations | Top 3 most frequent destinations |

### Per-Traffic-Type Metrics

| Metric | Meaning |
|--------|---------|
| packets | Total packets to this destination |
| delivered | Successfully delivered to destination |
| delivery_rate | (delivered/packets) × 100% |
| percentage | (packets/total_simulation) × 100% |
| avg_delay_ms | Mean latency to this destination |

---

## Comparing Normal vs. Exam Mode

### Expected Differences

| Aspect | Normal Mode | Exam Mode |
|--------|------------|-----------|
| **Total Traffic** | 100% baseline | 50-70% (other traffic blocked) |
| **Destinations** | 5 (Exam, Email, Cloud, Internet, P2P) | 2 (Exam, Email only) |
| **Delivery Rate** | ~95% | ~95-98% (less congestion) |
| **Avg Delay** | Baseline | May increase (concentrated traffic) |
| **Exam Server Load** | 40% | 50% |
| **Email Server Load** | 20% | 50% |
| **ACL Blocked** | 0% | ~10-15% |

### Reading the Comparison Report

The `simulation_comparison.json` file includes:

```json
{
  "normal_mode": {
    "total_packets": 10000,
    "delivery_rate": 95.2,
    "avg_delay_ms": 45.3,
    "avg_hops": 4.2
  },
  "exam_mode": {
    "total_packets": 6500,
    "delivery_rate": 97.8,
    "avg_delay_ms": 52.1,
    "avg_hops": 4.0
  },
  "deltas": {
    "packet_volume_change_percent": -35,
    "delivery_rate_improvement_percent": 2.6,
    "delay_increase_ms": 6.8,
    "hop_count_change": -0.2
  },
  "analysis": {
    "summary": "Exam mode produces lower traffic volumes with improved delivery rates and increased latency.",
    "packet_volume": "Exam mode reduces traffic by 35% - restriction to 2 servers",
    "delivery_rate": "Delivery improves by 2.6% in exam mode - likely due to reduced congestion",
    "latency": "Latency increases by 6.8 ms in exam mode - longer paths to concentrated servers"
  }
}
```

### Interpreting Deltas

- **packet_volume_change_percent**: Negative = exam traffic reduced (expected; ACL blocking)
- **delivery_rate_improvement_percent**: Positive = fewer packets = less congestion
- **delay_increase_ms**: Positive = longer average paths to concentrated servers
- **hop_count_change**: Usually minimal; indicates slight path changes

---

## Common Findings & Interpretations

### Finding: "Delivery rate drops from 97% to 85%"

**Possible causes**:
1. **Severe congestion**: Link bandwidth exceeded, high random loss
2. **Routing issues**: TTL exceeded, indicating misconfigured paths
3. **ACL enforcement**: Many packets blocked pre-routing
4. **Traffic spike**: Sudden increase in traffic rate

**How to fix**:
- Check `loss_breakdown` visualization: Which reason dominates?
- Review `delay_distribution`: High variance suggests congestion
- Examine `vlan_traffic`: Which VLANs show low delivery?
- Increase link bandwidth in config.yaml

### Finding: "Exam mode has 45ms latency vs normal 35ms"

**Possible causes**:
1. **Concentrated load**: All traffic to 2 servers vs 5 destinations
2. **Core bottleneck**: Limited core router capacity
3. **Queuing**: Higher queuing delay due to concentrated traffic
4. **Not necessarily bad**: Still <50ms is acceptable for enterprise

**What to do**:
- Monitor if latency further increases with more traffic
- Consider QoS to prioritize exam server traffic
- Check `per_vlan_statistics`: Are certain VLANs delayed more?

### Finding: "50% of packets are 6+ hops"

**Possible causes**:
1. **Campus-to-campus traffic**: Inter-campus paths naturally longer
2. **Inefficient routing**: Dijkstra producing non-optimal paths
3. **Network diameter**: Large topology requires many hops
4. **P2P traffic**: Random peer picks may be distant

**How to investigate**:
- Check topology diagram: What's expected hop count for each VLAN?
- Review `device_pair_communication`: Are remote device pairs sending heavily?
- Calculate expected hops: Campus1→Campus2 should be ~5-7 hops
- If >8 hops common: Possible routing bug

### Finding: "ACL blocking 20% in exam mode"

**This is expected!** Exam mode blocks:
- Cloud Server (10% normal traffic)
- Internet (10% normal traffic)
- P2P (20% normal traffic)

**Total blocked**: ~35-40% of normal traffic, but shows as 20% of total because fewer packets generated overall.

---

## Troubleshooting Guide

### Symptom: "All delivery rates ~50%"

**Diagnosis**:
- Likely extreme congestion or misconfigured topology
- Check packet loss breakdown: Is link_loss >50%?

**Fix**:
1. Increase bandwidth in config.yaml:
   ```yaml
   bandwidth:
     wan_link_mbps: 20000  # 2x current
   ```
2. Reduce traffic generation rate
3. Review network topology for obvious bottlenecks

### Symptom: "Huge latency variance (2ms to 500ms delays)"

**Diagnosis**:
- Network approaching saturation
- Queuing delays dominant
- Possible packet reordering

**Check**:
- Is delay_distribution showing many outliers?
- Are loss rates increasing?
- Is temporal_analysis curve flattening?

### Symptom: "TTL exceeded errors"

**Diagnosis**:
- Paths computed with >64 hops (very unlikely with 250 devices)
- Or max_ttl configured too low

**Fix**:
- Increase max_ttl in config:
  ```yaml
  simulation:
    max_ttl: 128  # Standard is 64
  ```
- Review topology: Should never need >12 hops

### Symptom: "Exam mode delivery worse than normal mode"

**Diagnosis**:
- Concentrating traffic on 2 servers causing saturation
- OR longer paths to those 2 servers vs distributed destinations

**Expected**: ~2-5% worse delivery is acceptable
**Unexpected**: >10% worse suggests network design issue

---

## Advanced Analysis

### Calculating Efficiency Metrics

**Path Efficiency**:
```
efficiency = (minimum_possible_hops / actual_hops) × 100%
```
- 100% = all packets take shortest path
- <80% = significant suboptimal routing

**Network Utilization**:
```
utilization = total_packets_delivered / (theoretical_max_capacity)
```
- <30% = underutilized
- 30-70% = optimal operating range
- >70% = approaching saturation

### Capacity Planning Insights

Use the metrics to project:
- **Can network handle 2x traffic?** If delivery drops to <85% at 1x, no
- **Which links need upgrade?** Check per-link loss vs bandwidth
- **Where are bottlenecks?** Identify VLANs/devices with high loss

---

**Last Updated**: 2026-04-08
**Version**: 2.0 (Analysis Guide)
