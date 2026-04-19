"""
Data Exporter Module
====================
Exports simulation results to structured formats (CSV, JSON, Pickle) for external
analysis and archival. Converts packet-level data and aggregated metrics to various
output formats.

Classes:
    DataExporter - Main class for exporting simulation data
"""

import pandas as pd
import json
import pickle
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


class DataExporter:
    """
    Exports network simulation results to multiple formats.

    Attributes:
        packets (list): List of packet objects from simulation
        results (dict): Aggregated results from simulation runs
        output_dir (str): Directory for saving export files
    """

    def __init__(
        self, packets: List[Any], results: Dict[str, Any], output_dir: str = "./output"
    ):
        """
        Initialize DataExporter with simulation data.

        Args:
            packets: List of Packet objects with src_ip, dst_ip, src_type, dst_type,
                    src_vlan, dst_vlan, bytes, delay_ms, hops, status, loss_reason, timestamp
            results: Dictionary with aggregated simulation results
            output_dir: Directory to save exports to
        """
        self.packets = packets
        self.results = results
        self.output_dir = output_dir

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Convert packets to DataFrame for easier manipulation
        self.df = self._packets_to_dataframe(packets)

    def _packets_to_dataframe(self, packets: List[Any]) -> pd.DataFrame:
        """
        Convert packet list to Pandas DataFrame.

        Args:
            packets: List of packet objects

        Returns:
            DataFrame with columns: timestamp, src_ip, dst_ip, src_type, dst_type,
                                   src_vlan, dst_vlan, bytes, delay_ms, hops,
                                   status, loss_reason
        """
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

        return pd.DataFrame(data)

    def to_csv(self, filename: Optional[str] = None, mode: str = "normal") -> str:
        """
        Export packet-level data to CSV format.

        Args:
            filename: Output filename (if None, uses default with timestamp)
            mode: Simulation mode ("normal" or "exam")

        Returns:
            Path to created CSV file
        """
        if filename is None:
            filename = f"simulation_results_{mode}.csv"

        filepath = os.path.join(self.output_dir, filename)
        self.df.to_csv(filepath, index=False)

        print(f"[OK] CSV export: {filepath}")
        return filepath

    def to_json(self, filename: str = "simulation_summary.json") -> str:
        """
        Export summary metrics to JSON format.

        Includes:
        - Top-level metrics (total packets, delivery rate, avg delay, avg hops)
        - Per-VLAN breakdown
        - Per-device breakdown (major devices)
        - Per-traffic-type breakdown
        - Loss reason breakdown

        Args:
            filename: Output filename

        Returns:
            Path to created JSON file
        """
        filepath = os.path.join(self.output_dir, filename)

        # Prepare JSON structure
        json_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_packets": len(self.df),
                "delivered_packets": len(self.df[self.df["status"] == "delivered"]),
                "dropped_packets": len(self.df[self.df["status"] != "delivered"]),
                "delivery_rate": self._calc_delivery_rate(),
                "avg_delay_ms": self.df["delay_ms"].mean(),
                "avg_hops": self.df["hops"].mean(),
                "max_delay_ms": self.df["delay_ms"].max(),
                "min_delay_ms": self.df["delay_ms"].min(),
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
        """
        Export full data structures to Pickle format for fast re-analysis.

        Args:
            filename: Output filename

        Returns:
            Path to created pickle file
        """
        filepath = os.path.join(self.output_dir, filename)

        data = {
            "packets": self.packets,
            "dataframe": self.df,
            "results": self.results,
            "timestamp": datetime.now().isoformat(),
        }

        with open(filepath, "wb") as f:
            pickle.dump(data, f)

        print(f"[OK] Pickle export: {filepath}")
        return filepath

    def _calc_delivery_rate(self) -> float:
        """Calculate overall packet delivery rate (%)."""
        if len(self.df) == 0:
            return 0.0
        delivered = len(self.df[self.df["status"] == "delivered"])
        return (delivered / len(self.df)) * 100

    def _calc_vlan_stats(self) -> Dict[int, Dict[str, Any]]:
        """Calculate per-VLAN statistics."""
        vlan_stats = {}

        # Consider both source and destination VLANs
        all_vlans = set(self.df["src_vlan"].dropna()) | set(
            self.df["dst_vlan"].dropna()
        )

        for vlan in sorted(all_vlans):
            if pd.isna(vlan):
                continue

            # Packets with this VLAN as source or destination
            vlan_packets = self.df[
                (self.df["src_vlan"] == vlan) | (self.df["dst_vlan"] == vlan)
            ]

            if len(vlan_packets) == 0:
                continue

            delivered = len(vlan_packets[vlan_packets["status"] == "delivered"])
            delivery_rate = (
                (delivered / len(vlan_packets)) * 100 if len(vlan_packets) > 0 else 0
            )

            vlan_stats[int(vlan)] = {
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

        return vlan_stats

    def _calc_device_stats(self) -> Dict[str, Dict[str, Any]]:
        """Calculate per-device statistics for major devices (servers, routers)."""
        device_stats = {}

        # Focus on major devices (servers and key infrastructure)
        major_devices = self.df[
            self.df["src_type"].isin(["Server", "Router", "Switch"])
        ]["src_name"].unique()

        for device in major_devices:
            device_packets = self.df[self.df["src_name"] == device]

            if len(device_packets) == 0:
                continue

            delivered = len(device_packets[device_packets["status"] == "delivered"])
            delivery_rate = (
                (delivered / len(device_packets)) * 100
                if len(device_packets) > 0
                else 0
            )

            device_stats[device] = {
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
                "primary_destinations": list(
                    device_packets["dst_name"].value_counts().head(5).index
                ),
            }

        return device_stats

    def _calc_traffic_type_stats(self) -> Dict[str, Dict[str, Any]]:
        """Calculate per-traffic-type statistics (based on destination)."""
        traffic_stats = {}

        server_names = ["Exam Server", "Email Server", "Cloud Server", "Internet GW"]

        for server in server_names:
            server_packets = self.df[
                self.df["dst_name"].str.contains(server, case=False, na=False)
            ]

            if len(server_packets) == 0:
                traffic_stats[server] = {
                    "packets": 0,
                    "delivery_rate": 0,
                    "avg_delay_ms": 0,
                    "percentage": 0,
                }
                continue

            delivered = len(server_packets[server_packets["status"] == "delivered"])
            delivery_rate = (
                (delivered / len(server_packets)) * 100
                if len(server_packets) > 0
                else 0
            )

            traffic_stats[server] = {
                "packets": len(server_packets),
                "delivered": delivered,
                "delivery_rate": round(delivery_rate, 2),
                "avg_delay_ms": round(server_packets["delay_ms"].mean(), 2),
                "percentage": round((len(server_packets) / len(self.df)) * 100, 2),
            }

        return traffic_stats

    def _calc_loss_breakdown(self) -> Dict[str, Any]:
        """Calculate packet loss breakdown by reason."""
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

    def _calc_hop_distribution(self) -> Dict[int, int]:
        """Calculate distribution of hop counts."""
        hop_counts = self.df["hops"].value_counts().to_dict()
        return {int(k): v for k, v in sorted(hop_counts.items())}

    def _get_loss_reasons(self, packets_df: pd.DataFrame) -> Dict[str, int]:
        """Get loss reason breakdown for a subset of packets."""
        return packets_df["loss_reason"].value_counts().to_dict()
