"""Network Analyzer Module
=======================

Computes detailed analytics on simulation results using plain Python data
structures. This keeps the reporting and visualization pipeline lightweight.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, pstdev
from typing import Any, Dict, List


class NetworkAnalyzer:
    """Performs detailed network analytics on simulation packet data."""

    def __init__(self, packets: List[Any]):
        self.packets = packets
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

    def _records_for_vlan(self, vlan: int) -> List[Dict[str, Any]]:
        return [
            r
            for r in self.records
            if r["src_vlan"] == vlan or r["dst_vlan"] == vlan
        ]

    def _mean(self, values: List[float]) -> float:
        return round(mean(values), 2) if values else 0

    def _std(self, values: List[float]) -> float:
        return round(pstdev(values), 2) if len(values) > 1 else 0

    def _quantile(self, values: List[float], q: float) -> float:
        if not values:
            return 0
        ordered = sorted(values)
        pos = (len(ordered) - 1) * q
        lower = int(pos)
        upper = min(lower + 1, len(ordered) - 1)
        if lower == upper:
            return round(ordered[lower], 2)
        frac = pos - lower
        return round(ordered[lower] + (ordered[upper] - ordered[lower]) * frac, 2)

    def get_overall_stats(self) -> Dict[str, Any]:
        if not self.records:
            return self._empty_stats()

        delivered = [r for r in self.records if r["status"] == "delivered"]
        traversed = [r for r in self.records if r["loss_reason"] != "acl_blocked"]
        delays = [float(r["effective_delay_ms"]) for r in traversed]
        hops = [int(r["effective_hops"]) for r in traversed]
        total = len(self.records)
        acl_blocked = sum(1 for r in self.records if r["loss_reason"] == "acl_blocked")
        dropped_ttl = sum(1 for r in self.records if r["loss_reason"] == "ttl_exceeded")
        dropped_loss = sum(1 for r in self.records if r["loss_reason"] in ("link_loss", "timeout", "other"))

        return {
            "total_packets": total,
            "delivered_packets": len(delivered),
            "dropped_packets": sum(1 for r in self.records if r["status"] != "delivered"),
            "dropped_loss_packets": dropped_loss,
            "dropped_ttl_packets": dropped_ttl,
            "acl_blocked_packets": acl_blocked,
            "delivery_rate": round((len(delivered) / total) * 100, 2) if total else 0,
            "avg_delay_ms": self._mean(delays),
            "std_delay_ms": self._std(delays),
            "min_delay_ms": round(min(delays), 2) if delays else 0,
            "max_delay_ms": round(max(delays), 2) if delays else 0,
            "avg_hops": self._mean(hops),
            "min_hops": min(hops) if hops else 0,
            "max_hops": max(hops) if hops else 0,
        }

    def get_vlan_statistics(self) -> List[Dict[str, Any]]:
        if not self.records:
            return []

        all_vlans = sorted(
            {
                int(v)
                for r in self.records
                for v in (r["src_vlan"], r["dst_vlan"])
                if v not in (None, "")
            }
        )

        vlan_stats = []
        for vlan in all_vlans:
            vlan_packets = self._records_for_vlan(vlan)
            if not vlan_packets:
                continue

            delivered = [r for r in vlan_packets if r["status"] == "delivered"]
            traversed = [r for r in vlan_packets if r["loss_reason"] != "acl_blocked"]
            delays = [float(r["effective_delay_ms"]) for r in traversed]
            hops = [int(r["effective_hops"]) for r in traversed]
            acl_blocked = sum(1 for r in vlan_packets if r["loss_reason"] == "acl_blocked")
            dropped_ttl = sum(1 for r in vlan_packets if r["loss_reason"] == "ttl_exceeded")
            dropped_loss = sum(1 for r in vlan_packets if r["loss_reason"] in ("link_loss", "timeout", "other"))
            vlan_stats.append(
                {
                    "vlan": vlan,
                    "packets_total": len(vlan_packets),
                    "packets_delivered": len(delivered),
                    "dropped_packets": sum(1 for r in vlan_packets if r["status"] != "delivered"),
                    "dropped_loss": dropped_loss,
                    "dropped_ttl": dropped_ttl,
                    "acl_blocked": acl_blocked,
                    "packets_lost": dropped_loss + dropped_ttl,
                    "delivery_rate": round((len(delivered) / len(vlan_packets)) * 100, 2),
                    "avg_delay_ms": self._mean(delays),
                    "avg_hops": self._mean(hops),
                    "loss_reasons": self._get_loss_reasons(vlan_packets),
                }
            )

        return vlan_stats

    def get_device_statistics(self) -> List[Dict[str, Any]]:
        if not self.records:
            return []

        device_stats = []
        all_devices = sorted({r["src_name"] for r in self.records if r["src_name"]})

        for device in all_devices:
            device_packets = [r for r in self.records if r["src_name"] == device]
            if not device_packets:
                continue

            delivered = [r for r in device_packets if r["status"] == "delivered"]
            traversed = [r for r in device_packets if r["loss_reason"] != "acl_blocked"]
            delays = [float(r["effective_delay_ms"]) for r in traversed]
            destination_counts = defaultdict(int)
            for r in device_packets:
                destination_counts[r["dst_name"]] += 1

            primary_destinations = [
                name for name, _ in sorted(destination_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            ]

            device_stats.append(
                {
                    "device": device,
                    "device_type": device_packets[0]["src_type"] if device_packets else "Unknown",
                    "vlan": device_packets[0]["src_vlan"] if device_packets else None,
                    "packets_sent": len(device_packets),
                    "packets_delivered": len(delivered),
                    "dropped_packets": sum(1 for r in device_packets if r["status"] != "delivered"),
                    "delivery_rate": round((len(delivered) / len(device_packets)) * 100, 2),
                    "avg_delay_ms": self._mean(delays),
                    "primary_destinations": ", ".join(primary_destinations),
                }
            )

        return device_stats

    def get_traffic_type_statistics(self) -> Dict[str, Dict[str, Any]]:
        if not self.records:
            return {}

        traffic_stats = {}
        for dest in sorted({r["dst_name"] for r in self.records if r["dst_name"]}):
            dest_packets = [r for r in self.records if r["dst_name"] == dest]
            if not dest_packets:
                continue

            delivered = [r for r in dest_packets if r["status"] == "delivered"]
            traversed = [r for r in dest_packets if r["loss_reason"] != "acl_blocked"]
            delays = [float(r["effective_delay_ms"]) for r in traversed]
            dropped_ttl = sum(1 for r in dest_packets if r["loss_reason"] == "ttl_exceeded")
            dropped_loss = sum(1 for r in dest_packets if r["loss_reason"] in ("link_loss", "timeout", "other"))
            traffic_stats[dest] = {
                "packets": len(dest_packets),
                "delivered": len(delivered),
                "dropped_packets": sum(1 for r in dest_packets if r["status"] != "delivered"),
                "dropped_loss": dropped_loss,
                "dropped_ttl": dropped_ttl,
                "acl_blocked": sum(1 for r in dest_packets if r["loss_reason"] == "acl_blocked"),
                "dropped": dropped_loss + dropped_ttl,
                "delivery_rate": round((len(delivered) / len(dest_packets)) * 100, 2),
                "avg_delay_ms": self._mean(delays),
                "avg_hops": self._mean([int(r["effective_hops"]) for r in traversed]),
                "percentage": round((len(dest_packets) / len(self.records)) * 100, 2),
            }

        return traffic_stats

    def get_loss_breakdown(self) -> Dict[str, Any]:
        if not self.records:
            return {}

        loss_breakdown = {
            "delivered": sum(1 for r in self.records if r["status"] == "delivered"),
            "dropped_loss": sum(1 for r in self.records if r["loss_reason"] not in ("none", "ttl_exceeded", "acl_blocked") and r["status"] != "delivered"),
            "dropped_ttl": sum(1 for r in self.records if r["loss_reason"] == "ttl_exceeded"),
            "acl_blocked": sum(1 for r in self.records if r["loss_reason"] == "acl_blocked"),
        }

        total = sum(loss_breakdown.values())
        if total > 0:
            loss_breakdown["percentages"] = {
                k: round((v / total) * 100, 2) for k, v in loss_breakdown.items()
            }

        return loss_breakdown

    def get_hop_distribution(self) -> Dict[int, int]:
        if not self.records:
            return {}

        counts = defaultdict(int)
        for r in self.records:
            counts[int(r["effective_hops"])] += 1
        return dict(sorted(counts.items()))

    def get_delay_distribution(self) -> Dict[int, Any]:
        if not self.records:
            return {}

        delay_dist = {}
        all_vlans = sorted(
            {
                int(v)
                for r in self.records
                for v in (r["src_vlan"], r["dst_vlan"])
                if v not in (None, "")
            }
        )

        for vlan in all_vlans:
            vlan_packets = self._records_for_vlan(vlan)
            if not vlan_packets:
                continue
            delays = [float(r["effective_delay_ms"]) for r in vlan_packets]
            delay_dist[vlan] = {
                "min": round(min(delays), 2) if delays else 0,
                "q1": self._quantile(delays, 0.25),
                "median": self._quantile(delays, 0.50),
                "q3": self._quantile(delays, 0.75),
                "max": round(max(delays), 2) if delays else 0,
                "mean": self._mean(delays),
            }

        return delay_dist

    def get_temporal_data(self) -> Dict[float, int]:
        if not self.records:
            return {}

        delivered = [r for r in self.records if r["status"] == "delivered"]
        if not delivered:
            return {}

        per_timestamp = defaultdict(int)
        for r in delivered:
            per_timestamp[float(r["timestamp"])] += 1

        cumulative = {}
        total = 0
        for ts in sorted(per_timestamp.keys()):
            total += per_timestamp[ts]
            cumulative[ts] = total
        return cumulative

    def get_device_pair_communication(self) -> Dict[str, Dict[str, int]]:
        if not self.records:
            return {}

        comm_matrix = defaultdict(lambda: defaultdict(int))
        for r in self.records:
            comm_matrix[r["src_name"]][r["dst_name"]] += 1
        return {src: dict(dests) for src, dests in comm_matrix.items()}

    def _get_loss_reasons(self, packets: List[Dict[str, Any]]) -> Dict[str, int]:
        reasons = defaultdict(int)
        for r in packets:
            if r["status"] != "delivered":
                reasons[r["loss_reason"]] += 1
        return dict(reasons)

    def _empty_stats(self) -> Dict[str, Any]:
        return {
            "total_packets": 0,
            "delivered_packets": 0,
            "dropped_packets": 0,
            "dropped_loss_packets": 0,
            "dropped_ttl_packets": 0,
            "acl_blocked_packets": 0,
            "delivery_rate": 0,
            "avg_delay_ms": 0,
            "std_delay_ms": 0,
            "min_delay_ms": 0,
            "max_delay_ms": 0,
            "avg_hops": 0,
            "min_hops": 0,
            "max_hops": 0,
        }
