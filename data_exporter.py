"""Data Exporter Module
====================

Exports simulation results to structured formats (CSV, JSON, Pickle) using
plain Python data structures.
"""

from __future__ import annotations

import csv
import json
import os
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional


class DataExporter:
    def __init__(self, packets: List[Any], results: Dict[str, Any], output_dir: str = "./output"):
        self.packets = packets
        self.results = results
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.records = [self._packet_to_record(pkt) for pkt in packets]

    def _packet_to_record(self, pkt: Any) -> Dict[str, Any]:
        loss_reason = getattr(pkt, "loss_reason", "none")
        return {
            "timestamp": getattr(pkt, "timestamp", 0),
            "src_ip": getattr(pkt, "src_ip", ""),
            "dst_ip": getattr(pkt, "dst_ip", ""),
            "src_name": getattr(pkt, "src_name", ""),
            "dst_name": getattr(pkt, "dst_name", ""),
            "src_type": getattr(pkt, "src_type", ""),
            "dst_type": getattr(pkt, "dst_type", ""),
            "src_vlan": getattr(pkt, "src_vlan", 0),
            "dst_vlan": getattr(pkt, "dst_vlan", 0),
            "bytes": getattr(pkt, "size", 0),
            "delay_ms": getattr(pkt, "delay_ms", 0),
            "hops": getattr(pkt, "hops", 0),
            "status": getattr(pkt, "status", "unknown"),
            "loss_reason": loss_reason,
            "acl_blocked_reason": getattr(pkt, "acl_blocked_reason", ""),
            "asa_fw_penalty_ms": getattr(pkt, "asa_fw_penalty_ms", 0.0),
            "effective_delay_ms": float(getattr(pkt, "delay_ms", 0)) + float(getattr(pkt, "asa_fw_penalty_ms", 0.0)),
            "effective_hops": int(getattr(pkt, "hops", 0)) + (1 if "ASA_FW" in getattr(pkt, "path", []) else 0),
        }

    def to_csv(self, filename: Optional[str] = None, mode: str = "normal") -> str:
        if filename is None:
            filename = f"simulation_results_{mode}.csv"

        filepath = os.path.join(self.output_dir, filename)
        if not self.records:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([])
            return filepath

        fieldnames = list(self.records[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.records)

        print(f"[OK] CSV export: {filepath}")
        return filepath

    def to_json(self, filename: str = "simulation_summary.json") -> str:
        filepath = os.path.join(self.output_dir, filename)

        json_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_packets": len(self.records),
                "delivered_packets": sum(1 for r in self.records if r["status"] == "delivered"),
                "dropped_packets": sum(1 for r in self.records if r["status"] != "delivered"),
                "dropped_loss_packets": sum(1 for r in self.records if r["loss_reason"] not in ("none", "ttl_exceeded", "acl_blocked") and r["status"] != "delivered"),
                "dropped_ttl_packets": sum(1 for r in self.records if r["loss_reason"] == "ttl_exceeded"),
                "acl_blocked_packets": sum(1 for r in self.records if r["loss_reason"] == "acl_blocked"),
                "delivery_rate": self._calc_delivery_rate(),
                "avg_delay_ms": self._safe_mean([r["effective_delay_ms"] for r in self.records if r["loss_reason"] != "acl_blocked"]),
                "avg_hops": self._safe_mean([r["effective_hops"] for r in self.records if r["loss_reason"] != "acl_blocked"]),
                "max_delay_ms": max([r["effective_delay_ms"] for r in self.records if r["loss_reason"] != "acl_blocked"], default=0),
                "min_delay_ms": min([r["effective_delay_ms"] for r in self.records if r["loss_reason"] != "acl_blocked"], default=0),
            },
            "per_vlan": self._calc_vlan_stats(),
            "per_device": self._calc_device_stats(),
            "per_traffic_type": self._calc_traffic_type_stats(),
            "loss_breakdown": self._calc_loss_breakdown(),
            "hop_distribution": self._calc_hop_distribution(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        print(f"[OK] JSON export: {filepath}")
        return filepath

    def to_pickle(self, filename: str = "simulation_data.pkl") -> str:
        filepath = os.path.join(self.output_dir, filename)
        data = {
            "packets": self.packets,
            "records": self.records,
            "results": self.results,
            "timestamp": datetime.now().isoformat(),
        }
        with open(filepath, "wb") as f:
            pickle.dump(data, f)
        print(f"[OK] Pickle export: {filepath}")
        return filepath

    def _calc_delivery_rate(self) -> float:
        if not self.records:
            return 0.0
        delivered = sum(1 for r in self.records if r["status"] == "delivered")
        return round((delivered / len(self.records)) * 100, 2)

    def _safe_mean(self, values: List[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    def _calc_vlan_stats(self) -> Dict[int, Dict[str, Any]]:
        vlan_stats = {}
        all_vlans = sorted({int(v) for r in self.records for v in (r["src_vlan"], r["dst_vlan"]) if v not in (None, "")})

        for vlan in all_vlans:
            vlan_packets = [r for r in self.records if r["src_vlan"] == vlan or r["dst_vlan"] == vlan]
            if not vlan_packets:
                continue
            delivered = sum(1 for r in vlan_packets if r["status"] == "delivered")
            traversed = [r for r in vlan_packets if r["loss_reason"] != "acl_blocked"]
            delays = [r["effective_delay_ms"] for r in traversed]
            hops = [r["effective_hops"] for r in traversed]
            dropped_loss = sum(1 for r in vlan_packets if r["loss_reason"] not in ("none", "ttl_exceeded", "acl_blocked") and r["status"] != "delivered")
            dropped_ttl = sum(1 for r in vlan_packets if r["loss_reason"] == "ttl_exceeded")
            vlan_stats[vlan] = {
                "packets_total": len(vlan_packets),
                "packets_delivered": delivered,
                "dropped_packets": sum(1 for r in vlan_packets if r["status"] != "delivered"),
                "dropped_loss": dropped_loss,
                "dropped_ttl": dropped_ttl,
                "acl_blocked": sum(1 for r in vlan_packets if r["loss_reason"] == "acl_blocked"),
                "packets_lost": dropped_loss + dropped_ttl,
                "delivery_rate": round((delivered / len(vlan_packets)) * 100, 2),
                "avg_delay_ms": self._safe_mean(delays),
                "avg_hops": self._safe_mean(hops),
                "loss_reasons": self._get_loss_reasons(vlan_packets),
            }

        return vlan_stats

    def _calc_device_stats(self) -> Dict[str, Dict[str, Any]]:
        device_stats = {}
        major_devices = sorted({r["src_name"] for r in self.records if r["src_type"] in ("server", "router", "switch")})

        for device in major_devices:
            device_packets = [r for r in self.records if r["src_name"] == device]
            if not device_packets:
                continue
            delivered = sum(1 for r in device_packets if r["status"] == "delivered")
            traversed = [r for r in device_packets if r["loss_reason"] != "acl_blocked"]
            delays = [r["effective_delay_ms"] for r in traversed]
            dst_counts: Dict[str, int] = {}
            for r in device_packets:
                dst_counts[r["dst_name"]] = dst_counts.get(r["dst_name"], 0) + 1
            primary_destinations = [k for k, _ in sorted(dst_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
            device_stats[device] = {
                "device_type": device_packets[0]["src_type"],
                "vlan": device_packets[0]["src_vlan"],
                "packets_sent": len(device_packets),
                "packets_delivered": delivered,
                "dropped_packets": sum(1 for r in device_packets if r["status"] != "delivered"),
                "delivery_rate": round((delivered / len(device_packets)) * 100, 2),
                "avg_delay_ms": self._safe_mean(delays),
                "primary_destinations": primary_destinations,
            }

        return device_stats

    def _calc_traffic_type_stats(self) -> Dict[str, Dict[str, Any]]:
        traffic_stats = {}
        destinations = sorted({r["dst_name"] for r in self.records if r["dst_name"]})

        for dest in destinations:
            dest_packets = [r for r in self.records if r["dst_name"] == dest]
            if not dest_packets:
                continue
            delivered = sum(1 for r in dest_packets if r["status"] == "delivered")
            traversed = [r for r in dest_packets if r["loss_reason"] != "acl_blocked"]
            delays = [r["effective_delay_ms"] for r in traversed]
            dropped_loss = sum(1 for r in dest_packets if r["loss_reason"] not in ("none", "ttl_exceeded", "acl_blocked") and r["status"] != "delivered")
            dropped_ttl = sum(1 for r in dest_packets if r["loss_reason"] == "ttl_exceeded")
            traffic_stats[dest] = {
                "packets": len(dest_packets),
                "delivered": delivered,
                "dropped_packets": sum(1 for r in dest_packets if r["status"] != "delivered"),
                "dropped_loss": dropped_loss,
                "dropped_ttl": dropped_ttl,
                "acl_blocked": sum(1 for r in dest_packets if r["loss_reason"] == "acl_blocked"),
                "dropped": dropped_loss + dropped_ttl,
                "delivery_rate": round((delivered / len(dest_packets)) * 100, 2),
                "avg_delay_ms": self._safe_mean(delays),
                "avg_hops": self._safe_mean([r["effective_hops"] for r in traversed]),
                "percentage": round((len(dest_packets) / len(self.records)) * 100, 2),
            }

        return traffic_stats

    def _calc_loss_breakdown(self) -> Dict[str, Any]:
        loss_breakdown = {
            "delivered": sum(1 for r in self.records if r["status"] == "delivered"),
            "dropped_loss": sum(1 for r in self.records if r["loss_reason"] not in ("none", "ttl_exceeded", "acl_blocked") and r["status"] != "delivered"),
            "dropped_ttl": sum(1 for r in self.records if r["loss_reason"] == "ttl_exceeded"),
            "acl_blocked": sum(1 for r in self.records if r["loss_reason"] == "acl_blocked"),
        }
        total = sum(loss_breakdown.values())
        if total:
            loss_breakdown["percentages"] = {k: round((v / total) * 100, 2) for k, v in loss_breakdown.items()}
        return loss_breakdown

    def _calc_hop_distribution(self) -> Dict[int, int]:
        hop_counts: Dict[int, int] = {}
        for r in self.records:
            hops = int(r["hops"])
            hop_counts[hops] = hop_counts.get(hops, 0) + 1
        return dict(sorted(hop_counts.items()))

    def _get_loss_reasons(self, packets: List[Dict[str, Any]]) -> Dict[str, int]:
        reasons: Dict[str, int] = {}
        for r in packets:
            if r["status"] != "delivered":
                reason = r["loss_reason"]
                reasons[reason] = reasons.get(reason, 0) + 1
        return reasons
