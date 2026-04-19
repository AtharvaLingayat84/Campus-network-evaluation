"""
Packet Collection Wrapper
==========================
Extends the CampusNetwork to collect packet-level data for analysis and export.
Each packet is tracked with full attributes: timestamp, src/dst, VLANs, delay, hops, status, loss_reason.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PacketRecord:
    """
    Complete packet record with all attributes needed for analysis.
    """

    # Identification
    src_name: str
    dst_name: str
    src_ip: str
    dst_ip: str

    # Network attributes
    src_type: str = ""
    dst_type: str = ""
    src_vlan: int = 0
    dst_vlan: int = 0

    # Size and timing
    size: int = 1500
    timestamp: float = 0.0
    delay_ms: float = 0.0

    # Routing
    hops: int = 0
    path: list = field(default_factory=list)

    # Status tracking
    status: str = "pending"  # pending, delivered, dropped
    loss_reason: str = "none"  # link_loss, ttl_exceeded, acl_blocked, timeout, none

    def __repr__(self):
        return f"PacketRecord({self.src_name}->{self.dst_name} {self.status})"


class PacketCollector:
    """
    Collects packet-level data during simulation for later analysis.
    """

    def __init__(self):
        self.packets = []

    def record_sent(
        self,
        src_name: str,
        src_ip: str,
        dst_name: str,
        dst_ip: str,
        src_type: str,
        dst_type: str,
        src_vlan: int,
        dst_vlan: int,
        size: int = 1500,
        timestamp: float = 0.0,
    ) -> PacketRecord:
        """
        Record a packet being sent.

        Returns:
            PacketRecord for tracking through delivery/drop
        """
        pkt = PacketRecord(
            src_name=src_name,
            src_ip=src_ip,
            dst_name=dst_name,
            dst_ip=dst_ip,
            src_type=src_type,
            dst_type=dst_type,
            src_vlan=src_vlan,
            dst_vlan=dst_vlan,
            size=size,
            timestamp=timestamp,
            status="pending",
        )
        self.packets.append(pkt)
        return pkt

    def record_delivered(
        self, pkt_record: PacketRecord, delay_ms: float, hops: int, path: list
    ):
        """Record successful packet delivery."""
        pkt_record.status = "delivered"
        pkt_record.delay_ms = delay_ms
        pkt_record.hops = hops
        pkt_record.path = path
        pkt_record.loss_reason = "none"

    def record_dropped(
        self,
        pkt_record: PacketRecord,
        reason: str,
        delay_ms: float = 0.0,
        hops: int = 0,
    ):
        """
        Record packet drop.

        Args:
            pkt_record: Packet to mark as dropped
            reason: Loss reason - 'link_loss', 'ttl_exceeded', 'acl_blocked', 'timeout', etc.
            delay_ms: Delay before drop (if applicable)
            hops: Hops traveled before drop
        """
        pkt_record.status = "dropped"
        pkt_record.loss_reason = reason
        pkt_record.delay_ms = delay_ms
        pkt_record.hops = hops

    def get_packets(self):
        """Return all collected packets."""
        return self.packets

    def get_stats(self):
        """Get quick statistics on collected packets."""
        if not self.packets:
            return {}

        total = len(self.packets)
        delivered = len([p for p in self.packets if p.status == "delivered"])
        dropped = total - delivered

        delivered_packets = [p for p in self.packets if p.status == "delivered"]
        avg_delay = (
            sum(p.delay_ms for p in delivered_packets) / len(delivered_packets)
            if delivered_packets
            else 0
        )
        avg_hops = (
            sum(p.hops for p in delivered_packets) / len(delivered_packets)
            if delivered_packets
            else 0
        )

        return {
            "total": total,
            "delivered": delivered,
            "dropped": dropped,
            "delivery_rate": round((delivered / total * 100), 2) if total > 0 else 0,
            "avg_delay_ms": round(avg_delay, 2),
            "avg_hops": round(avg_hops, 2),
        }
