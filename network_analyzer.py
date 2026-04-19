"""
Network Analyzer Module
=======================
Computes detailed analytics on simulation results including per-VLAN, per-device,
and per-traffic-type breakdowns. Provides comprehensive statistical aggregation
for reporting and visualization.

Classes:
    NetworkAnalyzer - Main class for network analysis
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from collections import defaultdict


class NetworkAnalyzer:
    """
    Performs detailed network analytics on simulation packet data.

    Attributes:
        df (pd.DataFrame): Packet-level data from simulation
        packets (list): Original packet objects for reference
    """

    def __init__(self, packets: List[Any]):
        """
        Initialize NetworkAnalyzer with packet data.

        Args:
            packets: List of Packet objects with all attributes
        """
        self.packets = packets
        self.df = self._packets_to_dataframe(packets)

    def _packets_to_dataframe(self, packets: List[Any]) -> pd.DataFrame:
        """Convert packet list to DataFrame."""
        data = []
        for pkt in packets:
            data.append(
                {
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
                    "loss_reason": getattr(pkt, "loss_reason", "none"),
                }
            )

        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_overall_stats(self) -> Dict[str, Any]:
        """
        Get overall network statistics.

        Returns:
            Dictionary with overall metrics (packets, delivery rate, delay, etc.)
        """
        if len(self.df) == 0:
            return self._empty_stats()

        delivered = len(self.df[self.df["status"] == "delivered"])
        total = len(self.df)

        return {
            "total_packets": total,
            "delivered_packets": delivered,
            "dropped_packets": total - delivered,
            "delivery_rate": round((delivered / total) * 100, 2) if total > 0 else 0,
            "avg_delay_ms": round(self.df["delay_ms"].mean(), 2),
            "std_delay_ms": round(self.df["delay_ms"].std(), 2),
            "min_delay_ms": round(self.df["delay_ms"].min(), 2),
            "max_delay_ms": round(self.df["delay_ms"].max(), 2),
            "avg_hops": round(self.df["hops"].mean(), 2),
            "min_hops": int(self.df["hops"].min()),
            "max_hops": int(self.df["hops"].max()),
        }

    def get_vlan_statistics(self) -> pd.DataFrame:
        """
        Get per-VLAN statistics.

        Returns:
            DataFrame with columns: vlan, packets_total, packets_delivered,
                                   packets_lost, delivery_rate, avg_delay_ms,
                                   avg_hops, loss_reasons
        """
        if len(self.df) == 0:
            return pd.DataFrame()

        vlan_stats = []

        # Consider both source and destination VLANs
        all_vlans = set(self.df["src_vlan"].dropna()) | set(
            self.df["dst_vlan"].dropna()
        )

        for vlan in sorted(all_vlans):
            if pd.isna(vlan):
                continue

            vlan_packets = self.df[
                (self.df["src_vlan"] == vlan) | (self.df["dst_vlan"] == vlan)
            ]

            if len(vlan_packets) == 0:
                continue

            delivered = len(vlan_packets[vlan_packets["status"] == "delivered"])
            delivery_rate = (
                (delivered / len(vlan_packets)) * 100 if len(vlan_packets) > 0 else 0
            )

            vlan_stats.append(
                {
                    "vlan": int(vlan),
                    "packets_total": len(vlan_packets),
                    "packets_delivered": delivered,
                    "packets_lost": len(
                        vlan_packets[vlan_packets["status"] != "delivered"]
                    ),
                    "delivery_rate": round(delivery_rate, 2),
                    "avg_delay_ms": round(vlan_packets["delay_ms"].mean(), 2),
                    "avg_hops": round(vlan_packets["hops"].mean(), 2),
                    "loss_reasons": self._get_loss_reasons(vlan_packets),
                }
            )

        return pd.DataFrame(vlan_stats)

    def get_device_statistics(self) -> pd.DataFrame:
        """
        Get per-device statistics for major devices.

        Returns:
            DataFrame with columns: device, device_type, vlan, packets_sent,
                                   packets_delivered, delivery_rate, avg_delay_ms,
                                   primary_destinations
        """
        if len(self.df) == 0:
            return pd.DataFrame()

        device_stats = []

        # Get all sending devices
        all_devices = self.df["src_name"].unique()

        for device in all_devices:
            device_packets = self.df[self.df["src_name"] == device]

            if len(device_packets) == 0:
                continue

            delivered = len(device_packets[device_packets["status"] == "delivered"])
            delivery_rate = (
                (delivered / len(device_packets)) * 100
                if len(device_packets) > 0
                else 0
            )

            # Get primary destinations
            primary_destinations = list(
                device_packets["dst_name"].value_counts().head(3).index
            )

            device_stats.append(
                {
                    "device": device,
                    "device_type": device_packets["src_type"].iloc[0]
                    if len(device_packets) > 0
                    else "Unknown",
                    "vlan": device_packets["src_vlan"].iloc[0]
                    if len(device_packets) > 0
                    else None,
                    "packets_sent": len(device_packets),
                    "packets_delivered": delivered,
                    "delivery_rate": round(delivery_rate, 2),
                    "avg_delay_ms": round(device_packets["delay_ms"].mean(), 2),
                    "primary_destinations": ", ".join(primary_destinations),
                }
            )

        return pd.DataFrame(device_stats)

    def get_traffic_type_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get per-traffic-type statistics (by destination server).

        Returns:
            Dictionary with statistics for each traffic type
        """
        if len(self.df) == 0:
            return {}

        traffic_stats = {}

        # Extract traffic type from destination name
        destinations = self.df["dst_name"].unique()

        for dest in destinations:
            dest_packets = self.df[self.df["dst_name"] == dest]

            if len(dest_packets) == 0:
                continue

            delivered = len(dest_packets[dest_packets["status"] == "delivered"])
            delivery_rate = (
                (delivered / len(dest_packets)) * 100 if len(dest_packets) > 0 else 0
            )

            traffic_stats[dest] = {
                "packets": len(dest_packets),
                "delivered": delivered,
                "dropped": len(dest_packets[dest_packets["status"] != "delivered"]),
                "delivery_rate": round(delivery_rate, 2),
                "avg_delay_ms": round(dest_packets["delay_ms"].mean(), 2),
                "avg_hops": round(dest_packets["hops"].mean(), 2),
                "percentage": round((len(dest_packets) / len(self.df)) * 100, 2),
            }

        return traffic_stats

    def get_loss_breakdown(self) -> Dict[str, Any]:
        """
        Get packet loss breakdown by reason.

        Returns:
            Dictionary with loss reason counts and percentages
        """
        if len(self.df) == 0:
            return {}

        loss_breakdown = {
            "delivered": len(self.df[self.df["status"] == "delivered"]),
            "link_loss": len(self.df[self.df["loss_reason"] == "link_loss"]),
            "ttl_exceeded": len(self.df[self.df["loss_reason"] == "ttl_exceeded"]),
            "acl_blocked": len(self.df[self.df["loss_reason"] == "acl_blocked"]),
            "timeout": len(self.df[self.df["loss_reason"] == "timeout"]),
            "other": len(self.df[self.df["loss_reason"] == "other"]),
        }

        total = sum(loss_breakdown.values())
        if total > 0:
            loss_breakdown["percentages"] = {
                k: round((v / total) * 100, 2) for k, v in loss_breakdown.items()
            }

        return loss_breakdown

    def get_hop_distribution(self) -> Dict[int, int]:
        """
        Get distribution of hop counts.

        Returns:
            Dictionary mapping hop count to frequency
        """
        if len(self.df) == 0:
            return {}

        hop_counts = self.df["hops"].value_counts().to_dict()
        return {int(k): v for k, v in sorted(hop_counts.items())}

    def get_delay_distribution(self) -> Dict[int, Any]:
        """
        Get delay statistics per VLAN.

        Returns:
            Dictionary with delay statistics for each VLAN
        """
        if len(self.df) == 0:
            return {}

        delay_dist = {}
        all_vlans = set(self.df["src_vlan"].dropna()) | set(
            self.df["dst_vlan"].dropna()
        )

        for vlan in sorted(all_vlans):
            if pd.isna(vlan):
                continue

            vlan_packets = self.df[
                (self.df["src_vlan"] == vlan) | (self.df["dst_vlan"] == vlan)
            ]

            if len(vlan_packets) == 0:
                continue

            delays = vlan_packets["delay_ms"].dropna()

            delay_dist[int(vlan)] = {
                "min": round(delays.min(), 2) if len(delays) > 0 else 0,
                "q1": round(delays.quantile(0.25), 2) if len(delays) > 0 else 0,
                "median": round(delays.median(), 2) if len(delays) > 0 else 0,
                "q3": round(delays.quantile(0.75), 2) if len(delays) > 0 else 0,
                "max": round(delays.max(), 2) if len(delays) > 0 else 0,
                "mean": round(delays.mean(), 2) if len(delays) > 0 else 0,
            }

        return delay_dist

    def get_temporal_data(self) -> Dict[float, int]:
        """
        Get cumulative packet delivery over time.

        Returns:
            Dictionary mapping timestamp to cumulative packet count
        """
        if len(self.df) == 0:
            return {}

        # Filter only delivered packets
        delivered = self.df[self.df["status"] == "delivered"].copy()

        if len(delivered) == 0:
            return {}

        # Sort by timestamp
        delivered = delivered.sort_values("timestamp")

        # Create cumulative count
        temporal_data = {}
        for idx, row in delivered.iterrows():
            ts = row["timestamp"]
            temporal_data[ts] = temporal_data.get(ts, 0) + 1

        # Convert to cumulative
        cumulative = {}
        total = 0
        for ts in sorted(temporal_data.keys()):
            total += temporal_data[ts]
            cumulative[ts] = total

        return cumulative

    def get_device_pair_communication(self) -> Dict[str, Dict[str, int]]:
        """
        Get communication volume between device pairs.

        Returns:
            Dictionary mapping (src, dst) to packet count
        """
        if len(self.df) == 0:
            return {}

        comm_matrix = defaultdict(lambda: defaultdict(int))

        for _, row in self.df.iterrows():
            src = row["src_name"]
            dst = row["dst_name"]
            comm_matrix[src][dst] += 1

        # Convert to regular dict
        return {src: dict(dests) for src, dests in comm_matrix.items()}

    def _get_loss_reasons(self, packets_df: pd.DataFrame) -> Dict[str, int]:
        """Get loss reason breakdown for a subset of packets."""
        if len(packets_df) == 0:
            return {}
        return (
            packets_df[packets_df["status"] != "delivered"]["loss_reason"]
            .value_counts()
            .to_dict()
        )

    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty stats structure."""
        return {
            "total_packets": 0,
            "delivered_packets": 0,
            "dropped_packets": 0,
            "delivery_rate": 0,
            "avg_delay_ms": 0,
            "std_delay_ms": 0,
            "min_delay_ms": 0,
            "max_delay_ms": 0,
            "avg_hops": 0,
            "min_hops": 0,
            "max_hops": 0,
        }
