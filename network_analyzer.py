"""Network Analyzer Module
=======================

Computes detailed analytics on simulation results using plain Python data
structures. This keeps the reporting and visualization pipeline lightweight.
"""

from __future__ import annotations

from collections import defaultdict
import logging
from statistics import mean, pstdev
from typing import Any, Dict, List


logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """Performs detailed network analytics on simulation packet data."""

    def __init__(self, packets: List[Any]):
        self.packets = packets
        self.records = [self._packet_to_record(pkt) for pkt in packets]

    def _delivered_packets(self) -> List[Dict[str, Any]]:
        return [r for r in self.records if r["status"] == "delivered"]

    def _dropped_packets(self) -> List[Dict[str, Any]]:
        return [r for r in self.records if r["status"] != "delivered" and r["loss_reason"] != "acl_blocked"]

    def _acl_blocked_packets(self) -> List[Dict[str, Any]]:
        return [r for r in self.records if r["loss_reason"] == "acl_blocked"]

    def _delivery_delay_records(self) -> List[Dict[str, Any]]:
        return self._delivered_packets()

    def _hop_value(self, record: Dict[str, Any]) -> int:
        value = record.get("effective_hops", record.get("hops", 0))
        return int(value or 0)

    def _delay_value(self, record: Dict[str, Any]) -> float:
        return float(record.get("effective_delay_ms", record.get("delay_ms", 0.0)) or 0.0)

    def _validate_subset(self, label: str, records: List[Dict[str, Any]]) -> None:
        if not self.records:
            logger.warning("No packet records available for analysis")
            return
        if not records:
            if label in {"acl_blocked", "hop:acl_blocked"}:
                return
            logger.warning("Subset '%s' is empty", label)
            return
        logger.debug("Subset '%s': %d records", label, len(records))
        logger.debug("Subset '%s' sample: %s", label, records[:2])

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

        outcomes = self.get_packet_outcomes()
        delay_stats = self.get_delay_stats()

        return {
            "total_packets": outcomes["counts"]["total_packets"],
            "delivered_packets": outcomes["counts"]["delivered"],
            "dropped_packets": outcomes["counts"]["dropped_total"],
            "dropped_loss_packets": outcomes["counts"]["dropped_loss"],
            "dropped_ttl_packets": outcomes["counts"]["dropped_ttl"],
            "acl_blocked_packets": outcomes["counts"]["acl_blocked"],
            "delivery_rate": outcomes["percentages"]["delivered"],
            "avg_delay_ms": delay_stats["overall"]["avg_delay_ms"],
            "std_delay_ms": delay_stats["overall"]["std_delay_ms"],
            "min_delay_ms": delay_stats["overall"]["min_delay_ms"],
            "max_delay_ms": delay_stats["overall"]["max_delay_ms"],
            "avg_hops": delay_stats["overall"]["avg_hops"],
            "min_hops": delay_stats["overall"]["min_hops"],
            "max_hops": delay_stats["overall"]["max_hops"],
        }

    def get_packet_outcomes(self) -> Dict[str, Any]:
        if not self.records:
            return {
                "counts": {"total_packets": 0, "delivered": 0, "dropped_loss": 0, "dropped_ttl": 0, "acl_blocked": 0, "dropped_total": 0},
                "percentages": {"delivered": 0, "dropped_loss": 0, "dropped_ttl": 0, "acl_blocked": 0, "dropped_total": 0},
            }

        delivered = self._delivered_packets()
        dropped = self._dropped_packets()
        acl_blocked = self._acl_blocked_packets()

        dropped_ttl = [r for r in dropped if r["loss_reason"] == "ttl_exceeded"]
        dropped_loss = [r for r in dropped if r["loss_reason"] in ("link_loss", "timeout", "other")]
        total = len(self.records)
        dropped_total = len(dropped) + len(acl_blocked)

        result = {
            "counts": {
                "total_packets": total,
                "delivered": len(delivered),
                "dropped_loss": len(dropped_loss),
                "dropped_ttl": len(dropped_ttl),
                "acl_blocked": len(acl_blocked),
                "dropped_total": dropped_total,
            },
            "percentages": {
                "delivered": round((len(delivered) / total) * 100, 2) if total else 0,
                "dropped_loss": round((len(dropped_loss) / total) * 100, 2) if total else 0,
                "dropped_ttl": round((len(dropped_ttl) / total) * 100, 2) if total else 0,
                "acl_blocked": round((len(acl_blocked) / total) * 100, 2) if total else 0,
                "dropped_total": round((dropped_total / total) * 100, 2) if total else 0,
            },
        }

        # Backward-compatible flat keys for existing callers.
        result.update({
            "total_packets": total,
            "delivered": len(delivered),
            "dropped_loss": len(dropped_loss),
            "dropped_ttl": len(dropped_ttl),
            "acl_blocked": len(acl_blocked),
            "dropped_packets": dropped_total,
            "delivery_rate": result["percentages"]["delivered"],
        })

        self._validate_subset("delivered", delivered)
        self._validate_subset("dropped", dropped)
        self._validate_subset("acl_blocked", acl_blocked)
        return result

    def _hop_distribution_for(self, kind: str) -> Dict[int, int]:
        """Return hop counts for a specific subset.

        kind: delivered | dropped | acl_blocked
        """
        if not self.records:
            return {}

        if kind == "delivered":
            subset = self._delivered_packets()
        elif kind == "dropped":
            subset = self._dropped_packets()
        elif kind == "acl_blocked":
            subset = self._acl_blocked_packets()
        else:
            raise ValueError(f"Unknown hop distribution kind: {kind}")

        self._validate_subset(f"hop:{kind}", subset)

        counts = defaultdict(int)
        for r in subset:
            counts[self._hop_value(r)] += 1
        return dict(sorted(counts.items()))

    def get_hop_distribution(self, kind: str = "delivered") -> Dict[int, int]:
        """Backward-compatible hop distribution API.

        Default behavior returns delivered-packet hops so existing plots keep working.
        """
        return self._hop_distribution_for(kind)

    def get_hop_distributions(self) -> Dict[str, Dict[int, int]]:
        """Return delivered, dropped, and ACL-blocked hop distributions."""
        return {
            "delivered": self._hop_distribution_for("delivered"),
            "dropped": self._hop_distribution_for("dropped"),
            "acl_blocked": self._hop_distribution_for("acl_blocked"),
        }

    def get_delay_stats(self) -> Dict[str, Any]:
        """Return delay statistics for delivered packets only."""
        delivered = self._delivered_packets()
        self._validate_subset("delay:delivered", delivered)

        delays = [self._delay_value(r) for r in delivered]
        hops = [self._hop_value(r) for r in delivered]

        per_vlan = {}
        for vlan in sorted({int(v) for r in delivered for v in (r["src_vlan"], r["dst_vlan"]) if v not in (None, "")}):
            vlan_delivered = [r for r in delivered if r["src_vlan"] == vlan or r["dst_vlan"] == vlan]
            vlan_delays = [self._delay_value(r) for r in vlan_delivered]
            vlan_hops = [self._hop_value(r) for r in vlan_delivered]
            per_vlan[vlan] = {
                "delivered_packets": len(vlan_delivered),
                "avg_delay_ms": self._mean(vlan_delays),
                "std_delay_ms": self._std(vlan_delays),
                "min_delay_ms": round(min(vlan_delays), 2) if vlan_delays else 0,
                "max_delay_ms": round(max(vlan_delays), 2) if vlan_delays else 0,
                "avg_hops": self._mean(vlan_hops),
            }

        return {
            "overall": {
                "count": len(delivered),
                "avg_delay_ms": self._mean(delays),
                "std_delay_ms": self._std(delays),
                "min_delay_ms": round(min(delays), 2) if delays else 0,
                "max_delay_ms": round(max(delays), 2) if delays else 0,
                "avg_hops": self._mean(hops),
                "min_hops": min(hops) if hops else 0,
                "max_hops": max(hops) if hops else 0,
            },
            "per_vlan": per_vlan,
        }

    def get_vlan_statistics(self) -> List[Dict[str, Any]]:
        return self.get_vlan_stats()

    def get_vlan_stats(self) -> List[Dict[str, Any]]:
        """Return per-VLAN generated, delivered, and failure metrics.

        Traffic is grouped by source VLAN so the numbers reflect traffic generated
        by that VLAN rather than unrelated transit traffic.
        """
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
            generated = [r for r in self.records if r["src_vlan"] == vlan]
            delivered = [r for r in generated if r["status"] == "delivered"]
            failed = [r for r in generated if r["status"] != "delivered"]
            acl_blocked = [r for r in generated if r["loss_reason"] == "acl_blocked"]
            ttl_drops = [r for r in generated if r["loss_reason"] == "ttl_exceeded"]
            loss_drops = [r for r in generated if r["loss_reason"] in ("link_loss", "timeout", "other")]

            delays = [self._delay_value(r) for r in delivered]
            hops = [self._hop_value(r) for r in delivered]
            generated_total = len(generated)
            success_rate = round((len(delivered) / generated_total) * 100, 2) if generated_total else 0
            failure_rate = round((len(failed) / generated_total) * 100, 2) if generated_total else 0

            vlan_stats.append(
                {
                    "vlan": vlan,
                    "generated_packets": generated_total,
                    "successful_packets": len(delivered),
                    "failed_packets": len(failed),
                    "success_rate": success_rate,
                    "failure_rate": failure_rate,
                    "packets_total": generated_total,
                    "packets_delivered": len(delivered),
                    "dropped_packets": len(failed),
                    "dropped_loss": len(loss_drops),
                    "dropped_ttl": len(ttl_drops),
                    "acl_blocked": len(acl_blocked),
                    "packets_lost": len(loss_drops) + len(ttl_drops),
                    "delivery_rate": success_rate,
                    "avg_delay_ms": self._mean(delays),
                    "avg_hops": self._mean(hops),
                    "loss_reasons": self._get_loss_reasons(generated),
                }
            )

            self._validate_subset(f"vlan:{vlan}", generated)

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
            traversed = delivered
            delays = [self._delay_value(r) for r in traversed]
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
            traversed = delivered
            delays = [self._delay_value(r) for r in traversed]
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
                "avg_hops": self._mean([self._hop_value(r) for r in traversed]),
                "percentage": round((len(dest_packets) / len(self.records)) * 100, 2),
            }

        return traffic_stats

    def get_loss_breakdown(self) -> Dict[str, Any]:
        outcomes = self.get_packet_outcomes()
        return {
            "delivered": outcomes["counts"]["delivered"],
            "dropped_loss": outcomes["counts"]["dropped_loss"],
            "dropped_ttl": outcomes["counts"]["dropped_ttl"],
            "acl_blocked": outcomes["counts"]["acl_blocked"],
            "dropped_packets": outcomes["counts"]["dropped_total"],
            "percentages": outcomes["percentages"],
        }

    def get_delay_distribution(self) -> Dict[int, Any]:
        return self.get_delay_stats()["per_vlan"]

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
